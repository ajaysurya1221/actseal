"""Generated numerical properties of ``actseal.stats.clopper_pearson_tail``.

Every case is produced by a seeded standard-library generator, so the suite is
deterministic and bounded. No expected value is read back from the unit under
test; references come from two independent oracles:

* **exact root bracketing** — each returned endpoint must sit within one
  bisection bracket (plus one ulp of rounding) of the true root, checked by
  evaluating the exact binomial tail with ``fractions.Fraction`` on both sides
  of the endpoint;
* **Decimal closed forms** — one-term tails (``x in {0, 1, n-1, n}``) have
  radical roots evaluated at 40 significant digits.

The structural properties (ordering, monotonicity in the count, nesting in
the tail, closed endpoints, supported domains) are stated from the definition
of a Clopper-Pearson interval, not from the implementation.
"""

from __future__ import annotations

import math
import random
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from actseal.stats import clopper_pearson_tail

MIN_TAIL = 2.5e-7
MAX_TAIL_EXCLUSIVE = 0.5
MAX_N = 10_000
GATE_TAIL = 0.0125
BRACKET = Fraction(1, 2**60)

SEED_BRACKETING = 20261006
SEED_ORDERING = 20261007
SEED_NESTING = 20261008
SEED_DOMAIN = 20261009
SEED_CLOSED_FORM = 20261010


# --------------------------------------------------------------------------- #
# Independent oracles
# --------------------------------------------------------------------------- #


def exact_tail(x: int, n: int, p: Fraction, *, upper: bool) -> Fraction:
    """P(X >= x) or P(X <= x) for X ~ Binomial(n, p), summed exactly."""
    ks = range(x, n + 1) if upper else range(x + 1)
    return sum((math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in ks), Fraction(0))


def clamp(value: Fraction) -> Fraction:
    return min(max(value, Fraction(0)), Fraction(1))


def slack(endpoint: float) -> Fraction:
    """One bisection bracket plus one ulp: the most an endpoint can miss its root by."""
    return BRACKET + Fraction.from_float(math.ulp(endpoint))


def assert_lower_bound_brackets_its_root(x: int, n: int, tail: float, low: float) -> None:
    """P(X >= x | p) is nondecreasing in p and equals ``tail`` at the true lower bound."""
    target = Fraction.from_float(tail)
    point = Fraction.from_float(low)
    below = clamp(point - slack(low))
    above = clamp(point + slack(low))
    assert exact_tail(x, n, below, upper=True) <= target, (x, n, tail, low)
    assert exact_tail(x, n, above, upper=True) > target, (x, n, tail, low)


def assert_upper_bound_brackets_its_root(x: int, n: int, tail: float, high: float) -> None:
    """P(X <= x | p) is nonincreasing in p and equals ``tail`` at the true upper bound."""
    target = Fraction.from_float(tail)
    point = Fraction.from_float(high)
    below = clamp(point - slack(high))
    above = clamp(point + slack(high))
    assert exact_tail(x, n, below, upper=False) > target, (x, n, tail, high)
    assert exact_tail(x, n, above, upper=False) <= target, (x, n, tail, high)


def closed_forms(x: int, n: int, tail: float) -> tuple[Decimal | None, Decimal | None]:
    """Radical roots of the one-term tails, or ``None`` where the endpoint is closed."""
    with localcontext() as context:
        context.prec = 40
        t = Decimal(tail)
        root = Decimal(1) / Decimal(n)
        low: Decimal | None = None
        high: Decimal | None = None
        if x == n:
            low = t**root  # p^n = tail
        elif x == 1:
            low = 1 - (1 - t) ** root  # 1 - (1 - p)^n = tail
        if x == 0:
            high = 1 - t**root  # (1 - p)^n = tail
        elif x == n - 1:
            high = (1 - t) ** root  # 1 - p^n = tail
        return low, high


def assert_close_to_decimal(got: float, reference: Decimal) -> None:
    error = abs(Fraction.from_float(got) - Fraction(reference))
    assert error <= BRACKET + 2 * Fraction.from_float(math.ulp(got)), (got, reference)


def random_tail(rng: random.Random) -> float:
    """A tail inside the supported domain ``[2.5e-7, 0.5)``; three shapes of draw."""
    shape = rng.randrange(3)
    if shape == 0:
        draw = rng.uniform(MIN_TAIL, MAX_TAIL_EXCLUSIVE)
    elif shape == 1:
        draw = math.ldexp(rng.random(), -rng.randrange(2, 22))  # small tails
    else:
        draw = rng.choice((MIN_TAIL, GATE_TAIL, 0.025, 0.1, 0.25, math.nextafter(0.5, 0.0)))
    return min(max(draw, MIN_TAIL), math.nextafter(MAX_TAIL_EXCLUSIVE, 0.0))


# --------------------------------------------------------------------------- #
# 1. Endpoints bracket the exact roots (independent Fraction oracle)
# --------------------------------------------------------------------------- #


def test_generated_endpoints_bracket_their_exact_roots() -> None:
    rng = random.Random(SEED_BRACKETING)  # noqa: S311
    cases = [(rng.randint(0, n), n) for n in (rng.randint(1, 60) for _ in range(40))]
    cases += [(0, 1), (1, 1), (1, 2), (7, 10), (38, 50), (130, 200), (199, 200)]
    checked = 0
    for x, n in cases:
        tail = random_tail(rng)
        low, high = clopper_pearson_tail(x, n, tail)
        if x > 0:
            assert_lower_bound_brackets_its_root(x, n, tail, low)
            checked += 1
        if x < n:
            assert_upper_bound_brackets_its_root(x, n, tail, high)
            checked += 1
    assert checked >= 60


@pytest.mark.parametrize(("x", "n"), [(0, 400), (1, 400), (200, 400), (399, 400)])
def test_large_n_endpoints_bracket_their_exact_roots(x: int, n: int) -> None:
    low, high = clopper_pearson_tail(x, n, GATE_TAIL)
    if x > 0:
        assert_lower_bound_brackets_its_root(x, n, GATE_TAIL, low)
    if x < n:
        assert_upper_bound_brackets_its_root(x, n, GATE_TAIL, high)


# --------------------------------------------------------------------------- #
# 2. Ordering and closed endpoints
# --------------------------------------------------------------------------- #


def test_generated_intervals_are_ordered_and_bracket_the_point_estimate() -> None:
    rng = random.Random(SEED_ORDERING)  # noqa: S311
    for _ in range(150):
        n = rng.randint(1, 400)
        x = rng.randint(0, n)
        tail = random_tail(rng)
        low, high = clopper_pearson_tail(x, n, tail)
        assert type(low) is float
        assert type(high) is float
        assert 0.0 <= low <= high <= 1.0, (x, n, tail)
        assert low < high, (x, n, tail)
        assert Fraction.from_float(low) <= Fraction(x, n) <= Fraction.from_float(high), (x, n, tail)
        assert (low == 0.0) is (x == 0), (x, n, tail)
        assert (high == 1.0) is (x == n), (x, n, tail)


def test_endpoints_are_strictly_monotone_in_the_count() -> None:
    rng = random.Random(SEED_ORDERING + 1)  # noqa: S311
    sizes = {1, 2, 3, *(rng.randint(4, 120) for _ in range(12))}
    for n in sorted(sizes):
        tail = random_tail(rng)
        previous = clopper_pearson_tail(0, n, tail)
        for x in range(1, n + 1):
            current = clopper_pearson_tail(x, n, tail)
            assert current[0] > previous[0], (x, n, tail)
            assert current[1] > previous[1], (x, n, tail)
            previous = current


def test_mirrored_counts_give_mirrored_intervals_within_rounding() -> None:
    """CP(n-x, n) is the reflection of CP(x, n): [1-high, 1-low] up to float rounding."""
    rng = random.Random(SEED_ORDERING + 2)  # noqa: S311
    for _ in range(40):
        n = rng.randint(1, 80)
        x = rng.randint(0, n)
        tail = random_tail(rng)
        low, high = clopper_pearson_tail(x, n, tail)
        mirrored_low, mirrored_high = clopper_pearson_tail(n - x, n, tail)
        for got, reference in ((mirrored_low, 1.0 - high), (mirrored_high, 1.0 - low)):
            error = abs(Fraction.from_float(got) - Fraction.from_float(reference))
            assert error <= 2 * BRACKET + 4 * Fraction.from_float(math.ulp(1.0)), (x, n, tail)


# --------------------------------------------------------------------------- #
# 3. Nesting in the tail
# --------------------------------------------------------------------------- #


def test_smaller_tails_give_nested_intervals_on_generated_counts() -> None:
    rng = random.Random(SEED_NESTING)  # noqa: S311
    for _ in range(40):
        n = rng.randint(1, 150)
        x = rng.randint(0, n)
        tails = sorted({random_tail(rng) for _ in range(5)}, reverse=True)
        previous = clopper_pearson_tail(x, n, tails[0])
        for tail in tails[1:]:
            current = clopper_pearson_tail(x, n, tail)
            assert current[0] <= previous[0], (x, n, tail)
            assert current[1] >= previous[1], (x, n, tail)
            previous = current


def test_tail_nesting_is_strict_across_one_ulp_where_the_root_moves() -> None:
    """Across the whole supported tail range the interval at the minimum tail is widest."""
    rng = random.Random(SEED_NESTING + 1)  # noqa: S311
    widest_tail = MIN_TAIL
    narrowest_tail = math.nextafter(MAX_TAIL_EXCLUSIVE, 0.0)
    for _ in range(30):
        n = rng.randint(1, 100)
        x = rng.randint(0, n)
        widest = clopper_pearson_tail(x, n, widest_tail)
        narrowest = clopper_pearson_tail(x, n, narrowest_tail)
        middle = clopper_pearson_tail(x, n, GATE_TAIL)
        assert widest[0] <= middle[0] <= narrowest[0], (x, n)
        assert widest[1] >= middle[1] >= narrowest[1], (x, n)
        if 0 < x < n:
            assert widest[1] - widest[0] > narrowest[1] - narrowest[0], (x, n)


# --------------------------------------------------------------------------- #
# 4. Closed forms (Decimal oracle) on generated sizes
# --------------------------------------------------------------------------- #


def test_one_term_tails_match_decimal_closed_forms_on_generated_sizes() -> None:
    rng = random.Random(SEED_CLOSED_FORM)  # noqa: S311
    sizes = {1, 2, 3, MAX_N, *(rng.randint(4, 2_000) for _ in range(10))}
    for n in sorted(sizes):
        tail = random_tail(rng)
        for x in sorted({0, 1, n - 1, n}):
            low, high = clopper_pearson_tail(x, n, tail)
            low_reference, high_reference = closed_forms(x, n, tail)
            if low_reference is not None:
                assert_close_to_decimal(low, low_reference)
            if high_reference is not None:
                assert_close_to_decimal(high, high_reference)


def test_closed_endpoints_tighten_as_n_grows_at_a_fixed_tail() -> None:
    """high(0, n) = 1 - tail^(1/n) and low(n, n) = tail^(1/n) move monotonically with n."""
    rng = random.Random(SEED_CLOSED_FORM + 1)  # noqa: S311
    tail = random_tail(rng)
    sizes = sorted({1, 2, 5, 10, 100, 1_000, MAX_N, *(rng.randint(3, 999) for _ in range(6))})
    previous_high = clopper_pearson_tail(0, sizes[0], tail)[1]
    previous_low = clopper_pearson_tail(sizes[0], sizes[0], tail)[0]
    for n in sizes[1:]:
        high = clopper_pearson_tail(0, n, tail)[1]
        low = clopper_pearson_tail(n, n, tail)[0]
        assert high < previous_high, (n, tail)
        assert low > previous_low, (n, tail)
        previous_high, previous_low = high, low


# --------------------------------------------------------------------------- #
# 5. Supported domains
# --------------------------------------------------------------------------- #


def test_domain_corners_are_accepted() -> None:
    for n in (1, 2, MAX_N):
        for tail in (MIN_TAIL, GATE_TAIL, math.nextafter(MAX_TAIL_EXCLUSIVE, 0.0)):
            for x in sorted({0, n}):
                low, high = clopper_pearson_tail(x, n, tail)
                assert 0.0 <= low < high <= 1.0, (x, n, tail)


def test_generated_out_of_domain_inputs_raise_the_documented_value_errors() -> None:
    rng = random.Random(SEED_DOMAIN)  # noqa: S311
    for _ in range(60):
        n = rng.randint(1, 50)
        x = rng.randint(0, n)
        tail = random_tail(rng)
        with pytest.raises(ValueError, match=r"^n must be between 1 and 10000$"):
            clopper_pearson_tail(x, rng.choice((0, -n, MAX_N + rng.randint(1, 1_000))), tail)
        with pytest.raises(ValueError, match=r"^successes must be between 0 and n$"):
            clopper_pearson_tail(rng.choice((-rng.randint(1, 9), n + rng.randint(1, 9))), n, tail)
        bad_tail = rng.choice(
            (
                0.0,
                -tail,
                math.nextafter(MIN_TAIL, 0.0),
                MAX_TAIL_EXCLUSIVE,
                rng.uniform(0.5, 1.0),
                1.0 + tail,
            )
        )
        with pytest.raises(
            ValueError, match=r"^tail must be between 2\.5e-7 \(inclusive\) and 0\.5 \(exclusive\)$"
        ):
            clopper_pearson_tail(x, n, bad_tail)


def test_domain_boundaries_are_exact_to_one_ulp() -> None:
    clopper_pearson_tail(0, 1, MIN_TAIL)
    clopper_pearson_tail(1, MAX_N, math.nextafter(MAX_TAIL_EXCLUSIVE, 0.0))
    with pytest.raises(ValueError, match="tail must be between"):
        clopper_pearson_tail(0, 1, math.nextafter(MIN_TAIL, 0.0))
    with pytest.raises(ValueError, match="tail must be between"):
        clopper_pearson_tail(0, 1, MAX_TAIL_EXCLUSIVE)
    with pytest.raises(ValueError, match="n must be between"):
        clopper_pearson_tail(0, MAX_N + 1, GATE_TAIL)
    with pytest.raises(ValueError, match="n must be between"):
        clopper_pearson_tail(0, 0, GATE_TAIL)
