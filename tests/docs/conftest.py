"""Fixtures for the documentation tests.

Generated files go to a task-owned temporary directory inside this checkout
(``.actseal/task08-docs-tmp/``, which ``.gitignore`` already excludes) rather
than the system temporary directory, so every comparison can be inspected in
place and nothing escapes the repository. Each fixture use gets a fresh
subdirectory that is removed afterwards.
"""

from __future__ import annotations

import re
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from actseal.runner import demo_run

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
TASK_TMP = ROOT / ".actseal" / "task08-docs-tmp"

#: Documents owned by Task 08; link and wording checks cover exactly these.
OWNED_DOCS: tuple[Path, ...] = (
    DOCS / "concepts.md",
    DOCS / "cli.md",
    DOCS / "python-api.md",
    DOCS / "faq.md",
    DOCS / "quickstart.md",
    DOCS / "providers.md",
    ROOT / "SECURITY.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "AGENTS.md",
)

_FENCE = re.compile(r"```(?P<language>[a-z]*)\n(?P<body>.*?)```", re.DOTALL)


def fences(path: Path, language: str) -> list[str]:
    """Bodies of every fenced block in ``path`` tagged with ``language``, in order."""
    text = path.read_text(encoding="utf-8")
    return [match["body"] for match in _FENCE.finditer(text) if match["language"] == language]


def table_rows(text: str, first_header: str) -> list[list[str]]:
    """Cells of every body row of the first Markdown table whose first header is given."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells and cells[0] == first_header and index + 1 < len(lines):
            rows: list[list[str]] = []
            for body in lines[index + 2 :]:
                if not body.startswith("|"):
                    break
                rows.append(_cells(body))
            return rows
    raise AssertionError(f"table with header {first_header!r} not found")


_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _cells(line: str) -> list[str]:
    """Split one table line on unescaped pipes; ``\\|`` inside a cell is a literal pipe."""
    if not line.startswith("|"):
        return []
    inner = line.strip()[1:-1]
    return [cell.strip().replace("\\|", "|") for cell in _UNESCAPED_PIPE.split(inner)]


@pytest.fixture
def task_tmpdir() -> Iterator[Path]:
    """A fresh, empty directory under the task-owned temporary root; removed afterwards."""
    TASK_TMP.mkdir(parents=True, exist_ok=True)
    directory = TASK_TMP / uuid.uuid4().hex
    directory.mkdir()
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def demo_workspace(task_tmpdir: Path) -> Path:
    """A directory in which ``actseal demo --out ./actseal-demo`` has already run."""
    result = demo_run(task_tmpdir / "actseal-demo")
    assert result.succeeded
    return task_tmpdir
