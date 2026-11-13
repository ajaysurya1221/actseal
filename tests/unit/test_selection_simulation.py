"""Seeded Monte Carlo of ``actseal.selection`` at a realistic risk limit.

``tests/properties/test_selection_properties.py`` already runs a seeded
Monte Carlo pipeline (select on a calibration split, then PASS/BLOCK a fresh
verification split with the frozen rule), but at a loose gate -
``max_risk = 0.25``, ``min_coverage = 0.25`` - that leaves enormous margin
everywhere and would not catch a selector that is only mildly overconfident.

This module repeats that shape of test at limits a real high-stakes
deployment would plausibly set: ``max_risk = 0.05`` and ``alpha = 0.05``. The
verification split is sized by :func:`actseal.selection.plan_sample_size`
itself, at a design point a planner would plausibly use (expected risk 1%,
expected coverage 90%, target pass probability 0.8), so the planner and the
pipeline cannot silently drift apart. The synthetic population is built so a
correctly chosen threshold's true risk sits far inside ``max_risk`` and its
true coverage far inside ``min_coverage``; the floor below is a property of
the whole pipeline (selection on calibration, then a fresh PASS/BLOCK
decision), not a restatement of any one function's own unit tests.
"""

from __future__ import annotations

import random

import pytest

from actseal.selection import (
    DEFAULT_SELECTION_TAIL,
    CalibrationCase,
    plan_sample_size,
    select_threshold,
)
from actseal.stats import clopper_pearson_tail as kernel

#: Mirrors ``actseal.assessment.TAIL_DIVISOR``: each one-sided tail spends
#: ``alpha / 4``.
TAIL_DIVISOR = 4

#: A case has no score at all (can never become an ACT) with this probability;
#: otherwise its score is uniform on [0, 1) and is wrong with probability
#: ``ERROR_RATE`` regardless of score - a clean, uniformly accurate population,
#: so every grid point's true risk is the same and selection is driven purely
#: by which point accepts the most cases while still clearing the target.
MISSING_RATE = 0.02
ERROR_RATE = 0.0005
GRID = (0.05, 0.15, 0.3, 0.5)

MAX_RISK = 0.05
MIN_COVERAGE = 0.5
ALPHA = 0.05
CALIBRATION_SIZE = 500

#: The design point handed to the planner: a realistic expectation of 1% risk
#: and 90% coverage, with the planner's own default target.
DESIGN_RISK = 0.01
DESIGN_COVERAGE = 0.9
DESIGN_TARGET = 0.8

SEED_MONTE_CARLO_REALISTIC = 20261117

#: 300 seeded draws finish in roughly 13s locally (well under the ~20s
#: budget): 283/300 (94.3%) passed and 17/300 (5.7%) selected nothing, on this
#: exact seed and draw count, against the 0.75 floor asserted below.
MONTE_CARLO_DRAWS = 300
PASS_RATE_FLOOR = 0.75


def draw_outcome(rng: random.Random) -> tuple[float | None, bool]:
    """One population draw as ``(score, correct)``; ``None`` means no score at all."""
    if rng.random() < MISSING_RATE:
        return None, False
    score = rng.random()
    return score, rng.random() >= ERROR_RATE


def draw_case(rng: random.Random) -> CalibrationCase:
    return CalibrationCase(*draw_outcome(rng))


def verification_passes(*, accepted: int, errors: int, total: int) -> bool:
    """The PASS rule of ``actseal.assessment``, rebuilt from its documented step."""
    tail = ALPHA / TAIL_DIVISOR
    if accepted == 0:
        return False  # risk.no_accepted_cases: the interval is [0, 1], never a PASS
    if kernel(errors, accepted, tail)[1] > MAX_RISK:
        return False
    return kernel(accepted, total, tail)[0] >= MIN_COVERAGE


def planned_verification_size() -> int:
    size = plan_sample_size(
        max_risk=MAX_RISK,
        min_coverage=MIN_COVERAGE,
        alpha=ALPHA,
        expected_risk=DESIGN_RISK,
        expected_coverage=DESIGN_COVERAGE,
        target_pass_probability=DESIGN_TARGET,
    )
    assert size is not None, "the realistic design point must itself be plannable"
    return size


def run_pipeline(*, n_verify: int, draws: int) -> tuple[int, int]:
    """``(verified PASSes, draws where nothing qualified)`` over seeded splits."""
    rng = random.Random(SEED_MONTE_CARLO_REALISTIC)  # noqa: S311
    passed = 0
    unselected = 0
    for _ in range(draws):
        calibration = [draw_case(rng) for _ in range(CALIBRATION_SIZE)]
        result = select_threshold(
            grid=GRID,
            cases=calibration,
            n_verify=n_verify,
            max_risk=MAX_RISK,
            min_coverage=MIN_COVERAGE,
            alpha=ALPHA,
            selection_tail=DEFAULT_SELECTION_TAIL,
        )
        if result.threshold is None:
            unselected += 1
            continue
        accepted = 0
        errors = 0
        for _ in range(n_verify):
            score, correct = draw_outcome(rng)
            if score is None or score < result.threshold:
                continue
            accepted += 1
            if not correct:
                errors += 1
        if verification_passes(accepted=accepted, errors=errors, total=n_verify):
            passed += 1
    return passed, unselected


def test_the_realistic_design_point_is_itself_plannable() -> None:
    """The planner must accept the design point before the pipeline can use it."""
    size = planned_verification_size()
    assert 1 <= size <= 10_000


def test_selection_pipeline_passes_at_a_realistic_risk_limit() -> None:
    """300 seeded draws at ``max_risk = 0.05``, ``alpha = 0.05`` (not the loose 0.25

    used by ``tests/properties/test_selection_properties.py``). Verification size
    comes from :func:`plan_sample_size` at a realistic design point, so selection
    is exercised exactly as a real deployment would size and run it: choose a
    threshold on calibration, then PASS/BLOCK a fresh verification split with the
    unchanged frozen rule.
    """
    n_verify = planned_verification_size()
    passed, unselected = run_pipeline(n_verify=n_verify, draws=MONTE_CARLO_DRAWS)
    rate = passed / MONTE_CARLO_DRAWS
    assert rate >= PASS_RATE_FLOOR, (rate, unselected)
    assert unselected <= MONTE_CARLO_DRAWS // 5, unselected


if __name__ == "__main__":  # pragma: no cover - manual measurement aid
    pytest.main([__file__, "-q"])
