"""Generated properties of ``actseal.selection``.

Every case is produced by a seeded standard-library generator, so the suite is
deterministic and bounded. No expected value is read back from the unit under
test; references come from three independent sources:

* **an exact brute-force oracle** - :func:`exact_pass_probability` enumerates
  every ``(ACT count, error count)`` pair, decides each one by calling the
  frozen ``actseal.stats.clopper_pearson_tail`` directly, and weights it with
  binomial masses summed in :class:`fractions.Fraction`, so the reference
  depends on no float arithmetic of its own;
* **the frozen kernel itself** - the two comparisons that ``selection``
  rewrites into binomial tail statements are swept against
  ``clopper_pearson_tail``, including limits set exactly to a kernel endpoint;
* **a seeded Monte Carlo** - calibration and verification splits drawn from one
  synthetic score distribution, scored with the verification PASS rule rebuilt
  here from ``actseal.assessment``'s documented statistics step, never by
  calling ``selection``.

The structural properties (monotonicity of the passing error table, order
independence of selection) are stated from the definition of the gate, not from
the implementation.
"""

from __future__ import annotations

import math
import random
from fractions import Fraction
from functools import cache

import pytest

from actseal.selection import (
    DEFAULT_SELECTION_TAIL,
    CalibrationCase,
    _coverage_ok,
    _max_passing_errors,
    _risk_ok,
    pass_probability,
    plan_sample_size,
    select_threshold,
)
from actseal.stats import clopper_pearson_tail

TAIL_DIVISOR = 4

SEED_ORACLE = 20261113
SEED_MIRROR = 20261114
SEED_ORDER = 20261115
SEED_MONTE_CARLO = 20261116


# --------------------------------------------------------------------------- #
# 1. Exact brute-force oracle for pass_probability
# --------------------------------------------------------------------------- #


@cache
def kernel(successes: int, n: int, tail: float) -> tuple[float, float]:
    """The frozen kernel, memoized so the oracles stay affordable."""
    return clopper_pearson_tail(successes, n, tail)


def binomial_mass(k: int, n: int, p: Fraction) -> Fraction:
    return math.comb(n, k) * p**k * (1 - p) ** (n - k)


def exact_pass_probability(
    *,
    n_verify: int,
    risk: float,
    coverage: float,
    max_risk: float,
    min_coverage: float,
    alpha: float,
) -> Fraction:
    """Enumerate the PASS region of ``actseal.assessment`` and weight it exactly.

    PASS needs at least one ACT, a risk upper bound at most ``max_risk`` and a
    coverage lower bound at least ``min_coverage``, each tail ``alpha / 4``.
    Masses are exact rationals at the supplied binary64 inputs.
    """
    tail = alpha / TAIL_DIVISOR
    coverage_mass = Fraction.from_float(coverage)
    risk_mass = Fraction.from_float(risk)
    total = Fraction(0)
    for accepted in range(1, n_verify + 1):
        if kernel(accepted, n_verify, tail)[0] < min_coverage:
            continue
        outer = binomial_mass(accepted, n_verify, coverage_mass)
        if outer == 0:
            continue
        inner = Fraction(0)
        for errors in range(accepted + 1):
            if kernel(errors, accepted, tail)[1] <= max_risk:
                inner += binomial_mass(errors, accepted, risk_mass)
        total += outer * inner
    return total


ORACLE_CASES = (
    {"n_verify": 1, "risk": 0.0, "coverage": 1.0, "max_risk": 1.0, "min_coverage": 0.0},
    {"n_verify": 1, "risk": 0.5, "coverage": 0.5, "max_risk": 0.99, "min_coverage": 0.0},
    {"n_verify": 4, "risk": 0.1, "coverage": 0.9, "max_risk": 0.5, "min_coverage": 0.2},
    {"n_verify": 8, "risk": 0.02, "coverage": 0.7, "max_risk": 0.3, "min_coverage": 0.4},
    {"n_verify": 12, "risk": 0.25, "coverage": 0.5, "max_risk": 0.6, "min_coverage": 0.1},
    {"n_verify": 15, "risk": 0.0, "coverage": 0.8, "max_risk": 0.2, "min_coverage": 0.5},
    {"n_verify": 20, "risk": 0.05, "coverage": 0.95, "max_risk": 0.25, "min_coverage": 0.6},
    {"n_verify": 20, "risk": 1.0, "coverage": 1.0, "max_risk": 1.0, "min_coverage": 0.0},
    {"n_verify": 20, "risk": 0.3, "coverage": 0.0, "max_risk": 0.5, "min_coverage": 0.0},
    {"n_verify": 30, "risk": 0.02, "coverage": 0.6, "max_risk": 0.2, "min_coverage": 0.25},
)


@pytest.mark.parametrize("case", ORACLE_CASES)
@pytest.mark.parametrize("alpha", [0.05, 0.2])
def test_pass_probability_matches_the_exact_oracle(case: dict[str, float], alpha: float) -> None:
    reference = exact_pass_probability(alpha=alpha, **case)  # type: ignore[arg-type]
    got = pass_probability(alpha=alpha, **case)  # type: ignore[arg-type]
    assert abs(Fraction.from_float(got) - reference) <= Fraction(1, 10**12), (case, alpha)


def test_pass_probability_matches_the_exact_oracle_on_generated_inputs() -> None:
    rng = random.Random(SEED_ORACLE)  # noqa: S311
    for _ in range(25):
        case = {
            "n_verify": rng.randint(1, 18),
            "risk": rng.choice((0.0, 0.01, rng.random() * 0.4)),
            "coverage": rng.choice((1.0, rng.uniform(0.2, 1.0))),
            "max_risk": rng.uniform(0.1, 1.0),
            "min_coverage": rng.choice((0.0, rng.uniform(0.0, 0.8))),
            "alpha": rng.choice((0.05, 0.1, 0.5)),
        }
        reference = exact_pass_probability(**case)  # type: ignore[arg-type]
        got = pass_probability(**case)  # type: ignore[arg-type]
        assert abs(Fraction.from_float(got) - reference) <= Fraction(1, 10**12), case


def test_the_probability_is_a_probability_on_generated_inputs() -> None:
    rng = random.Random(SEED_ORACLE + 1)  # noqa: S311
    for _ in range(40):
        value = pass_probability(
            n_verify=rng.randint(1, 2_000),
            risk=rng.random(),
            coverage=rng.random(),
            max_risk=rng.random(),
            min_coverage=rng.random(),
            alpha=rng.choice((1e-6, 0.01, 0.05, 0.3, 0.9)),
        )
        assert 0.0 <= value <= 1.0


# --------------------------------------------------------------------------- #
# 2. The rewritten gate comparisons against the frozen kernel
# --------------------------------------------------------------------------- #

MIRROR_SIZES = (*range(1, 17), 24)
MIRROR_TAILS = (0.025, 0.1)


def test_the_risk_comparison_agrees_with_the_kernel_upper_endpoint() -> None:
    rng = random.Random(SEED_MIRROR)  # noqa: S311
    checked = 0
    for accepted in MIRROR_SIZES:
        for tail in MIRROR_TAILS:
            for max_risk in (0.0, 0.05, 0.2, 0.9, 1.0, rng.random()):
                for errors in range(accepted + 1):
                    expected = clopper_pearson_tail(errors, accepted, tail)[1] <= max_risk
                    got = _risk_ok(errors=errors, accepted=accepted, tail=tail, max_risk=max_risk)
                    assert got is expected, (errors, accepted, tail, max_risk)
                    checked += 1
    assert checked >= 1_000


def test_the_coverage_comparison_agrees_with_the_kernel_lower_endpoint() -> None:
    rng = random.Random(SEED_MIRROR + 1)  # noqa: S311
    checked = 0
    for total in MIRROR_SIZES:
        for tail in MIRROR_TAILS:
            for min_coverage in (0.0, 0.1, 0.5, 0.95, 1.0, rng.random()):
                for accepted in range(total + 1):
                    expected = clopper_pearson_tail(accepted, total, tail)[0] >= min_coverage
                    got = _coverage_ok(
                        accepted=accepted, total=total, tail=tail, min_coverage=min_coverage
                    )
                    assert got is expected, (accepted, total, tail, min_coverage)
                    checked += 1
    assert checked >= 1_000


def test_the_comparisons_agree_with_the_kernel_at_its_own_endpoints() -> None:
    """The hardest inputs: a limit equal to, or one part in 1e12 from, an endpoint."""
    checked = 0
    for size in (3, 7, 25, 61, 400):
        for tail in (0.0125, 0.05):
            for count in range(min(size, 5)):
                low, high = clopper_pearson_tail(count, size, tail)
                for limit in (high, high * (1.0 - 1e-12), high * (1.0 + 1e-12)):
                    expected = high <= limit
                    got = _risk_ok(errors=count, accepted=size, tail=tail, max_risk=limit)
                    assert got is expected, ("risk", count, size, tail, limit)
                    checked += 1
                for limit in (low, low * (1.0 - 1e-12), low * (1.0 + 1e-12)):
                    expected = low >= limit
                    got = _coverage_ok(accepted=count, total=size, tail=tail, min_coverage=limit)
                    assert got is expected, ("coverage", count, size, tail, limit)
                    checked += 1
    assert checked >= 100


def test_the_passing_error_table_is_nondecreasing_in_the_act_count() -> None:
    """A wider ACT sample can only tighten the risk bound, never loosen it."""
    rng = random.Random(SEED_MIRROR + 2)  # noqa: S311
    for _ in range(20):
        last = rng.randint(1, 600)
        table = _max_passing_errors(
            first=1, last=last, tail=rng.choice((0.0125, 0.025, 0.1)), max_risk=rng.random()
        )
        assert len(table) == last
        assert list(table) == sorted(table)
        assert all(-1 <= value <= index + 1 for index, value in enumerate(table))


# --------------------------------------------------------------------------- #
# 3. Selection is a function of the counts, not of the case order
# --------------------------------------------------------------------------- #


def test_selection_does_not_depend_on_case_order() -> None:
    rng = random.Random(SEED_ORDER)  # noqa: S311
    grid = (0.2, 0.4, 0.6, 0.8)
    for _ in range(20):
        cases = [
            CalibrationCase(
                None if rng.random() < 0.1 else round(rng.random(), 3), rng.random() < 0.9
            )
            for _ in range(rng.randint(0, 150))
        ]
        arguments = {
            "grid": grid,
            "n_verify": 150,
            "max_risk": 0.25,
            "min_coverage": 0.2,
            "alpha": 0.1,
        }
        reference = select_threshold(cases=cases, **arguments)  # type: ignore[arg-type]
        shuffled = list(cases)
        rng.shuffle(shuffled)
        assert select_threshold(cases=shuffled, **arguments) == reference  # type: ignore[arg-type]
        assert select_threshold(cases=cases[::-1], **arguments) == reference  # type: ignore[arg-type]
        assert select_threshold(cases=tuple(cases), **arguments) == reference  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 4. Seeded Monte Carlo: select on calibration, PASS on fresh verification
# --------------------------------------------------------------------------- #

#: Synthetic population. A case produces no score, so can never be an ACT, with
#: probability ``MISSING_RATE``; otherwise its score is uniform on [0, 1) and
#: scores below ``WEAK_SCORE`` are far more error-prone, so a threshold buys
#: accuracy with coverage.
MISSING_RATE = 0.05
WEAK_SCORE = 0.4
WEAK_ERROR = 0.25
STRONG_ERROR = 0.03

GRID = (0.3, 0.5, 0.7, 0.9)
MAX_RISK = 0.25
MIN_COVERAGE = 0.25
ALPHA = 0.1
#: Calibration split size, and the threshold the run is designed around.
CALIBRATION_SIZE = 150
DESIGN_THRESHOLD = 0.5
#: The design point is the plug-in pair the selector is expected to face, with
#: the calibration error count taken at this quantile rather than at its mean:
#: sizing a run for the average calibration draw leaves half of all draws
#: unable to qualify any threshold.
DESIGN_QUANTILE = Fraction(95, 100)
#: Verification size the planner returns at that design point (pinned here so
#: the Monte Carlo and the planner cannot drift apart silently).
VERIFICATION_SIZE = 295

MONTE_CARLO_DRAWS = 2_000
#: The floor this pipeline must clear. Not weakened: see
#: ``test_an_overly_narrow_selection_tail_stops_qualifying_thresholds`` for the
#: other end of the trade-off.
PASS_RATE_FLOOR = 0.75
NARROW_TAIL = 0.0025
NARROW_TAIL_DRAWS = 300


def error_rate(score: float) -> float:
    return WEAK_ERROR if score < WEAK_SCORE else STRONG_ERROR


def draw_outcome(rng: random.Random) -> tuple[float | None, bool]:
    """One population draw as ``(score, correct)``; ``None`` means no score at all."""
    if rng.random() < MISSING_RATE:
        return None, False
    score = rng.random()
    return score, rng.random() >= error_rate(score)


def draw_case(rng: random.Random) -> CalibrationCase:
    return CalibrationCase(*draw_outcome(rng))


def true_risk_and_coverage(threshold: float) -> tuple[float, float]:
    """Population risk among ACT and population coverage at one threshold."""
    weak = max(0.0, WEAK_SCORE - threshold)
    strong = 1.0 - max(threshold, WEAK_SCORE)
    width = weak + strong
    risk = (weak * WEAK_ERROR + strong * STRONG_ERROR) / width
    return risk, (1.0 - MISSING_RATE) * width


def binomial_quantile(n: int, p: float, quantile: Fraction) -> int:
    """Smallest ``k`` with ``P(Bin(n, p) <= k) >= quantile``, summed exactly."""
    mass = Fraction.from_float(p)
    total = Fraction(0)
    for k in range(n + 1):
        total += binomial_mass(k, n, mass)
        if total >= quantile:
            return k
    return n


def design_point(selection_tail: float) -> tuple[float, float]:
    """The conservative plug-in pair expected at ``DESIGN_THRESHOLD``."""
    risk, coverage = true_risk_and_coverage(DESIGN_THRESHOLD)
    accepted = round(coverage * CALIBRATION_SIZE)
    errors = binomial_quantile(accepted, risk, DESIGN_QUANTILE)
    return (
        kernel(errors, accepted, selection_tail)[1],
        kernel(accepted, CALIBRATION_SIZE, selection_tail)[0],
    )


def verification_passes(*, accepted: int, errors: int, total: int) -> bool:
    """The PASS rule of ``actseal.assessment``, rebuilt from its documented step."""
    tail = ALPHA / TAIL_DIVISOR
    if accepted == 0:
        return False  # risk.no_accepted_cases: the interval is [0, 1], never a PASS
    if kernel(errors, accepted, tail)[1] > MAX_RISK:
        return False
    return kernel(accepted, total, tail)[0] >= MIN_COVERAGE


def run_pipeline(*, selection_tail: float, draws: int) -> tuple[int, int]:
    """``(verified PASSes, draws where nothing qualified)`` over seeded splits."""
    rng = random.Random(SEED_MONTE_CARLO)  # noqa: S311
    passed = 0
    unselected = 0
    for _ in range(draws):
        calibration = [draw_case(rng) for _ in range(CALIBRATION_SIZE)]
        result = select_threshold(
            grid=GRID,
            cases=calibration,
            n_verify=VERIFICATION_SIZE,
            max_risk=MAX_RISK,
            min_coverage=MIN_COVERAGE,
            alpha=ALPHA,
            selection_tail=selection_tail,
        )
        if result.threshold is None:
            unselected += 1
            continue
        accepted = 0
        errors = 0
        for _ in range(VERIFICATION_SIZE):
            score, correct = draw_outcome(rng)
            if score is None or score < result.threshold:
                continue
            accepted += 1
            if not correct:
                errors += 1
        if verification_passes(accepted=accepted, errors=errors, total=VERIFICATION_SIZE):
            passed += 1
    return passed, unselected


def test_the_planner_sizes_the_verification_split_at_the_design_point() -> None:
    risk, coverage = design_point(DEFAULT_SELECTION_TAIL)
    planned = plan_sample_size(
        max_risk=MAX_RISK,
        min_coverage=MIN_COVERAGE,
        alpha=ALPHA,
        expected_risk=risk,
        expected_coverage=coverage,
    )
    assert planned == VERIFICATION_SIZE
    assert (
        pass_probability(
            n_verify=VERIFICATION_SIZE,
            risk=risk,
            coverage=coverage,
            max_risk=MAX_RISK,
            min_coverage=MIN_COVERAGE,
            alpha=ALPHA,
        )
        >= 0.8
    )


def test_verification_passes_at_least_three_quarters_of_the_time_after_selection() -> None:
    """2000 seeded draws of the whole pipeline at the planner's design point.

    Selection sees only the calibration split; the PASS decision is taken on a
    fresh verification split of the same population with the frozen rule. The
    floor is a property of the pipeline, not of one stage: conservative plug-ins
    must not make selection so timid that it stops qualifying thresholds.
    """
    passed, unselected = run_pipeline(
        selection_tail=DEFAULT_SELECTION_TAIL, draws=MONTE_CARLO_DRAWS
    )
    rate = passed / MONTE_CARLO_DRAWS
    assert rate >= PASS_RATE_FLOOR, (rate, unselected)
    assert unselected <= MONTE_CARLO_DRAWS // 10, unselected


def test_an_overly_narrow_selection_tail_stops_qualifying_thresholds() -> None:
    """The other end of the trade-off: too much conservatism makes selection useless."""
    default_passed, default_unselected = run_pipeline(
        selection_tail=DEFAULT_SELECTION_TAIL, draws=NARROW_TAIL_DRAWS
    )
    narrow_passed, narrow_unselected = run_pipeline(
        selection_tail=NARROW_TAIL, draws=NARROW_TAIL_DRAWS
    )
    assert narrow_unselected > default_unselected
    assert narrow_passed < default_passed
    assert narrow_passed / NARROW_TAIL_DRAWS < PASS_RATE_FLOOR
    assert default_passed / NARROW_TAIL_DRAWS >= PASS_RATE_FLOOR
