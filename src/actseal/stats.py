"""Exact Clopper-Pearson tail inversion for the Actseal risk/coverage gate.

Attribution
-----------
The numerical kernel in this module is ported from agent-reliability-ci (ARCI),
Copyright 2026 Ajay Surya Senthilrajan, Apache License 2.0, at the immutable
commit ``d13dd94124cb71d378a4e76224fc115b750e8133``:
https://github.com/ajaysurya1221/agent-reliability-ci

Copied units from ``src/arci/stats.py`` at that commit:

* lines 8-10: ``_MAX_N``, ``_BISECTION_STEPS``, ``_MIN_TAIL``;
* lines 15-19: ``_validate_counts``;
* lines 28-59: ``_compare_binomial_prefix``;
* lines 62-83: ``_tail_is_greater``;
* lines 86-102: ``_tail_root``;
* lines 105-113: ``clopper_pearson_tail`` (body unchanged, see modifications).

Local modifications (Apache-2.0 section 4(b) notice; this file was changed):

* ``clopper_pearson_tail`` additionally rejects booleans and non-integer counts
  with ``TypeError`` and a boolean, non-numeric or non-finite tail with
  ``TypeError``/``ValueError`` before the copied validation runs. An integer
  tail too large to convert to binary64 is treated as non-finite
  (``ValueError``) rather than leaking ``OverflowError``. These are Actseal's
  public-boundary rules from CONTRACTS section 1; they reject inputs the
  original accepted by Python's bool/int promotion and never widen the
  numerical domain.
* ``_validate`` (lines 22-25), ``clopper_pearson`` (lines 116-120) and every
  Wilson/Newcombe/Bonferroni unit are intentionally not ported: CONTRACTS
  section 5 freezes only ``clopper_pearson_tail`` and assessment calls it with
  the ``alpha / 4`` tail directly.
* The ``statistics.NormalDist`` import and ``_WILSON_Z_95`` are omitted.
* Tooling-only edits to copied lines, with no behavioral effect: the first
  ``term`` assignment in ``_compare_binomial_prefix`` carries an explicit
  ``int`` annotation (typeshed types ``int ** int`` as ``Any`` under strict
  mypy), and two Ruff ``noqa`` markers suppress positional-argument-count and
  magic-number findings on otherwise unchanged copied lines.

Numerical semantics are unchanged: every bisection step compares a binomial
tail with the target exactly in integer arithmetic at the supplied binary64
inputs, and each returned endpoint is the midpoint of a fixed 60-step
bisection bracket, so bounds depend only on the counts, the tail and IEEE-754
midpoints, never on libm. Returned endpoints are finite-bisection
approximations to the real roots, not the exact roots. Supported domain:
``0 <= successes <= n``, ``1 <= n <= 10_000`` and ``2.5e-7 <= tail < 0.5``.

This module imports only the standard library and nothing else from Actseal so
the numerical tests remain independently runnable.
"""

from __future__ import annotations

import math

_MAX_N = 10_000
_BISECTION_STEPS = 60
_MIN_TAIL = 2.5e-7


def _validate_counts(successes: int, n: int) -> None:
    if n < 1 or n > _MAX_N:
        raise ValueError("n must be between 1 and 10000")
    if successes < 0 or successes > n:
        raise ValueError("successes must be between 0 and n")


def _compare_binomial_prefix(m: int, n: int, a: int, b: int, t: int, d: int) -> int:  # noqa: PLR0917
    """Compare P(X <= m) with t/d, for p=a/b and power-of-two b."""
    if m < 0:
        return -1

    q = b - a
    term: int = math.comb(n, m) * a**m * q ** (n - m)
    total = term
    scale = 1 << (n * (b.bit_length() - 1))
    threshold = scale * t

    while True:
        scaled = total * d
        if scaled > threshold:
            return 1
        if m == 0:
            return (scaled > threshold) - (scaled < threshold)

        numerator = m * q
        denominator = (n - m + 1) * a

        # Remaining descending terms have decreasing ratios. Their sum
        # is bounded above by term * r / (1-r), when r < 1.
        if numerator < denominator:
            gap = denominator - numerator
            if scaled * gap + term * d * numerator < threshold * gap:
                return -1

        # Exact division: this is the next integer binomial numerator.
        term = term * numerator // denominator
        total += term
        m -= 1


def _tail_is_greater(x: int, n: int, p: float, target: float, *, upper: bool) -> bool:
    """Compare a binomial tail exactly at the supplied binary64 inputs."""
    if p <= 0.0:
        return x == 0 if upper else True
    if p >= 1.0:
        return True if upper else x == n

    a, b = p.as_integer_ratio()
    t, d = target.as_integer_ratio()
    cutoff = x - 1 if upper else x
    complement = upper

    # Reflect when needed so descending terms decrease from the start.
    # Form complements as integers, without rounded float subtraction.
    if cutoff * b > (n + 1) * a:
        cutoff = n - cutoff - 1
        a = b - a
        complement = not complement

    if complement:
        return _compare_binomial_prefix(cutoff, n, a, b, d - t, d) < 0
    return _compare_binomial_prefix(cutoff, n, a, b, t, d) > 0


def _tail_root(x: int, n: int, target: float, *, upper: bool) -> float:
    """Solve a binomial upper or lower tail equation by bisection."""
    low = 0.0
    high = 1.0
    for _ in range(_BISECTION_STEPS):
        midpoint = (low + high) / 2.0
        greater = _tail_is_greater(x, n, midpoint, target, upper=upper)
        if upper:
            if greater:
                high = midpoint
            else:
                low = midpoint
        elif greater:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def _require_count(name: str, value: object) -> int:
    """Actseal boundary: counts are plain integers, never booleans."""
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    return value


def _require_tail(value: object) -> float:
    """Actseal boundary: the tail is a finite number, never a boolean.

    An integer too large for binary64 makes ``math.isfinite`` raise
    ``OverflowError`` instead of answering; such a tail is not finite in the
    supported domain and is reported as the documented ``ValueError`` without
    echoing the input.
    """
    if type(value) is bool or not isinstance(value, int | float):
        raise TypeError("tail must be a number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("tail must be finite")
    return value


def clopper_pearson_tail(successes: int, n: int, tail: float) -> tuple[float, float]:
    """Return an exact interval by directly inverting each tail probability."""
    successes = _require_count("successes", successes)
    n = _require_count("n", n)
    tail = _require_tail(tail)
    _validate_counts(successes, n)
    if not _MIN_TAIL <= tail < 0.5:  # noqa: PLR2004
        raise ValueError("tail must be between 2.5e-7 (inclusive) and 0.5 (exclusive)")

    low = 0.0 if successes == 0 else _tail_root(successes, n, tail, upper=True)
    high = 1.0 if successes == n else _tail_root(successes, n, tail, upper=False)
    return low, high
