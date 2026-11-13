"""Calibration-split threshold selection and verification sample-size planning.

Actseal v1 verifies one prespecified threshold: on the ``n`` scheduled
verification cases a case is an ACT when the model's score clears the locked
threshold, the run PASSes when the Clopper-Pearson upper bound on
error-among-ACT is at most ``max_risk`` and the lower bound on coverage
(ACT / scheduled) is at least ``min_coverage``, and each of the four one-sided
tails spends ``alpha / 4``. v2 adds a *separate calibration split* on which a
threshold may be chosen. The guarantee still comes from the unchanged
verification stage, so nothing here may be trusted to bound risk: this module
is a deterministic pure planner that predicts how a candidate threshold would
fare, and the gate re-decides the question on held-out evidence.

Three pure functions:

* :func:`pass_probability` - the probability that verification PASSes when the
  ACT count ``A ~ Bin(n_verify, coverage)`` and the error count
  ``E | A ~ Bin(A, risk)``, under exactly the PASS rule of
  ``actseal.assessment`` (``A > 0``, risk upper bound at most ``max_risk``,
  coverage lower bound at least ``min_coverage``, every tail ``alpha / 4``).
* :func:`plan_sample_size` - the smallest scheduled ``n`` whose predicted pass
  probability at a design point reaches a target.
* :func:`select_threshold` - the grid point that accepts the most calibration
  cases among those whose *conservatively plugged-in* predicted pass
  probability reaches the target.

How the PASS rule is mirrored
-----------------------------

``assess`` decides each side by comparing a Clopper-Pearson endpoint with a
limit, and each endpoint is the midpoint of a 60-step bisection bracket around
the exact tail root (``actseal.stats``). Calling that kernel once per candidate
is far too slow at ``n_verify = 10_000`` (seconds per call), so the comparisons
are rewritten as the equivalent binomial tail statements they invert:

* ``clopper_pearson_tail(e, a, t)[1] <= max_risk``  iff
  ``P(X <= e) <= t`` for ``X ~ Bin(a, max_risk)``;
* ``clopper_pearson_tail(a, n, t)[0] >= min_coverage``  iff
  ``P(X >= a) <= t`` for ``X ~ Bin(n, min_coverage)``.

Both hold because the kernel's endpoints are the roots of exactly those tails
and each tail is monotone in ``p``. The tails themselves are evaluated in
binary64 from ``math.lgamma``, so the rewritten comparison can only disagree
with the bisected endpoint when the root sits within a relative
``_BOUNDARY_SLACK`` of the limit; inside that band the exact kernel is called
and decides. The band is far wider than both error sources it has to cover:
the binary64 tail is accurate to about ``1e-11`` relative (``lgamma`` at
``n = 10_000`` carries about ``1e-11`` absolute error), and the bisection
midpoint sits within ``2**-60`` of the root, which moves a binomial tail by at
most ``n * 2**-60 < 1e-14`` absolute. Decisions outside the band therefore
match the frozen kernel, and decisions inside it *are* the frozen kernel.

Numerical notes
---------------

* Both binomial tails are summed from their anchor term outwards with
  strictly decreasing ratios, and truncated only when the bound
  ``remaining_terms * term`` is below ``_TRUNCATION`` of the partial sum.
* :func:`pass_probability` precomputes the largest passing error count for
  every reachable ACT count. That count is nondecreasing in the ACT count
  (a wider sample can only tighten the risk bound), so one upward walk with
  the exact one-step identities
  ``P(X <= m | a + 1) = P(X <= m | a) - p * P(X = m | a)`` and
  ``P(X <= m + 1 | a) = P(X <= m | a) + P(X = m + 1 | a)``
  builds the whole table in ``O(n)`` tail-free steps. Rounding accumulates
  additively, bounding the absolute error of the returned probability by
  roughly ``n`` machine epsilons.
* ``plan_sample_size`` scans a documented schedule rather than bisecting:
  the pass probability is not exactly monotone in ``n``, because both bounds
  move on the integer lattice of achievable counts.

Determinism: no randomness, no iteration over unordered containers, and the
only mutable state is a bounded memo of the pure numerical kernel. This module
imports only the standard library and ``actseal.stats``; like that kernel it
reports domain errors as ``ValueError`` and type errors as ``TypeError``,
rather than through the record-schema hierarchy.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from actseal.stats import clopper_pearson_tail

__all__ = [
    "DEFAULT_SELECTION_TAIL",
    "MAX_GRID_POINTS",
    "REASON_NO_THRESHOLD",
    "REASON_SELECTED",
    "CalibrationCase",
    "GridPoint",
    "SelectionResult",
    "pass_probability",
    "plan_sample_size",
    "select_threshold",
]

#: Reason code of a successful selection.
REASON_SELECTED: Final = "selected"
#: Reason code when no grid point reaches the target predicted pass probability.
REASON_NO_THRESHOLD: Final = "calibration.no_threshold"
#: Largest accepted candidate grid (callers supply the grid; it is never derived
#: from observed scores).
MAX_GRID_POINTS: Final = 32
#: One-sided tail for the conservative calibration plug-ins: a 95% bound on
#: each plug-in, twice as conservative as the gate's own ``alpha / 4`` spend at
#: ``alpha = 0.1``. On the Monte Carlo pipeline of
#: ``tests/properties/test_selection_properties.py`` (2000 seeded draws, 150
#: calibration cases, 295 verification cases) the verified PASS rate by tail was
#: 0.999 at 0.2, 0.995 at 0.1, 0.971 at 0.05, 0.925 at 0.025, 0.852 at 0.0125
#: and 0.605 at 0.0025, where 40% of draws could no longer qualify any
#: threshold. 0.05 keeps the plug-ins honest without making selection useless.
DEFAULT_SELECTION_TAIL: Final = 0.05

# Mirrors of frozen constants that live in modules this one must not import:
# ``actseal.stats`` supported sample size and tail domain, the ``alpha`` domain
# of ``actseal.records.GateLimits``, and ``actseal.assessment.TAIL_DIVISOR``.
_MAX_N: Final = 10_000
_MIN_TAIL: Final = 2.5e-7
_MAX_TAIL_EXCLUSIVE: Final = 0.5
_MIN_ALPHA: Final = 1e-6
_TAIL_DIVISOR: Final = 4

#: Relative band around the family tail where the binary64 comparison defers to
#: the exact bisection kernel.
_BOUNDARY_SLACK: Final = 1e-7
#: Relative cut for a bounded, strictly decreasing tail remainder.
_TRUNCATION: Final = 1e-18
#: Bounded memo of the exact kernel. Pure function, so results never change.
_MEMO_SIZE: Final = 8_192

_PLAN_SCHEDULE: Final = ((1, 200, 1), (205, 500, 5), (525, 2_000, 25), (2_100, 10_000, 100))


# --------------------------------------------------------------------------- #
# Public boundary
# --------------------------------------------------------------------------- #


def _require_count(name: str, value: object) -> int:
    """Counts are plain integers, never booleans."""
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    return value


def _require_flag(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be a boolean")
    return value


def _require_number(name: str, value: object) -> float:
    """Numbers are finite and never booleans; an unconvertible integer is not finite."""
    if type(value) is bool or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{name} must be finite")
    return float(value)


def _require_unit(name: str, value: object) -> float:
    number = _require_number(name, value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return number


def _require_alpha(value: object) -> float:
    alpha = _require_number("alpha", value)
    if not _MIN_ALPHA <= alpha < 1.0:
        raise ValueError("alpha must be between 1e-6 (inclusive) and 1 (exclusive)")
    return alpha


def _require_tail(name: str, value: object) -> float:
    tail = _require_number(name, value)
    if not _MIN_TAIL <= tail < _MAX_TAIL_EXCLUSIVE:
        raise ValueError(f"{name} must be between 2.5e-7 (inclusive) and 0.5 (exclusive)")
    return tail


def _require_size(name: str, value: object) -> int:
    size = _require_count(name, value)
    if size < 1 or size > _MAX_N:
        raise ValueError(f"{name} must be between 1 and 10000")
    return size


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    """One scored calibration case.

    ``score`` is ``None`` when the case can never become an ACT whatever the
    threshold (a provider failure, or a choice outside the allowlist).
    ``correct`` is meaningful only when ``score`` is not ``None``.
    """

    score: float | None
    correct: bool

    def __post_init__(self) -> None:
        if self.score is not None:
            object.__setattr__(self, "score", _require_number("score", self.score))
        object.__setattr__(self, "correct", _require_flag("correct", self.correct))


@dataclass(frozen=True, slots=True)
class GridPoint:
    """What one candidate threshold did on calibration, and what it predicts."""

    threshold: float
    accepted: int
    errors: int
    predicted_pass_probability: float


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """The chosen threshold (or ``None``) with the full evaluated grid."""

    threshold: float | None
    reason: str
    points: tuple[GridPoint, ...]


# --------------------------------------------------------------------------- #
# Binomial kernel (binary64, from math.lgamma)
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=_MEMO_SIZE)
def _exact_tail(successes: int, n: int, tail: float) -> tuple[float, float]:
    """Memoized ``actseal.stats.clopper_pearson_tail``; the kernel is pure."""
    return clopper_pearson_tail(successes, n, tail)


def _log_pmf(k: int, n: int, p: float) -> float:
    """``log P(X = k)`` for ``X ~ Bin(n, p)``; ``-inf`` for impossible outcomes."""
    if k < 0 or k > n:
        return -math.inf
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (
        math.lgamma(n + 1.0)
        - math.lgamma(k + 1.0)
        - math.lgamma(n - k + 1.0)
        + k * math.log(p)
        + (n - k) * math.log1p(-p)
    )


def _pmf(k: int, n: int, p: float) -> float:
    """``P(X = k)`` for ``X ~ Bin(n, p)``; underflows to 0.0, never raises."""
    return math.exp(_log_pmf(k, n, p))


def _lower_tail(k: int, n: int, p: float) -> float:
    """``P(X <= k)`` for ``X ~ Bin(n, p)``."""
    if k < 0:
        return 0.0
    if k >= n or p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    if k * (1.0 - p) > (n - k) * p:  # k > n * p: sum the better-scaled complement
        return min(1.0, max(0.0, 1.0 - _upper_tail(k + 1, n, p)))
    anchor = _pmf(k, n, p)
    if anchor == 0.0:
        return 0.0
    odds = (1.0 - p) / p
    term = 1.0
    total = 1.0
    for j in range(k, 0, -1):
        term *= j * odds / (n - j + 1)
        total += term
        if term * j < total * _TRUNCATION:
            break
    return min(1.0, anchor * total)


def _upper_tail(k: int, n: int, p: float) -> float:
    """``P(X >= k)`` for ``X ~ Bin(n, p)``."""
    if k > n:
        return 0.0
    if k <= 0 or p >= 1.0:
        return 1.0
    if p <= 0.0:
        return 0.0
    if k * (1.0 - p) < (n - k) * p:  # k < n * p: sum the better-scaled complement
        return min(1.0, max(0.0, 1.0 - _lower_tail(k - 1, n, p)))
    anchor = _pmf(k, n, p)
    if anchor == 0.0:
        return 0.0
    odds = p / (1.0 - p)
    term = 1.0
    total = 1.0
    for j in range(k, n):
        term *= (n - j) * odds / (j + 1)
        total += term
        if term * (n - j) < total * _TRUNCATION:
            break
    return min(1.0, anchor * total)


# --------------------------------------------------------------------------- #
# The two gate comparisons of actseal.assessment
# --------------------------------------------------------------------------- #


def _compare(value: float, tail: float) -> bool | None:
    """``value <= tail``, or ``None`` when the two are too close to decide in binary64."""
    if value < tail * (1.0 - _BOUNDARY_SLACK):
        return True
    if value > tail * (1.0 + _BOUNDARY_SLACK):
        return False
    return None


def _risk_ok(
    *, errors: int, accepted: int, tail: float, max_risk: float, cdf: float | None = None
) -> bool:
    """Mirror ``clopper_pearson_tail(errors, accepted, tail)[1] <= max_risk``.

    ``cdf`` is an already-known value of ``P(X <= errors)`` for
    ``X ~ Bin(accepted, max_risk)``, which the callers carry along their walk;
    it is recomputed from scratch before any boundary decision.
    """
    if max_risk >= 1.0:
        return True  # the upper endpoint is at most 1.0
    if errors >= accepted or max_risk <= 0.0:
        return False  # the endpoint is exactly 1.0, resp. strictly positive
    decision = None if cdf is None else _compare(cdf, tail)
    if decision is None:
        decision = _compare(_lower_tail(errors, accepted, max_risk), tail)
    if decision is None:
        return _exact_tail(errors, accepted, tail)[1] <= max_risk
    return decision


def _coverage_ok(*, accepted: int, total: int, tail: float, min_coverage: float) -> bool:
    """Mirror ``clopper_pearson_tail(accepted, total, tail)[0] >= min_coverage``."""
    if min_coverage <= 0.0:
        return True  # the lower endpoint is never negative
    if accepted <= 0:
        return False  # the lower endpoint is exactly 0.0
    if min_coverage >= 1.0:
        return False  # the lower endpoint is always strictly below 1.0
    decision = _compare(_upper_tail(accepted, total, min_coverage), tail)
    if decision is None:
        return _exact_tail(accepted, total, tail)[0] >= min_coverage
    return decision


# --------------------------------------------------------------------------- #
# Pass probability
# --------------------------------------------------------------------------- #


def _minimum_accepted(*, total: int, tail: float, min_coverage: float) -> int | None:
    """Smallest ACT count that clears the coverage floor, or ``None`` if none does.

    PASS also needs at least one ACT, so the search starts at one. The coverage
    lower bound is strictly increasing in the ACT count, hence the bisection.
    """
    if not _coverage_ok(accepted=total, total=total, tail=tail, min_coverage=min_coverage):
        return None
    low = 1
    high = total
    while low < high:
        middle = (low + high) // 2
        if _coverage_ok(accepted=middle, total=total, tail=tail, min_coverage=min_coverage):
            high = middle
        else:
            low = middle + 1
    return low


def _extend_errors(
    *, errors: int, cdf: float, accepted: int, tail: float, max_risk: float
) -> tuple[int, float]:
    """Raise the error count while the risk bound still clears the limit."""
    while errors < accepted:
        candidate = cdf + _pmf(errors + 1, accepted, max_risk)
        if not _risk_ok(
            errors=errors + 1, accepted=accepted, tail=tail, max_risk=max_risk, cdf=candidate
        ):
            break
        cdf = candidate
        errors += 1
    return errors, cdf


def _max_passing_errors(*, first: int, last: int, tail: float, max_risk: float) -> tuple[int, ...]:
    """Largest passing error count for every ACT count in ``[first, last]``.

    ``-1`` means no error count passes at that ACT count. The risk upper bound
    is increasing in the error count and decreasing in the ACT count, so the
    table is nondecreasing and one upward walk suffices.
    """
    if max_risk >= 1.0:
        return tuple(range(first, last + 1))
    errors, cdf = _extend_errors(errors=-1, cdf=0.0, accepted=first, tail=tail, max_risk=max_risk)
    table = [errors]
    for accepted in range(first + 1, last + 1):
        if errors >= 0:
            cdf = max(0.0, cdf - max_risk * _pmf(errors, accepted - 1, max_risk))
        errors, cdf = _extend_errors(
            errors=errors, cdf=cdf, accepted=accepted, tail=tail, max_risk=max_risk
        )
        table.append(errors)
    return tuple(table)


def _pass_mass(
    *, total: int, coverage: float, risk: float, first: int, table: tuple[int, ...]
) -> float:
    """Sum ``P(A = a) * P(E <= table[a] | A = a)`` over the ACT counts that can PASS."""
    errors = table[0]
    cdf = _lower_tail(errors, first, risk)
    mass = _pmf(first, total, coverage) * cdf
    for index in range(1, len(table)):
        accepted = first + index
        if errors >= 0:
            cdf = max(0.0, cdf - risk * _pmf(errors, accepted - 1, risk))
        while errors < table[index]:
            errors += 1
            cdf = min(1.0, cdf + _pmf(errors, accepted, risk))
        mass += _pmf(accepted, total, coverage) * cdf
    return min(1.0, max(0.0, mass))


def pass_probability(
    *,
    n_verify: int,
    risk: float,
    coverage: float,
    max_risk: float,
    min_coverage: float,
    alpha: float,
) -> float:
    """Probability that verification PASSes at a given true risk and coverage.

    The ACT count is ``A ~ Bin(n_verify, coverage)`` and the error count is
    ``E | A ~ Bin(A, risk)``; PASS is exactly the rule of
    ``actseal.assessment``: ``A > 0``, the Clopper-Pearson upper bound on
    ``E / A`` at most ``max_risk``, and the lower bound on ``A / n_verify`` at
    least ``min_coverage``, every tail ``alpha / 4``.
    """
    size = _require_size("n_verify", n_verify)
    true_risk = _require_unit("risk", risk)
    true_coverage = _require_unit("coverage", coverage)
    limit_risk = _require_unit("max_risk", max_risk)
    limit_coverage = _require_unit("min_coverage", min_coverage)
    tail = _require_alpha(alpha) / _TAIL_DIVISOR

    first = _minimum_accepted(total=size, tail=tail, min_coverage=limit_coverage)
    if first is None:
        return 0.0
    table = _max_passing_errors(first=first, last=size, tail=tail, max_risk=limit_risk)
    return _pass_mass(total=size, coverage=true_coverage, risk=true_risk, first=first, table=table)


# --------------------------------------------------------------------------- #
# Sample-size planning
# --------------------------------------------------------------------------- #


def _plan_candidates(max_n: int) -> tuple[int, ...]:
    """The documented schedule up to ``max_n``, which is always its last entry."""
    candidates: list[int] = []
    for start, stop, step in _PLAN_SCHEDULE:
        candidates.extend(range(start, min(stop, max_n) + 1, step))
    if not candidates or candidates[-1] != max_n:
        candidates.append(max_n)
    return tuple(candidates)


def plan_sample_size(
    *,
    max_risk: float,
    min_coverage: float,
    alpha: float,
    expected_risk: float,
    expected_coverage: float,
    target_pass_probability: float = 0.8,
    max_n: int = 10_000,
) -> int | None:
    """Smallest scheduled verification size whose predicted pass probability reaches the target.

    The schedule is every size up to 200, then steps of 5 to 500, 25 to 2000
    and 100 to 10000, with ``max_n`` always included. It is scanned rather than
    bisected because :func:`pass_probability` is not exactly monotone in the
    sample size: both bounds move on the integer lattice of achievable counts.
    Returns ``None`` when no scheduled size reaches the target.
    """
    limit_risk = _require_unit("max_risk", max_risk)
    limit_coverage = _require_unit("min_coverage", min_coverage)
    family_alpha = _require_alpha(alpha)
    design_risk = _require_unit("expected_risk", expected_risk)
    design_coverage = _require_unit("expected_coverage", expected_coverage)
    target = _require_unit("target_pass_probability", target_pass_probability)
    ceiling = _require_size("max_n", max_n)

    for candidate in _plan_candidates(ceiling):
        probability = pass_probability(
            n_verify=candidate,
            risk=design_risk,
            coverage=design_coverage,
            max_risk=limit_risk,
            min_coverage=limit_coverage,
            alpha=family_alpha,
        )
        if probability >= target:
            return candidate
    return None


# --------------------------------------------------------------------------- #
# Threshold selection
# --------------------------------------------------------------------------- #


def _validate_grid(grid: object) -> tuple[float, ...]:
    if isinstance(grid, str | bytes | bytearray) or not isinstance(grid, Sequence):
        raise TypeError("grid must be a sequence")
    if not 1 <= len(grid) <= MAX_GRID_POINTS:
        raise ValueError(f"grid must hold 1..{MAX_GRID_POINTS} thresholds")
    thresholds = tuple(_require_number("grid", item) for item in grid)
    previous = 0.0
    for threshold in thresholds:
        if not previous < threshold <= 1.0:
            raise ValueError("grid must be strictly increasing inside (0, 1]")
        previous = threshold
    return thresholds


def _validate_cases(cases: object) -> tuple[CalibrationCase, ...]:
    if isinstance(cases, str | bytes | bytearray) or not isinstance(cases, Sequence):
        raise TypeError("cases must be a sequence")
    if len(cases) > _MAX_N:
        raise ValueError("cases must hold at most 10000 calibration cases")
    for index, case in enumerate(cases):
        if not isinstance(case, CalibrationCase):
            raise TypeError(f"cases[{index}] must be CalibrationCase")
    return tuple(cases)


def _counts(cases: tuple[CalibrationCase, ...], threshold: float) -> tuple[int, int]:
    """``(accepted, errors)`` at one threshold; a scoreless case is never an ACT."""
    accepted = 0
    errors = 0
    for case in cases:
        if case.score is None or case.score < threshold:
            continue
        accepted += 1
        if not case.correct:
            errors += 1
    return accepted, errors


def select_threshold(
    *,
    grid: Sequence[float],
    cases: Sequence[CalibrationCase],
    n_verify: int,
    max_risk: float,
    min_coverage: float,
    alpha: float,
    target_pass_probability: float = 0.8,
    selection_tail: float = DEFAULT_SELECTION_TAIL,
) -> SelectionResult:
    """Choose a threshold on a calibration split, conservatively.

    Every candidate comes from the caller's ``grid``; nothing is derived from
    the observed scores. For each grid point the calibration split gives an
    accepted count and an error count, which are turned into conservative
    plug-ins at ``selection_tail``: the risk plug-in is the Clopper-Pearson
    upper bound on error-among-ACT (1.0 when nothing is accepted, as the gate
    claims no zero risk there) and the coverage plug-in is the lower bound on
    accepted-among-scheduled. :func:`pass_probability` at those plug-ins is the
    prediction. The selected point is the one accepting the most calibration
    cases among those reaching ``target_pass_probability``, ties going to the
    higher threshold; when none reaches it the threshold is ``None`` with
    reason ``calibration.no_threshold``.

    This is a planning aid only: the PASS guarantee comes from the unchanged
    verification stage on held-out evidence, never from these predictions.
    """
    thresholds = _validate_grid(grid)
    calibration = _validate_cases(cases)
    size = _require_size("n_verify", n_verify)
    limit_risk = _require_unit("max_risk", max_risk)
    limit_coverage = _require_unit("min_coverage", min_coverage)
    family_alpha = _require_alpha(alpha)
    target = _require_unit("target_pass_probability", target_pass_probability)
    tail = _require_tail("selection_tail", selection_tail)

    total = len(calibration)
    points: list[GridPoint] = []
    for threshold in thresholds:
        accepted, errors = _counts(calibration, threshold)
        if accepted == 0:
            plug_in_risk = 1.0
            plug_in_coverage = 0.0
        else:
            plug_in_risk = _exact_tail(errors, accepted, tail)[1]
            plug_in_coverage = _exact_tail(accepted, total, tail)[0]
        points.append(
            GridPoint(
                threshold,
                accepted,
                errors,
                pass_probability(
                    n_verify=size,
                    risk=plug_in_risk,
                    coverage=plug_in_coverage,
                    max_risk=limit_risk,
                    min_coverage=limit_coverage,
                    alpha=family_alpha,
                ),
            )
        )

    chosen: GridPoint | None = None
    for point in points:  # ascending grid, so ">=" sends ties to the higher threshold
        if point.predicted_pass_probability >= target and (
            chosen is None or point.accepted >= chosen.accepted
        ):
            chosen = point
    if chosen is None:
        return SelectionResult(None, REASON_NO_THRESHOLD, tuple(points))
    return SelectionResult(chosen.threshold, REASON_SELECTED, tuple(points))
