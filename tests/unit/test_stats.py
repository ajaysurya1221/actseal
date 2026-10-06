"""Independent numerical evidence for ``actseal.stats.clopper_pearson_tail``.

No expected value in this file is produced by calling the implementation under
test. References come from four independent sources:

1. a ``fractions.Fraction`` binomial tail oracle (direct pmf sums, no
   complement or reflection) driving the same 60-step bisection schedule;
2. closed forms for one-term tails evaluated with ``decimal`` at 40 digits;
3. canonical hexadecimal bounds and SciPy-derived golden vectors recorded in
   the approved upstream source;
4. frequentist coverage computed exactly with ``Fraction`` from the binomial
   pmf, which depends on no implementation detail.

Attribution
-----------
Adapted from agent-reliability-ci (ARCI), Copyright 2026 Ajay Surya
Senthilrajan, Apache License 2.0, commit
``d13dd94124cb71d378a4e76224fc115b750e8133``:
https://github.com/ajaysurya1221/agent-reliability-ci

Copied/adapted units:

* ``tests/unit/stats/test_cp_reproducibility.py``: ``CANONICAL``, ``GRID_N``,
  ``GRID_P``, ``GRID_TARGETS``, ``_pmf``, ``_oracle_tail``, ``_oracle_tails``,
  ``_oracle_root``, ``_oracle_interval``, ``_reflection_points``,
  ``_random_probability``, ``_closed_form``, ``LIBM_COUNTS`` and the tests
  ``test_tail_comparison_matches_the_fraction_oracle_on_a_grid``,
  ``test_tail_comparison_is_exact_at_and_beside_equality``,
  ``test_tail_comparison_handles_endpoints``,
  ``test_tail_comparison_matches_the_oracle_on_random_binary64_inputs``,
  ``test_bounds_match_the_fraction_bisection_on_random_counts``,
  ``test_canonical_bounds_are_exact``,
  ``test_canonical_bounds_follow_from_the_fraction_bisection``,
  ``test_edge_counts_keep_their_closed_endpoint``,
  ``test_bounds_do_not_call_libm``,
  ``test_largest_supported_n_at_the_minimum_tail`` and
  ``test_supported_range_is_enforced``.
* ``tests/acceptance/test_stats_gate.py`` lines 19-42: ``CP_GOLDEN`` (values
  recorded upstream from ``scipy.stats.binomtest(...).proportion_ci``) and the
  assertion of ``test_clopper_pearson_matches_exact_reference``.

Local modifications: imports target ``actseal.stats``; golden confidences are
converted to a tail with the upstream expression ``(1.0 - confidence) / 2.0``
because Actseal does not port ``clopper_pearson``; ARCI's frozen gate fixtures
are not used. Everything after the "Actseal additions" marker is original.
ARCI's ``tests/unit/stats/test_stats.py`` was not in the dispatch packet, so
the monotonicity, nesting, symmetry and coverage tests below were written
independently rather than copied.
"""

from __future__ import annotations

import inspect
import math
import random
import sys
from collections.abc import Callable, Iterator
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import accumulate
from pathlib import Path

import pytest

import actseal.stats as stats_module
from actseal.stats import (
    _tail_is_greater,  # the unit under test
    clopper_pearson_tail,
)

GATE_TAIL = 0.0125  # alpha 0.05 split four ways: CONTRACTS section 5
MIN_TAIL = 2.5e-7
MAX_N = 10_000
BISECTION_STEPS = 60

# Canonical bounds of clopper_pearson_tail(x, n, 0.0125), as float.hex().
CANONICAL = (
    (38, 50, "0x1.3260888cc2d7cp-1", "0x1.c333f6b1990a0p-1"),
    (130, 200, "0x1.23a6984ce7bd4p-1", "0x1.730611ce6cb6cp-1"),
    (138, 200, "0x1.38e507468bd6ep-1", "0x1.85f47f46da8e4p-1"),
    (187, 200, "0x1.c4f9e23162ecap-1", "0x1.efadb37e2f212p-1"),
)

GRID_N = (1, 2, 3, 5, 7, 8, 13, 21, 50)
GRID_P = (
    0.0,
    5e-324,
    2.0**-60,
    1e-9,
    0.0125,
    0.25,
    1.0 / 3.0,
    0.5,
    2.0 / 3.0,
    0.75,
    0.9875,
    1.0 - 2.0**-53,
    1.0,
)
GRID_TARGETS = (MIN_TAIL, GATE_TAIL, 0.25, 0.4999999999999999, 0.5, 0.75, 1.0 - MIN_TAIL)

# Golden values recorded upstream from scipy.stats.binomtest(...).proportion_ci. Each row is
# successes, n, confidence, low and high; the tail is half of one minus the confidence.
CP_GOLDEN = [
    (190, 200, 0.975, 0.903744200551, 0.978351375522),
    (130, 200, 0.975, 0.569630393398, 0.724655682038),
    (0, 20, 0.975, 0.0, 0.196759679705),
    (20, 20, 0.975, 0.803240320295, 1.0),
    (19, 20, 0.975, 0.720677509796, 0.999371258630),
    (13, 20, 0.975, 0.377936165362, 0.865327076539),
    (1, 10000, 0.975, 0.000001257877, 0.000637920920),
    (9999, 10000, 0.975, 0.999362079080, 0.999998742123),
    (5000, 10000, 0.975, 0.488744692327, 0.511255307673),
    (190, 200, 0.9875, 0.897867622022, 0.980531985264),
    (3, 7, 0.95, 0.098988278443, 0.815948432360),
]


def _pmf(n: int, p: float) -> list[Fraction]:
    prob = Fraction.from_float(p)
    complement = 1 - prob
    return [math.comb(n, k) * prob**k * complement ** (n - k) for k in range(n + 1)]


def _oracle_tail(x: int, n: int, p: float, *, upper: bool) -> Fraction:
    """Directly summed P(X >= x) or P(X <= x): no complement, no reflection."""
    terms = _pmf(n, p)
    return sum(terms[x:] if upper else terms[: x + 1], Fraction(0))


def _oracle_tails(n: int, p: float) -> Iterator[tuple[int, bool, Fraction]]:
    """Every tail at (n, p): running sums of the mass function, from each end separately."""
    terms = _pmf(n, p)
    lower = list(accumulate(terms))
    upper = list(accumulate(reversed(terms)))[::-1]
    for x in range(n + 1):
        yield x, True, upper[x]
        yield x, False, lower[x]


def _oracle_root(x: int, n: int, tail: float, *, upper: bool) -> float:
    """The gate's 60-step bisection on [0, 1], driven by the Fraction oracle."""
    low, high = 0.0, 1.0
    target = Fraction.from_float(tail)
    for _ in range(BISECTION_STEPS):
        midpoint = (low + high) / 2.0
        greater = _oracle_tail(x, n, midpoint, upper=upper) > target
        if upper == greater:
            high = midpoint
        else:
            low = midpoint
    return (low + high) / 2.0


def _oracle_interval(x: int, n: int, tail: float) -> tuple[float, float]:
    low = 0.0 if x == 0 else _oracle_root(x, n, tail, upper=True)
    high = 1.0 if x == n else _oracle_root(x, n, tail, upper=False)
    return low, high


def _reflection_points(n: int) -> list[float]:
    """Probabilities on and beside the reflection boundary cutoff = (n + 1) p."""
    points: list[float] = []
    for cutoff in range(n + 1):
        p = cutoff / (n + 1)
        if 0.0 < p < 1.0:
            points += [math.nextafter(p, 0.0), p, math.nextafter(p, 1.0)]
    return points


# --- 1. Independent tail oracle ------------------------------------------------------------


@pytest.mark.parametrize("n", GRID_N)
def test_tail_comparison_matches_the_fraction_oracle_on_a_grid(n: int) -> None:
    checked = 0
    for p in (*GRID_P, *_reflection_points(n)):
        for x, upper, exact in _oracle_tails(n, p):
            for target in GRID_TARGETS:
                expected = exact > Fraction.from_float(target)
                assert _tail_is_greater(x, n, p, target, upper=upper) is expected, (x, n, p, target)
                checked += 1
    assert checked >= len(GRID_P) * (n + 1) * 2 * len(GRID_TARGETS)


@pytest.mark.parametrize("n", [1, 2, 3, 4, 7, 8])
def test_tail_comparison_is_exact_at_and_beside_equality(n: int) -> None:
    """Dyadic p gives tails that are binary64 values: equal is not greater; one ulp decides."""
    exercised = 0
    for p in (0.125, 0.25, 0.5, 0.625, 0.75, 0.875):
        for x, upper, exact in _oracle_tails(n, p):
            target = float(exact)
            if not 0.0 < exact < 1.0 or Fraction.from_float(target) != exact:
                continue
            below, above = math.nextafter(target, 0.0), math.nextafter(target, 1.0)
            assert _tail_is_greater(x, n, p, target, upper=upper) is False
            assert _tail_is_greater(x, n, p, below, upper=upper) is True
            assert _tail_is_greater(x, n, p, above, upper=upper) is False
            exercised += 1
    assert exercised >= n


@pytest.mark.parametrize("n", [1, 5, 50])
def test_tail_comparison_handles_endpoints(n: int) -> None:
    for target in (MIN_TAIL, GATE_TAIL, 0.4999999999999999):
        for p in (0.0, 1.0):
            # P(X >= 0) = P(X <= n) = 1 at every p, including the clamped endpoints.
            assert _tail_is_greater(0, n, p, target, upper=True) is True
            assert _tail_is_greater(n, n, p, target, upper=False) is True
        # At p = 0 all mass is at 0; at p = 1 all mass is at n.
        assert _tail_is_greater(1, n, 0.0, target, upper=True) is False
        assert _tail_is_greater(0, n, 0.0, target, upper=False) is True
        assert _tail_is_greater(n, n, 1.0, target, upper=True) is True
        assert _tail_is_greater(n - 1, n, 1.0, target, upper=False) is False


# --- 2. Seeded random binary64 inputs ------------------------------------------------------


def _random_probability(rng: random.Random) -> float:
    draw = rng.random()
    shape = rng.randrange(4)
    if shape == 0:
        return draw
    if shape == 1:
        return math.ldexp(draw, -rng.randrange(1, 64))
    if shape == 2:
        return 1.0 - math.ldexp(draw, -rng.randrange(1, 53))
    return rng.randrange(1, 1 << 12) / (1 << 12)


def test_tail_comparison_matches_the_oracle_on_random_binary64_inputs() -> None:
    rng = random.Random(20261005)  # noqa: S311
    for _ in range(2000):
        n = rng.randint(1, 64)
        x = rng.randint(0, n)
        p = _random_probability(rng)
        target = rng.uniform(MIN_TAIL, 0.5) if rng.random() < 0.75 else rng.random()
        upper = rng.random() < 0.5
        expected = _oracle_tail(x, n, p, upper=upper) > Fraction.from_float(target)
        assert _tail_is_greater(x, n, p, target, upper=upper) is expected, (x, n, p, target, upper)


def test_bounds_match_the_fraction_bisection_on_random_counts() -> None:
    rng = random.Random(5)  # noqa: S311
    cases = [(0, 1), (1, 1), (0, 9), (9, 9), (1, 13), (12, 13)]
    cases += [(rng.randint(0, n), n) for n in (rng.randint(2, 30) for _ in range(14))]
    for x, n in cases:
        tail = rng.choice((MIN_TAIL, GATE_TAIL, rng.uniform(MIN_TAIL, 0.5)))
        assert clopper_pearson_tail(x, n, tail) == _oracle_interval(x, n, tail), (x, n, tail)


# --- 3. Canonical bounds -------------------------------------------------------------------


@pytest.mark.parametrize(("x", "n", "low_hex", "high_hex"), CANONICAL)
def test_canonical_bounds_are_exact(x: int, n: int, low_hex: str, high_hex: str) -> None:
    low, high = clopper_pearson_tail(x, n, GATE_TAIL)
    assert (low.hex(), high.hex()) == (low_hex, high_hex)
    assert (low, high) == (float.fromhex(low_hex), float.fromhex(high_hex))


@pytest.mark.parametrize(("x", "n", "low_hex", "high_hex"), CANONICAL)
def test_canonical_bounds_follow_from_the_fraction_bisection(
    x: int, n: int, low_hex: str, high_hex: str
) -> None:
    low, high = _oracle_interval(x, n, GATE_TAIL)
    assert (low.hex(), high.hex()) == (low_hex, high_hex)


@pytest.mark.parametrize("n", [1, 50, 200])
def test_edge_counts_keep_their_closed_endpoint(n: int) -> None:
    assert clopper_pearson_tail(0, n, GATE_TAIL)[0] == 0.0
    assert clopper_pearson_tail(n, n, GATE_TAIL)[1] == 1.0
    assert clopper_pearson_tail(0, n, GATE_TAIL) == _oracle_interval(0, n, GATE_TAIL)
    assert clopper_pearson_tail(n, n, GATE_TAIL) == _oracle_interval(n, n, GATE_TAIL)


# --- 4. libm independence ------------------------------------------------------------------

LIBM_COUNTS = ((0, 1), (1, 1), (0, 50), (50, 50), (5, 10), (38, 50), (130, 200), (1, 200))


def test_bounds_do_not_call_libm(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {counts: clopper_pearson_tail(*counts, GATE_TAIL) for counts in LIBM_COUNTS}

    def forbidden(name: str) -> Callable[..., float]:
        def call(*args: object) -> float:
            raise AssertionError(f"math.{name}{args} called")

        return call

    for name in ("log", "log1p", "exp", "lgamma", "pow", "sqrt"):
        monkeypatch.setattr(math, name, forbidden(name))

    assert {counts: clopper_pearson_tail(*counts, GATE_TAIL) for counts in LIBM_COUNTS} == expected
    assert clopper_pearson_tail(38, 50, GATE_TAIL) == (
        float.fromhex(CANONICAL[0][2]),
        float.fromhex(CANONICAL[0][3]),
    )
    assert clopper_pearson_tail(MAX_N, MAX_N, MIN_TAIL)[1] == 1.0


# --- 5. Supported range --------------------------------------------------------------------


def _closed_form(x: int, n: int, tail: float) -> tuple[Decimal | None, Decimal | None]:
    """Bounds solvable in closed form (one-term tails), to 40 significant digits."""
    with localcontext() as context:
        context.prec = 40
        t, root = Decimal(tail), Decimal(1) / Decimal(n)
        if x == 0:
            return None, 1 - t**root  # (1 - p)^n = tail
        if x == 1:
            return 1 - (1 - t) ** root, None  # 1 - (1 - p)^n = tail
        if x == n - 1:
            return None, (1 - t) ** root  # 1 - p^n = tail
        if x == n:
            return t**root, None  # p^n = tail
    raise AssertionError("no closed form")


def _assert_within_bisection_tolerance(got: float, reference: Decimal) -> None:
    error = abs(Fraction.from_float(got) - Fraction(reference))
    # The bisection bracket shrinks to 2**-60 or stalls at one ulp of the bound.
    assert error <= max(Fraction(2) ** -60, 2 * Fraction.from_float(math.ulp(got))), (
        got,
        reference,
    )


@pytest.mark.parametrize("x", [0, 1, 9_999, 10_000])
def test_largest_supported_n_at_the_minimum_tail(x: int) -> None:
    n = MAX_N
    low, high = clopper_pearson_tail(x, n, MIN_TAIL)
    assert 0.0 <= low < high <= 1.0
    for got, reference in zip((low, high), _closed_form(x, n, MIN_TAIL), strict=True):
        if reference is None:
            continue
        _assert_within_bisection_tolerance(got, reference)


def test_supported_range_is_enforced() -> None:
    clopper_pearson_tail(1, MAX_N, MIN_TAIL)
    with pytest.raises(ValueError, match="n must be"):
        clopper_pearson_tail(1, MAX_N + 1, MIN_TAIL)
    with pytest.raises(ValueError, match="tail must be"):
        clopper_pearson_tail(1, 10, math.nextafter(MIN_TAIL, 0.0))


# ============================================================================================
# Actseal additions (original, not copied from ARCI)
# ============================================================================================

# --- 6. SciPy-derived golden vectors (upstream acceptance lines 19-42) ----------------------


@pytest.mark.parametrize(("x", "n", "conf", "low", "high"), CP_GOLDEN)
def test_clopper_pearson_matches_exact_reference(
    x: int, n: int, conf: float, low: float, high: float
) -> None:
    got_low, got_high = clopper_pearson_tail(x, n, (1.0 - conf) / 2.0)
    assert got_low == pytest.approx(low, rel=0, abs=1e-9)
    assert got_high == pytest.approx(high, rel=0, abs=1e-9)


def test_golden_confidences_map_onto_the_gate_tail() -> None:
    """The upstream 0.975 confidence is the alpha=0.05, alpha/4 tail Actseal gates with."""
    upstream_tail = (1.0 - 0.975) / 2.0
    assert upstream_tail == pytest.approx(GATE_TAIL, rel=0, abs=2e-17)
    low, high = clopper_pearson_tail(190, 200, GATE_TAIL)
    assert low == pytest.approx(0.903744200551, rel=0, abs=1e-9)
    assert high == pytest.approx(0.978351375522, rel=0, abs=1e-9)


# --- 7. Closed-form oracles across the domain ------------------------------------------------

CLOSED_FORM_N = (1, 2, 3, 5, 20, 50, 200, 1_000, MAX_N)
CLOSED_FORM_TAILS = (MIN_TAIL, 0.00625, GATE_TAIL, 0.025, 0.25, 0.4999999999999999)


@pytest.mark.parametrize("tail", CLOSED_FORM_TAILS)
@pytest.mark.parametrize("n", CLOSED_FORM_N)
def test_one_term_tails_match_decimal_closed_forms(n: int, tail: float) -> None:
    """x in {0, 1, n-1, n} has a one-term tail whose root is an explicit radical."""
    for x in sorted({0, 1, n - 1, n}):
        low, high = clopper_pearson_tail(x, n, tail)
        assert 0.0 <= low <= high <= 1.0
        references = _closed_form(x, n, tail)
        for got, reference in zip((low, high), references, strict=True):
            if reference is None:
                continue
            _assert_within_bisection_tolerance(got, reference)


def test_n_equals_one_bounds_are_the_tail_itself() -> None:
    """Hand-derived: for n=1, P(X>=1)=p and P(X<=0)=1-p, so the roots are t and 1-t."""
    for tail in CLOSED_FORM_TAILS:
        low, high = clopper_pearson_tail(1, 1, tail)
        assert high == 1.0
        _assert_within_bisection_tolerance(low, Decimal(tail))
        low, high = clopper_pearson_tail(0, 1, tail)
        assert low == 0.0
        _assert_within_bisection_tolerance(high, Decimal(1) - Decimal(tail))


def test_hand_reasoned_two_trial_interval() -> None:
    """Hand-derived: n=2, x=1, tail=1/4 gives 1-(1-p)^2=1/4 and 1-p^2=1/4, roots 1-sqrt(3)/2
    and sqrt(3)/2."""
    with localcontext() as context:
        context.prec = 40
        half_root_three = Decimal(3).sqrt() / 2
        low_reference = 1 - half_root_three
        high_reference = half_root_three
    low, high = clopper_pearson_tail(1, 2, 0.25)
    _assert_within_bisection_tolerance(low, low_reference)
    _assert_within_bisection_tolerance(high, high_reference)
    assert low == pytest.approx(0.1339745962155614, rel=0, abs=1e-15)
    assert high == pytest.approx(0.8660254037844386, rel=0, abs=1e-15)


def test_interior_counts_match_the_fraction_bisection_at_every_gate_tail() -> None:
    """Representative interior counts, including the a=0/e=0 style corners, versus the oracle."""
    cases = ((1, 2), (2, 5), (3, 7), (5, 10), (7, 10), (9, 10), (13, 20), (19, 20), (38, 50))
    for tail in (MIN_TAIL, 0.00625, GATE_TAIL, 0.025):
        for x, n in cases:
            assert clopper_pearson_tail(x, n, tail) == _oracle_interval(x, n, tail), (x, n, tail)


# --- 8. Structural properties that hold for any correct Clopper-Pearson interval -------------


@pytest.mark.parametrize("n", [1, 2, 7, 20, 50])
def test_bounds_bracket_the_point_estimate_and_are_monotone_in_x(n: int) -> None:
    previous_low, previous_high = clopper_pearson_tail(0, n, GATE_TAIL)
    assert previous_low == 0.0
    assert 0.0 < previous_high <= 1.0
    for x in range(1, n + 1):
        low, high = clopper_pearson_tail(x, n, GATE_TAIL)
        assert 0.0 < low <= x / n <= high <= 1.0, (x, n)
        # Both endpoints are strictly increasing in x; high(n) == 1.0 > high(n - 1).
        assert low > previous_low, (x, n)
        assert high > previous_high, (x, n)
        previous_low, previous_high = low, high


@pytest.mark.parametrize(("x", "n"), [(0, 1), (1, 1), (3, 7), (5, 10), (13, 20), (190, 200)])
def test_smaller_tails_give_nested_wider_intervals(x: int, n: int) -> None:
    tails = (0.4999999999999999, 0.25, 0.025, GATE_TAIL, 0.00625, MIN_TAIL)
    previous = clopper_pearson_tail(x, n, tails[0])
    for tail in tails[1:]:
        current = clopper_pearson_tail(x, n, tail)
        assert current[0] <= previous[0], (x, n, tail)
        assert current[1] >= previous[1], (x, n, tail)
        previous = current


@pytest.mark.parametrize("n", [1, 2, 4, 8, 16])
def test_tail_comparison_is_symmetric_under_reflection(n: int) -> None:
    """P(X >= x | p) == P(X <= n-x | 1-p); dyadic p keeps 1-p exact in binary64."""
    for p in (0.0625, 0.125, 0.25, 0.375, 0.5, 0.75, 0.9375):
        mirrored = 1.0 - p
        assert Fraction.from_float(mirrored) == 1 - Fraction.from_float(p)
        for x in range(n + 1):
            for target in (MIN_TAIL, GATE_TAIL, 0.25, 0.4999999999999999):
                assert _tail_is_greater(x, n, p, target, upper=True) is _tail_is_greater(
                    n - x, n, mirrored, target, upper=False
                ), (x, n, p, target)


@pytest.mark.parametrize("n", [1, 3, 10, 25])
def test_exact_frequentist_coverage_is_at_least_one_minus_two_tails(n: int) -> None:
    """Sum the exact binomial mass of every x whose interval covers p: >= 1 - 2*tail."""
    tail = GATE_TAIL
    intervals = [clopper_pearson_tail(x, n, tail) for x in range(n + 1)]
    floor = 1 - 2 * Fraction.from_float(tail)
    for p in (0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99):
        exact_p = Fraction.from_float(p)
        covered = Fraction(0)
        for x, (low, high) in enumerate(intervals):
            if Fraction.from_float(low) <= exact_p <= Fraction.from_float(high):
                covered += math.comb(n, x) * exact_p**x * (1 - exact_p) ** (n - x)
        assert covered >= floor, (n, p, float(covered))


def test_results_are_deterministic_plain_floats() -> None:
    first = clopper_pearson_tail(13, 20, GATE_TAIL)
    second = clopper_pearson_tail(13, 20, GATE_TAIL)
    assert first == second
    assert type(first) is tuple
    assert all(type(value) is float for value in first)


# --- 9. Actseal public boundary -------------------------------------------------------------


@pytest.mark.parametrize(
    ("successes", "n", "tail"),
    [
        (-1, 10, GATE_TAIL),
        (11, 10, GATE_TAIL),
        (1, 0, GATE_TAIL),
        (0, 0, GATE_TAIL),
        (1, -5, GATE_TAIL),
        (1, MAX_N + 1, GATE_TAIL),
        (MAX_N + 1, MAX_N + 1, GATE_TAIL),
        (1, 10, 0.0),
        (1, 10, -0.0125),
        (1, 10, 0.5),
        (1, 10, 0.975),
        (1, 10, 1.0),
        (1, 10, 2.0),
        (1, 10, math.nextafter(MIN_TAIL, 0.0)),
        (1, 10, math.inf),
        (1, 10, -math.inf),
        (1, 10, math.nan),
    ],
)
def test_invalid_ranges_and_nonfinite_tails_raise_value_error(
    successes: int, n: int, tail: float
) -> None:
    with pytest.raises(ValueError, match="must be"):
        clopper_pearson_tail(successes, n, tail)


@pytest.mark.parametrize(
    ("successes", "n", "tail"),
    [
        (True, 10, GATE_TAIL),
        (False, 10, GATE_TAIL),
        (1, True, GATE_TAIL),
        (1, 10, True),
        (1, 10, False),
        (1.0, 10, GATE_TAIL),
        (1, 10.0, GATE_TAIL),
        (Fraction(1), 10, GATE_TAIL),
        (1, 10, "0.0125"),
        (1, 10, None),
        (1, 10, Decimal("0.0125")),
    ],
)
def test_booleans_and_non_integer_inputs_raise_type_error(
    successes: object, n: object, tail: object
) -> None:
    with pytest.raises(TypeError):
        clopper_pearson_tail(successes, n, tail)  # type: ignore[arg-type]


def test_domain_boundaries_are_inclusive_and_exclusive_exactly() -> None:
    low, high = clopper_pearson_tail(0, 1, MIN_TAIL)
    assert low == 0.0
    assert high < 1.0
    low, high = clopper_pearson_tail(MAX_N, MAX_N, 0.4999999999999999)
    assert high == 1.0
    assert 0.0 < low < 1.0
    with pytest.raises(ValueError, match="tail must be between"):
        clopper_pearson_tail(0, 1, 0.5)
    with pytest.raises(ValueError, match="tail must be between"):
        clopper_pearson_tail(0, 1, math.nextafter(MIN_TAIL, 0.0))
    with pytest.raises(ValueError, match="n must be between"):
        clopper_pearson_tail(0, MAX_N + 1, MIN_TAIL)


def test_error_messages_name_the_invariant_without_echoing_values() -> None:
    with pytest.raises(ValueError, match=r"^successes must be between 0 and n$"):
        clopper_pearson_tail(11, 10, GATE_TAIL)
    with pytest.raises(ValueError, match=r"^n must be between 1 and 10000$"):
        clopper_pearson_tail(0, 0, GATE_TAIL)
    with pytest.raises(TypeError, match=r"^successes must be an integer$"):
        clopper_pearson_tail(True, 10, GATE_TAIL)  # bool is an int to the type checker
    with pytest.raises(TypeError, match=r"^tail must be a number$"):
        clopper_pearson_tail(1, 10, "0.0125")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"^tail must be finite$"):
        clopper_pearson_tail(1, 10, math.nan)


# --- 10. Module isolation ---------------------------------------------------------------------


def _module_source() -> str:
    return Path(inspect.getfile(stats_module)).read_text(encoding="utf-8")


def _code_after_docstring(source: str) -> str:
    marker = "from __future__ import annotations"
    assert marker in source
    return source[source.index(marker) :]


def test_stats_module_is_stdlib_only_and_independent_of_other_actseal_modules() -> None:
    code = _code_after_docstring(_module_source())
    imports = [
        line.strip()
        for line in code.splitlines()
        if line.startswith(("import ", "from ")) and "__future__" not in line
    ]
    assert imports == ["import math"]
    assert not any(name in sys.modules for name in ("scipy", "numpy"))
    for forbidden in ("wilson", "newcombe", "NormalDist", "scipy", "actseal."):
        assert forbidden not in code, forbidden
    assert not hasattr(stats_module, "wilson")
    assert not hasattr(stats_module, "newcombe")
    assert not hasattr(stats_module, "clopper_pearson")
    public = [name for name in vars(stats_module) if not name.startswith("_")]
    assert public == ["annotations", "math", "clopper_pearson_tail"]


def test_attribution_is_preserved_in_the_port() -> None:
    source = _module_source()
    assert "d13dd94124cb71d378a4e76224fc115b750e8133" in source
    assert "Apache License 2.0" in source
    assert "Copyright 2026 Ajay Surya Senthilrajan" in source
    assert "agent-reliability-ci" in source
