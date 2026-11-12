"""The ``actseal`` command line (plan/CONTRACTS.md section 7).

Commands include ``lock``, ``verify``, ``replay``, ``demo`` and the separately
versioned ``plan``, ``calibrate``, ``qualify`` and ``replay-selection``; every
command accepts ``--json``. Exit codes are PASS 0, BLOCK 1, INCONCLUSIVE 2 and
ERROR 3. Usage errors, setup errors, invalid inputs, existing destinations and
operating-system failures are ERROR 3 (never argparse's default 2). Usage
diagnostics are rewritten to name only option strings, metavars, accepted
choices and token counts: a raw command-line value is never echoed. ``lock``
returns 0 on success; ``demo`` returns 0 only when the deliberately bad run is
BLOCK, the fixed run is PASS and both fresh replays equal the recorded verdicts.

Output discipline: with ``--json`` exactly one JSON object is written to
stdout and nothing else; warnings and captured failures are fields of that
object. Every JSON receipt, including every error and usage error, carries
``schema_version`` (``RECEIPT_SCHEMA_VERSION``, 1) and ``command``; the field
names, types and meanings of versioned receipts are stable through 1.x
(docs/stability.md). Without ``--json`` the report goes to stdout and
warnings/failures/notes to stderr; ``--help`` and ``--version`` remain text.
Abbreviated long options are rejected by the root parser and every
subcommand. Error messages name fields, invariants or errno text; they never
echo input values, paths supplied by the operating system, raw bodies or
arbitrary exception text.

Importing this module imports no adapter or optional library; ``replay`` and
``demo`` never initialize a live provider (the demo uses the stdlib fixture
adapter only inside the runner's fixture branch).

Experimental providers (docs/stability.md PROVISIONAL, ADR 0017): the stable
``--provider`` choices are ``fixture``, ``laya`` and ``recorded``. ``jev`` and
``decision-api`` are accepted by collection commands only with the explicit opt-in
``--experimental-provider``; a missing opt-in, the opt-in with a stable
provider, or ``--responses`` with ``jev`` is a usage error (ERROR 3) raised
before any provider is constructed, any environment variable is read or any
request is made. ``replay`` and ``demo`` do not accept the flag at all. The
adapter itself rejects ``--offline`` as a setup error before reading its key.
No receipt field is added for the opt-in: the receipt shapes stay frozen and
the provider is visible in the recorded ``model_identity``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Final

from actseal import __version__
from actseal.assessment import REASON_RECORDED_FAULT_SCOPE
from actseal.compatibility import LEGACY_GUIDANCE
from actseal.errors import ActsealError, IntegrityError, SchemaError
from actseal.normalization import RECORDING_WARNING
from actseal.records import (
    DecisionRecord,
    EvidenceBundle,
    FaultResult,
    ModelIdentity,
    ProviderFailure,
    Verdict,
)
from actseal.replay import REASON_LEGACY_SCHEMA, replay
from actseal.runner import demo_run, lock_run, open_model, verify_run
from actseal.selection import DEFAULT_SELECTION_TAIL, SelectionResult, plan_sample_size

if TYPE_CHECKING:
    from actseal.adapters.base import DecisionModel
    from actseal.qualification import CalibrationRun, QualificationRun
    from actseal.report import ReportData

__all__ = ["EXIT_CODES", "EXIT_ERROR", "RECEIPT_SCHEMA_VERSION", "main"]

EXIT_CODES: Final[Mapping[str, int]] = {"PASS": 0, "BLOCK": 1, "INCONCLUSIVE": 2, "ERROR": 3}
EXIT_ERROR: Final = 3
#: Schema version written into every ``--json`` receipt, successes and errors alike.
RECEIPT_SCHEMA_VERSION: Final = 1

#: STABLE provider choices; selectable without any opt-in.
_PROVIDERS: Final = ("fixture", "laya", "recorded")
#: PROVISIONAL provider choices; each requires ``--experimental-provider``.
_EXPERIMENTAL_PROVIDERS: Final = ("jev", "decision-api")
_PROVIDER_CHOICES: Final = (*_PROVIDERS, *_EXPERIMENTAL_PROVIDERS)
_EXPERIMENTAL_FLAG: Final = "--experimental-provider"
_COMMAND_NAMES: Final = (
    "lock",
    "verify",
    "replay",
    "demo",
    "plan",
    "calibrate",
    "qualify",
    "replay-selection",
    "report",
)
_JSON_FLAG: Final = "--json"
#: Accepted values per choice argument, keyed by the name argparse uses in diagnostics.
_CHOICES: Final[Mapping[str, tuple[str, ...]]] = {
    "COMMAND": _COMMAND_NAMES,
    "--provider": _PROVIDER_CHOICES,
}
_ARGUMENT_MESSAGE: Final = re.compile(r"^argument (?P<name>[^:]+): (?P<rest>.*)$", re.DOTALL)
_REQUIRED_MESSAGE: Final = re.compile(r"^the following arguments are required: (?P<names>.+)$")
_COUNT_MESSAGE: Final = re.compile(r"^expected (one|at least one|at most one|\d+) arguments?$")
_DEMO_NOTE: Final = (
    "Authored synthetic demonstration (evidence_scope=demo): the same frozen policy "
    "evaluated against two authored fixture outcomes. Not a population benchmark, "
    "not a trained or repaired model, not deployment certification."
)
_QUALIFICATION_DEMO_NOTE: Final = (
    "Authored synthetic qualification demonstration (evidence_scope=demo): "
    "64 calibration cases select a threshold; 100 separate verification cases "
    "produce the verdict. No population or deployment claim."
)


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #


class _UsageError(Exception):
    """A command-line usage problem; always exit code 3."""


class _ParserExitError(Exception):
    """argparse asked to exit (``--help``); carries the requested status."""

    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


def _bounded_usage_message(message: str) -> str:
    """Rewrite an argparse diagnostic so it names options and invariants, never argv values.

    Argument names come from the parser definition (option strings and metavars),
    never from the command line; choice inventories come from ``_CHOICES``.
    Any message shape not recognized here collapses to a generic hint.
    """
    required = _REQUIRED_MESSAGE.match(message)
    if required is not None:
        return f"the following arguments are required: {required['names']}"
    argument = _ARGUMENT_MESSAGE.match(message)
    if argument is None:
        return "invalid command line; see --help"
    name, rest = argument["name"], argument["rest"]
    if rest.startswith("invalid choice"):
        choices = _CHOICES.get(name)
        detail = f" (choose from {', '.join(choices)})" if choices else ""
        return f"argument {name}: invalid choice{detail}"
    if _COUNT_MESSAGE.match(rest) is not None:
        return f"argument {name}: {rest}"
    if rest.startswith("ignored explicit argument"):
        return f"argument {name}: does not take a value"
    return f"argument {name}: invalid value"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise _UsageError(_bounded_usage_message(message))

    def exit(self, status: int = 0, message: str | None = None) -> None:  # type: ignore[override]
        if message:
            sys.stderr.write(message)
        raise _ParserExitError(status)


def _add_provider_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--calibration", required=True, type=Path, metavar="PATH")
    parser.add_argument("--verification", required=True, type=Path, metavar="PATH")
    parser.add_argument("--provider", required=True, choices=_PROVIDER_CHOICES)
    parser.add_argument("--responses", type=Path, metavar="PATH", default=None)
    parser.add_argument("--model", metavar="NAME", default=None)
    parser.add_argument("--revision", metavar="REV", default=None)
    parser.add_argument("--endpoint", metavar="URL", default=None)
    parser.add_argument("--api-key-env", metavar="NAME", default=None)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        _EXPERIMENTAL_FLAG,
        action="store_true",
        help=(
            "opt in to a PROVISIONAL provider (required with jev or decision-api, "
            "rejected with fixture, laya or recorded)"
        ),
    )


def _build_parser() -> _Parser:
    parser = _Parser(
        prog="actseal",
        description="Verify a frozen categorical decision policy with replayable evidence.",
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"actseal {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # Every subcommand parser disables abbreviation too: ``--ou`` is never ``--out``.
    lock = commands.add_parser(
        "lock", help="seal contract, inputs and provider identity", allow_abbrev=False
    )
    lock.add_argument("--contract", required=True, type=Path, metavar="PATH")
    _add_provider_arguments(lock)
    lock.add_argument("--out", required=True, type=Path, metavar="PATH")

    verify = commands.add_parser(
        "verify", help="collect evidence for a lock and assess it", allow_abbrev=False
    )
    verify.add_argument("--lock", required=True, type=Path, metavar="PATH")
    _add_provider_arguments(verify)
    verify.add_argument("--out", required=True, type=Path, metavar="DIRECTORY")

    replay_parser = commands.add_parser(
        "replay", help="recompute a verdict from a bundle", allow_abbrev=False
    )
    replay_parser.add_argument("bundle", type=Path, metavar="DIRECTORY")
    replay_parser.add_argument("--expected-lock-sha256", metavar="HEX", default=None)

    demo = commands.add_parser(
        "demo", help="run the packaged synthetic demonstration", allow_abbrev=False
    )
    demo.add_argument("--out", type=Path, metavar="NEW_DIRECTORY")
    demo.add_argument("--qualify", action="store_true", help="run synthetic threshold selection")

    plan = commands.add_parser(
        "plan", help="plan verification size under supplied assumptions", allow_abbrev=False
    )
    for name in ("max-risk", "min-coverage", "alpha", "expected-risk", "expected-coverage"):
        plan.add_argument(f"--{name}", required=True, type=float, metavar="FLOAT")
    plan.add_argument("--target-pass-probability", type=float, default=0.8, metavar="FLOAT")

    calibration_parsers = []
    for command in ("calibrate", "qualify"):
        calibration = commands.add_parser(
            command,
            help="select a threshold"
            + (" and verify on held-out cases" if command == "qualify" else ""),
            allow_abbrev=False,
        )
        calibration.add_argument("--contract", required=True, type=Path, metavar="PATH")
        _add_provider_arguments(calibration)
        calibration.add_argument("--out", required=True, type=Path, metavar="DIRECTORY")
        calibration.add_argument("--grid", type=float, nargs="+", metavar="FLOAT")
        calibration.add_argument(
            "--target-pass-probability", type=float, default=0.8, metavar="FLOAT"
        )
        calibration.add_argument(
            "--selection-tail", type=float, default=DEFAULT_SELECTION_TAIL, metavar="FLOAT"
        )
        calibration_parsers.append(calibration)

    replay_selection_parser = commands.add_parser(
        "replay-selection", help="recompute calibration selection offline", allow_abbrev=False
    )
    replay_selection_parser.add_argument("directory", type=Path, metavar="DIRECTORY")

    report_parser = commands.add_parser(
        "report", help="render replayed evidence as HTML, Markdown and a badge", allow_abbrev=False
    )
    report_parser.add_argument("directory", type=Path, metavar="DIRECTORY")
    report_parser.add_argument("--out", required=True, type=Path, metavar="OUTDIR")
    report_parser.add_argument("--attestation-ref", metavar="TEXT")

    for subparser in (
        lock,
        verify,
        replay_parser,
        demo,
        plan,
        *calibration_parsers,
        replay_selection_parser,
        report_parser,
    ):
        subparser.add_argument(_JSON_FLAG, action="store_true", help="machine-readable output")
    return parser


def _check_provider_options(args: argparse.Namespace) -> None:
    """Provider/option rules, checked before any input is read or provider built.

    ``fixture`` requires ``--responses``; ``laya`` and ``jev`` forbid it.
    ``--offline`` is accepted by the stable providers: the fixture adapter
    performs no network access at all, so the flag simply states its existing
    behavior. The PROVISIONAL ``jev`` provider is accepted only with the
    explicit ``--experimental-provider`` opt-in, which the stable providers
    reject; ``jev`` with ``--offline`` is left to the adapter, which refuses it
    as a setup error before reading any environment variable.
    """
    provider: str = args.provider
    experimental: bool = args.experimental_provider
    if provider in _EXPERIMENTAL_PROVIDERS:
        if not experimental:
            raise _UsageError(f"{_EXPERIMENTAL_FLAG} is required with --provider {provider}")
    elif experimental:
        raise _UsageError(f"{_EXPERIMENTAL_FLAG} is not accepted with --provider {provider}")
    if provider in {"fixture", "recorded"}:
        if args.responses is None:
            raise _UsageError(f"--responses is required with --provider {provider}")
    elif args.responses is not None:
        raise _UsageError(f"--responses is not accepted with --provider {provider}")
    for name in ("model", "revision"):
        value = getattr(args, name)
        if provider in {"recorded", "decision-api"}:
            if value is None or not value.strip():
                raise _UsageError(f"--{name} is required with --provider {provider}")
        elif value is not None:
            raise _UsageError(f"--{name} is not accepted with --provider {provider}")
    if provider == "decision-api":
        if args.endpoint is None or not args.endpoint.strip():
            raise _UsageError("--endpoint is required with --provider decision-api")
    else:
        for name in ("endpoint", "api_key_env"):
            if getattr(args, name) is not None:
                option = name.replace("_", "-")
                raise _UsageError(f"--{option} is not accepted with --provider {provider}")


def _open_selected_model(args: argparse.Namespace) -> DecisionModel:
    """Keep existing provider calls unchanged; pass new options only to the new profiles."""
    if args.provider in {"recorded", "decision-api"}:
        return open_model(
            args.provider,
            responses=args.responses,
            offline=args.offline,
            model=args.model,
            revision=args.revision,
            endpoint=args.endpoint,
            api_key_env=args.api_key_env,
        )
    return open_model(args.provider, responses=args.responses, offline=args.offline)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


class _Output:
    """One report per invocation: a JSON object or text lines plus stderr notes."""

    def __init__(self, command: str, *, as_json: bool) -> None:
        self.command = command
        self.as_json = as_json

    def report(self, payload: dict[str, object], lines: Sequence[str], notes: Sequence[str]) -> int:
        code = payload["exit_code"]
        if not isinstance(code, int):  # pragma: no cover - payloads are built below
            raise TypeError("exit_code")
        if self.as_json:
            document = {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "command": self.command,
                **payload,
            }
            sys.stdout.write(json.dumps(document, sort_keys=True, ensure_ascii=False) + "\n")
        else:
            for line in lines:
                sys.stdout.write(line + "\n")
            for note in notes:
                sys.stderr.write(f"actseal {self.command}: {note}\n")
        sys.stdout.flush()
        sys.stderr.flush()
        return code

    def error(self, message: str) -> int:
        payload: dict[str, object] = {
            "exit_code": EXIT_ERROR,
            "ok": False,
            "status": "ERROR",
            "error": message,
        }
        return self.report(payload, [], [f"error: {message}"])


def _verdict_data(verdict: Verdict) -> dict[str, object]:
    return {
        "status": verdict.status,
        "reasons": list(verdict.reasons),
        "total": verdict.total,
        "accepted": verdict.accepted,
        "errors": verdict.errors,
        "risk": {"lower": verdict.risk.lower, "upper": verdict.risk.upper},
        "coverage": {"lower": verdict.coverage.lower, "upper": verdict.coverage.upper},
        "evidence_scope": verdict.evidence_scope,
        "lock_sha256": verdict.lock_sha256,
    }


def _verdict_lines(verdict: Verdict, indent: str = "") -> list[str]:
    return [
        f"{indent}status: {verdict.status}",
        f"{indent}reasons: {' '.join(verdict.reasons)}",
        f"{indent}accepted/total: {verdict.accepted}/{verdict.total}",
        f"{indent}errors/accepted: {verdict.errors}/{verdict.accepted}",
        f"{indent}risk: [{verdict.risk.lower!r}, {verdict.risk.upper!r}]",
        f"{indent}coverage: [{verdict.coverage.lower!r}, {verdict.coverage.upper!r}]",
        f"{indent}evidence_scope: {verdict.evidence_scope}",
        f"{indent}lock_sha256: {verdict.lock_sha256}",
    ]


def _identity_data(identity: ModelIdentity) -> dict[str, object]:
    return {
        "provider": identity.provider,
        "model": identity.model,
        "revision": identity.revision,
        "adapter_version": identity.adapter_version,
        "normalizer_version": identity.normalizer_version,
    }


def _count(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _failures(records: Sequence[DecisionRecord]) -> dict[str, int]:
    """Terminal failure codes per case: the normalized ``ProviderFailure`` outcome.

    Transport failures pass through normalization unchanged, and bodies rejected
    by normalization (malformed response, unknown choice, identity mismatch,
    input too long) become failures only there, so counting outcomes covers both
    once per case.
    """
    return _count(
        [record.outcome.code for record in records if isinstance(record.outcome, ProviderFailure)]
    )


def _warnings(records: Sequence[DecisionRecord]) -> dict[str, int]:
    """Normalized outcomes carry the capture warnings plus any normalizer warning codes."""
    return _count([warning for record in records for warning in record.outcome.warnings])


def _faults(faults: Sequence[FaultResult], expected: Mapping[str, str]) -> dict[str, object]:
    return {
        fault.scenario_id: {
            "action": fault.decision.action,
            "expected_action": expected[fault.scenario_id],
        }
        for fault in faults
    }


def _format_counts(counts: Mapping[str, int]) -> str:
    return " ".join(f"{key}={value}" for key, value in counts.items()) or "none"


def _bundle_payload(bundle: EvidenceBundle) -> tuple[dict[str, object], list[str], list[str]]:
    """Verdict plus surfaced failures/warnings/faults for one evidence bundle."""
    failures = _failures(bundle.records)
    warnings = _warnings(bundle.records)
    expected = {spec.scenario_id: spec.expected_action for spec in bundle.lock.fault_inventory}
    faults = _faults(bundle.faults, expected)
    payload: dict[str, object] = {
        **_verdict_data(bundle.verdict),
        "failures": failures,
        "warnings": warnings,
        "faults": faults,
    }
    lines = _verdict_lines(bundle.verdict)
    lines.append(
        "faults: "
        + " ".join(f"{fault.scenario_id}={fault.decision.action}" for fault in bundle.faults)
    )
    notes = [f"failures: {_format_counts(failures)}", f"warnings: {_format_counts(warnings)}"]
    return payload, lines, notes


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def _run_lock(args: argparse.Namespace, output: _Output) -> int:
    _check_provider_options(args)
    lock = lock_run(
        args.contract,
        args.calibration,
        args.verification,
        args.out,
        model_factory=lambda: _open_selected_model(args),
    )
    identity = lock.model_identity
    payload: dict[str, object] = {
        "exit_code": 0,
        "ok": True,
        "lock_sha256": lock.sha256,
        "implementation_sha256": lock.implementation_sha256,
        "replay_engine_version": lock.replay_engine_version,
        "evidence_scope": lock.contract.evidence_scope,
        "contract": lock.contract.name,
        "model_identity": _identity_data(identity),
        "verification_cases": len(lock.verification_cases),
        "calibration_cases": len(lock.calibration_inventory),
        "out": str(args.out),
    }
    lines = [
        f"lock_sha256: {lock.sha256}",
        f"implementation_sha256: {lock.implementation_sha256}",
        f"replay_engine_version: {lock.replay_engine_version}",
        f"contract: {lock.contract.name}",
        f"evidence_scope: {lock.contract.evidence_scope}",
        f"provider: {identity.provider}",
        f"model: {identity.model}",
        f"revision: {identity.revision}",
        f"verification_cases: {len(lock.verification_cases)}",
        f"calibration_cases: {len(lock.calibration_inventory)}",
        f"out: {args.out}",
    ]
    return output.report(payload, lines, [])


def _run_verify(args: argparse.Namespace, output: _Output) -> int:
    _check_provider_options(args)
    provider: str = args.provider
    bundle, path = verify_run(
        args.lock,
        args.calibration,
        args.verification,
        args.out,
        provider=provider,
        model_factory=lambda: _open_selected_model(args),
    )
    payload, lines, notes = _bundle_payload(bundle)
    code = EXIT_CODES[bundle.verdict.status]
    payload.update({"exit_code": code, "ok": code == 0, "out": str(path)})
    lines.append(f"out: {path}")
    return output.report(payload, lines, notes)


def _run_replay(args: argparse.Namespace, output: _Output) -> int:
    expected: str | None = args.expected_lock_sha256
    verdict = replay(args.bundle, expected_lock_sha256=expected)
    code = EXIT_CODES[verdict.status]
    # Advisory, human-readable notes; legacy (actseal 0.1.0) evidence gets the
    # pinned-replay guidance so the ERROR is actionable.
    notes = [LEGACY_GUIDANCE] if REASON_LEGACY_SCHEMA in verdict.reasons else []
    if REASON_RECORDED_FAULT_SCOPE in verdict.reasons:
        notes.append(RECORDING_WARNING)
    payload: dict[str, object] = {
        **_verdict_data(verdict),
        "exit_code": code,
        "ok": code == 0,
        "bundle": str(args.bundle),
        "expected_lock_sha256": expected,
        "notes": notes,
    }
    lines = [*_verdict_lines(verdict), f"bundle: {args.bundle}"]
    if expected is not None:
        lines.append(f"expected_lock_sha256: {expected}")
    return output.report(payload, lines, notes)


def _run_demo(args: argparse.Namespace, output: _Output) -> int:
    if args.qualify:
        return _run_qualification_demo(args, output)
    if args.out is None:
        raise _UsageError("the following arguments are required: --out")
    result = demo_run(args.out)
    code = 0 if result.succeeded else EXIT_ERROR
    runs: dict[str, object] = {}
    lines = [
        f"demo: {_DEMO_NOTE}",
        f"out: {result.destination}",
        f"duration_s: {result.duration_s:.3f}",
    ]
    notes: list[str] = []
    for run in result.runs:
        run_payload, run_lines, run_notes = _bundle_payload(run.bundle)
        runs[run.name] = {
            **run_payload,
            "expected_status": run.expected_status,
            "as_expected": run.as_expected,
            "lock": str(run.lock_path),
            "evidence": str(run.bundle_path),
            "replay": _verdict_data(run.replayed),
            "replay_matches": run.replayed == run.verdict,
        }
        match = "match" if run.replayed == run.verdict else "MISMATCH"
        lines.append(
            f"[{run.name}] expected {run.expected_status}, observed {run.verdict.status}, "
            f"replay {run.replayed.status} ({match})"
        )
        lines.extend("  " + line for line in run_lines)
        lines.append(f"  lock: {run.lock_path}")
        lines.append(f"  evidence: {run.bundle_path}")
        notes.extend(f"[{run.name}] {note}" for note in run_notes)
    lines.append("result: " + ("success" if result.succeeded else "FAILURE"))
    payload: dict[str, object] = {
        "exit_code": code,
        "ok": result.succeeded,
        "status": "PASS" if result.succeeded else "ERROR",
        "evidence_scope": "demo",
        "demo_only": True,
        "note": _DEMO_NOTE,
        "out": str(result.destination),
        "duration_s": result.duration_s,
        "runs": runs,
    }
    return output.report(payload, lines, notes)


def _selection_data(selection: SelectionResult) -> dict[str, object]:
    return {
        "threshold": selection.threshold,
        "reason": selection.reason,
        "points": [
            {
                "threshold": point.threshold,
                "accepted": point.accepted,
                "errors": point.errors,
                "predicted_pass_probability": point.predicted_pass_probability,
            }
            for point in selection.points
        ],
    }


def _run_plan(args: argparse.Namespace, output: _Output) -> int:
    assumptions = {
        "max_risk": args.max_risk,
        "min_coverage": args.min_coverage,
        "alpha": args.alpha,
        "expected_risk": args.expected_risk,
        "expected_coverage": args.expected_coverage,
    }
    size = plan_sample_size(**assumptions, target_pass_probability=args.target_pass_probability)
    code = 0 if size is not None else 2
    payload: dict[str, object] = {
        "exit_code": code,
        "ok": code == 0,
        "status": "PLANNED" if size is not None else "INCONCLUSIVE",
        "verification_cases": size,
        "max_verification_cases": 10_000,
        "target_pass_probability": args.target_pass_probability,
        "assumptions": assumptions,
        "reason": "planning.reachable" if size is not None else "planning.not_reachable",
    }
    line = (
        f"required scheduled verification size: {size}"
        if size is not None
        else "not reachable within 10,000"
    )
    return output.report(payload, [line], [])


def _calibration_payload(result: CalibrationRun) -> tuple[dict[str, object], list[str]]:
    selected = result.selection.threshold is not None
    code = 0 if selected else 2
    payload: dict[str, object] = {
        "exit_code": code,
        "ok": selected,
        "status": "SELECTED" if selected else "INCONCLUSIVE",
        "out": str(result.destination),
        "calibration": str(result.destination / "calibration"),
        "contract": str(result.contract_path) if result.contract_path is not None else None,
        "calibration_manifest_sha256": result.manifest_sha256,
        "selection": _selection_data(result.selection),
    }
    lines = [
        f"selection: {result.selection.reason}",
        f"threshold: {result.selection.threshold}",
        f"calibration: {result.destination / 'calibration'}",
    ]
    if result.contract_path is not None:
        lines.append(f"derived contract: {result.contract_path}")
    return payload, lines


def _run_calibrate(args: argparse.Namespace, output: _Output) -> int:
    from actseal.qualification import (  # noqa: PLC0415 - separate opt-in workflow
        DEFAULT_GRID,
        calibrate_run,
    )

    _check_provider_options(args)
    result = calibrate_run(
        args.contract,
        args.calibration,
        args.verification,
        args.out,
        model_factory=lambda: _open_selected_model(args),
        grid=DEFAULT_GRID if args.grid is None else tuple(args.grid),
        target_pass_probability=args.target_pass_probability,
        selection_tail=args.selection_tail,
    )
    payload, lines = _calibration_payload(result)
    notes = [RECORDING_WARNING] if args.provider == "recorded" else []
    return output.report(payload, lines, notes)


def _qualification_payload(
    result: QualificationRun,
) -> tuple[dict[str, object], list[str], list[str]]:
    payload, lines = _calibration_payload(result.calibration)
    bundle_payload: dict[str, object] | None = None
    notes: list[str] = []
    if result.bundle is not None:
        bundle_payload, verdict_lines, notes = _bundle_payload(result.bundle)
        lines.extend(verdict_lines)
        code = EXIT_CODES[result.bundle.verdict.status]
        payload.update({"status": result.bundle.verdict.status, "exit_code": code, "ok": code == 0})
    payload.update(
        {
            "lock_sha256": result.lock.sha256 if result.lock is not None else None,
            "evidence": str(result.bundle_path) if result.bundle_path is not None else None,
            "qualification": str(result.receipt_path) if result.receipt_path is not None else None,
            "verdict": bundle_payload,
        }
    )
    lines.append(f"out: {result.destination}")
    return payload, lines, notes


def _run_qualify(args: argparse.Namespace, output: _Output) -> int:
    from actseal.qualification import (  # noqa: PLC0415 - separate opt-in workflow
        DEFAULT_GRID,
        qualify_run,
    )

    _check_provider_options(args)
    result = qualify_run(
        args.contract,
        args.calibration,
        args.verification,
        args.out,
        provider=args.provider,
        model_factory=lambda: _open_selected_model(args),
        grid=DEFAULT_GRID if args.grid is None else tuple(args.grid),
        target_pass_probability=args.target_pass_probability,
        selection_tail=args.selection_tail,
    )
    payload, lines, notes = _qualification_payload(result)
    if args.provider == "recorded":
        notes.append(RECORDING_WARNING)
    return output.report(payload, lines, notes)


def _run_replay_selection(args: argparse.Namespace, output: _Output) -> int:
    from actseal.qualification import replay_selection  # noqa: PLC0415 - pure offline path

    selection = replay_selection(args.directory)
    code = 0 if selection.threshold is not None else 2
    payload: dict[str, object] = {
        "exit_code": code,
        "ok": code == 0,
        "status": "SELECTED" if code == 0 else "INCONCLUSIVE",
        "out": str(args.directory),
        "selection": _selection_data(selection),
    }
    return output.report(
        payload, [f"selection: {selection.reason}", f"threshold: {selection.threshold}"], []
    )


def _run_qualification_demo(args: argparse.Namespace, output: _Output) -> int:
    from importlib.resources import as_file, files  # noqa: PLC0415 - demo only

    from actseal.qualification import qualify_run  # noqa: PLC0415 - demo only

    destination = args.out
    if destination is None:
        destination = Path(tempfile.mkdtemp(prefix="actseal-qualification-")) / "demo"
    with as_file(files("actseal.demo_data")) as inputs:
        result = qualify_run(
            inputs / "qualify.toml",
            inputs / "qualify_calibration.jsonl",
            inputs / "qualify_verification.jsonl",
            destination,
            provider="fixture",
            model_factory=lambda: open_model(
                "fixture", responses=inputs / "qualify_responses.jsonl", offline=True
            ),
        )
    payload, lines, notes = _qualification_payload(result)
    payload.update(
        {
            "mode": "qualify",
            "demo_only": True,
            "evidence_scope": "demo",
            "note": _QUALIFICATION_DEMO_NOTE,
        }
    )
    return output.report(payload, [f"demo: {_QUALIFICATION_DEMO_NOTE}", *lines], notes)


def _report_document(path: Path, limit: int) -> bytes:
    """Bounded regular-file reads for the qualification links outside the bundle."""
    import stat  # noqa: PLC0415 - report only

    from actseal.evidence import _read_exact  # noqa: PLC0415 - report only

    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= limit:
        raise SchemaError("report: expected a bounded nonempty regular file")
    return _read_exact(path, "report input", info.st_size)


def _load_report_data(directory: Path, destination: Path) -> ReportData:
    """Delegate replay to its existing stages; only join already validated artifacts.

    The public replay facade turns invalid input into an ERROR verdict. Using
    its stages preserves the distinction between a replayed diagnostic ERROR
    and evidence that failed replay, without copying any decision logic.
    """
    from dataclasses import replace  # noqa: PLC0415 - report only

    from actseal.evidence import read_bundle_files  # noqa: PLC0415 - report only
    from actseal.qualification import (  # noqa: PLC0415 - report only
        _decode_plan,
        _json_document,
        _object,
        _read_sidecar,
        replay_selection,
    )
    from actseal.replay import (  # noqa: PLC0415 - reuse the existing replay implementation
        _check_identity,
        _decode_evidence,
        _decode_lock,
        _InvalidEvidenceError,
        _reassess,
    )
    from actseal.report import ReportData  # noqa: PLC0415 - presentation only
    from actseal.serialization import canonical_json, sha256_bytes, to_data  # noqa: PLC0415

    qualified = any(
        os.path.lexists(directory / name)
        for name in ("calibration", "evidence", "qualification.json")
    )
    bundle_path = directory / "evidence" if qualified else directory
    protected = [bundle_path, directory / "calibration"] if qualified else [bundle_path]
    if any(destination.resolve().is_relative_to(path.resolve()) for path in protected):
        raise SchemaError("report: output must be outside the evidence directories")
    files = read_bundle_files(bundle_path)
    try:
        lock = _decode_lock(files["lock.json"])
        _check_identity(lock, files, None)
        records, faults, stored = _decode_evidence(lock, files)
        verdict = _reassess(lock, records, faults, stored)
    except _InvalidEvidenceError:
        raise IntegrityError("report: evidence does not replay") from None
    manifest_sha256 = sha256_bytes(files["manifest.json"])
    if not qualified:
        return ReportData(lock, verdict, manifest_sha256)

    sidecar = _read_sidecar(directory / "calibration")
    plan = _decode_plan(sidecar["selection_plan.json"])
    selection = replay_selection(directory / "calibration")
    if _read_sidecar(directory / "calibration") != sidecar:
        raise IntegrityError("report: calibration changed during replay")
    calibration_manifest_sha256 = sha256_bytes(sidecar["manifest.json"])
    receipt = _object(
        _json_document(_report_document(directory / "qualification.json", 1024 * 1024)),
        {"schema_version", "calibration_manifest_sha256", "lock_sha256", "verdict"},
        "qualification",
    )
    if (
        type(receipt["schema_version"]) is not int
        or receipt["schema_version"] != 1
        or receipt["calibration_manifest_sha256"] != calibration_manifest_sha256
        or receipt["lock_sha256"] != lock.sha256
        or canonical_json(receipt["verdict"]) != canonical_json(to_data(verdict))
        or _report_document(directory / "lock.json", 32 * 1024 * 1024) != files["lock.json"]
    ):
        raise IntegrityError("report: qualification receipt or lock does not match evidence")
    if (
        selection.threshold != lock.contract.policy.threshold
        or plan.contract
        != replace(lock.contract, policy=replace(lock.contract.policy, threshold=1.0))
        or plan.model_identity != lock.model_identity
        or plan.calibration_sha256 != lock.calibration_sha256
        or plan.verification_sha256 != lock.verification_sha256
        or plan.n_verify != len(lock.verification_cases)
        or plan.implementation_sha256 != lock.implementation_sha256
        or plan.replay_engine_version != lock.replay_engine_version
        or sidecar["calibration.jsonl"] != files["calibration.jsonl"]
    ):
        raise IntegrityError("report: selection plan does not match verification lock")
    return ReportData(
        lock,
        verdict,
        manifest_sha256,
        selection,
        plan.document(),
        len(lock.calibration_inventory),
        calibration_manifest_sha256,
    )


def _run_report(args: argparse.Namespace, output: _Output) -> int:
    from actseal.report import render_report  # noqa: PLC0415 - presentation only

    data = _load_report_data(args.directory, args.out)
    render_report(data, args.out, attestation_ref=args.attestation_ref)
    return output.report(
        {"exit_code": 0, "ok": True, "status": data.verdict.status, "out": str(args.out)},
        [f"report: {data.verdict.status}", f"out: {args.out}"],
        [],
    )


_COMMANDS: Final = {
    "lock": _run_lock,
    "verify": _run_verify,
    "replay": _run_replay,
    "demo": _run_demo,
    "plan": _run_plan,
    "calibrate": _run_calibrate,
    "qualify": _run_qualify,
    "replay-selection": _run_replay_selection,
    "report": _run_report,
}


# --------------------------------------------------------------------------- #
# Error sanitization and entry point
# --------------------------------------------------------------------------- #


def _sanitize(exc: BaseException) -> str:
    """A message naming the failure class or invariant, never an input value or path."""
    if isinstance(exc, ActsealError):
        return f"{type(exc).__name__}: {exc}"
    if isinstance(exc, FileExistsError):
        return "destination already exists"
    if isinstance(exc, OSError):
        detail = os.strerror(exc.errno) if isinstance(exc.errno, int) else "unspecified"
        return f"operating-system error: {detail}"
    if isinstance(exc, NotImplementedError):
        return f"unsupported platform operation: {exc}"
    return f"unexpected {type(exc).__name__}"


def _parse(arguments: Sequence[str]) -> argparse.Namespace:
    """Parse the full command line; leftover tokens are counted, never echoed."""
    args, extras = _build_parser().parse_known_args(arguments)
    if extras:
        raise _UsageError(
            f"unrecognized arguments: {len(extras)} token(s) not accepted; see --help"
        )
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command; return its exit code (PASS 0, BLOCK 1, INCONCLUSIVE 2, ERROR 3)."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    as_json = _JSON_FLAG in arguments
    command = arguments[0] if arguments and arguments[0] in _COMMANDS else "actseal"
    output = _Output(command, as_json=as_json)
    try:
        args = _parse(arguments)
    except _ParserExitError as exit_request:
        return 0 if exit_request.status == 0 else EXIT_ERROR
    except _UsageError as usage:
        return output.error(f"usage: {usage}")
    output = _Output(args.command, as_json=bool(args.json))
    try:
        return _COMMANDS[args.command](args, output)
    except _UsageError as usage:
        return output.error(f"usage: {usage}")
    except Exception as exc:  # every failure of any kind must become ERROR 3
        return output.error(_sanitize(exc))
