"""README/docs image references and orphan outputs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from visual.visual_support import make_asset, make_output, probe_bytes

RAW = "https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets"
BLOB = "https://github.com/ajaysurya1221/actseal/blob/v1.0.0/docs/assets"


def _render_probe(kit: ModuleType) -> Any:
    def render(_context: Any) -> Mapping[str, bytes]:
        return {"probe.svg": probe_bytes(kit)}

    return render


def _assets(kit: ModuleType, *, implemented: bool = True) -> tuple[object, ...]:
    renderer = _render_probe(kit) if implemented else None
    return (make_asset(kit, outputs=(make_output(kit, "probe.svg"),), renderer=renderer),)


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
    assert [(ref.line, ref.target, ref.alt, ref.needs_alt) for ref in refs] == [
        (1, "docs/assets/probe.svg", "Hero", True),
        (2, "docs/assets/dark.svg", None, False),
        (2, "docs/assets/probe.svg", "Figure", True),
        (3, "https://img.shields.io/x.svg", "Badge", True),
    ]


def test_single_quoted_unquoted_and_multiline_html_are_parsed(
    kit: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "README.md").write_text(
        "intro\n"
        "<img\n"
        "  src='docs/assets/probe.svg'\n"
        "  alt='Single quoted'\n"
        ">\n"
        "<img src=docs/assets/bare.svg alt=bare>\n"
        "<picture>\n"
        "  <source srcset='docs/assets/a.svg 1x, docs/assets/b.svg 2x'>\n"
        '  <img src="docs/assets/c.svg"\n'
        '       alt="Multi">\n'
        "</picture>\n",
        encoding="utf-8",
    )
    refs = kit.references.scan_references(tmp_path)
    assert [(ref.line, ref.target, ref.alt) for ref in refs] == [
        (2, "docs/assets/probe.svg", "Single quoted"),
        (6, "docs/assets/bare.svg", "bare"),
        (8, "docs/assets/a.svg", None),
        (8, "docs/assets/b.svg", None),
        (9, "docs/assets/c.svg", "Multi"),
    ]


def test_classification(kit: ModuleType) -> None:
    classify = kit.references.classify
    assert classify("docs/assets/x.svg") == "local"
    assert classify(f"{RAW}/x.svg") == "same-repo"
    assert classify(f"{BLOB}/x.svg?raw=true") == "same-repo"
    assert classify("https://img.shields.io/pypi/v/actseal.svg") == "badge"
    assert (
        classify("https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml/badge.svg")
        == "badge"
    )
    assert classify("https://raw.githubusercontent.com/other/repo/main/x.svg") == "external"
    assert classify("https://github.com/other/repo/blob/main/x.svg") == "external"
    assert classify("//cdn.example.com/x.png") == "external"
    assert classify("data:image/png;base64,AAAA") == "external"


def test_recognized_badges_are_exempt(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text(
        "![PyPI](https://img.shields.io/pypi/v/actseal.svg)\n"
        "![CI](https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml/badge.svg)\n",
        encoding="utf-8",
    )
    assert kit.references.check_references(repo, _assets(kit)) == ([], 0)


def test_unrecognized_external_images_fail(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text(
        "![Logo](https://example.com/logo.png)\n"
        "![Other](https://raw.githubusercontent.com/other/repo/main/docs/assets/probe.svg)\n",
        encoding="utf-8",
    )
    errors, checked = kit.references.check_references(repo, _assets(kit))
    assert checked == 2
    other = "https://raw.githubusercontent.com/other/repo/main/docs/assets/probe.svg"
    assert errors == [
        "README.md:1: 'https://example.com/logo.png' is an external image, not a recognized badge",
        f"README.md:2: '{other}' is an external image, not a recognized badge",
    ]


def test_missing_reference_fails(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text("![Hero](docs/assets/hero-light.svg)\n", encoding="utf-8")
    errors, checked = kit.references.check_references(repo, _assets(kit))
    assert checked == 1
    assert errors == ["README.md:1: 'docs/assets/hero-light.svg' does not exist"]


def test_same_repo_absolute_urls_are_validated_locally(kit: ModuleType, repo: Path) -> None:
    (repo / "README.md").write_text(
        f"![Missing]({RAW}/hero-light.svg)\n![Probe]({BLOB}/probe.svg?raw=true)\n",
        encoding="utf-8",
    )
    errors, checked = kit.references.check_references(repo, _assets(kit))
    assert checked == 2
    assert errors == [
        f"README.md:1: '{RAW}/hero-light.svg' does not exist",
        f"README.md:2: '{BLOB}/probe.svg?raw=true' does not exist",
    ]
    _commit_probe(repo, kit)
    errors, _ = kit.references.check_references(repo, _assets(kit))
    assert errors == [f"README.md:1: '{RAW}/hero-light.svg' does not exist"]


def test_declared_existing_reference_passes(kit: ModuleType, repo: Path) -> None:
    _commit_probe(repo, kit)
    (repo / "README.md").write_text("![Probe](docs/assets/probe.svg)\n", encoding="utf-8")
    assert kit.references.check_references(repo, _assets(kit)) == ([], 1)


def test_existing_file_of_unimplemented_asset_fails(kit: ModuleType, repo: Path) -> None:
    _commit_probe(repo, kit)
    (repo / "README.md").write_text("![Probe](docs/assets/probe.svg)\n", encoding="utf-8")
    errors, checked = kit.references.check_references(repo, _assets(kit, implemented=False))
    assert checked == 1
    assert errors == [
        (
            "README.md:1: 'docs/assets/probe.svg' belongs to unimplemented asset 'probe' "
            "(planned in Task 99)"
        )
    ]


def test_missing_or_empty_alt_text_fails(kit: ModuleType, repo: Path) -> None:
    _commit_probe(repo, kit)
    (repo / "README.md").write_text(
        '<img src="docs/assets/probe.svg" alt="">\n'
        '<img src="docs/assets/probe.svg">\n'
        "![](docs/assets/probe.svg)\n"
        '<img src="docs/assets/probe.svg" alt="  ">\n',
        encoding="utf-8",
    )
    errors, _ = kit.references.check_references(repo, _assets(kit))
    assert errors == [
        f"README.md:{line}: image 'docs/assets/probe.svg' has no alt text" for line in (1, 2, 3, 4)
    ]


def test_picture_sources_do_not_need_alt(kit: ModuleType, repo: Path) -> None:
    _commit_probe(repo, kit)
    (repo / "README.md").write_text(
        '<picture><source srcset="docs/assets/probe.svg">'
        '<img src="docs/assets/probe.svg" alt="Probe"></picture>\n',
        encoding="utf-8",
    )
    assert kit.references.check_references(repo, _assets(kit)) == ([], 2)


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
