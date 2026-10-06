"""The demo session runner: exact commands, exit-code checks, pauses, environment, refusal.

Everything here runs through injected process, clock and output doubles or
through ``sys.executable`` children of this test process. No test invokes
``uvx``, ``actseal``, a recorder or a renderer, and no cast, GIF or receipt is
produced.
"""

from __future__ import annotations

import importlib
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from visual.visual_support import SRC_DIR, load_kit

SCRIPT = SRC_DIR / "demo_session.py"

APPROVED_COMMANDS = (
    "uvx --python 3.12 actseal demo --out ./actseal-demo",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence",
    "uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence",
)
APPROVED_EXITS = (0, 0, 1)


@pytest.fixture(scope="session")
def session() -> ModuleType:
    load_kit()
    return importlib.import_module("demo_session")


class Log:
    """Interleaved record of every sleep, command and printed line."""

    def __init__(self, exits: Sequence[int | BaseException]) -> None:
        self.events: list[tuple[str, Any]] = []
        self._exits = list(exits)

    def run(self, argv: Sequence[str]) -> int:
        assert isinstance(argv, tuple), "the runner must receive the step's argument array"
        self.events.append(("run", list(argv)))
        outcome = self._exits.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def sleep(self, seconds: float) -> None:
        self.events.append(("sleep", seconds))

    def emit(self, line: str) -> None:
        self.events.append(("emit", line))

    def of(self, kind: str) -> list[Any]:
        return [payload for name, payload in self.events if name == kind]


def _run(
    session: ModuleType,
    tmp_path: Path,
    exits: Sequence[int | BaseException],
    *,
    pause: float = 4.0,
    hold: float = 3.0,
) -> tuple[int, Log]:
    log = Log(exits)
    code = session.run_session(
        session.STEPS,
        output_dir=tmp_path / session.OUTPUT_DIR_NAME,
        runner=log.run,
        sleep=log.sleep,
        emit=log.emit,
        pauses=session.Pauses(before_command=pause, after_exit=hold),
    )
    return code, log


# --------------------------------------------------------------------------- #
# Command shapes
# --------------------------------------------------------------------------- #


def test_steps_are_exactly_the_three_approved_commands(session: ModuleType) -> None:
    assert tuple(step.label for step in session.STEPS) == APPROVED_COMMANDS
    assert tuple(step.expected_exit for step in session.STEPS) == APPROVED_EXITS
    assert session.EXPECTED_EXITS == APPROVED_EXITS
    for step, text in zip(session.STEPS, APPROVED_COMMANDS, strict=True):
        assert step.argv == tuple(text.split(" "))
        assert isinstance(step.argv, tuple)
        assert all(isinstance(part, str) and part for part in step.argv)


def test_labels_are_derived_from_the_argument_array(session: ModuleType) -> None:
    step = session.Step(("echo", "two words", "$HOME"), 0)
    assert step.label == shlex.join(step.argv)
    assert step.label == "echo 'two words' '$HOME'"


def test_commands_share_one_fresh_output_directory(session: ModuleType) -> None:
    first, fixed, bad = session.STEPS
    assert first.argv[-2:] == ("--out", f"./{session.OUTPUT_DIR_NAME}")
    assert fixed.argv[-1] == f"./{session.OUTPUT_DIR_NAME}/fixed/evidence"
    assert bad.argv[-1] == f"./{session.OUTPUT_DIR_NAME}/bad/evidence"
    assert "--offline" not in first.argv
    assert fixed.argv[1] == bad.argv[1] == "--offline"
    assert all(step.argv[0] == "uvx" for step in session.STEPS)
    assert all(session.PYTHON_PIN in step.argv for step in session.STEPS)


def test_source_never_uses_a_shell(session: ModuleType) -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ("shell=True", "os.system", "eval(", "exec(", "os.popen"):
        assert forbidden not in text
    assert session.__file__ == str(SCRIPT)


# --------------------------------------------------------------------------- #
# Success path and pause boundaries
# --------------------------------------------------------------------------- #


def test_success_requires_zero_zero_one_and_prints_every_exit(
    session: ModuleType, tmp_path: Path
) -> None:
    code, log = _run(session, tmp_path, [0, 0, 1])
    assert code == 0
    assert log.of("run") == [list(step.argv) for step in session.STEPS]
    assert log.of("emit") == [
        "demo-session: 3 commands; expected exits 0, 0, 1",
        f"$ {APPROVED_COMMANDS[0]}",
        "exit 0 (expected 0)",
        f"$ {APPROVED_COMMANDS[1]}",
        "exit 0 (expected 0)",
        f"$ {APPROVED_COMMANDS[2]}",
        "exit 1 (expected 1)",
        "demo-session: all 3 commands exited as expected (0, 0, 1)",
    ]


def test_pauses_happen_only_at_command_boundaries(session: ModuleType, tmp_path: Path) -> None:
    code, log = _run(session, tmp_path, [0, 0, 1], pause=1.5, hold=0.5)
    assert code == 0
    kinds = [name for name, _ in log.events]
    expected = ["emit"]
    for _ in session.STEPS:
        expected += ["sleep", "emit", "run", "emit", "sleep"]
    expected += ["emit"]
    assert kinds == expected
    assert log.of("sleep") == [1.5, 0.5] * 3
    # Every run is bracketed by its printed command line and its printed exit
    # code; a sleep never directly precedes or follows a child process.
    for (name, _), (following, _) in zip(log.events, log.events[1:], strict=False):
        assert not (name == "run" and following == "sleep")
        assert not (name == "sleep" and following == "run")


def test_zero_pauses_never_call_the_clock(session: ModuleType, tmp_path: Path) -> None:
    code, log = _run(session, tmp_path, [0, 0, 1], pause=0, hold=0)
    assert code == 0
    assert log.of("sleep") == []


def test_default_pauses_leave_room_inside_the_demo_window(
    session: ModuleType, kit: ModuleType
) -> None:
    pauses = session.Pauses()
    total = len(session.STEPS) * (pauses.before_command + pauses.after_exit)
    assert 0 < total < kit.inventory.DEMO_MAX_SECONDS - 10
    assert pauses.before_command <= session.MAX_PAUSE_SECONDS
    assert pauses.after_exit <= session.MAX_PAUSE_SECONDS


# --------------------------------------------------------------------------- #
# Failure paths
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("exits", "failing", "observed"),
    [
        ([1], 1, 1),
        ([2], 1, 2),
        ([0, 1], 2, 1),
        ([0, 2], 2, 2),
        ([0, 0, 0], 3, 0),
        ([0, 0, 2], 3, 2),
        ([0, 0, 3], 3, 3),
    ],
)
def test_any_exit_mismatch_stops_the_session_with_exit_one(
    session: ModuleType,
    tmp_path: Path,
    exits: list[int],
    failing: int,
    observed: int,
) -> None:
    code, log = _run(session, tmp_path, exits)
    assert code == 1
    assert len(log.of("run")) == failing
    expected = session.STEPS[failing - 1].expected_exit
    lines = log.of("emit")
    assert lines[-2] == f"exit {observed} (expected {expected})"
    assert lines[-1] == (
        f"demo-session: command {failing} exited {observed}, expected {expected}; stopping"
    )
    assert not any("all 3 commands exited" in line for line in lines)
    # No hold after a mismatch, and no pause before a command that never runs.
    assert log.of("sleep") == [4.0, 3.0] * (failing - 1) + [4.0]


def test_a_command_that_cannot_start_fails_the_session(session: ModuleType, tmp_path: Path) -> None:
    error = session.SessionError("uvx: cannot start process: No such file or directory")
    code, log = _run(session, tmp_path, [0, error])
    assert code == 1
    assert len(log.of("run")) == 2
    assert log.of("emit")[-1] == f"demo-session: command 2 failed to run: {error}"
    assert log.of("sleep") == [4.0, 3.0, 4.0]


def test_run_inherited_reports_a_missing_executable(session: ModuleType, tmp_path: Path) -> None:
    missing = tmp_path / "no-such-tool"
    with pytest.raises(session.SessionError, match="cannot start process"):
        session.run_inherited([str(missing)])
    with pytest.raises(session.SessionError, match="empty command"):
        session.run_inherited([])


# --------------------------------------------------------------------------- #
# Reused output directory
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", ["directory", "file", "dangling-symlink"])
def test_reused_output_path_is_refused_before_anything_runs(
    session: ModuleType, tmp_path: Path, kind: str
) -> None:
    target = tmp_path / session.OUTPUT_DIR_NAME
    if kind == "directory":
        target.mkdir()
    elif kind == "file":
        target.write_text("stale\n", encoding="utf-8")
    else:
        target.symlink_to(tmp_path / "missing-target")
    code, log = _run(session, tmp_path, [0, 0, 1])
    assert code == 2
    assert log.of("run") == []
    assert log.of("sleep") == []
    assert log.of("emit") == [
        f"demo-session: refusing to run: {target} already exists; use a fresh working directory"
    ]


def test_main_refuses_reused_directory_in_cwd(session: ModuleType, tmp_path: Path) -> None:
    (tmp_path / session.OUTPUT_DIR_NAME).mkdir()
    log = Log([0, 0, 1])
    code = session.main([], runner=log.run, sleep=log.sleep, emit=log.emit, cwd=tmp_path)
    assert code == 2
    assert log.of("run") == []
    assert any("already exists" in line for line in log.of("emit"))


def test_refusal_message_for_a_free_path_is_none(session: ModuleType, tmp_path: Path) -> None:
    assert session.refuse_existing_output(tmp_path / "fresh") is None


# --------------------------------------------------------------------------- #
# Process shape: inherited output, closed stdin, allowlisted environment
# --------------------------------------------------------------------------- #


def test_run_inherited_passes_arrays_closed_stdin_and_allowlisted_env(
    session: ModuleType,
) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def spawn(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 7)

    source = {"PATH": "/bin", "HOME": "/h", "JEV_API_KEY": "secret", "AWS_SECRET": "x"}
    code = session.run_inherited(("uvx", "--python", "3.12"), spawn=spawn, environment=source)
    assert code == 7
    assert calls == [
        (
            ["uvx", "--python", "3.12"],
            {"stdin": subprocess.DEVNULL, "env": {"PATH": "/bin", "HOME": "/h"}},
        )
    ]
    args, kwargs = calls[0]
    assert isinstance(args, list)
    assert "shell" not in kwargs
    assert "stdout" not in kwargs
    assert "stderr" not in kwargs
    assert "capture_output" not in kwargs
    assert "input" not in kwargs


def test_allowlisted_environment_copies_only_named_present_keys(session: ModuleType) -> None:
    source = {
        "TERM": "xterm-256color",
        "PATH": "/usr/bin",
        "OPENAI_API_KEY": "nope",
        "AUTHORIZATION": "Bearer nope",
        "SHELL": "/bin/zsh",
        "LC_ALL": "C.UTF-8",
    }
    env = session.allowlisted_environment(source)
    assert env == {"PATH": "/usr/bin", "TERM": "xterm-256color", "LC_ALL": "C.UTF-8"}
    assert list(env) == [name for name in session.ENV_ALLOWLIST if name in source]
    assert session.allowlisted_environment({}) == {}
    assert all(name.isupper() for name in session.ENV_ALLOWLIST)
    # Names that carry a credential *value* are never allowlisted. Two names
    # configure where uv looks for credentials and are deliberately forwarded
    # with task-owned empty targets: an existing empty netrc file and an
    # empty credential-store directory. They are listed explicitly rather
    # than loosening the word check.
    secret_words = {"KEY", "API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIALS", "NETRC"}
    safe_path_names = {"NETRC", "UV_CREDENTIALS_DIR"}
    for name in session.ENV_ALLOWLIST:
        if name in safe_path_names:
            continue
        assert not secret_words & set(name.split("_")), name
    assert safe_path_names <= set(session.ENV_ALLOWLIST)


SESSION_ROOT = "/recording-session"
CONTROLLED_PREFIX = {
    "PATH": "/usr/bin",
    "HOME": "/Users/operator",
    "TERM": "xterm-256color",
    "LANG": "en_US.UTF-8",
    "SHELL": "/bin/sh",
    "UV_CACHE_DIR": f"{SESSION_ROOT}/uv-cache",
    "UV_TOOL_DIR": f"{SESSION_ROOT}/uv-tools",
    "UV_NO_CONFIG": "1",
    "UV_NO_ENV_FILE": "1",
    "UV_DEFAULT_INDEX": "https://pypi.org/simple",
    "UV_KEYRING_PROVIDER": "disabled",
    "NETRC": f"{SESSION_ROOT}/netrc",
    "UV_CREDENTIALS_DIR": f"{SESSION_ROOT}/uv-credentials",
    "ASCIINEMA_CONFIG_HOME": f"{SESSION_ROOT}/asciinema-config",
    "ASCIINEMA_STATE_HOME": f"{SESSION_ROOT}/asciinema-state",
}
#: Index, source, find-links, credential and configuration overrides that must
#: never reach a child even when the parent environment carries them.
FORBIDDEN_OVERRIDES = (
    "UV_INDEX",
    "UV_INDEX_URL",
    "UV_EXTRA_INDEX_URL",
    "UV_FIND_LINKS",
    "UV_INDEX_STRATEGY",
    "UV_PUBLISH_TOKEN",
    "UV_PUBLISH_USERNAME",
    "UV_PUBLISH_PASSWORD",
    "UV_CONFIG_FILE",
    "UV_PYTHON",
    "UV_PRERELEASE",
    "UV_INSECURE_HOST",
    "UV_NATIVE_TLS",
    "UV_OFFLINE",
    "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL",
    "PIP_FIND_LINKS",
    "UV_PUBLISH_CHECK_URL",
    "UV_HTTP_TIMEOUT",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "XDG_CONFIG_HOME",
    "VIRTUAL_ENV",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "CODEX_HOME",
)


def test_controlled_prefix_values_reach_children_and_overrides_do_not(
    session: ModuleType,
) -> None:
    source = {
        **CONTROLLED_PREFIX,
        **dict.fromkeys(FORBIDDEN_OVERRIDES, "must-not-pass"),
    }
    env = session.allowlisted_environment(source)
    for name in (
        "UV_CACHE_DIR",
        "UV_TOOL_DIR",
        "UV_NO_CONFIG",
        "UV_NO_ENV_FILE",
        "UV_DEFAULT_INDEX",
        "UV_KEYRING_PROVIDER",
        "NETRC",
        "UV_CREDENTIALS_DIR",
        "PATH",
        "HOME",
        "TERM",
        "LANG",
    ):
        assert env[name] == CONTROLLED_PREFIX[name]
    assert env["UV_DEFAULT_INDEX"] == "https://pypi.org/simple"
    assert env["UV_KEYRING_PROVIDER"] == "disabled"
    # The two credential-location names carry task-owned paths, never values.
    assert env["NETRC"] == f"{SESSION_ROOT}/netrc"
    assert env["UV_CREDENTIALS_DIR"] == f"{SESSION_ROOT}/uv-credentials"
    assert env["NETRC"] != env["HOME"]
    assert not env["NETRC"].startswith(env["HOME"])
    assert not env["UV_CREDENTIALS_DIR"].startswith(env["HOME"])
    assert not set(env) & set(FORBIDDEN_OVERRIDES)
    assert not set(session.ENV_ALLOWLIST) & set(FORBIDDEN_OVERRIDES)
    # The recorder's own configuration roots are for the recorder, not for uvx.
    assert "ASCIINEMA_CONFIG_HOME" not in env
    assert "ASCIINEMA_STATE_HOME" not in env
    assert "SHELL" not in env
    # Only one uv name family is forwarded: task-owned paths plus the safety settings.
    uv_names = [name for name in session.ENV_ALLOWLIST if name.startswith("UV_")]
    assert uv_names == [
        "UV_CACHE_DIR",
        "UV_TOOL_DIR",
        "UV_PYTHON_INSTALL_DIR",
        "UV_NO_CONFIG",
        "UV_NO_ENV_FILE",
        "UV_DEFAULT_INDEX",
        "UV_KEYRING_PROVIDER",
        "UV_CREDENTIALS_DIR",
    ]
    assert "NETRC" in session.ENV_ALLOWLIST


def test_home_is_forwarded_unchanged_not_repurposed(session: ModuleType) -> None:
    env = session.allowlisted_environment(CONTROLLED_PREFIX)
    assert env["HOME"] == CONTROLLED_PREFIX["HOME"]
    assert "HOME" in session.ENV_ALLOWLIST
    text = SCRIPT.read_text(encoding="utf-8")
    assert "HOME=" not in text
    assert "CODEX_HOME" not in text


def test_allowlisted_environment_defaults_to_the_process_environment(
    session: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TERM", "probe-term")
    monkeypatch.setenv("DEMO_SESSION_PROBE_SECRET", "must-not-pass")
    env = session.allowlisted_environment()
    assert env["TERM"] == "probe-term"
    assert "DEMO_SESSION_PROBE_SECRET" not in env
    assert set(env) <= set(session.ENV_ALLOWLIST)


def test_child_output_streams_unchanged_and_exit_is_real(
    session: ModuleType, capfd: pytest.CaptureFixture[str]
) -> None:
    program = (
        "import sys\n"
        "sys.stdout.write('out line\\n\\x1b[31mred\\x1b[0m\\n')\n"
        "sys.stderr.write('err line\\n')\n"
        "sys.stdout.flush()\n"
        "print(repr(sys.stdin.read()))\n"
        "sys.exit(3)\n"
    )
    code = session.run_inherited((sys.executable, "-c", program))
    out, err = capfd.readouterr()
    assert code == 3
    assert out == "out line\n\x1b[31mred\x1b[0m\n''\n"
    assert err == "err line\n"


def test_session_lines_and_child_output_interleave_in_order(
    session: ModuleType, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    steps = (
        session.Step((sys.executable, "-c", "print('first child')"), 0),
        session.Step((sys.executable, "-c", "import sys; print('second'); sys.exit(4)"), 4),
    )
    code = session.run_session(
        steps,
        output_dir=tmp_path / session.OUTPUT_DIR_NAME,
        runner=session.run_inherited,
        sleep=lambda _seconds: None,
        emit=session.emit_line,
        pauses=session.Pauses(before_command=0, after_exit=0),
    )
    out, err = capfd.readouterr()
    assert code == 0
    assert err == ""
    assert out == (
        "demo-session: 2 commands; expected exits 0, 4\n"
        f"$ {steps[0].label}\n"
        "first child\n"
        "exit 0 (expected 0)\n"
        f"$ {steps[1].label}\n"
        "second\n"
        "exit 4 (expected 4)\n"
        "demo-session: all 2 commands exited as expected (0, 4)\n"
    )


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def test_main_defaults_and_flags_set_the_pauses(session: ModuleType, tmp_path: Path) -> None:
    log = Log([0, 0, 1])
    assert session.main([], runner=log.run, sleep=log.sleep, emit=log.emit, cwd=tmp_path) == 0
    assert log.of("sleep") == [4.0, 3.0] * 3
    assert log.of("emit")[0].startswith("demo-session: child environment names: ")
    assert log.of("run") == [list(step.argv) for step in session.STEPS]

    log = Log([0, 0, 1])
    argv = ["--pause", "1.25", "--hold", "0"]
    assert session.main(argv, runner=log.run, sleep=log.sleep, emit=log.emit, cwd=tmp_path) == 0
    assert log.of("sleep") == [1.25] * 3


@pytest.mark.parametrize(
    "argv",
    [
        ["--pause", "nan"],
        ["--pause", "inf"],
        ["--pause", "-1"],
        ["--hold", "31"],
        ["--hold", "soon"],
        ["--speed", "2"],
        ["extra"],
    ],
)
def test_invalid_options_exit_two_without_running(
    session: ModuleType, tmp_path: Path, argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    log = Log([0, 0, 1])
    assert session.main(argv, runner=log.run, sleep=log.sleep, emit=log.emit, cwd=tmp_path) == 2
    assert log.of("run") == []
    assert log.of("sleep") == []
    assert "usage: demo_session.py" in capsys.readouterr().err


def test_help_exits_zero_without_running(
    session: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = Log([0, 0, 1])
    code = session.main(["--help"], runner=log.run, sleep=log.sleep, emit=log.emit, cwd=tmp_path)
    assert code == 0
    assert log.of("run") == []
    out = capsys.readouterr().out
    assert "--pause SECONDS" in out
    assert "--hold SECONDS" in out
    assert "0, 0, 1" in out


def test_script_refuses_reused_directory_as_a_process(tmp_path: Path) -> None:
    """The script path itself: refusal happens before any child process starts."""
    (tmp_path / "actseal-demo").mkdir()
    result = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert "refusing to run" in result.stdout
    assert "actseal-demo already exists" in result.stdout
    assert "$ uvx" not in result.stdout


def test_script_imports_only_the_standard_library() -> None:
    program = (
        "import sys\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        "import demo_session\n"
        "prefixes = ('actseal', 'fontTools')\n"
        "print(sorted(name for name in sys.modules if name.startswith(prefixes)))\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter and literal script, no user input
        [sys.executable, "-c", program], capture_output=True, text=True, check=False, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"
