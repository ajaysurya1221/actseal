"""Packaged authored inputs for ``actseal demo`` (ADR 0013).

The eight resource files beside this marker are byte-identical to the copies
under ``examples/support_triage`` and are authored synthetic data with
``evidence_scope = "demo"``. They are inputs only: the demo generates locks and
evidence from them at run time through the real product pipeline.
"""

from __future__ import annotations

from typing import Final

__all__ = ["RESOURCE_FILES", "RUNS"]

#: The two demonstration runs, in execution order.
RUNS: Final[tuple[str, ...]] = ("bad", "fixed")

#: Every immutable resource file name shipped for the demo.
RESOURCE_FILES: Final[tuple[str, ...]] = tuple(
    f"{run}{suffix}"
    for run in RUNS
    for suffix in (".toml", "_calibration.jsonl", "_verification.jsonl", "_responses.jsonl")
)
