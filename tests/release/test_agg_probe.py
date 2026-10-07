"""``check_release.py agg-version``: fail-closed probe of the approved agg pin (amendment V1-040).

Everything here is offline. The accepted toolchain's manifest, hash-verification
and bounded-execution helpers are exercised against a temporary manifest whose
``linux-x86_64`` artifact hash is the hash of a local double, and the platform
check is satisfied by patching the toolchain's ``platform_key`` on the very
module object the helper imports. A real Linux execution of the approved pin
happens only in hosted CI; nothing here claims it.
"""

from __future__ import annotations

import hashlib
import os
import types
from pathlib import Path

import pytest
from release_support import ROOT, load_tool, python_script, run_main

AGG_HASH_DARWIN = "742b2b6230529b72f310acb835e9479496000f2eabc97b0993cabe1d7fe70171"
LINUX = "linux-x86_64"
LINUX_FILENAME = "agg-x86_64-unknown-linux-gnu"
EXECUTED = "agg-executed"

_DOUBLE = """
import pathlib
import sys
import time

pathlib.Path({marker!r}).write_text("ran " + " ".join(sys.argv[1:]) + "\\n", encoding="utf-8")
time.sleep({sleep})
sys.stdout.write({stdout!r})
sys.exit({code})
"""


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return load_tool()


@pytest.fixture
def toolchain(tool: types.ModuleType) -> types.ModuleType:
    module = tool._toolchain(ROOT)
    assert isinstance(module, types.ModuleType)
    return module


@pytest.fixture(autouse=True)
def linux(toolchain: types.ModuleType, monkeypatch: pytest.MonkeyPatch) -> object:
    """Satisfy the platform requirement on any host; returns the real ``platform_key``."""
    original = toolchain.platform_key
    monkeypatch.setattr(toolchain, "platform_key", lambda: LINUX)
    return original


def manifest_text(*, version: str = "1.9.0", linux_sha: str | None, kind: str = "binary") -> str:
    linux_block = (
        ""
        if linux_sha is None
        else (
            "\n[[agg.artifacts]]\n"
            f'platform = "{LINUX}"\n'
            f'url = "https://github.com/asciinema/agg/releases/download/v{version}/{LINUX_FILENAME}"\n'
            f'filename = "{LINUX_FILENAME}"\n'
            f'sha256 = "{linux_sha}"\n'
        )
    )
    return (
        "[agg]\n"
        f'version = "{version}"\n'
        'license = "GPL-3.0-or-later"\n'
        f'license_url = "https://github.com/asciinema/agg/blob/v{version}/LICENSE"\n'
        f'source_url = "https://github.com/asciinema/agg/releases/tag/v{version}"\n'
        'source_commit = "26ca84c02523973198fca28533369edcfc7ed929"\n'
        f'kind = "{kind}"\n'
        'purpose = "GIF rendering of the raw recording"\n'
        "\n[[agg.artifacts]]\n"
        'platform = "darwin-arm64"\n'
        f'url = "https://github.com/asciinema/agg/releases/download/v{version}/agg-aarch64-apple-darwin"\n'
        'filename = "agg-aarch64-apple-darwin"\n'
        f'sha256 = "{AGG_HASH_DARWIN}"\n' + linux_block
    )


class Probe:
    """A temporary cache, double binary and manifest pinned to the double's hash."""

    def __init__(self, base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.base = base
        self.cache = base / "cache"
        self.marker = base / EXECUTED
        monkeypatch.setenv("ACTSEAL_ASSET_TOOLS", str(self.cache))
        self.binary = self.cache / "agg-1.9.0" / LINUX_FILENAME
        self.manifest = base / "tools.toml"

    def install(self, *, stdout: str = "agg 1.9.0\n", code: int = 0, sleep: float = 0.0) -> str:
        self.binary.parent.mkdir(parents=True, exist_ok=True)
        python_script(
            self.binary,
            _DOUBLE.format(marker=str(self.marker), stdout=stdout, code=code, sleep=sleep),
        )
        return hashlib.sha256(self.binary.read_bytes()).hexdigest()

    def pin(self, sha: str | None, **overrides: str) -> Path:
        self.manifest.write_text(manifest_text(linux_sha=sha, **overrides), encoding="utf-8")
        return self.manifest

    def executed(self) -> bool:
        return self.marker.exists()


@pytest.fixture
def probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Probe:
    return Probe(tmp_path, monkeypatch)


def failure(tool: types.ModuleType, manifest: Path, **kwargs: float) -> str:
    with pytest.raises(tool.ReleaseCheckError) as excinfo:
        tool.check_agg_version(ROOT, manifest, **kwargs)
    return str(excinfo.value)


# --------------------------------------------------------------------------- #
# Positive path
# --------------------------------------------------------------------------- #


def test_matching_pin_runs_once_and_reports_version_platform_and_hash(
    tool: types.ModuleType, probe: Probe, capsys: pytest.CaptureFixture[str]
) -> None:
    sha = probe.install()
    manifest = probe.pin(sha)
    report = tool.check_agg_version(ROOT, manifest)
    assert report == {
        "agg_version": "agg 1.9.0",
        "platform": LINUX,
        "agg_artifact_sha256": sha,
        "agg_binary": str(probe.binary),
    }
    assert probe.marker.read_text(encoding="utf-8") == "ran --version\n"
    err = capsys.readouterr().err
    assert "agg 1.9.0 on linux-x86_64" in err
    assert sha in err
    assert "hash verified before execution" in err


def test_cli_prints_machine_readable_lines(
    tool: types.ModuleType, probe: Probe, capsys: pytest.CaptureFixture[str]
) -> None:
    sha = probe.install()
    manifest = probe.pin(sha)
    code, out, err = run_main(
        tool, ["--root", str(ROOT), "agg-version", "--manifest", str(manifest)], capsys
    )
    assert code == 0
    assert out == (
        f"agg_version=agg 1.9.0\nplatform={LINUX}\nagg_artifact_sha256={sha}\n"
        f"agg_binary={probe.binary}\n"
    )
    assert "approved manifest artifact" in err


def test_helper_stays_stdlib_only_until_the_probe_runs(tool: types.ModuleType) -> None:
    source = (ROOT / "tools" / "check_release.py").read_text(encoding="utf-8")
    assert "\nimport actseal_assets" not in source
    assert "\nfrom actseal_assets" not in source
    assert tool.AGG_PROBE_TIMEOUT_S == 10.0
    assert tool.AGG_APPROVED_VERSION == "1.9.0"
    assert tool.AGG_PLATFORM == LINUX


# --------------------------------------------------------------------------- #
# Fail-closed paths; nothing executes before verification succeeds
# --------------------------------------------------------------------------- #


def test_non_linux_platform_fails_before_anything_runs(
    tool: types.ModuleType,
    probe: Probe,
    toolchain: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sha = probe.install()
    manifest = probe.pin(sha)
    for platform in ("darwin-arm64", "linux-aarch64", "windows-x86_64"):
        monkeypatch.setattr(toolchain, "platform_key", lambda platform=platform: platform)
        message = failure(tool, manifest)
        assert f"requires an actual {LINUX} runner; running on {platform}" in message
    assert not probe.executed()


def test_real_platform_key_is_consulted_without_a_patch(
    tool: types.ModuleType,
    probe: Probe,
    toolchain: types.ModuleType,
    linux: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert callable(linux)
    monkeypatch.setattr(toolchain, "platform_key", linux)  # restore the real detection
    sha = probe.install()
    manifest = probe.pin(sha)
    if toolchain.platform_key() == LINUX:
        pytest.skip("this host is linux-x86_64; the unpatched path is the positive test")
    assert "requires an actual" in failure(tool, manifest)
    assert not probe.executed()


def test_manifest_without_a_linux_artifact_fails(tool: types.ModuleType, probe: Probe) -> None:
    probe.install()
    manifest = probe.pin(None)
    assert f"no {LINUX} artifact for agg 1.9.0" in failure(tool, manifest)
    assert not probe.executed()


def test_this_worktree_manifest_is_reported_honestly(tool: types.ModuleType, probe: Probe) -> None:
    """The committed manifest here may lack the Linux pin; the probe must say so, not guess."""
    probe.install()
    committed = ROOT / "docs" / "assets" / "src" / "tools.toml"
    text = committed.read_text(encoding="utf-8")
    if LINUX_FILENAME in text:
        pytest.skip("this worktree carries the approved Linux agg pin")
    assert f"no {LINUX} artifact" in failure(tool, committed)
    assert not probe.executed()


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"version": "1.8.0"}, "manifest pins agg 1.8.0, approved pin is 1.9.0"),
        ({"kind": "font"}, "declared as 'font'"),
    ],
)
def test_wrong_manifest_pin_fails(
    tool: types.ModuleType, probe: Probe, overrides: dict[str, str], fragment: str
) -> None:
    sha = probe.install()
    manifest = probe.pin(sha, **overrides)
    assert fragment in failure(tool, manifest)
    assert not probe.executed()


def test_missing_tool_or_invalid_manifest_fails(
    tool: types.ModuleType, probe: Probe, tmp_path: Path
) -> None:
    probe.install()
    empty = tmp_path / "empty.toml"
    empty.write_text("", encoding="utf-8")
    assert "declares no 'agg' tool" in failure(tool, empty)
    broken = tmp_path / "broken.toml"
    broken.write_text(manifest_text(linux_sha="not-a-hash"), encoding="utf-8")
    assert "tool manifest invalid" in failure(tool, broken)
    assert "cannot read manifest" in failure(tool, tmp_path / "absent.toml")
    assert not probe.executed()


def test_missing_cached_binary_fails(tool: types.ModuleType, probe: Probe) -> None:
    manifest = probe.pin("a" * 64)
    message = failure(tool, manifest)
    assert "not cached" in message
    assert "run setup_tools.py" in message
    assert not probe.executed()


def test_tampered_binary_is_rejected_before_execution(tool: types.ModuleType, probe: Probe) -> None:
    sha = probe.install()
    manifest = probe.pin(sha)
    tampered = probe.binary.read_bytes().replace(b"agg 1.9.0", b"agg 1.9.0")
    probe.binary.write_bytes(tampered + b"\n# tampered\n")
    message = failure(tool, manifest)
    assert "does not match pinned" in message
    assert not probe.executed()


@pytest.mark.parametrize(
    "stdout",
    ["agg 1.8.0\n", "agg1.9.0\n", "agg 1.9.0 (release)\n", "AGG 1.9.0\n", "", "1.9.0\n"],
)
def test_unexpected_version_output_fails(tool: types.ModuleType, probe: Probe, stdout: str) -> None:
    sha = probe.install(stdout=stdout)
    manifest = probe.pin(sha)
    message = failure(tool, manifest)
    assert "expected exactly 'agg 1.9.0'" in message
    assert repr(stdout.strip()) in message
    assert probe.executed()


def test_nonzero_exit_fails(tool: types.ModuleType, probe: Probe) -> None:
    sha = probe.install(code=3)
    manifest = probe.pin(sha)
    assert "exited 3" in failure(tool, manifest)


def test_timeout_fails(tool: types.ModuleType, probe: Probe) -> None:
    sha = probe.install(sleep=3.0)
    manifest = probe.pin(sha)
    assert "failed to run" in failure(tool, manifest, timeout=0.5)


def test_probe_never_reads_credentials(
    tool: types.ModuleType, probe: Probe, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JEV_API_KEY", "pypi-not-a-real-credential-value-abcdefghijk")
    monkeypatch.setenv("GH_TOKEN", "ghp_notarealtokenvalue0123456789abcdef")
    sha = probe.install()
    report = tool.check_agg_version(ROOT, probe.pin(sha))
    rendered = " ".join(report.values())
    assert os.environ["JEV_API_KEY"] not in rendered
    assert os.environ["GH_TOKEN"] not in rendered
