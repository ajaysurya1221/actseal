"""Pinned tool manifest, hash verification and bounded tool execution."""

from __future__ import annotations

import importlib
import io
import json
import stat
import sys
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from visual.visual_support import MANIFEST, REPO_ROOT

APPROVED_PINS = {
    ("fonttools", "fonttools-4.66.1-py3-none-any.whl"): (
        "7234ae9e28db64273fbbfa72caebd0a97e3bdba6b05064114741b9539ef339d0"
    ),
    ("jetbrains-mono", "JetBrainsMono-Regular.ttf"): (
        "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f"
    ),
    ("jetbrains-mono", "JetBrainsMono-Bold.ttf"): (
        "5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb"
    ),
    ("asciinema", "asciinema-aarch64-apple-darwin"): (
        "1f0c76da7855601df93e5dccdf69b7c683b81beff1411e38b3802de1f5fc7a1c"
    ),
    ("agg", "agg-aarch64-apple-darwin"): (
        "742b2b6230529b72f310acb835e9479496000f2eabc97b0993cabe1d7fe70171"
    ),
    ("resvg", "resvg-macos-arm64.zip"): (
        "06440eb5aa14a28cbfc7e40ae39e1ffa71adc051b89fbaa913b4f1d9b905d09f"
    ),
    ("resvg", "resvg-linux-x86_64.tar.gz"): (
        "fa8c26495a187e592c501db15bf9e8a9fdc051d4b2b336b39703d5b59f912b9d"
    ),
}
APPROVED_VERSIONS = {
    "fonttools": ("4.66.1", "MIT"),
    "jetbrains-mono": ("2.304", "OFL-1.1"),
    "asciinema": ("3.2.1", "GPL-3.0-or-later"),
    "agg": ("1.9.0", "GPL-3.0-or-later"),
    "resvg": ("0.48.1", "Apache-2.0 OR MIT"),
}
APPROVED_COMMITS = {
    "jetbrains-mono": "cd5227bd1f61dff3bbd6c814ceaf7ffd95e947d9",
    "asciinema": "70c4af0505fe1dbc7a2170392559d258bd4af92c",
    "agg": "26ca84c02523973198fca28533369edcfc7ed929",
    "resvg": "68b14c4c3bccdb60344c777406486b54c36ec1a4",
}


def test_manifest_matches_the_approved_pins(kit: ModuleType) -> None:
    manifest = kit.tools.load_manifest(MANIFEST)
    assert kit.tools.validate_manifest(manifest) == []
    assert {name: (t.version, t.license) for name, t in manifest.items()} == APPROVED_VERSIONS
    for name, commit in APPROVED_COMMITS.items():
        assert manifest[name].source_commit == commit
    pinned = {
        (name, artifact.filename): artifact.sha256
        for name, tool in manifest.items()
        for artifact in tool.artifacts
        if artifact.verify == "sha256"
    }
    assert pinned == APPROVED_PINS
    notice = next(a for a in manifest["jetbrains-mono"].artifacts if a.filename == "OFL.txt")
    assert notice.verify == "receipt"


def test_lockfile_pins_the_same_fonttools_wheel(kit: ModuleType) -> None:
    manifest = kit.tools.load_manifest(MANIFEST)
    assert kit.tools.check_lock_pin(REPO_ROOT, manifest["fonttools"]) == []
    (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")


def test_lockfile_mismatch_is_reported(kit: ModuleType, tmp_path: Path) -> None:
    manifest = kit.tools.load_manifest(MANIFEST)
    assert kit.tools.check_lock_pin(tmp_path, manifest["fonttools"]) == ["uv.lock is missing"]
    (tmp_path / "uv.lock").write_text("nothing\n", encoding="utf-8")
    errors = kit.tools.check_lock_pin(tmp_path, manifest["fonttools"])
    assert errors == [
        "uv.lock does not pin fonttools-4.66.1-py3-none-any.whl at sha256 7234ae9e28db…"
    ]


def _manifest_with(tmp_path: Path, replacements: dict[str, str]) -> Path:
    text = MANIFEST.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert old in text
        text = text.replace(old, new)
    path = tmp_path / "tools.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_manifest_validation_rejects_bad_entries(kit: ModuleType, tmp_path: Path) -> None:
    path = _manifest_with(
        tmp_path,
        {
            '"742b2b6230529b72f310acb835e9479496000f2eabc97b0993cabe1d7fe70171"': '"abc"',
            'platform = "linux-x86_64"': 'platform = "windows-arm64"',
            "https://github.com/asciinema/agg/blob/v1.9.0/LICENSE": (
                "http://github.com/asciinema/agg/blob/v1.9.0/LICENSE"
            ),
        },
    )
    errors = kit.tools.validate_manifest(kit.tools.load_manifest(path))
    assert errors == [
        "agg: license_url must be https",
        "agg/agg-aarch64-apple-darwin: sha256 is not 64 lowercase hex characters",
        "resvg/resvg-linux-x86_64.tar.gz: unknown platform 'windows-arm64'",
    ]


def test_manifest_structural_errors_raise(kit: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "tools.toml"
    path.write_text('[agg]\nversion = ""\n', encoding="utf-8")
    with pytest.raises(kit.tools.ToolError, match="version must be a non-empty string"):
        kit.tools.load_manifest(path)
    with pytest.raises(kit.tools.ToolError, match="cannot read manifest"):
        kit.tools.load_manifest(tmp_path / "missing.toml")


def test_verified_binary_requires_cache_and_matching_hash(
    kit: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "cache"
    monkeypatch.setenv(kit.tools.CACHE_ENV, str(cache))
    payload = b"#!/bin/sh\nexit 0\n"
    digest = kit.tools.sha256_bytes(payload)
    path = _manifest_with(
        tmp_path, {"742b2b6230529b72f310acb835e9479496000f2eabc97b0993cabe1d7fe70171": digest}
    )
    agg = kit.tools.load_manifest(path)["agg"]
    with pytest.raises(kit.tools.ToolError, match="not cached"):
        kit.tools.verified_binary(tmp_path, agg, "darwin-arm64")
    binary = kit.tools.cached_binary_path(agg, agg.artifact_for("darwin-arm64"))
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"tampered")
    with pytest.raises(kit.tools.ToolError, match="does not match pinned"):
        kit.tools.verified_binary(tmp_path, agg, "darwin-arm64")
    binary.write_bytes(payload)
    assert kit.tools.verified_binary(tmp_path, agg, "darwin-arm64") == binary
    with pytest.raises(kit.tools.ToolError, match="no pinned artifact for platform linux-x86_64"):
        kit.tools.verified_binary(tmp_path, agg, "linux-x86_64")


MEMBER = b"#!/bin/sh\necho resvg\n"
RESVG_MAC_PIN = "06440eb5aa14a28cbfc7e40ae39e1ffa71adc051b89fbaa913b4f1d9b905d09f"
RESVG_LINUX_PIN = "fa8c26495a187e592c501db15bf9e8a9fdc051d4b2b336b39703d5b59f912b9d"


def _zip_with(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _targz_with(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _resvg_pinned_to(
    kit: ModuleType, tmp_path: Path, archive: bytes, *, platform_name: str = "darwin-arm64"
) -> Any:
    pin = RESVG_MAC_PIN if platform_name == "darwin-arm64" else RESVG_LINUX_PIN
    path = _manifest_with(tmp_path, {pin: kit.tools.sha256_bytes(archive)})
    return kit.tools.load_manifest(path)["resvg"]


def test_archive_member_is_bound_to_the_retained_pinned_archive(
    kit: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(kit.tools.CACHE_ENV, str(tmp_path / "cache"))
    archive = _zip_with({"resvg-macos-arm64/resvg": MEMBER, "resvg-macos-arm64/README": b"r"})
    resvg = _resvg_pinned_to(kit, tmp_path, archive)
    artifact = resvg.artifact_for("darwin-arm64")
    binary = kit.tools.cached_binary_path(resvg, artifact)
    retained = kit.tools.cached_archive_path(resvg, artifact)
    binary.parent.mkdir(parents=True)

    # Forged executable plus a coherent receipt, but no retained archive.
    forged = b"#!/bin/sh\necho evil\n"
    binary.write_bytes(forged)
    receipt = kit.tools.receipt_path(tmp_path, resvg, "darwin-arm64")
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "archive_sha256": artifact.sha256,
                "extracted_sha256": kit.tools.sha256_bytes(forged),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(kit.tools.ToolError, match=r"pinned archive .* is not retained"):
        kit.tools.verified_binary(tmp_path, resvg, "darwin-arm64")

    # Retained archive that does not match the pin.
    retained.write_bytes(_zip_with({"resvg": forged}))
    with pytest.raises(kit.tools.ToolError, match=r"archive .* does not match pinned"):
        kit.tools.verified_binary(tmp_path, resvg, "darwin-arm64")

    # Pinned archive present, executable still forged: bytes must differ.
    retained.write_bytes(archive)
    with pytest.raises(kit.tools.ToolError, match="executable bytes differ from member 'resvg'"):
        kit.tools.verified_binary(tmp_path, resvg, "darwin-arm64")

    # Correct executable derived from the pinned archive passes, receipt or not.
    binary.write_bytes(MEMBER)
    receipt.unlink()
    assert kit.tools.verified_binary(tmp_path, resvg, "darwin-arm64") == binary

    # Corrupting the retained archive afterwards is caught on the next verification.
    retained.write_bytes(archive + b"\x00")
    with pytest.raises(kit.tools.ToolError, match=r"archive .* does not match pinned"):
        kit.tools.verified_binary(tmp_path, resvg, "darwin-arm64")


def test_tar_archive_member_verification(
    kit: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(kit.tools.CACHE_ENV, str(tmp_path / "cache"))
    archive = _targz_with({"resvg-linux-x86_64/resvg": MEMBER})
    resvg = _resvg_pinned_to(kit, tmp_path, archive, platform_name="linux-x86_64")
    artifact = resvg.artifact_for("linux-x86_64")
    binary = kit.tools.cached_binary_path(resvg, artifact)
    binary.parent.mkdir(parents=True)
    binary.write_bytes(MEMBER)
    kit.tools.cached_archive_path(resvg, artifact).write_bytes(archive)
    assert kit.tools.verified_binary(tmp_path, resvg, "linux-x86_64") == binary


def test_extract_member_requires_exactly_one_match(kit: ModuleType) -> None:
    extract = kit.tools.extract_member
    assert extract(_zip_with({"a/resvg": MEMBER}), "x.zip", "resvg") == MEMBER
    assert extract(_targz_with({"resvg": MEMBER}), "x.tar.gz", "resvg") == MEMBER
    with pytest.raises(
        kit.tools.ToolError, match="expected exactly one member named 'resvg', found none"
    ):
        extract(_zip_with({"other": b"x"}), "x.zip", "resvg")
    with pytest.raises(kit.tools.ToolError, match="found a/resvg, b/resvg"):
        extract(_zip_with({"a/resvg": b"1", "b/resvg": b"2"}), "x.zip", "resvg")
    with pytest.raises(kit.tools.ToolError, match="unsupported archive type"):
        extract(b"", "x.7z", "resvg")
    with pytest.raises(kit.tools.ToolError, match="cannot read archive"):
        extract(b"not a zip", "x.zip", "resvg")
    with pytest.raises(kit.tools.ToolError, match="cannot read archive"):
        extract(b"not a tar", "x.tar.gz", "resvg")


def test_setup_install_retains_the_archive_and_verifies(
    kit: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(kit.tools.CACHE_ENV, str(tmp_path / "cache"))
    setup = importlib.import_module("setup_tools")
    archive = _zip_with({"resvg": MEMBER})
    resvg = _resvg_pinned_to(kit, tmp_path, archive)
    artifact = resvg.artifact_for("darwin-arm64")
    record = setup.install_binary(resvg, artifact, archive)
    assert record["archive_sha256"] == artifact.sha256
    assert record["extracted_sha256"] == kit.tools.sha256_bytes(MEMBER)
    assert Path(record["archive_retained"]).read_bytes() == archive
    installed = Path(record["installed"])
    assert installed.read_bytes() == MEMBER
    assert installed.stat().st_mode & stat.S_IXUSR
    assert kit.tools.verified_binary(tmp_path, resvg, "darwin-arm64") == installed
    with pytest.raises(kit.tools.ToolError, match="does not match pinned"):
        setup.verify(archive + b"x", artifact)


def test_agg_command_keeps_speed_one_and_idle_limit_beyond_duration(kit: ModuleType) -> None:
    command = kit.tools.agg_command(
        Path("/cache/agg"),
        Path("demo.cast"),
        Path("demo.gif"),
        duration_seconds=33.2,
        font_dir=Path("fonts"),
    )
    assert command[:5] == ["/cache/agg", "--speed", "1", "--idle-time-limit", "35"]
    assert float(command[4]) > 33.2
    assert command[-2:] == ["demo.cast", "demo.gif"]
    assert "JetBrains Mono" in command
    with pytest.raises(kit.tools.ToolError, match="must be positive"):
        kit.tools.agg_command(
            Path("agg"), Path("a"), Path("b"), duration_seconds=0, font_dir=Path("f")
        )


def test_resvg_command_uses_exact_social_size_and_pinned_fonts(kit: ModuleType) -> None:
    command = kit.tools.resvg_command(
        Path("/cache/resvg"),
        Path("social.svg"),
        Path("social.png"),
        width=1280,
        height=640,
        font_dir=Path("fonts"),
    )
    assert command[1:5] == ["--width", "1280", "--height", "640"]
    assert "--skip-system-fonts" in command
    assert command[-2:] == ["social.svg", "social.png"]


def test_platform_key_shape(kit: ModuleType) -> None:
    key = kit.tools.platform_key()
    system, _, arch = key.partition("-")
    assert system in {"darwin", "linux"}
    assert arch


def test_run_tool_is_bounded_and_reports_failure(kit: ModuleType) -> None:
    ok = kit.tools.run_tool([sys.executable, "-c", "print('hi')"], timeout=30)
    assert ok.stdout.strip() == b"hi"
    with pytest.raises(kit.tools.ToolError, match="exited 3"):
        kit.tools.run_tool([sys.executable, "-c", "import sys; sys.exit(3)"], timeout=30)
    with pytest.raises(kit.tools.ToolError, match="failed to run"):
        kit.tools.run_tool([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.5)
    with pytest.raises(kit.tools.ToolError, match="failed to run"):
        kit.tools.run_tool(["/nonexistent/actseal-tool"], timeout=1)


def test_font_checks_require_every_pin_and_the_notice(kit: ModuleType, tmp_path: Path) -> None:
    manifest = kit.tools.load_manifest(MANIFEST)
    font = manifest["jetbrains-mono"]
    assert kit.tools.check_fonts(tmp_path, font) == ([], False)
    font_dir = tmp_path / kit.inventory.FONT_DIR
    font_dir.mkdir(parents=True)
    (font_dir / "JetBrainsMono-Regular.ttf").write_bytes(b"not the pinned font")
    errors, present = kit.tools.check_fonts(tmp_path, font)
    assert present is True
    assert errors == [
        "docs/assets/src/fonts/JetBrainsMono-Regular.ttf: sha256 does not match the pin",
        "docs/assets/src/fonts/JetBrainsMono-Bold.ttf is missing",
        "docs/assets/src/fonts/OFL.txt (upstream font notice) is missing",
    ]
    (font_dir / "OFL.txt").write_text("Copyright 2020 The JetBrains Mono Project Authors\n")
    assert kit.tools.check_font_license(tmp_path) == [
        "docs/assets/src/fonts/OFL.txt lacks 'SIL OPEN FONT LICENSE Version 1.1'"
    ]
