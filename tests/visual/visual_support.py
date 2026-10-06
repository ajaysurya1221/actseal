"""Helpers for the asset toolchain tests.

The toolchain lives outside the ``actseal`` package under
``docs/assets/src``. It is imported by path so these tests run in the default
core environment: nothing here needs fontTools or the network.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "docs" / "assets" / "src"
MANIFEST = SRC_DIR / "tools.toml"
FONTTOOLS_WHEEL = "fonttools-4.66.1-py3-none-any.whl"


def load_kit() -> ModuleType:
    """Import ``actseal_assets`` from ``docs/assets/src``."""
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    return importlib.import_module("actseal_assets")


def lock_pin_lines() -> str:
    """The real uv.lock lines that pin the fontTools universal wheel."""
    lines = [
        line
        for line in (REPO_ROOT / "uv.lock").read_text(encoding="utf-8").split("\n")
        if FONTTOOLS_WHEEL in line
    ]
    assert lines, "uv.lock no longer pins the fontTools universal wheel"
    return "\n".join(lines) + "\n"


def make_repo(tmp_path: Path) -> Path:
    """A minimal repository: real manifest, matching lock pin, empty README."""
    src = tmp_path / "docs" / "assets" / "src"
    src.mkdir(parents=True)
    (src / "tools.toml").write_bytes(MANIFEST.read_bytes())
    (tmp_path / "uv.lock").write_text(lock_pin_lines(), encoding="utf-8")
    (tmp_path / "README.md").write_text("# Probe\n", encoding="utf-8")
    return tmp_path


def make_output(
    kit: ModuleType,
    path: str = "probe.svg",
    *,
    kind: str = "svg",
    width: int | None = 1600,
    height: int | None = 400,
    display_width: int | None = 880,
    outlined: bool = False,
    max_bytes: int | None = None,
) -> Any:
    return kit.inventory.Output(
        path=path,
        kind=kind,
        width=width,
        height=height,
        display_width=display_width,
        outlined=outlined,
        max_bytes=max_bytes,
    )


def make_asset(
    kit: ModuleType,
    name: str = "probe",
    *,
    outputs: tuple[Any, ...],
    renderer: Any = None,
    sources: tuple[Any, ...] = (),
    needs: tuple[str, ...] = (),
    task: str = "99",
) -> Any:
    return kit.inventory.Asset(
        name=name,
        priority="test",
        task=task,
        summary="probe asset for tests",
        outputs=outputs,
        sources=sources,
        needs=needs,
        renderer=renderer,
    )


def probe_document(kit: ModuleType, width: int = 1600, height: int = 400) -> Any:
    """A valid figure: title/desc, one rectangle and one readable label."""
    root = kit.svg.document(width, height, title="Probe", desc="A probe figure for tests.")
    root.add("rect", x=10, y=10, width=200, height=100, fill="#1f6feb")
    label = root.add("g", font_family="ui-monospace, monospace", font_size=28)
    label.add("text", x=20, y=70, fill="#ffffff").text("probe")
    return root


def probe_bytes(kit: ModuleType, width: int = 1600, height: int = 400) -> bytes:
    data: bytes = kit.svg.serialize_bytes(probe_document(kit, width, height))
    return data


def png_bytes(width: int, height: int) -> bytes:
    """Only the signature and IHDR; sufficient for header checks."""
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            b"\x00\x00\x00\x0dIHDR",
            width.to_bytes(4, "big"),
            height.to_bytes(4, "big"),
            b"\x08\x06\x00\x00\x00",
        ]
    )


def gif_bytes(width: int, height: int, padding: int = 0) -> bytes:
    return b"".join(
        [
            b"GIF89a",
            width.to_bytes(2, "little"),
            height.to_bytes(2, "little"),
            b"\x00\x00\x00",
            b"\x00" * padding,
            b"\x3b",
        ]
    )
