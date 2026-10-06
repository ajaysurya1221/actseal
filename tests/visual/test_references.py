"""README/docs image references and orphan outputs."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

from visual.visual_support import make_asset, make_output, probe_bytes


def _assets(kit: ModuleType) -> tuple[object, ...]:
    return (make_asset(kit, outputs=(make_output(kit, "probe.svg"),)),)


def _commit_probe(repo: Path, kit: ModuleType) -> None:
    (repo / "docs" / "assets" / "probe.svg").write_bytes(probe_bytes(kit))


def test_markdown_html_and_picture_references_are_found(kit: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "![Hero](docs/assets/probe.svg)\n"
        '<picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/dark.svg">'
        '<img alt="Figure" src="docs/assets/probe.svg"></picture>\n'
        "![Badge](https://img.shields.io/x.svg)\n",
        encoding="utf-8",
    )
    refs = kit.references.scan_references(tmp_path)
    assert [(ref.line, ref.target, ref.alt) for ref in refs] == [
        (1, "docs/assets/probe.svg", "Hero"),
        (2, "docs/assets/dark.svg", None),
        (2, "docs/assets/probe.svg", "Figure"),
        (3, "https://img.shields.io/x.svg", "Badge"),
    ]


def test_remote_references_are_ignored(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text("![b](https://img.shields.io/x.svg)\n", encoding="utf-8")
    assert kit.references.check_references(repo, _assets(kit)) == ([], 0)


def test_missing_reference_fails(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text("![Hero](docs/assets/hero-light.svg)\n", encoding="utf-8")
    errors, checked = kit.references.check_references(repo, _assets(kit))
    assert checked == 1
    assert errors == ["README.md:1: 'docs/assets/hero-light.svg' does not exist"]


def test_declared_existing_reference_passes(kit: ModuleType, repo: Path) -> None:
    _commit_probe(repo, kit)
    (repo / "README.md").write_text("![Probe](docs/assets/probe.svg)\n", encoding="utf-8")
    assert kit.references.check_references(repo, _assets(kit)) == ([], 1)


def test_empty_alt_text_fails(kit: ModuleType, repo: Path) -> None:
    _commit_probe(repo, kit)
    (repo / "README.md").write_text('<img src="docs/assets/probe.svg" alt="">\n', encoding="utf-8")
    errors, _ = kit.references.check_references(repo, _assets(kit))
    assert errors == ["README.md:1: image 'docs/assets/probe.svg' has empty alt text"]


def test_undeclared_or_outside_targets_fail(kit: ModuleType, repo: Path) -> None:
    (repo / "docs" / "assets" / "stray.svg").write_bytes(probe_bytes(kit))
    (repo / "docs" / "other.svg").write_bytes(probe_bytes(kit))
    (repo / "docs" / "guide.md").write_text(
        "![Stray](assets/stray.svg)\n![Other](other.svg)\n", encoding="utf-8"
    )
    errors, checked = kit.references.check_references(repo, _assets(kit))
    assert checked == 2
    assert errors == [
        "docs/guide.md:1: 'assets/stray.svg' is not a declared asset output",
        "docs/guide.md:2: 'other.svg' is outside docs/assets",
    ]


def test_orphan_outputs_are_reported(kit: ModuleType, repo: Path) -> None:
    _commit_probe(repo, kit)
    (repo / "docs" / "assets" / "stray.png").write_bytes(b"x")
    (repo / "docs" / "assets" / "src" / "demo.cast").write_bytes(b"{}")
    assert kit.references.check_orphans(repo, _assets(kit)) == [
        "docs/assets/stray.png is not declared by any asset"
    ]
