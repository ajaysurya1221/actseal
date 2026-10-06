"""Temporary regeneration, reference comparison and honest reporting."""

from __future__ import annotations

import itertools
import json
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from visual.visual_support import make_asset, make_output, probe_bytes, probe_document


def _errors(report: Any) -> list[str]:
    return [finding.message for finding in report.errors]


def _messages(report: Any, scope: str) -> list[str]:
    return [f.message for f in report.findings if f.scope == scope]


def _deterministic(kit: ModuleType) -> Any:
    def render(_context: Any) -> Mapping[str, bytes]:
        return {"probe.svg": probe_bytes(kit)}

    return make_asset(kit, outputs=(make_output(kit),), renderer=render)


def test_write_then_check_round_trip(kit: ModuleType, repo: Path) -> None:
    asset = _deterministic(kit)
    written = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert written.ok
    assert written.written == ["probe.svg"]
    target = repo / "docs" / "assets" / "probe.svg"
    assert target.read_bytes() == probe_bytes(kit)
    checked = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert checked.ok
    assert checked.checked == ["probe"]
    assert "docs/assets/probe.svg matches regeneration (" in "\n".join(_messages(checked, "probe"))
    assert checked.summary() == "check: 1 asset(s) checked; 0 planned/not implemented; 0 error(s)"


def test_missing_committed_reference_fails_check(kit: ModuleType, repo: Path) -> None:
    report = kit.pipeline.run(repo, mode="check", assets=(_deterministic(kit),))
    assert _errors(report) == ["docs/assets/probe.svg is not committed; run render.py --write"]
    assert not (repo / "docs" / "assets" / "probe.svg").exists()


def test_stale_committed_reference_fails_check(kit: ModuleType, repo: Path) -> None:
    asset = _deterministic(kit)
    kit.pipeline.run(repo, mode="write", assets=(asset,))
    target = repo / "docs" / "assets" / "probe.svg"
    target.write_bytes(target.read_bytes().replace(b"#1f6feb", b"#1f6fec"))
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert len(_errors(report)) == 1
    assert _errors(report)[0].startswith("docs/assets/probe.svg differs at byte ")
    assert "(line 5)" in _errors(report)[0]


def test_nondeterministic_renderer_is_rejected(kit: ModuleType, repo: Path) -> None:
    counter = itertools.count()

    def render(_context: Any) -> Mapping[str, bytes]:
        root = probe_document(kit)
        root.add("rect", x=next(counter), y=0, width=1, height=1, fill="#000")
        data: bytes = kit.svg.serialize_bytes(root)
        return {"probe.svg": data}

    asset = make_asset(kit, outputs=(make_output(kit),), renderer=render)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert _errors(report) == ["nondeterministic renderer: probe.svg changed between runs"]
    assert not (repo / "docs" / "assets" / "probe.svg").exists()


def test_renderer_output_set_must_match_declaration(kit: ModuleType, repo: Path) -> None:
    def render(_context: Any) -> Mapping[str, bytes]:
        return {"other.svg": probe_bytes(kit)}

    asset = make_asset(kit, outputs=(make_output(kit),), renderer=render)
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert _errors(report) == [
        "renderer produced undeclared output other.svg",
        "renderer did not produce declared output probe.svg",
    ]


def test_invalid_output_is_never_written(kit: ModuleType, repo: Path) -> None:
    def render(_context: Any) -> Mapping[str, bytes]:
        root = probe_document(kit)
        root.add("script").text("alert(1)")
        data: bytes = kit.svg.serialize_bytes(root)
        return {"probe.svg": data}

    asset = make_asset(kit, outputs=(make_output(kit),), renderer=render)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    errors = _errors(report)
    assert any("forbidden element <script>" in error for error in errors)
    assert errors[-1] == "docs/assets/probe.svg: refusing to write an invalid output"
    assert not (repo / "docs" / "assets" / "probe.svg").exists()


def test_wrong_dimensions_fail_check_before_comparison(kit: ModuleType, repo: Path) -> None:
    def render(_context: Any) -> Mapping[str, bytes]:
        return {"probe.svg": probe_bytes(kit, 1600, 300)}

    asset = make_asset(kit, outputs=(make_output(kit),), renderer=render)
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert "docs/assets/probe.svg: height='300', expected '400'" in _errors(report)


def test_planned_assets_are_reported_not_passed(kit: ModuleType, repo: Path) -> None:
    planned = make_asset(kit, name="future", outputs=(make_output(kit, "future.svg"),), task="42")
    report = kit.pipeline.run(repo, mode="check", assets=(planned,))
    assert report.ok
    assert report.checked == []
    assert report.planned == ["future"]
    assert _messages(report, "future") == ["not implemented (planned in Task 42)"]
    assert report.summary() == "check: 0 asset(s) checked; 1 planned/not implemented; 0 error(s)"


def test_requesting_a_planned_asset_explicitly_fails(kit: ModuleType, repo: Path) -> None:
    planned = make_asset(kit, name="future", outputs=(make_output(kit, "future.svg"),))
    report = kit.pipeline.run(repo, mode="write", only=("future",), assets=(planned,))
    assert _errors(report) == ["not implemented (planned in Task 99)"]


def test_unknown_only_name_fails(kit: ModuleType, repo: Path) -> None:
    report = kit.pipeline.run(repo, mode="check", only=("nope",), assets=(_deterministic(kit),))
    assert _errors(report) == ["unknown asset(s): nope"]


def test_only_restricts_rendering_but_keeps_global_checks(kit: ModuleType, repo: Path) -> None:
    first = _deterministic(kit)
    second = make_asset(kit, name="second", outputs=(make_output(kit, "second.svg"),))
    (repo / "docs" / "assets" / "stray.svg").write_bytes(b"x")
    report = kit.pipeline.run(repo, mode="check", only=("probe",), assets=(first, second))
    assert _messages(report, "second") == []
    assert "docs/assets/stray.svg is not declared by any asset" in _errors(report)


def test_readme_reference_to_missing_asset_fails(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text("![Hero](docs/assets/hero-light.svg)\n", encoding="utf-8")
    report = kit.pipeline.run(repo, mode="check", assets=())
    assert _errors(report) == ["README.md:1: 'docs/assets/hero-light.svg' does not exist"]


def test_readme_reference_to_declared_output_passes(kit: ModuleType, repo: Path) -> None:
    asset = _deterministic(kit)
    kit.pipeline.run(repo, mode="write", assets=(asset,))
    (repo / "README.md").write_text("![Probe](docs/assets/probe.svg)\n", encoding="utf-8")
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert report.ok
    assert _messages(report, "references") == ["1 image reference(s) checked"]


def test_readme_reference_to_planned_asset_file_fails(kit: ModuleType, repo: Path) -> None:
    planned = make_asset(kit, name="future", outputs=(make_output(kit, "future.svg"),))
    (repo / "docs" / "assets" / "future.svg").write_bytes(probe_bytes(kit))
    (repo / "README.md").write_text("![Future](docs/assets/future.svg)\n", encoding="utf-8")
    report = kit.pipeline.run(repo, mode="check", assets=(planned,))
    assert _errors(report) == [
        (
            "README.md:1: 'docs/assets/future.svg' belongs to unimplemented asset 'future' "
            "(planned in Task 99)"
        )
    ]


def test_implemented_asset_requiring_missing_tool_fails(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(kit.tools.CACHE_ENV, str(repo / "cache"))
    asset = make_asset(
        kit,
        outputs=(make_output(kit),),
        renderer=_deterministic(kit).renderer,
        needs=("resvg", "jetbrains-mono"),
    )
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    errors = _errors(report)
    assert errors[0].startswith("requires resvg 0.48.1: resvg 0.48.1 is not cached at ")
    assert errors[1] == (
        "requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, "
        "JetBrainsMono-Bold.ttf, OFL.txt"
    )
    assert errors[-1] == "skipped rendering because prerequisites failed"
    assert report.checked == []


def test_planned_asset_requirements_are_informational(
    kit: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(kit.tools.CACHE_ENV, str(repo / "cache"))
    asset = make_asset(kit, outputs=(make_output(kit),), needs=("agg",))
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert report.ok
    assert _messages(report, "probe")[0].startswith("requires agg 1.9.0: agg 1.9.0 is not cached")


def test_unknown_tool_requirement_fails(kit: ModuleType, repo: Path) -> None:
    asset = make_asset(kit, outputs=(make_output(kit),), needs=("imagemagick",))
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert _errors(report) == ["requires unknown tool 'imagemagick'"]


def test_committed_recording_is_validated_even_for_planned_assets(
    kit: ModuleType, repo: Path
) -> None:
    source = kit.inventory.Source(path="demo.cast", kind="cast", min_seconds=20, max_seconds=40)
    output = make_output(kit, "demo.gif", kind="gif", width=None, height=None, display_width=None)
    asset = make_asset(kit, name="demo", outputs=(output,), sources=(source,))
    absent = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert absent.ok
    assert "source docs/assets/src/demo.cast is not present" in _messages(absent, "demo")
    cast = repo / "docs" / "assets" / "src" / "demo.cast"
    header = json.dumps({"version": 2, "width": 80, "height": 24})
    cast.write_text(header + "\n" + json.dumps([3.0, "o", "too short"]) + "\n", encoding="utf-8")
    report = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert _errors(report) == ["docs/assets/src/demo.cast: duration 3.00s is below 20s"]


def test_missing_font_license_fails_when_fonts_are_present(kit: ModuleType, repo: Path) -> None:
    manifest = repo / "docs" / "assets" / "src" / "tools.toml"
    text = manifest.read_text(encoding="utf-8")
    regular, bold = b"regular font bytes", b"bold font bytes"
    text = text.replace(
        "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f",
        kit.tools.sha256_bytes(regular),
    ).replace(
        "5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb",
        kit.tools.sha256_bytes(bold),
    )
    manifest.write_text(text, encoding="utf-8")
    font_dir = repo / kit.inventory.FONT_DIR
    font_dir.mkdir(parents=True)
    (font_dir / "JetBrainsMono-Regular.ttf").write_bytes(regular)
    (font_dir / "JetBrainsMono-Bold.ttf").write_bytes(bold)
    report = kit.pipeline.run(repo, mode="check", assets=())
    assert _errors(report) == [
        "docs/assets/src/fonts/OFL.txt (upstream font notice) is missing",
        "aborting before any renderer runs: 1 prerequisite error(s) above (fonts)",
    ]
    (font_dir / "OFL.txt").write_text(
        "Copyright 2020 The JetBrains Mono Project Authors\n"
        "This Font Software is licensed under the SIL Open Font License, Version 1.1.\n"
        "SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n",
        encoding="utf-8",
    )
    report = kit.pipeline.run(repo, mode="check", assets=())
    assert report.ok
    assert _messages(report, "fonts") == ["jetbrains-mono 2.304 present with upstream notice"]


def test_manifest_and_lock_pin_problems_fail(kit: ModuleType, repo: Path) -> None:
    (repo / "uv.lock").write_text("nothing\n", encoding="utf-8")
    report = kit.pipeline.run(repo, mode="check", assets=())
    assert _errors(report) == [
        "fonttools: uv.lock does not pin fonttools-4.66.1-py3-none-any.whl at sha256 7234ae9e28db…",
        "aborting before any renderer runs: 1 prerequisite error(s) above (manifest)",
    ]
    (repo / "docs" / "assets" / "src" / "tools.toml").write_text("[x\n", encoding="utf-8")
    broken = kit.pipeline.run(repo, mode="check", assets=())
    assert len(_errors(broken)) == 1
    assert _errors(broken)[0].startswith("cannot read manifest")


def _counting(kit: ModuleType) -> tuple[Any, list[str]]:
    calls: list[str] = []

    def render(_context: Any) -> Mapping[str, bytes]:
        calls.append("render")
        return {"probe.svg": probe_bytes(kit)}

    return make_asset(kit, outputs=(make_output(kit),), renderer=render), calls


def _pin_fonts_to(kit: ModuleType, repo: Path, regular: bytes, bold: bytes) -> Path:
    manifest = repo / "docs" / "assets" / "src" / "tools.toml"
    text = manifest.read_text(encoding="utf-8")
    text = text.replace(
        "a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f",
        kit.tools.sha256_bytes(regular),
    ).replace(
        "5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb",
        kit.tools.sha256_bytes(bold),
    )
    manifest.write_text(text, encoding="utf-8")
    font_dir = repo / str(kit.inventory.FONT_DIR)
    font_dir.mkdir(parents=True, exist_ok=True)
    (font_dir / "OFL.txt").write_text(
        "Copyright 2020 The JetBrains Mono Project Authors\n"
        "SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n",
        encoding="utf-8",
    )
    return font_dir


def test_wrong_font_bytes_block_rendering_and_writes(kit: ModuleType, repo: Path) -> None:
    font_dir = _pin_fonts_to(kit, repo, b"regular", b"bold")
    (font_dir / "JetBrainsMono-Regular.ttf").write_bytes(b"not the pinned regular")
    (font_dir / "JetBrainsMono-Bold.ttf").write_bytes(b"bold")
    asset, calls = _counting(kit)
    for mode in ("write", "check"):
        report = kit.pipeline.run(repo, mode=mode, assets=(asset,))
        errors = _errors(report)
        assert errors == [
            "docs/assets/src/fonts/JetBrainsMono-Regular.ttf: sha256 does not match the pin",
            "aborting before any renderer runs: 1 prerequisite error(s) above (fonts)",
        ]
        assert report.checked == []
        assert report.written == []
    assert calls == []
    assert not (repo / "docs" / "assets" / "probe.svg").exists()


def test_correct_font_bytes_allow_rendering(kit: ModuleType, repo: Path) -> None:
    font_dir = _pin_fonts_to(kit, repo, b"regular", b"bold")
    (font_dir / "JetBrainsMono-Regular.ttf").write_bytes(b"regular")
    (font_dir / "JetBrainsMono-Bold.ttf").write_bytes(b"bold")
    asset, calls = _counting(kit)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert report.ok
    assert report.written == ["probe.svg"]
    assert calls == ["render", "render"]


def test_lock_pin_mismatch_blocks_rendering_and_writes(kit: ModuleType, repo: Path) -> None:
    (repo / "uv.lock").write_text("nothing\n", encoding="utf-8")
    asset, calls = _counting(kit)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert _errors(report)[-1] == (
        "aborting before any renderer runs: 1 prerequisite error(s) above (manifest)"
    )
    assert calls == []
    assert report.written == []
    assert not (repo / "docs" / "assets" / "probe.svg").exists()


def test_invalid_manifest_entry_blocks_rendering(kit: ModuleType, repo: Path) -> None:
    manifest = repo / "docs" / "assets" / "src" / "tools.toml"
    text = manifest.read_text(encoding="utf-8").replace(
        "https://github.com/asciinema/agg/blob/v1.9.0/LICENSE",
        "http://github.com/asciinema/agg/blob/v1.9.0/LICENSE",
    )
    manifest.write_text(text, encoding="utf-8")
    asset, calls = _counting(kit)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert "agg: license_url must be https" in _errors(report)
    assert calls == []
    assert report.written == []


def test_unfetched_fonts_stay_informational_without_implemented_need(
    kit: ModuleType, repo: Path
) -> None:
    asset, calls = _counting(kit)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert report.ok
    assert _messages(report, "fonts") == ["jetbrains-mono 2.304 not fetched; run setup_tools.py"]
    assert calls == ["render", "render"]


def test_reference_errors_do_not_block_first_write(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text("![Probe](docs/assets/probe.svg)\n", encoding="utf-8")
    asset, calls = _counting(kit)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert _errors(report) == ["README.md:1: 'docs/assets/probe.svg' does not exist"]
    assert report.written == ["probe.svg"]
    assert calls == ["render", "render"]
    assert kit.pipeline.run(repo, mode="check", assets=(asset,)).ok


def test_real_inventory_is_structurally_valid(kit: ModuleType) -> None:
    assert kit.inventory.validate_inventory() == []
    assert kit.inventory.ASSET_NAMES == (
        "hero",
        "how-it-works",
        "architecture",
        "demo",
        "social",
        "where",
        "matrix",
        "boundary",
    )
    social = kit.inventory.get_asset("social")
    assert (social.outputs[0].width, social.outputs[0].height) == (1280, 640)
    demo = kit.inventory.get_asset("demo")
    assert demo.outputs[0].max_bytes == 3_000_000
    assert (demo.sources[0].min_seconds, demo.sources[0].max_seconds) == (20.0, 40.0)
    assert all(output.outlined for output in kit.inventory.get_asset("hero").outputs)
    with pytest.raises(KeyError, match="unknown asset 'logo'"):
        kit.inventory.get_asset("logo")


def test_inventory_validation_catches_bad_declarations(kit: ModuleType) -> None:
    source = kit.inventory.Source(path="../demo.cast", kind="cast")
    bad = (
        make_asset(kit, name="a", outputs=(make_output(kit, "x.svg", kind="png"),)),
        make_asset(kit, name="a", outputs=(make_output(kit, "sub/x.svg"),)),
        make_asset(kit, name="b", outputs=(), sources=(source,)),
    )
    assert kit.inventory.validate_inventory(bad) == [
        "duplicate asset names in inventory",
        "a: x.svg does not end with .png",
        "a: output 'sub/x.svg' must be a plain filename",
        "b: declares no outputs",
        "b: source '../demo.cast' must be a plain filename",
    ]


@pytest.mark.parametrize(
    "name",
    [
        "../escaped.svg",
        "..\\escaped.svg",
        ".hidden.svg",
        "a/b.svg",
        "x..svg",
        "/abs.svg",
        "é.svg",
        "",
    ],
)
def test_plain_filename_rejects_traversal_and_hidden_names(kit: ModuleType, name: str) -> None:
    assert not kit.inventory.is_plain_filename(name)


@pytest.mark.parametrize("name", ["hero-light.svg", "demo.gif", "social.png", "a_b.c.d"])
def test_plain_filename_accepts_ordinary_names(kit: ModuleType, name: str) -> None:
    assert kit.inventory.is_plain_filename(name)


def test_invalid_declarations_abort_before_any_renderer_runs(kit: ModuleType, repo: Path) -> None:
    calls: list[str] = []

    def render(_context: Any) -> Mapping[str, bytes]:
        calls.append("render")
        return {"../escaped.svg": probe_bytes(kit)}

    escaped = make_asset(kit, name="escape", outputs=(make_output(kit, "../escaped.svg"),))
    escaped = kit.inventory.Asset(
        name=escaped.name,
        priority=escaped.priority,
        task=escaped.task,
        summary=escaped.summary,
        outputs=escaped.outputs,
        renderer=render,
    )
    good = _deterministic(kit)
    for mode in ("write", "check"):
        report = kit.pipeline.run(repo, mode=mode, assets=(good, escaped))
        assert not report.ok
        assert "escape: output '../escaped.svg' must be a plain filename" in _errors(report)
        assert _errors(report)[-1] == (
            "aborting before any renderer runs: 1 prerequisite error(s) above (inventory)"
        )
        assert report.checked == []
        assert report.written == []
    assert calls == []
    assert not (repo / "docs" / "escaped.svg").exists()
    assert not (repo / "docs" / "assets" / "probe.svg").exists()


def test_symlinked_output_is_never_followed(kit: ModuleType, repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "probe.svg"
    victim.write_bytes(b"original")
    asset_dir = repo / "docs" / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / "probe.svg").symlink_to(victim)
    asset = _deterministic(kit)
    written = kit.pipeline.run(repo, mode="write", assets=(asset,))
    assert _errors(written) == [
        "docs/assets/probe.svg is a symlink; refusing to follow it; nothing written"
    ]
    assert victim.read_bytes() == b"original"
    assert written.written == []
    checked = kit.pipeline.run(repo, mode="check", assets=(asset,))
    assert _errors(checked) == [
        "docs/assets/probe.svg is a symlink; refusing to follow it; not compared"
    ]


def test_symlinked_asset_directory_is_refused(kit: ModuleType, repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (repo / "docs" / "assets").rename(repo / "docs" / "assets-real")
    (repo / "docs" / "assets").symlink_to(outside, target_is_directory=True)
    (repo / "docs" / "assets-real" / "src").rename(repo / "docs" / "assets" / "src")
    asset = _deterministic(kit)
    report = kit.pipeline.run(repo, mode="write", assets=(asset,))
    errors = _errors(report)
    assert errors[0].startswith("docs/assets resolves to ")
    assert errors[0].endswith(", outside the repository; refusing to continue")
    assert errors[-1] == (
        "aborting before any renderer runs: 1 prerequisite error(s) above (inventory)"
    )
    assert list(outside.iterdir()) == [outside / "src"]
    assert report.written == []


def test_mode_must_be_write_or_check(kit: ModuleType, repo: Path) -> None:
    with pytest.raises(ValueError, match="mode must be"):
        kit.pipeline.run(repo, mode="dry-run", assets=())
