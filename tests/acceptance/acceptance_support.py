"""Acceptance-only helpers: independent synthetic inputs, subprocess CLI runs, wire rehashing.

Nothing here is a production authority. Inputs are generated from the documented
TOML/JSONL/fixture shapes; bundle rewrites recompute the documented manifest
with ``hashlib``/``json`` only, so a forgery whose *ordinary* file hashes are
all consistent can be handed to the real replay. Expected verdict behavior is
stated independently in the test modules (exit-code table, policy table and an
independent Clopper-Pearson oracle that bisects the binomial tail in ordinary
floating-point arithmetic), never read back from the product.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from actseal.normalization import request_sha256
from actseal.records import CapturedOutcome, DecisionRequest, ModelIdentity

ROOT = Path(__file__).resolve().parents[2]
LABELS: tuple[str, ...] = ("billing", "technical", "sales")
QUESTION_ID = "department"
MODULE_ENTRY: tuple[str, ...] = (sys.executable, "-m", "actseal")
CONSOLE_ENTRY: tuple[str, ...] = (str(Path(sys.executable).parent / "actseal"),)
ENTRIES: dict[str, tuple[str, ...]] = {"module": MODULE_ENTRY, "console": CONSOLE_ENTRY}
EXIT_CODES: dict[str, int] = {"PASS": 0, "BLOCK": 1, "INCONCLUSIVE": 2, "ERROR": 3}
BUNDLE_FILES: tuple[str, ...] = (
    "manifest.json",
    "lock.json",
    "calibration.jsonl",
    "verification.jsonl",
    "records.jsonl",
    "faults.jsonl",
    "verdict.json",
)
DATA_FILES: tuple[str, ...] = BUNDLE_FILES[1:]
FULL = {"lower": 0.0, "upper": 1.0}
ZERO_HASH = "0" * 64

_TEMPLATES: dict[str, tuple[str, ...]] = {
    "billing": (
        "I was charged twice for invoice {n}; please refund the duplicate.",
        "My receipt for order {n} shows the wrong amount.",
    ),
    "technical": (
        "The app crashes on launch since update {n}.",
        "Error code E{n} appears when I open the dashboard.",
    ),
    "sales": (
        "Do you offer volume pricing for {n} seats?",
        "Can I get a quote for plan tier {n}?",
    ),
}


# --------------------------------------------------------------------------- #
# Synthetic inputs (documented shapes only)
# --------------------------------------------------------------------------- #


def contract_toml(
    *,
    name: str = "acceptance-triage",
    threshold: float = 0.9,
    max_risk: float = 0.05,
    min_coverage: float = 0.5,
    alpha: float = 0.05,
    allowed: Sequence[str] = LABELS,
    evidence_scope: str = "demo",
) -> str:
    allowed_text = ", ".join(f'"{label}"' for label in allowed)
    return f"""\
schema_version = 1
name = "{name}"
evidence_scope = "{evidence_scope}"
population = "Acceptance synthetic support-routing inputs; no deployment claim"

[question]
question_id = "{QUESTION_ID}"
instructions = "Select the department responsible for this ticket."
options = [
  {{label = "billing", description = "Payments and refunds"}},
  {{label = "technical", description = "Technical support"}},
  {{label = "sales", description = "Purchasing questions"}},
]

[policy]
allowed_labels = [{allowed_text}]
threshold = {threshold!r}

[risk]
max_risk = {max_risk!r}
min_coverage = {min_coverage!r}
alpha = {alpha!r}
"""


def make_cases(prefix: str, count: int) -> tuple[tuple[str, str, str], ...]:
    """``count`` unique cases whose gold label is ``LABELS[index % 3]``."""
    cases: list[tuple[str, str, str]] = []
    for index in range(count):
        label = LABELS[index % len(LABELS)]
        template = _TEMPLATES[label][(index // len(LABELS)) % 2]
        state = f"Ticket {prefix.upper()}-{index:04d}: " + template.format(n=1000 + index)
        cases.append((f"{prefix}-{index:04d}", state, label))
    return tuple(cases)


def cases_jsonl(cases: Sequence[tuple[str, str, str]], newline: str = "\n") -> str:
    return "".join(
        json.dumps({"case_id": cid, "state": state, "expected_label": label}, ensure_ascii=False)
        + newline
        for cid, state, label in cases
    )


def answer_body(choice: str, selected: float = 0.95) -> str:
    """A fixture inner answer whose remaining mass is split evenly over the other labels."""
    rest = (1.0 - selected) / (len(LABELS) - 1)
    probabilities = {label: (selected if label == choice else rest) for label in LABELS}
    return json.dumps({"type": "choice", "choice": choice, "probabilities": probabilities})


def laya_envelope(choice: str, selected: float = 0.95) -> str:
    """The complete native Laya response envelope around a well-formed inner answer."""
    envelope = {
        "model": "laya-rl-agent",
        "answers": {QUESTION_ID: json.loads(answer_body(choice, selected))},
        "usage": {
            "input_tokens": 57,
            "output_tokens": 0,
            "state_tokens": 15,
            "state_tokens_dropped": 0,
            "truncated": False,
            "truncated_questions": [],
        },
    }
    return json.dumps(envelope)


def responses_jsonl(rows: Mapping[str, tuple[str | None, str | None]]) -> str:
    return "".join(
        json.dumps(
            {"case_id": cid, "body_json": body, "failure_code": failure, "warnings": []},
            ensure_ascii=False,
        )
        + "\n"
        for cid, (body, failure) in rows.items()
    )


@dataclass(frozen=True)
class Workspace:
    """One complete fixture workflow input set on disk."""

    directory: Path
    contract: Path
    calibration: Path
    verification: Path
    responses: Path
    cases: tuple[tuple[str, str, str], ...]


def write_workspace(
    directory: Path,
    *,
    count: int,
    wrong: Sequence[int] = (),
    failures: Mapping[int, str] | None = None,
    selected: float = 0.95,
    contract: str | None = None,
    prefix: str = "acc",
) -> Workspace:
    """Write contract, both splits and a fixture file for ``count`` verification cases.

    Index ``i`` in ``wrong`` answers the next cyclic label instead of gold; index
    ``i`` in ``failures`` records that transport failure code instead of a body.
    """
    directory.mkdir(parents=True, exist_ok=False)
    cases = make_cases(prefix, count)
    calibration = make_cases(f"{prefix}-cal", 6)
    rows: dict[str, tuple[str | None, str | None]] = {}
    for index, (cid, _, gold) in enumerate(cases):
        if failures and index in failures:
            rows[cid] = (None, failures[index])
            continue
        choice = LABELS[(LABELS.index(gold) + 1) % len(LABELS)] if index in wrong else gold
        rows[cid] = (answer_body(choice, selected), None)
    paths = Workspace(
        directory,
        directory / "contract.toml",
        directory / "calibration.jsonl",
        directory / "verification.jsonl",
        directory / "responses.jsonl",
        cases,
    )
    paths.contract.write_text(contract or contract_toml(), encoding="utf-8")
    paths.calibration.write_bytes(cases_jsonl(calibration).encode("utf-8"))
    paths.verification.write_bytes(cases_jsonl(cases).encode("utf-8"))
    paths.responses.write_bytes(responses_jsonl(rows).encode("utf-8"))
    return paths


# --------------------------------------------------------------------------- #
# Scripted in-process provider (public DecisionModel protocol only)
# --------------------------------------------------------------------------- #

Script = Callable[[str], tuple[str | None, str | None, tuple[str, ...], bool]]


class ScriptedModel:
    """A DecisionModel whose captures follow ``script(case_id)``; records every call."""

    def __init__(self, identity: ModelIdentity, script: Script) -> None:
        self._identity = identity
        self._script = script
        self.calls: list[tuple[str, float]] = []
        self.closed = 0

    def identity(self) -> ModelIdentity:
        return self._identity

    def decide(self, request: DecisionRequest, *, timeout_s: float) -> CapturedOutcome:
        self.calls.append((request.case_id, timeout_s))
        body, failure, warnings, fallback = self._script(request.case_id)
        return CapturedOutcome(
            request_sha256(request), self._identity, body, failure, warnings, fallback_used=fallback
        )

    def close(self) -> None:
        self.closed += 1


def laya_identity() -> ModelIdentity:
    return ModelIdentity(
        "laya",
        "convaiinnovations/laya-typed-decisions",
        "e929ae5cf69bc34259cd2f95c9e91145b818b1f0",
        (("model.safetensors", "4f" * 32),),
        "1",
        "1",
        (("device", "cpu"), ("dtype", "torch.float32"), ("threads", "4")),
    )


# --------------------------------------------------------------------------- #
# Subprocess CLI
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CliResult:
    code: int
    stdout: str
    stderr: str

    def json(self) -> dict[str, object]:
        """``--json`` output is exactly one JSON object on one line."""
        assert self.stdout.endswith("\n"), self.stdout
        assert self.stdout.count("\n") == 1, self.stdout
        document = json.loads(self.stdout)
        assert isinstance(document, dict)
        return {str(key): value for key, value in document.items()}


def clean_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONSAFEPATH"}
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_cli(
    entry: Sequence[str],
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: float = 300.0,
    env: Mapping[str, str] | None = None,
) -> CliResult:
    result = subprocess.run(  # noqa: S603 - fixed entrypoints with test-owned arguments
        [*entry, *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
        env=dict(env) if env is not None else clean_env(),
        timeout=timeout,
    )
    return CliResult(result.returncode, result.stdout, result.stderr)


def lock_argv(workspace: Workspace, out: Path, *extra: str) -> list[str]:
    return [
        "lock",
        "--contract",
        str(workspace.contract),
        "--calibration",
        str(workspace.calibration),
        "--verification",
        str(workspace.verification),
        "--provider",
        "fixture",
        "--responses",
        str(workspace.responses),
        "--out",
        str(out),
        *extra,
    ]


def verify_argv(workspace: Workspace, lock: Path, out: Path, *extra: str) -> list[str]:
    return [
        "verify",
        "--lock",
        str(lock),
        "--calibration",
        str(workspace.calibration),
        "--verification",
        str(workspace.verification),
        "--provider",
        "fixture",
        "--responses",
        str(workspace.responses),
        "--out",
        str(out),
        *extra,
    ]


def tree(root: Path) -> dict[str, str]:
    """Relative path to SHA256 for every regular file under ``root``."""
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# --------------------------------------------------------------------------- #
# Independent wire helpers (hashlib/json only)
# --------------------------------------------------------------------------- #


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    """Documented canonical JSON: sorted keys, compact separators, UTF-8, no newline."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def read_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_bytes().decode("utf-8").split("\n")[:-1]:
        row = json.loads(line)
        assert isinstance(row, dict)
        rows.append(row)
    return rows


def read_document(path: Path) -> dict[str, object]:
    document = json.loads(path.read_bytes().decode("utf-8"))
    assert isinstance(document, dict)
    return document


def rows_bytes(rows: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(canonical(row) + b"\n" for row in rows)


def document_bytes(document: Mapping[str, object]) -> bytes:
    return canonical(document) + b"\n"


def nested(document: Mapping[str, object], *keys: str) -> dict[str, object]:
    value: object = document
    for key in keys:
        assert isinstance(value, dict), keys
        value = value[key]
    assert isinstance(value, dict), keys
    return value


def reseal_lock(lock: Mapping[str, object]) -> dict[str, object]:
    """Recompute the lock's own seal over the document with only ``sha256`` omitted."""
    unsealed = {key: value for key, value in lock.items() if key != "sha256"}
    return {**unsealed, "sha256": sha256_hex(canonical(unsealed))}


def rehash_bundle(bundle: Path, replacements: Mapping[str, bytes]) -> None:
    """Replace files and rewrite ``manifest.json`` so every ordinary hash is consistent again."""
    for name, data in replacements.items():
        assert name in DATA_FILES, name
        (bundle / name).write_bytes(data)
    files = {
        name: {"size": len(data), "sha256": sha256_hex(data)}
        for name in DATA_FILES
        for data in [(bundle / name).read_bytes()]
    }
    unsealed: dict[str, object] = {"schema_version": 1, "files": files}
    manifest = {**unsealed, "sha256": sha256_hex(canonical(unsealed))}
    (bundle / "manifest.json").write_bytes(document_bytes(manifest))


# --------------------------------------------------------------------------- #
# Independent Clopper-Pearson oracle (binomial formula, floating-point bisection)
# --------------------------------------------------------------------------- #


def _tail_at_least(successes: int, trials: int, probability: float) -> float:
    return math.fsum(
        math.comb(trials, k) * probability**k * (1.0 - probability) ** (trials - k)
        for k in range(successes, trials + 1)
    )


def _tail_at_most(successes: int, trials: int, probability: float) -> float:
    return math.fsum(
        math.comb(trials, k) * probability**k * (1.0 - probability) ** (trials - k)
        for k in range(successes + 1)
    )


def _bisect(function: Callable[[float], float], target: float, *, increasing: bool) -> float:
    low, high = 0.0, 1.0
    for _ in range(200):
        mid = (low + high) / 2.0
        value = function(mid)
        if (value < target) == increasing:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def clopper_pearson(successes: int, trials: int, tail: float) -> tuple[float, float]:
    """One-sided Clopper-Pearson bounds at ``tail`` each, by bisection on the binomial tail.

    This uses the binomial formula with ``math.comb`` and finite floating-point
    arithmetic (200 bisection steps); it is independent of the product's kernel,
    not an exact-arithmetic oracle. Callers compare with an absolute tolerance.
    """
    assert trials >= 1
    assert 0 <= successes <= trials
    lower = (
        0.0
        if successes == 0
        else _bisect(lambda p: _tail_at_least(successes, trials, p), tail, increasing=True)
    )
    upper = (
        1.0
        if successes == trials
        else _bisect(lambda p: _tail_at_most(successes, trials, p), tail, increasing=False)
    )
    return lower, upper


def expected_bounds(
    total: int, accepted: int, errors: int, alpha: float
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Risk and coverage intervals under the ADR 0003 rule (tail alpha/4; a == 0 -> [0, 1])."""
    tail = alpha / 4.0
    risk = (0.0, 1.0) if accepted == 0 else clopper_pearson(errors, accepted, tail)
    coverage = clopper_pearson(accepted, total, tail)
    return risk, coverage


def expected_status(
    total: int, accepted: int, errors: int, *, max_risk: float, min_coverage: float, alpha: float
) -> str:
    """The frozen statistical verdict table applied to independently computed bounds."""
    risk, coverage = expected_bounds(total, accepted, errors, alpha)
    if risk[0] > max_risk or coverage[1] < min_coverage:
        return "BLOCK"
    if accepted > 0 and risk[1] <= max_risk and coverage[0] >= min_coverage:
        return "PASS"
    return "INCONCLUSIVE"
