"""The ``actseal`` command line (plan/CONTRACTS.md section 7).

Commands are exactly ``lock``, ``verify``, ``replay`` and ``demo``; every
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
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from actseal import __version__
from actseal.compatibility import LEGACY_GUIDANCE
from actseal.errors import ActsealError
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

__all__ = ["EXIT_CODES", "EXIT_ERROR", "RECEIPT_SCHEMA_VERSION", "main"]

EXIT_CODES: Final[Mapping[str, int]] = {"PASS": 0, "BLOCK": 1, "INCONCLUSIVE": 2, "ERROR": 3}
EXIT_ERROR: Final = 3
#: Schema version written into every ``--json`` receipt, successes and errors alike.
RECEIPT_SCHEMA_VERSION: Final = 1

_PROVIDERS: Final = ("fixture", "laya")
_COMMAND_NAMES: Final = ("lock", "verify", "replay", "demo")
_JSON_FLAG: Final = "--json"
#: Accepted values per choice argument, keyed by the name argparse uses in diagnostics.
_CHOICES: Final[Mapping[str, tuple[str, ...]]] = {
    "COMMAND": _COMMAND_NAMES,
    "--provider": _PROVIDERS,
}
_ARGUMENT_MESSAGE: Final = re.compile(r"^argument (?P<name>[^:]+): (?P<rest>.*)$", re.DOTALL)
_REQUIRED_MESSAGE: Final = re.compile(r"^the following arguments are required: (?P<names>.+)$")
_COUNT_MESSAGE: Final = re.compile(r"^expected (one|at least one|at most one|\d+) arguments?$")
_DEMO_NOTE: Final = (
    "Authored synthetic demonstration (evidence_scope=demo): the same frozen policy "
    "evaluated against two authored fixture outcomes. Not a population benchmark, "
    "not a trained or repaired model, not deployment certification."
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
    parser.add_argument("--provider", required=True, choices=_PROVIDERS)
    parser.add_argument("--responses", type=Path, metavar="PATH", default=None)
    parser.add_argument("--offline", action="store_true")


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
    demo.add_argument("--out", required=True, type=Path, metavar="NEW_DIRECTORY")

    for subparser in (lock, verify, replay_parser, demo):
        subparser.add_argument(_JSON_FLAG, action="store_true", help="machine-readable output")
    return parser


def _check_provider_options(args: argparse.Namespace) -> None:
    """``fixture`` requires ``--responses``; ``laya`` forbids it.

    ``--offline`` is accepted by both providers: the fixture adapter performs no
    network access at all, so the flag simply states its existing behavior.
    """
    if args.provider == "fixture":
        if args.responses is None:
            raise _UsageError("--responses is required with --provider fixture")
    elif args.responses is not None:
        raise _UsageError("--responses is not accepted with --provider laya")


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
    provider: str = args.provider
    responses: Path | None = args.responses
    offline: bool = args.offline
    lock = lock_run(
        args.contract,
        args.calibration,
        args.verification,
        args.out,
        model_factory=lambda: open_model(provider, responses=responses, offline=offline),
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
    responses: Path | None = args.responses
    offline: bool = args.offline
    bundle, path = verify_run(
        args.lock,
        args.calibration,
        args.verification,
        args.out,
        provider=provider,
        model_factory=lambda: open_model(provider, responses=responses, offline=offline),
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


_COMMANDS: Final = {
    "lock": _run_lock,
    "verify": _run_verify,
    "replay": _run_replay,
    "demo": _run_demo,
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
