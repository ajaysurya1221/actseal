"""Run, check and record the action-gate example (Task 07).

    uv run --frozen python examples/action_gate/run.py --check
    uv run --frozen python examples/action_gate/run.py --route
    uv run --frozen python examples/action_gate/run.py --record DIRECTORY --source-commit SHA

No key, model download or network is needed: the only provider is the
recorded-response fixture in this directory, which stands in for a model.

``--check`` (exit 0 only when every line below holds):

* runs a fresh offline verification (lock, verify, replay) of the authored
  evaluation data into a temporary directory and requires the fresh replay to
  equal the fresh verdict;
* opens the application gate on that fresh lock and verdict, routes the
  label-free tickets, and requires every disposition and the local queue
  journal to equal the authored expectations;
* for every active recorded run under ``recorded/`` (amendment V1-020): the
  example checks only what is specific to it, namely that ``PRODUCER.json``
  describes the root ``lock.json`` (seal, producer fingerprint, engine), that
  the root ``lock.json`` equals the bundle's ``lock.json`` byte for byte, that
  the archived contract equals the frozen ``contract.toml`` and the archived
  model identity equals the current fixture identity, that the bundle's
  datasets and the producer's input hashes equal the committed authored
  inputs, and that ``records.jsonl``, ``faults.jsonl`` and the verdict (apart
  from the lock seal) equal a fresh run. Everything general (bundle structure
  and hashes, lock seal, replay-engine compatibility through the packaged
  registry, inventories, semantics) is owned by the core ``replay``: each
  active run must replay to a non-``ERROR`` verdict equal to its archived
  verdict. An unsupported (unapproved producer) or damaged archive is an
  error, even beside a valid run; nothing is skipped as benign, nothing is
  rewritten, resealed, moved or auto-approved. An unsupported active archive
  passes only through an explicit compatibility review that registers both
  its producer fingerprint and the running fingerprint for the engine in the
  packaged registry (producer/engine approval, never an archive allowlist);
  for ``recorded/a5fe090202f7`` that review is complete (amendment V1-037
  approved its producer and the 1.0.0 source; amendment V1-055 approved the
  1.0.1 source beside both, so the unchanged archive keeps replaying under
  1.0.1; see docs/versioning.md). Excluding an archive requires a separately
  recorded amendment, and none exists. A new ``--record`` run is a separately
  identified run that does not repair, replace or reseal an older one;
* performs the routing demonstration (the only queue operations in
  ``--check``) only after every active archive passed.

``--route`` performs the same fresh verification and archive checks, refuses
before any queue operation when anything fails, and otherwise replays the
first recorded run, opens the gate on the replayed verdict and routes the
tickets, printing each disposition and the queue journal. ``--record`` writes
a new run directory (``PRODUCER.json``, ``lock.json``, ``evidence/``) and
refuses an existing destination.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TextIO

from gate import ActionGate, Disposition, GateClosedError, LocalQueue, Ticket, route_all

import actseal
from actseal.adapters.fixture import FixtureModel
from actseal.contract import parse_contract, read_input_text
from actseal.errors import ActsealError, IntegrityError, SchemaError
from actseal.evidence import (
    CALIBRATION_FILE,
    FAULTS_FILE,
    LOCK_FILE,
    RECORDS_FILE,
    VERDICT_FILE,
    VERIFICATION_FILE,
    decode_document,
    read_bundle_files,
)
from actseal.locking import parse_lock
from actseal.policy import (
    REASON_ALLOWED,
    REASON_DISALLOWED_CHOICE,
    REASON_LOW_CONFIDENCE,
    REASON_PROVIDER_PREFIX,
    REASON_UNKNOWN_CHOICE,
)
from actseal.records import Action, EvidenceBundle, PlanLock, Verdict
from actseal.replay import replay
from actseal.runner import EVIDENCE_DIRECTORY, LOCK_FILE_NAME, lock_run, verify_run
from actseal.serialization import implementation_fingerprint, sha256_bytes, strict_json_loads

__all__ = [
    "EXAMPLE_DIR",
    "EXPECTED_DISPOSITIONS",
    "INPUT_FILES",
    "PRODUCER_FILE",
    "PRODUCER_FORMAT",
    "RECORDED_DIR",
    "FreshRun",
    "Producer",
    "check",
    "check_recorded",
    "load_producer",
    "load_tickets",
    "main",
    "record",
    "recorded_runs",
    "route",
    "verify",
]

EXAMPLE_DIR = Path(__file__).resolve().parent
RECORDED_DIR = EXAMPLE_DIR / "recorded"
REPO_ROOT = EXAMPLE_DIR.parents[1]
INPUT_FILES = ("contract.toml", "calibration.jsonl", "verification.jsonl", "responses.jsonl")
RESPONSES_FILE = "responses.jsonl"
TICKETS_FILE = "tickets.jsonl"
PRODUCER_FILE = "PRODUCER.json"
PRODUCER_FORMAT = "actseal-action-gate-recorded-run/1"
PRODUCER_KEYS = frozenset(
    {
        "format",
        "actseal_version",
        "implementation_sha256",
        "replay_engine_version",
        "lock_sha256",
        "verdict_status",
        "source_commit",
        "uv_lock_sha256",
        "inputs",
        "note",
    }
)
PRODUCER_NOTE = (
    "Authored synthetic evaluation data (evidence_scope demo) collected through the "
    "recorded-response fixture; no model, key or network was involved. The bytes of this "
    "run are preserved as produced; a later implementation produces a separately "
    "identified run instead of resealing this one."
)
TICKET_KEYS = frozenset({"ticket_id", "text"})
STATUSES = frozenset({"PASS", "BLOCK", "INCONCLUSIVE", "ERROR"})
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
COMMIT_HEX = re.compile(r"[0-9a-f]{40}")
FINGERPRINT_PREFIX = 12

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

#: Authored expectation for every run-time ticket: (action, reason, queue written to).
EXPECTED_DISPOSITIONS: dict[str, tuple[Action, str, str | None]] = {
    "T-1001": ("ACT", REASON_ALLOWED, "billing"),
    "T-1002": ("ACT", REASON_ALLOWED, "technical"),
    "T-1003": ("ACT", REASON_ALLOWED, "sales"),
    "T-1004": ("ABSTAIN", REASON_LOW_CONFIDENCE, None),
    "T-1005": ("ESCALATE", f"{REASON_PROVIDER_PREFIX}timeout", None),
    "T-1006": ("DENY", REASON_DISALLOWED_CHOICE, None),
    "T-1007": ("DENY", REASON_UNKNOWN_CHOICE, None),
    "T-1008": ("ESCALATE", f"{REASON_PROVIDER_PREFIX}malformed_response", None),
}


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FreshRun:
    """One offline verification of the authored data plus its fresh replay."""

    lock: PlanLock
    lock_path: Path
    bundle: EvidenceBundle
    bundle_path: Path
    replayed: Verdict


@dataclass(frozen=True, slots=True)
class Producer:
    """Identity of the implementation and inputs that produced a recorded run."""

    format_id: str
    actseal_version: str
    implementation_sha256: str
    replay_engine_version: str
    lock_sha256: str
    verdict_status: str
    source_commit: str
    uv_lock_sha256: str | None
    inputs: tuple[tuple[str, str], ...]

    def to_json(self) -> str:
        data = {
            "format": self.format_id,
            "actseal_version": self.actseal_version,
            "implementation_sha256": self.implementation_sha256,
            "replay_engine_version": self.replay_engine_version,
            "lock_sha256": self.lock_sha256,
            "verdict_status": self.verdict_status,
            "source_commit": self.source_commit,
            "uv_lock_sha256": self.uv_lock_sha256,
            "inputs": dict(self.inputs),
            "note": PRODUCER_NOTE,
        }
        return json.dumps(data, indent=2, sort_keys=True) + "\n"


class Report:
    """Line-oriented check output; ``errors`` decides the exit code."""

    def __init__(self, out: TextIO) -> None:
        self._out = out
        self.errors = 0

    def ok(self, message: str) -> None:
        self._out.write(f"[ok] {message}\n")

    def info(self, message: str) -> None:
        self._out.write(f"[info] {message}\n")

    def error(self, message: str) -> None:
        self.errors += 1
        self._out.write(f"[error] {message}\n")


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


def _hex(field: str, value: object, pattern: re.Pattern[str]) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise SchemaError(f"{field}: must be lowercase hex of the documented length")
    return value


def _text(field: str, value: object) -> str:
    if type(value) is not str or not value:
        raise SchemaError(f"{field}: must be a nonempty string")
    return value


def load_tickets(path: Path) -> tuple[Ticket, ...]:
    """Read label-free tickets: exactly ``ticket_id`` and ``text`` per row, unique ids."""
    tickets: list[Ticket] = []
    seen: set[str] = set()
    for index, row in enumerate(read_input_text(path).split("\n")):
        if not row:
            continue
        value = strict_json_loads(row)
        if type(value) is not dict or set(value) != TICKET_KEYS:
            raise SchemaError(f"tickets[{index}]: expected exactly ticket_id, text")
        ticket = Ticket(_text("ticket_id", value["ticket_id"]), _text("text", value["text"]))
        if ticket.ticket_id in seen:
            raise SchemaError(f"tickets[{index}].ticket_id: duplicate ticket id")
        seen.add(ticket.ticket_id)
        tickets.append(ticket)
    if not tickets:
        raise SchemaError("tickets: must contain at least one row")
    return tuple(tickets)


def input_hashes(directory: Path = EXAMPLE_DIR) -> tuple[tuple[str, str], ...]:
    return tuple((name, sha256_bytes((directory / name).read_bytes())) for name in INPUT_FILES)


def uv_lock_sha256() -> str | None:
    path = REPO_ROOT / "uv.lock"
    return sha256_bytes(path.read_bytes()) if path.is_file() else None


# --------------------------------------------------------------------------- #
# Verification (offline, fixture provider)
# --------------------------------------------------------------------------- #


def verify(directory: Path, inputs: Path = EXAMPLE_DIR) -> FreshRun:
    """Lock, verify and replay the authored evaluation data into the NEW ``directory``."""
    directory.mkdir(parents=False, exist_ok=False)
    responses = inputs / RESPONSES_FILE
    calibration = inputs / "calibration.jsonl"
    verification = inputs / "verification.jsonl"
    lock_path = directory / LOCK_FILE_NAME
    lock = lock_run(
        inputs / "contract.toml",
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
    return FreshRun(lock, lock_path, bundle, bundle_path, replayed)


# --------------------------------------------------------------------------- #
# Recorded runs
# --------------------------------------------------------------------------- #


def record(destination: Path, *, source_commit: str) -> Producer:
    """Produce one new recorded run and its producer identity; never overwrites."""
    _hex("source_commit", source_commit, COMMIT_HEX)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fresh = verify(destination)
    if fresh.replayed != fresh.bundle.verdict:
        raise RuntimeError("fresh replay does not equal the recorded verdict")
    producer = Producer(
        PRODUCER_FORMAT,
        actseal.__version__,
        fresh.lock.implementation_sha256,
        fresh.lock.replay_engine_version,
        fresh.lock.sha256,
        fresh.bundle.verdict.status,
        source_commit,
        uv_lock_sha256(),
        input_hashes(),
    )
    with (destination / PRODUCER_FILE).open("x", encoding="utf-8", newline="") as handle:
        handle.write(producer.to_json())
    return producer


def load_producer(run_dir: Path) -> Producer:
    """Strictly decode ``PRODUCER.json``; every defect is :class:`SchemaError`."""
    value = strict_json_loads(read_input_text(run_dir / PRODUCER_FILE))
    if type(value) is not dict or set(value) != PRODUCER_KEYS:
        raise SchemaError("producer: unexpected field set")
    if value["format"] != PRODUCER_FORMAT:
        raise SchemaError("producer.format: unsupported format")
    status = _text("producer.verdict_status", value["verdict_status"])
    if status not in STATUSES:
        raise SchemaError("producer.verdict_status: unsupported value")
    uv_lock = value["uv_lock_sha256"]
    inputs = value["inputs"]
    if type(inputs) is not dict or set(inputs) != set(INPUT_FILES):
        raise SchemaError("producer.inputs: must list exactly the four input files")
    _text("producer.note", value["note"])
    return Producer(
        PRODUCER_FORMAT,
        _text("producer.actseal_version", value["actseal_version"]),
        _hex("producer.implementation_sha256", value["implementation_sha256"], SHA256_HEX),
        _text("producer.replay_engine_version", value["replay_engine_version"]),
        _hex("producer.lock_sha256", value["lock_sha256"], SHA256_HEX),
        status,
        _hex("producer.source_commit", value["source_commit"], COMMIT_HEX),
        None if uv_lock is None else _hex("producer.uv_lock_sha256", uv_lock, SHA256_HEX),
        tuple(
            (name, _hex(f"producer.inputs.{name}", inputs[name], SHA256_HEX))
            for name in INPUT_FILES
        ),
    )


def recorded_runs(root: Path = RECORDED_DIR) -> tuple[Path, ...]:
    """Every recorded run directory, sorted by name."""
    if not root.is_dir():
        return ()
    return tuple(sorted(path for path in root.iterdir() if path.is_dir()))


def _recorded_lock(run_dir: Path, producer: Producer) -> PlanLock:
    lock = parse_lock(read_input_text(run_dir / LOCK_FILE_NAME))
    if lock.sha256 != producer.lock_sha256:
        raise SchemaError("lock.sha256: does not match PRODUCER.json")
    if lock.implementation_sha256 != producer.implementation_sha256:
        raise SchemaError("lock.implementation_sha256: does not match PRODUCER.json")
    if lock.replay_engine_version != producer.replay_engine_version:
        raise SchemaError("lock.replay_engine_version: does not match PRODUCER.json")
    return lock


def _check_archive_agreement(
    run_dir: Path, producer: Producer, lock: PlanLock, recorded: dict[str, bytes]
) -> None:
    """Example-specific agreement checks; general validity belongs to the core replay.

    The root ``lock.json`` must be the bundle's ``lock.json`` byte for byte;
    the archived contract must be the frozen ``contract.toml``; the archived
    model identity must be the current fixture identity; the bundle's datasets
    and the producer's recorded input hashes must be the committed authored
    inputs. A consistently rewritten archive (changed policy, data or fixture
    with every hash recomputed) is caught here even when it would replay.
    """
    if read_input_text(run_dir / LOCK_FILE_NAME).encode("utf-8") != recorded[LOCK_FILE]:
        raise IntegrityError("lock.json: root copy differs from the bundle copy")
    if lock.contract != parse_contract(EXAMPLE_DIR / "contract.toml"):
        raise IntegrityError("lock.contract: differs from the frozen contract.toml")
    if lock.model_identity != FixtureModel(EXAMPLE_DIR / RESPONSES_FILE).identity():
        raise IntegrityError("lock.model_identity: differs from the current fixture identity")
    for name in (CALIBRATION_FILE, VERIFICATION_FILE):
        if recorded[name] != (EXAMPLE_DIR / name).read_bytes():
            raise IntegrityError(f"{name}: bundle dataset differs from the committed input")
    if producer.inputs != input_hashes():
        raise IntegrityError("producer.inputs: differ from the committed authored inputs")


def _check_reproduction(
    name: str, recorded: dict[str, bytes], fresh: FreshRun, report: Report
) -> None:
    """Records, faults and the verdict (apart from the seal) depend only on the inputs."""
    fresh_files = read_bundle_files(fresh.bundle_path)
    for file_name in (RECORDS_FILE, FAULTS_FILE):
        if recorded[file_name] != fresh_files[file_name]:
            report.error(f"{name}: {file_name} differs from the fresh run")
    recorded_verdict = decode_document(VERDICT_FILE, recorded[VERDICT_FILE], Verdict)
    if replace(recorded_verdict, lock_sha256=fresh.lock.sha256) != fresh.replayed:
        report.error(f"{name}: verdict differs from the fresh run beyond the lock seal")


def _check_replay(
    name: str, run_dir: Path, producer: Producer, recorded: dict[str, bytes], report: Report
) -> bool:
    """Core replay owns general validation: the result must be non-ERROR and equal the record."""
    recorded_verdict = decode_document(VERDICT_FILE, recorded[VERDICT_FILE], Verdict)
    replayed = replay(run_dir / EVIDENCE_DIRECTORY, expected_lock_sha256=producer.lock_sha256)
    running = implementation_fingerprint()
    if replayed.status != "ERROR" and replayed == recorded_verdict:
        how = "exact" if producer.implementation_sha256 == running else "registry-approved"
        report.ok(f"{name}: replay equals the recorded {replayed.status} ({how} implementation)")
        return True
    report.error(
        f"{name}: replay {replayed.status} {list(replayed.reasons)} does not reproduce the "
        f"recorded {recorded_verdict.status}; the archive is damaged or its producer "
        f"{producer.implementation_sha256[:FINGERPRINT_PREFIX]} is not supported by the running "
        f"implementation {running[:FINGERPRINT_PREFIX]} (no registry approval); bytes preserved"
    )
    return False


def check_recorded(run_dir: Path, fresh: FreshRun, report: Report) -> bool:
    """Check one active recorded run (V1-020); return whether it passed every check."""
    name = f"recorded/{run_dir.name}"
    try:
        producer = load_producer(run_dir)
        lock = _recorded_lock(run_dir, producer)
        recorded = read_bundle_files(run_dir / EVIDENCE_DIRECTORY)
        _check_archive_agreement(run_dir, producer, lock, recorded)
    except (ActsealError, OSError) as exc:
        report.error(f"{name}: {exc}")
        return False
    before = report.errors
    _check_reproduction(name, recorded, fresh, report)
    replayed = _check_replay(name, run_dir, producer, recorded, report)
    return replayed and report.errors == before


def check_all_recorded(fresh: FreshRun, recorded_root: Path, report: Report) -> tuple[Path, ...]:
    """Every active recorded run must pass; a missing recording is an error."""
    runs = recorded_runs(recorded_root)
    if not runs:
        report.error("recorded: no recorded run under recorded/")
    for run_dir in runs:
        check_recorded(run_dir, fresh, report)
    return runs


# --------------------------------------------------------------------------- #
# Application routing
# --------------------------------------------------------------------------- #


def _open_gate(lock: PlanLock, verdict: Verdict, expected_lock_sha256: str) -> ActionGate:
    return ActionGate(
        lock,
        verdict,
        FixtureModel(EXAMPLE_DIR / RESPONSES_FILE),
        expected_lock_sha256=expected_lock_sha256,
    )


def _disposition_matches(disposition: Disposition) -> bool:
    expected = EXPECTED_DISPOSITIONS.get(disposition.ticket_id)
    if expected is None:
        return False
    action, reason, queue = expected
    return (
        disposition.action == action
        and disposition.reason == reason
        and disposition.queue == queue
        and disposition.executed == (action == "ACT")
    )


def check_routing(fresh: FreshRun, report: Report) -> None:
    tickets = load_tickets(EXAMPLE_DIR / TICKETS_FILE)
    try:
        gate = _open_gate(fresh.lock, fresh.replayed, fresh.lock.sha256)
    except GateClosedError as exc:
        report.error(f"routing: gate closed: {exc}")
        return
    queue = LocalQueue()
    dispositions = route_all(gate, tickets, queue)
    if {ticket.ticket_id for ticket in tickets} != set(EXPECTED_DISPOSITIONS):
        report.error("routing: tickets.jsonl does not list exactly the expected tickets")
    for disposition in dispositions:
        if _disposition_matches(disposition):
            report.ok(
                f"routing: {disposition.ticket_id} {disposition.action} ({disposition.reason})"
                f" -> {disposition.path}" + (f" {disposition.queue}" if disposition.queue else "")
            )
        else:
            report.error(f"routing: {disposition.ticket_id} unexpected {disposition}")
    expected_journal: list[tuple[str, str]] = []
    for ticket in tickets:
        expected = EXPECTED_DISPOSITIONS.get(ticket.ticket_id)
        if expected is not None and expected[0] == "ACT" and expected[2] is not None:
            expected_journal.append((expected[2], ticket.ticket_id))
    if list(queue.journal) == expected_journal:
        report.ok(f"routing: queue journal holds exactly the {len(expected_journal)} ACT tickets")
    else:
        report.error(f"routing: queue journal {queue.journal} differs from {expected_journal}")


def _describe(verdict: Verdict) -> str:
    return (
        f"{verdict.status} n={verdict.total} a={verdict.accepted} e={verdict.errors} "
        f"risk=[{verdict.risk.lower:.4f}, {verdict.risk.upper:.4f}] "
        f"coverage=[{verdict.coverage.lower:.4f}, {verdict.coverage.upper:.4f}] "
        f"reasons={list(verdict.reasons)}"
    )


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def _fresh_and_recorded(report: Report, recorded_root: Path, *, demo: bool) -> tuple[Path, ...]:
    """Fresh verification plus every active archive check, then optionally the routing demo.

    The routing demonstration is the only queue operation of ``--check`` and
    runs only when nothing before it failed; ``--route`` skips it and routes
    through a recorded run itself after the same checks.
    """
    with tempfile.TemporaryDirectory(prefix="actseal-action-gate-") as temporary:
        fresh = verify(Path(temporary) / "fresh")
        report.info(f"fresh verification: {_describe(fresh.bundle.verdict)}")
        if fresh.replayed == fresh.bundle.verdict:
            report.ok("fresh replay equals the fresh verdict")
        else:
            report.error("fresh replay differs from the fresh verdict")
        runs = check_all_recorded(fresh, recorded_root, report)
        if not demo:
            return runs
        if report.errors == 0:
            check_routing(fresh, report)
        else:
            report.info("routing: skipped; no queue operation while any active archive fails")
    return runs


def check(out: TextIO, recorded_root: Path = RECORDED_DIR) -> int:
    report = Report(out)
    _fresh_and_recorded(report, recorded_root, demo=True)
    out.write(f"action_gate --check: {report.errors} error(s)\n")
    return EXIT_OK if report.errors == 0 else EXIT_FAILED


def route(out: TextIO, recorded_root: Path = RECORDED_DIR) -> int:
    """Route the tickets through the first recorded run, only after every active archive passed."""
    report = Report(out)
    runs = _fresh_and_recorded(report, recorded_root, demo=False)
    if report.errors or not runs:
        out.write(
            f"route refused: {report.errors} error(s); no queue operation was performed. "
            "An unsupported active archive passes only through an explicit compatibility "
            "review registering both its producer fingerprint and the running fingerprint for "
            "the engine in the packaged registry; excluding it needs a separately recorded "
            "amendment. A new --record run does not repair, replace or reseal it\n"
        )
        return EXIT_FAILED
    run_dir = runs[0]
    producer = load_producer(run_dir)
    lock = _recorded_lock(run_dir, producer)
    verdict = replay(run_dir / EVIDENCE_DIRECTORY, expected_lock_sha256=producer.lock_sha256)
    out.write(f"recorded/{run_dir.name}: replayed {_describe(verdict)}\n")
    try:
        gate = _open_gate(lock, verdict, producer.lock_sha256)
    except GateClosedError as exc:
        out.write(f"gate closed: {exc}\n")
        return EXIT_FAILED
    queue = LocalQueue()
    for disposition in route_all(gate, load_tickets(EXAMPLE_DIR / TICKETS_FILE), queue):
        target = f" {disposition.queue}" if disposition.queue else ""
        out.write(
            f"{disposition.ticket_id}: {disposition.action} ({disposition.reason})"
            f" -> {disposition.path}{target}\n"
        )
    out.write(f"queue journal: {list(queue.journal)}\n")
    return EXIT_OK


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run.py", allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify, route and check recorded runs")
    mode.add_argument("--route", action="store_true", help="route the tickets through the gate")
    mode.add_argument("--record", metavar="DIRECTORY", help="write a new recorded run")
    parser.add_argument(
        "--source-commit", metavar="SHA", help="40-hex producer commit for --record"
    )
    return parser


def main(argv: list[str] | None = None, out: TextIO | None = None) -> int:
    stream = sys.stdout if out is None else out
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code else EXIT_OK
    if args.record is None and args.source_commit is not None:
        parser.print_usage(sys.stderr)
        return EXIT_USAGE
    if args.check:
        return check(stream)
    if args.route:
        return route(stream)
    if args.source_commit is None or COMMIT_HEX.fullmatch(args.source_commit) is None:
        parser.print_usage(sys.stderr)
        return EXIT_USAGE
    producer = record(Path(args.record), source_commit=args.source_commit)
    stream.write(
        f"recorded {args.record}: {producer.verdict_status} lock {producer.lock_sha256} "
        f"implementation {producer.implementation_sha256}\n"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
