"""Relative links and anchors in the owned documents resolve inside the checkout."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from docs.conftest import OWNED_DOCS, ROOT

_LINK = re.compile(r"(?<!!)\[[^\]]*\]\((?P<target>[^)\s]+)\)")
_HEADING = re.compile(r"^#{1,6}\s+(?P<title>.+?)\s*$", re.MULTILINE)
_IMAGE = re.compile(r"!\[[^\]]*\]\((?P<target>[^)\s]+)\)")


def _anchor(title: str) -> str:
    """GitHub-style heading slug: lowercase, punctuation dropped, spaces to hyphens."""
    cleaned = re.sub(r"[`*_]", "", title)
    cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"[^\w\s-]", "", cleaned.lower())
    return cleaned.strip().replace(" ", "-")


def _links(path: Path) -> list[str]:
    return [match["target"] for match in _LINK.finditer(path.read_text(encoding="utf-8"))]


@pytest.mark.parametrize("document", OWNED_DOCS, ids=lambda path: str(path.relative_to(ROOT)))
def test_relative_links_resolve_and_anchors_exist(document: Path) -> None:
    for target in _links(document):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        location, _, fragment = target.partition("#")
        resolved = document if location == "" else (document.parent / location).resolve()
        assert resolved.exists(), (document.name, target)
        assert ROOT in resolved.parents or resolved == ROOT, (document.name, target)
        if fragment:
            assert resolved.is_file(), (document.name, target)
            headings = {
                _anchor(match["title"])
                for match in _HEADING.finditer(resolved.read_text(encoding="utf-8"))
            }
            assert fragment in headings, (document.name, target)


@pytest.mark.parametrize("document", OWNED_DOCS, ids=lambda path: str(path.relative_to(ROOT)))
def test_owned_documents_reference_no_images(document: Path) -> None:
    """Static P1 assets are not accepted yet; the reference docs embed none."""
    assert _IMAGE.findall(document.read_text(encoding="utf-8")) == [], document.name


def test_every_owned_document_links_to_a_normative_document() -> None:
    normative = ("stability.md", "threat-model.md", "statistical-contract.md", "CONTRACTS.md")
    for document in OWNED_DOCS:
        if document.name == "AGENTS.md":
            continue
        targets = " ".join(_links(document))
        assert any(name in targets for name in normative), document.name
