"""Typed runner for the three approved Actseal quickstart commands.

    python docs/assets/src/demo_session.py [--pause SECONDS] [--hold SECONDS]

This is the command the recorder captures (see ``recording.md`` beside this
file). It runs exactly the approved quickstart, in order, with argument arrays
and never a shell:

    uvx --python 3.12 actseal demo --out ./actseal-demo
    uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
    uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence

Before each command it prints the command built from the same argument array,
streams the child's stdout and stderr unchanged to the inherited terminal, then
prints the actual exit code next to the expected one (0, 0, 1). Any mismatch or
failure to start a process stops the session with exit 1; exit 0 happens only
after all three commands exited as expected. A reused ``./actseal-demo``
directory is refused before anything runs (exit 2).

Pauses are real ``time.sleep`` calls at command boundaries only, so the capture
stays readable without editing timestamps or trimming output. Children receive
an allowlisted environment and a closed stdin; nothing is captured, filtered,
redacted or replayed here. The module has no dependency outside the standard
library and never imports the asset toolchain or ``actseal``.
"""

from __future__ import annotations

import argparse
import math
import os
import shlex
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

OUTPUT_DIR_NAME = "actseal-demo"
PYTHON_PIN = "3.12"
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
PREFIX = "demo-session:"
MAX_PAUSE_SECONDS = 30.0

#: Only these names are copied from the parent environment into each child.
#: Nothing else is read, so credentials are never inspected, even to redact them.
ENV_ALLOWLIST: tuple[str, ...] = (
    "PATH",
    "HOME",
    "TERM",
    "COLORTERM",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "UV_CACHE_DIR",
    "UV_PYTHON_INSTALL_DIR",
    "UV_TOOL_DIR",
)


class SessionError(RuntimeError):
    """A command could not be started."""


@dataclass(frozen=True, slots=True)
class Step:
    """One approved command and the exit code it must produce."""

    argv: tuple[str, ...]
    expected_exit: int

    @property
    def label(self) -> str:
        """The printed command line, derived from the argument array itself."""
        return shlex.join(self.argv)


STEPS: tuple[Step, ...] = (
    Step(("uvx", "--python", PYTHON_PIN, "actseal", "demo", "--out", f"./{OUTPUT_DIR_NAME}"), 0),
    Step(
        (
            "uvx",
            "--offline",
            "--python",
            PYTHON_PIN,
            "actseal",
            "replay",
            f"./{OUTPUT_DIR_NAME}/fixed/evidence",
        ),
        0,
    ),
    Step(
        (
            "uvx",
            "--offline",
            "--python",
            PYTHON_PIN,
            "actseal",
            "replay",
            f"./{OUTPUT_DIR_NAME}/bad/evidence",
        ),
        1,
    ),
)
EXPECTED_EXITS: tuple[int, ...] = tuple(step.expected_exit for step in STEPS)


@dataclass(frozen=True, slots=True)
class Pauses:
    """Real pauses, in seconds, applied only between commands.

    ``before_command`` precedes each printed command line; ``after_exit``
    follows each printed exit line, so the final one holds the last exit code
    on screen. Neither runs while a child process is executing.
    """

    before_command: float = 4.0
    after_exit: float = 3.0


Runner = Callable[[Sequence[str]], int]
Sleeper = Callable[[float], None]
Emitter = Callable[[str], None]


class Spawner(Protocol):
    """The process primitive ``run_inherited`` needs: argument list, stdin, environment."""

    def __call__(
        self, args: list[str], *, stdin: int, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]: ...


def allowlisted_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Copy only the allowlisted names that are present; never iterate the source."""
    env: Mapping[str, str] = os.environ if source is None else source
    return {name: env[name] for name in ENV_ALLOWLIST if name in env}


def _spawn(
    args: list[str], *, stdin: int, env: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    # stdout/stderr are deliberately not passed: the child inherits the terminal.
    return subprocess.run(args, stdin=stdin, env=env, check=False)  # noqa: S603 - fixed argument arrays from STEPS, no shell


def run_inherited(
    argv: Sequence[str],
    *,
    spawn: Spawner = _spawn,
    environment: Mapping[str, str] | None = None,
) -> int:
    """Run ``argv`` with inherited stdout/stderr, closed stdin and an allowlisted environment."""
    if not argv:
        msg = "empty command"
        raise SessionError(msg)
    try:
        completed = spawn(
            list(argv), stdin=subprocess.DEVNULL, env=allowlisted_environment(environment)
        )
    except OSError as exc:
        msg = f"{argv[0]}: cannot start process: {exc}"
        raise SessionError(msg) from exc
    return int(completed.returncode)


def emit_line(line: str) -> None:
    """Write one line to stdout and flush, so it lands before any child output."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def refuse_existing_output(output_dir: Path) -> str | None:
    """Why the session must not start, or ``None`` when the output path is free."""
    if output_dir.is_symlink() or output_dir.exists():
        return f"refusing to run: {output_dir} already exists; use a fresh working directory"
    return None


def run_session(
    steps: Sequence[Step] = STEPS,
    *,
    output_dir: Path,
    runner: Runner,
    sleep: Sleeper,
    emit: Emitter,
    pauses: Pauses,
) -> int:
    """Run every step in order; stop at the first mismatch or start failure."""
    problem = refuse_existing_output(output_dir)
    if problem is not None:
        emit(f"{PREFIX} {problem}")
        return EXIT_REFUSED
    expected = ", ".join(str(step.expected_exit) for step in steps)
    emit(f"{PREFIX} {len(steps)} commands; expected exits {expected}")
    for index, step in enumerate(steps, start=1):
        if pauses.before_command > 0:
            sleep(pauses.before_command)
        emit(f"$ {step.label}")
        try:
            code = runner(step.argv)
        except SessionError as exc:
            emit(f"{PREFIX} command {index} failed to run: {exc}")
            return EXIT_FAILED
        emit(f"exit {code} (expected {step.expected_exit})")
        if code != step.expected_exit:
            emit(f"{PREFIX} command {index} exited {code}, expected {step.expected_exit}; stopping")
            return EXIT_FAILED
        if pauses.after_exit > 0:
            sleep(pauses.after_exit)
    emit(f"{PREFIX} all {len(steps)} commands exited as expected ({expected})")
    return EXIT_OK


def _seconds(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        msg = f"{text!r} is not a number of seconds"
        raise argparse.ArgumentTypeError(msg) from exc
    if not math.isfinite(value) or value < 0 or value > MAX_PAUSE_SECONDS:
        msg = f"{text!r} must be between 0 and {MAX_PAUSE_SECONDS:g} seconds"
        raise argparse.ArgumentTypeError(msg)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demo_session.py",
        description=(
            "Run the three approved Actseal quickstart commands with visible exit codes; "
            "exit 0 only when they exit 0, 0, 1."
        ),
        allow_abbrev=False,
    )
    defaults = Pauses()
    parser.add_argument(
        "--pause",
        type=_seconds,
        default=defaults.before_command,
        metavar="SECONDS",
        help=f"real pause before each command (default {defaults.before_command:g})",
    )
    parser.add_argument(
        "--hold",
        type=_seconds,
        default=defaults.after_exit,
        metavar="SECONDS",
        help=f"real pause after each printed exit code (default {defaults.after_exit:g})",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Runner = run_inherited,
    sleep: Sleeper = time.sleep,
    emit: Emitter = emit_line,
    cwd: Path | None = None,
) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_REFUSED
    pauses = Pauses(before_command=args.pause, after_exit=args.hold)
    base = Path.cwd() if cwd is None else cwd
    emit(f"{PREFIX} child environment names: {' '.join(allowlisted_environment()) or '(none)'}")
    return run_session(
        STEPS,
        output_dir=base / OUTPUT_DIR_NAME,
        runner=runner,
        sleep=sleep,
        emit=emit,
        pauses=pauses,
    )


if __name__ == "__main__":
    sys.exit(main())
