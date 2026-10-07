"""Fixtures for the application example tests; helpers live in ``examples_support``."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from examples.examples_support import EXAMPLE_DIR, load_module


@pytest.fixture(scope="session")
def gate() -> ModuleType:
    """The example's application module."""
    return load_module("gate")


@pytest.fixture(scope="session")
def run() -> ModuleType:
    """The example's entry point module."""
    return load_module("run")


@pytest.fixture(scope="session")
def generator() -> ModuleType:
    """The example's deterministic data generator."""
    return load_module("generate_data")


@pytest.fixture(scope="session")
def fresh(run: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One fresh offline verification of the committed example data (lock, bundle, replay)."""
    return run.verify(tmp_path_factory.mktemp("fresh") / "run")


@pytest.fixture
def responses() -> Path:
    return EXAMPLE_DIR / "responses.jsonl"
