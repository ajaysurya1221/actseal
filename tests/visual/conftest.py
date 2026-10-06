"""Fixtures for the asset toolchain tests; helpers live in ``visual_support``."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from visual.visual_support import load_kit, make_repo


@pytest.fixture(scope="session")
def kit() -> ModuleType:
    """The ``actseal_assets`` package imported from ``docs/assets/src``."""
    return load_kit()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal repository: real manifest, matching lock pin, empty README."""
    return make_repo(tmp_path)
