"""Composition of the accepted components into the v1 collection protocol.

This module connects contracts, locking, providers, normalization, policy,
faults, assessment, evidence and replay (plan/CONTRACTS.md section 7). It
reimplements none of them. Its only execution constants are the fixed
30.0-second request deadline (``REQUEST_TIMEOUT_S``) and the provider's own
120-second startup bound; both are source bytes covered by the implementation
fingerprint (ADR 0008), and no function here accepts a deadline override.

Protocol:

* ``lock``: read and validate the contract and both raw splits, build the
  provider, observe its actual identity, close it, seal a lock and write the
  lock document exclusively to a new file.
* ``verify``: read the lock structurally, validate seal/compatibility/inputs,
  check the requested provider against the locked provider, require the EXACT
  running implementation fingerprint (a lock that is merely replay-compatible
  may be replayed but never collected against), build the provider, compare
  its COMPLETE observed identity with the locked identity,
  capture every locked verification case exactly once in lock order, run the
  six-scenario fault campaign, assess, and publish one new evidence bundle.
  Every provider is closed in a ``finally`` block, including identity and
  publication failures. Setup errors propagate: an incomplete run never
  becomes a bundle. Captured failures (including a regular Laya timeout or
  unavailable) are terminal records that stay in the evidence; assessment
  decides their meaning (ADR 0009) and the run never restarts or retries.
* ``demo``: copy the packaged ADR 0013 inputs into a caller-requested new
  directory, run ``lock`` and ``verify`` for the deliberately bad and the fixed
  fixture, replay both bundles with their expected lock digests and report the
  genuine results. No metric is authored here.

Module import loads no adapter: the fixture adapter is imported only inside
the fixture branch of :func:`open_model`, the Laya adapter only inside the
Laya branch and the experimental Jev adapter only inside the Jev branch, so
``replay`` works with optional libraries absent and never loads a transport.

``records.PROVIDERS`` admits every provider a serialized identity may name.
:func:`open_model` constructs only the providers registered in
``_REGISTERED_PROVIDERS``, each through its own explicit branch; an admitted
but unregistered provider fails loudly before any adapter import, so it can
never be routed to Laya by omission. The PROVISIONAL ``jev`` adapter
(plan/v1/CHANGE_LOG.md V1-011, ADR 0017) is registered here: passing the
explicit string ``"jev"`` to :func:`open_model` is the Python opt-in, the
command line additionally requires ``--experimental-provider``, and the
adapter is imported lazily from ``actseal.experimental.providers.jev`` only
when selected. Its constructor rejects ``offline=True`` with
:class:`~actseal.errors.ProviderSetupError` before reading any environment
variable, and reads only ``JEV_API_KEY`` otherwise; this module adds no
fallback, retry or key handling of its own.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from actseal.assessment import assess
from actseal.compatibility import require_exact_implementation
from actseal.contract import parse_cases, parse_contract, read_input_text
from actseal.errors import IntegrityError, ProviderSetupError, SchemaError
from actseal.evidence import write_bundle
from actseal.faults import run_fault_campaign
from actseal.locking import MAX_LOCK_BYTES, create_lock, parse_lock, validate_inputs, validate_lock
from actseal.normalization import normalize
from actseal.policy import evaluate
from actseal.records import (
    PROVIDERS,
    Case,
    DecisionRecord,
    DecisionRequest,
    EvidenceBundle,
    ModelIdentity,
    PlanLock,
    Verdict,
)
from actseal.replay import replay
from actseal.serialization import canonical_json, to_data

if TYPE_CHECKING:
    from actseal.adapters.base import DecisionModel

__all__ = [
    "DEMO_EXPECTED",
    "DEMO_INPUTS_DIRECTORY",
    "DEMO_RUNS",
    "EVIDENCE_DIRECTORY",
    "LOCK_FILE_NAME",
    "REQUEST_TIMEOUT_S",
    "DemoResult",
    "DemoRun",
    "ModelFactory",
    "collect",
    "demo_run",
    "lock_run",
    "open_model",
    "verify_run",
    "write_lock",
]

#: Fixed per-request deadline for every ordinary capture (ADR 0008).
REQUEST_TIMEOUT_S: Final = 30.0

LOCK_FILE_NAME: Final = "lock.json"
EVIDENCE_DIRECTORY: Final = "evidence"
DEMO_INPUTS_DIRECTORY: Final = "inputs"
DEMO_RUNS: Final[tuple[str, ...]] = ("bad", "fixed")
#: The prespecified outcome of each demo run (ADR 0013); success requires both.
DEMO_EXPECTED: Final[dict[str, str]] = {"bad": "BLOCK", "fixed": "PASS"}

_FILE_MODE: Final = 0o644
_LF: Final = b"\n"
#: PROVISIONAL providers (docs/stability.md): constructed only on explicit
#: selection, imported lazily from ``actseal.experimental`` and outside the
#: 1.x stability promise.
_EXPERIMENTAL_PROVIDERS: Final[frozenset[str]] = frozenset({"jev"})
#: Providers this runner can construct, each through its own explicit branch of
#: :func:`open_model`. Must stay a subset of ``records.PROVIDERS``: an admitted
#: provider without a branch here is rejected instead of falling through to Laya.
_REGISTERED_PROVIDERS: Final[frozenset[str]] = frozenset({"fixture", "laya"}) | (
    _EXPERIMENTAL_PROVIDERS
)

ModelFactory = Callable[[], "DecisionModel"]


# --------------------------------------------------------------------------- #
# Provider construction
# --------------------------------------------------------------------------- #


def open_model(provider: str, *, responses: Path | None, offline: bool) -> DecisionModel:
    """Build the requested provider; adapters are imported only inside their branch.

    ``fixture`` requires ``responses``; ``laya`` and the PROVISIONAL ``jev``
    reject it. Selecting ``"jev"`` explicitly is the Python opt-in for the
    experimental adapter; it is imported only in that branch, and
    ``offline=True`` is rejected by its constructor before any environment
    read or request. Every argument check precedes every adapter import.
    """
    if provider not in PROVIDERS:
        raise SchemaError("provider: unsupported value")
    if provider not in _REGISTERED_PROVIDERS:
        # Admitted for serialized identities but not registered with this runner:
        # fail before importing or constructing any adapter. Never route an
        # unregistered provider to Laya.
        raise SchemaError("provider: admitted for records but not registered with the runner")
    if provider == "fixture":
        if responses is None:
            raise SchemaError("responses: required for the fixture provider")
        # ``offline`` is accepted and needs no action: the fixture adapter reads one
        # local file and never touches the network, so it is already offline.
        from actseal.adapters.fixture import FixtureModel  # noqa: PLC0415 - adapter branch only

        return FixtureModel(responses)
    if responses is not None:
        raise SchemaError(f"responses: not accepted by the {provider} provider")
    if provider == "laya":
        from actseal.adapters.laya import LayaModel  # noqa: PLC0415 - adapter branch only

        return LayaModel(offline=offline)
    if provider == "jev":
        # PROVISIONAL (ADR 0017): imported only here, never by replay or at
        # module import. The constructor rejects offline before reading the key.
        from actseal.experimental.providers.jev import (  # noqa: PLC0415 - adapter branch only
            JevModel,
        )

        return JevModel(offline=offline)
    # Unreachable while _REGISTERED_PROVIDERS matches the branches above; kept so
    # a future registration without a branch fails instead of building Laya.
    raise SchemaError("provider: registered without a construction branch")


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


def _check_new_path(field: str, path: Path) -> None:
    """Reject a path that is not a ``Path``, contains NUL or already exists (even dangling)."""
    if not isinstance(path, Path):
        raise SchemaError(f"{field}: must be a Path")
    if "\x00" in os.fspath(path):
        raise SchemaError(f"{field}: must not contain NUL")
    if os.path.lexists(path):
        raise FileExistsError(f"{field}: already exists")
    if not path.parent.is_dir():
        raise SchemaError(f"{field}: parent directory does not exist")


def _write_new_file(path: Path, data: bytes) -> None:
    """Create a new regular file exclusively (never following a symlink) and write ``data``."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(path, flags, _FILE_MODE)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def write_lock(lock: PlanLock, destination: Path) -> Path:
    """Write one canonical lock document plus one LF to the NEW file ``destination``."""
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    _check_new_path("destination", destination)
    validate_lock(lock)
    data = canonical_json(to_data(lock)) + _LF
    if len(data) > MAX_LOCK_BYTES:
        raise SchemaError(f"lock: canonical document exceeds {MAX_LOCK_BYTES} bytes")
    _write_new_file(destination, data)
    return destination


def _read_lock(path: Path) -> PlanLock:
    """Structural decode (bounded at the lock ceiling); callers validate the seal."""
    return parse_lock(read_input_text(path, limit=MAX_LOCK_BYTES))


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #


def collect(
    model: DecisionModel, lock: PlanLock, cases: tuple[Case, ...]
) -> tuple[DecisionRecord, ...]:
    """Capture every case exactly once, in order, at the fixed deadline; never stop early.

    Each capture is normalized against the LOCKED identity and evaluated with
    the locked policy, exactly as assessment and replay will recompute it.
    Captured failures are terminal records; only provider setup errors raise.
    The lock must name the exact running implementation: a foreign producer
    fingerprint is :class:`IntegrityError` before any ``decide`` call, even
    when that fingerprint is registered as replay-compatible.
    """
    if not isinstance(lock, PlanLock):
        raise SchemaError("lock: must be PlanLock")
    require_exact_implementation(lock)
    question = lock.contract.question
    policy = lock.contract.policy
    records: list[DecisionRecord] = []
    for case in cases:
        if not isinstance(case, Case):
            raise SchemaError("cases: must contain Case records")
        request = DecisionRequest(case.case_id, case.state, question)
        capture = model.decide(request, timeout_s=REQUEST_TIMEOUT_S)
        outcome = normalize(capture, question, lock.model_identity)
        decision = evaluate(outcome, policy)
        records.append(DecisionRecord(case.case_id, capture, outcome, decision))
    return tuple(records)


def _observe_identity(model: DecisionModel) -> ModelIdentity:
    identity = model.identity()
    if not isinstance(identity, ModelIdentity):
        raise ProviderSetupError("identity: provider did not report a ModelIdentity")
    return identity


# --------------------------------------------------------------------------- #
# lock / verify
# --------------------------------------------------------------------------- #


def lock_run(
    contract_path: Path,
    calibration_path: Path,
    verification_path: Path,
    destination: Path,
    *,
    model_factory: ModelFactory,
) -> PlanLock:
    """Seal a lock over the inputs and the provider's observed identity; write it exclusively."""
    _check_new_path("destination", destination)
    contract = parse_contract(contract_path)
    calibration = read_input_text(calibration_path)
    verification = read_input_text(verification_path)
    # Malformed splits are rejected before a provider (possibly a 120 s native
    # worker) is built; create_lock repeats these checks and adds leakage checks.
    parse_cases(calibration, contract.question)
    parse_cases(verification, contract.question)
    model = model_factory()
    try:
        identity = _observe_identity(model)
    finally:
        model.close()
    lock = create_lock(contract, calibration, verification, identity)
    write_lock(lock, destination)
    return lock


def verify_run(
    lock_path: Path,
    calibration_path: Path,
    verification_path: Path,
    destination: Path,
    *,
    provider: str,
    model_factory: ModelFactory,
) -> tuple[EvidenceBundle, Path]:
    """Execute the locked collection protocol once and publish one new evidence bundle.

    Every lock, input, implementation and provider check precedes provider
    construction; the complete observed identity is compared before any
    ``decide`` call. The provider is closed on every path.
    """
    _check_new_path("destination", destination)
    if provider not in PROVIDERS:
        raise SchemaError("provider: unsupported value")
    lock = _read_lock(lock_path)
    calibration = read_input_text(calibration_path)
    verification = read_input_text(verification_path)
    cases = validate_inputs(lock, calibration, verification)
    if lock.model_identity.provider != provider:
        raise IntegrityError("model_identity.provider: requested provider does not match the lock")
    require_exact_implementation(lock)
    model = model_factory()
    try:
        if _observe_identity(model) != lock.model_identity:
            raise IntegrityError(
                "model_identity: observed provider identity does not match the lock"
            )
        records = collect(model, lock, cases)
        faults = run_fault_campaign(lock)
        verdict = assess(records, lock, faults)
        bundle = EvidenceBundle(lock, calibration, verification, records, faults, verdict)
        path = write_bundle(bundle, destination)
    finally:
        model.close()
    return bundle, path


# --------------------------------------------------------------------------- #
# demo
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class DemoRun:
    """One demonstration run: its lock, bundle, genuine verdict and fresh replay."""

    name: str
    expected_status: str
    lock: PlanLock
    lock_path: Path
    bundle: EvidenceBundle
    bundle_path: Path
    replayed: Verdict

    @property
    def verdict(self) -> Verdict:
        return self.bundle.verdict

    @property
    def as_expected(self) -> bool:
        return self.verdict.status == self.expected_status and self.replayed == self.verdict


@dataclass(frozen=True, slots=True)
class DemoResult:
    """Both runs plus the measured wall-clock duration (reported, never sealed)."""

    destination: Path
    runs: tuple[DemoRun, ...]
    duration_s: float

    @property
    def succeeded(self) -> bool:
        return tuple(run.name for run in self.runs) == DEMO_RUNS and all(
            run.as_expected for run in self.runs
        )


def _copy_resources(destination: Path) -> dict[str, Path]:
    """Write the packaged resource files, byte for byte, as new files under ``destination``."""
    from importlib.resources import files  # noqa: PLC0415 - demo only, not on the replay path

    from actseal.demo_data import RESOURCE_FILES  # noqa: PLC0415 - demo only

    package = files("actseal.demo_data")
    destination.mkdir(parents=False, exist_ok=False)
    copies: dict[str, Path] = {}
    for name in RESOURCE_FILES:
        data = package.joinpath(name).read_bytes()
        target = destination / name
        _write_new_file(target, data)
        copies[name] = target
    return copies


def _demo_run(name: str, inputs: dict[str, Path], directory: Path) -> DemoRun:
    from actseal.adapters.fixture import FixtureModel  # noqa: PLC0415 - fixture branch only

    responses = inputs[f"{name}_responses.jsonl"]
    contract = inputs[f"{name}.toml"]
    calibration = inputs[f"{name}_calibration.jsonl"]
    verification = inputs[f"{name}_verification.jsonl"]
    directory.mkdir(parents=False, exist_ok=False)
    lock_path = directory / LOCK_FILE_NAME
    lock = lock_run(
        contract,
        calibration,
        verification,
        lock_path,
        model_factory=lambda: FixtureModel(responses),
    )
    bundle, bundle_path = verify_run(
        lock_path,
        calibration,
        verification,
        directory / EVIDENCE_DIRECTORY,
        provider="fixture",
        model_factory=lambda: FixtureModel(responses),
    )
    replayed = replay(bundle_path, expected_lock_sha256=lock.sha256)
    return DemoRun(name, DEMO_EXPECTED[name], lock, lock_path, bundle, bundle_path, replayed)


def demo_run(destination: Path) -> DemoResult:
    """Run the packaged ADR 0013 demonstration into the NEW directory ``destination``.

    Both runs always execute and are reported; the caller decides exit status
    from :attr:`DemoResult.succeeded`. Nothing outside ``destination`` is written.
    """
    _check_new_path("destination", destination)
    started = time.monotonic()
    destination.mkdir(parents=False, exist_ok=False)
    inputs = _copy_resources(destination / DEMO_INPUTS_DIRECTORY)
    runs = tuple(_demo_run(name, inputs, destination / name) for name in DEMO_RUNS)
    return DemoResult(destination, runs, time.monotonic() - started)
