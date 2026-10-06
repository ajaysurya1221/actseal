"""Authoring-only toolchain for Actseal's documentation assets.

Nothing in this package is imported by the ``actseal`` runtime. Optional
authoring libraries (fontTools) are imported lazily inside the functions that
need them, so the default core test environment stays valid without the
``assets`` dependency group. External tools (asciinema, agg, resvg) are never
committed; ``setup_tools.py`` fetches them into a cache and every execution
re-verifies the pinned SHA-256 first.
"""

from __future__ import annotations

from . import checks, cli, inventory, outline, pipeline, references, svg, tools

__all__ = [
    "checks",
    "cli",
    "inventory",
    "outline",
    "pipeline",
    "references",
    "svg",
    "tools",
]
