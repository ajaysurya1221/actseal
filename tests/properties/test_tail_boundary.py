"""Public-boundary behaviour of ``clopper_pearson_tail`` for out-of-domain numbers.

Task 04 corrected one defect: an integer tail too large for binary64 made
``math.isfinite`` raise ``OverflowError`` and that exception leaked to the
caller. The documented boundary is ``ValueError("tail must be finite")`` with
no echo of the input. Everything else at the boundary (``TypeError`` for
booleans, non-numeric tails and non-plain-integer counts; the other
``ValueError`` messages; every valid interval) is unchanged.
"""

from __future__ import annotations

import enum
import math
import random
import sys
from decimal import Decimal
from fractions import Fraction

import pytest

from actseal.stats import clopper_pearson_tail

GATE_TAIL = 0.0125
# int -> float rounds to nearest: 2**1024 - 2**970 is the halfway point above the
# largest binary64 and is the smallest integer that overflows; one less converts.
FIRST_OVERFLOWING_INT = 2**1024 - 2**970
LAST_CONVERTIBLE_INT = FIRST_OVERFLOWING_INT - 1
SEED_OVERFLOW = 20261011

HUGE_TAILS = (
    10**1000,
    -(10**1000),
    2**1024,
    -(2**1024),
    10**400,
    -(10**400),
    FIRST_OVERFLOWING_INT,
    -FIRST_OVERFLOWING_INT,
)


class _PlainIntSubclass(int):
    pass


class _Count(enum.IntEnum):
    ONE = 1
    TEN = 10


# --------------------------------------------------------------------------- #
# Overflowing integer tails
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("tail", HUGE_TAILS, ids=lambda value: f"bits={value.bit_length()}")
def test_overflowing_integer_tail_is_a_finite_value_error_without_echo(tail: int) -> None:
    with pytest.raises(ValueError, match=r"^tail must be finite$") as caught:
        clopper_pearson_tail(1, 10, tail)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert str(caught.value) == "tail must be finite"
    assert not any(char.isdigit() for char in str(caught.value))


def test_generated_overflowing_tails_never_leak_overflow_error() -> None:
    rng = random.Random(SEED_OVERFLOW)  # noqa: S311
    for _ in range(100):
        magnitude = rng.getrandbits(rng.randint(1025, 4_000)) | (1 << 1024)
        tail = -magnitude if rng.random() < 0.5 else magnitude
        with pytest.raises(ValueError, match=r"^tail must be finite$") as caught:
            clopper_pearson_tail(rng.randint(0, 10), 10, tail)
        assert not isinstance(caught.value, OverflowError)
        assert caught.value.__context__ is None


def test_overflow_boundary_is_exact_at_the_last_convertible_integer() -> None:
    assert math.isfinite(LAST_CONVERTIBLE_INT)
    with pytest.raises(OverflowError):
        float(FIRST_OVERFLOWING_INT)
    with pytest.raises(ValueError, match=r"^tail must be between"):
        clopper_pearson_tail(1, 10, LAST_CONVERTIBLE_INT)
    with pytest.raises(ValueError, match=r"^tail must be between"):
        clopper_pearson_tail(1, 10, -LAST_CONVERTIBLE_INT)
    with pytest.raises(ValueError, match=r"^tail must be finite$"):
        clopper_pearson_tail(1, 10, FIRST_OVERFLOWING_INT)
    with pytest.raises(ValueError, match=r"^tail must be finite$"):
        clopper_pearson_tail(1, 10, -FIRST_OVERFLOWING_INT)


@pytest.mark.parametrize("tail", [0, 1, 2, -1, sys.maxsize, -sys.maxsize])
def test_small_integer_tails_are_numbers_outside_the_range(tail: int) -> None:
    with pytest.raises(ValueError, match=r"^tail must be between"):
        clopper_pearson_tail(1, 10, tail)


@pytest.mark.parametrize("tail", [math.inf, -math.inf, math.nan])
def test_non_finite_float_tails_keep_the_finite_message(tail: float) -> None:
    with pytest.raises(ValueError, match=r"^tail must be finite$") as caught:
        clopper_pearson_tail(1, 10, tail)
    assert caught.value.__context__ is None


# --------------------------------------------------------------------------- #
# TypeError boundary is unchanged
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "tail",
    [True, False, "0.0125", b"0.0125", None, Decimal("0.0125"), Fraction(1, 80), 1j, [0.0125]],
    ids=lambda value: type(value).__name__,
)
def test_boolean_and_non_numeric_tails_are_type_errors(tail: object) -> None:
    with pytest.raises(TypeError, match=r"^tail must be a number$"):
        clopper_pearson_tail(1, 10, tail)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "count",
    [True, False, 1.0, Fraction(1), Decimal(1), "1", None, _PlainIntSubclass(1), _Count.ONE],
    ids=lambda value: type(value).__name__,
)
def test_non_plain_integer_counts_are_type_errors(count: object) -> None:
    with pytest.raises(TypeError, match=r"^successes must be an integer$"):
        clopper_pearson_tail(count, 10, GATE_TAIL)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^n must be an integer$"):
        clopper_pearson_tail(1, count, GATE_TAIL)  # type: ignore[arg-type]


def test_count_type_errors_precede_the_tail_check() -> None:
    with pytest.raises(TypeError, match=r"^successes must be an integer$"):
        clopper_pearson_tail(True, 10, 10**1000)
    with pytest.raises(TypeError, match=r"^n must be an integer$"):
        clopper_pearson_tail(1, 10.0, 10**1000)  # type: ignore[arg-type]
    # A huge tail is reported before the count ranges are examined.
    with pytest.raises(ValueError, match=r"^tail must be finite$"):
        clopper_pearson_tail(11, 10, 10**1000)
    with pytest.raises(ValueError, match=r"^tail must be finite$"):
        clopper_pearson_tail(1, 0, 10**1000)


# --------------------------------------------------------------------------- #
# Valid inputs are untouched by the boundary change
# --------------------------------------------------------------------------- #


def _exact_upper_tail(x: int, n: int, p: Fraction) -> Fraction:
    return sum((math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(x, n + 1)), Fraction(0))


def test_valid_intervals_still_bracket_their_exact_roots() -> None:
    low, high = clopper_pearson_tail(38, 50, GATE_TAIL)
    assert 0.0 < low < 38 / 50 < high < 1.0
    slack = Fraction(1, 2**60) + Fraction.from_float(math.ulp(low))
    target = Fraction.from_float(GATE_TAIL)
    point = Fraction.from_float(low)
    assert _exact_upper_tail(38, 50, point - slack) <= target
    assert _exact_upper_tail(38, 50, point + slack) > target
    assert clopper_pearson_tail(38, 50, GATE_TAIL) == (low, high)
    assert clopper_pearson_tail(0, 1, GATE_TAIL)[0] == 0.0
    assert clopper_pearson_tail(1, 1, GATE_TAIL)[1] == 1.0
