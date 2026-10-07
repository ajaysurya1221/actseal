"""PROVISIONAL surfaces (docs/stability.md: anything under ``actseal.experimental``).

Nothing in this package is part of the 1.x stability promise. Importing it
loads nothing beyond the standard library; concrete experimental providers live
in submodules and are never imported by the core, by replay or by the runner
unless explicitly registered.
"""

from __future__ import annotations
