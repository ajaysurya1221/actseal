"""Locked parameters are never rounded into a stricter-looking value."""

from __future__ import annotations

import pytest

from actseal import report


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (0.05, "0.05"),
        (0.95, "0.95"),
        (1.0, "1"),
        (0.0, "0"),
        (1e-05, "1e-05"),
        (4e-05, "4e-05"),
        (0.90001, "0.90001"),
        (0.9000049, "0.9000049"),
    ],
)
def test_exact_keeps_every_locked_digit(value: float, text: str) -> None:
    rendered = report._exact(value)
    assert rendered == text
    assert float(rendered) == value


def test_exact_never_collapses_distinct_grid_points() -> None:
    assert report._exact(0.90001) != report._exact(0.9000049)


@pytest.mark.parametrize(
    ("share", "text"),
    [
        (0.05, "5.0"),
        (0.95, "95.0"),
        (1 - 0.05, "95.0"),
        (0.25, "25.0"),
        (1e-05, "0.001"),
        (1 - 1e-06, "99.9999"),
    ],
)
def test_percent_is_one_decimal_only_when_exact(share: float, text: str) -> None:
    assert report._percent(share) == text


def test_small_risk_limit_is_not_shown_as_zero() -> None:
    assert report._percent(1e-05) != "0.0"
    assert report._exact(1e-05) != "0"
