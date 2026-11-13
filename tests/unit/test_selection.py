"""Unit tests for ``actseal.selection``: boundary rules and documented edge cases.

The numerical content of the three functions is pinned by independent oracles in
``tests/properties/test_selection_properties.py``. This file covers the public
boundary (types, domains, grid validation), the degenerate calibration splits
(no cases, no scores, nothing accepted), the tie rule, and the behaviour the
module promises in prose: a zero ACT count never passes, a scoreless case is
never accepted but still counts in the coverage denominator, and a smaller
selection tail is never less conservative.
"""

from __future__ import annotations

import math

import pytest

from actseal.selection import (
    DEFAULT_SELECTION_TAIL,
    MAX_GRID_POINTS,
    REASON_NO_THRESHOLD,
    REASON_SELECTED,
    CalibrationCase,
    SelectionResult,
    pass_probability,
    plan_sample_size,
    select_threshold,
)

GATE = {"max_risk": 0.3, "min_coverage": 0.2, "alpha": 0.1}


def block(score: float | None, count: int, wrong: int) -> list[CalibrationCase]:
    """``count`` cases at one score, the first ``wrong`` of them incorrect."""
    return [CalibrationCase(score, index >= wrong) for index in range(count)]


#: 120 calibration cases: a clean top band, a nearly clean middle band and a
#: bottom band bad enough to make the lowest threshold unselectable.
CASES = tuple(block(0.9, 40, 0) + block(0.6, 40, 1) + block(0.3, 40, 25))


# --------------------------------------------------------------------------- #
# CalibrationCase
# --------------------------------------------------------------------------- #


def test_calibration_case_accepts_a_missing_score() -> None:
    case = CalibrationCase(None, False)
    assert case.score is None
    assert case.correct is False


def test_calibration_case_normalizes_an_integer_score() -> None:
    case = CalibrationCase(1, True)
    assert type(case.score) is float
    assert case.score == 1.0


def test_calibration_case_rejects_a_non_numeric_or_boolean_score() -> None:
    with pytest.raises(TypeError, match=r"^score must be a number$"):
        CalibrationCase("0.5", True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^score must be a number$"):
        CalibrationCase(True, True)


def test_calibration_case_rejects_a_non_finite_score() -> None:
    for score in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError, match=r"^score must be finite$"):
            CalibrationCase(score, True)


def test_calibration_case_rejects_a_non_boolean_correct_flag() -> None:
    with pytest.raises(TypeError, match=r"^correct must be a boolean$"):
        CalibrationCase(0.5, 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^correct must be a boolean$"):
        CalibrationCase(0.5, None)  # type: ignore[arg-type]


def test_calibration_case_is_frozen() -> None:
    case = CalibrationCase(0.5, True)
    with pytest.raises(AttributeError):
        case.score = 0.6  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Boundary rules of pass_probability
# --------------------------------------------------------------------------- #


def test_pass_probability_rejects_a_sample_size_outside_the_supported_range() -> None:
    for size in (0, -1, 10_001):
        with pytest.raises(ValueError, match=r"^n_verify must be between 1 and 10000$"):
            pass_probability(n_verify=size, risk=0.0, coverage=1.0, **GATE)


def test_pass_probability_rejects_a_non_integer_sample_size() -> None:
    for size in (1.0, True, "10"):
        with pytest.raises(TypeError, match=r"^n_verify must be an integer$"):
            pass_probability(n_verify=size, risk=0.0, coverage=1.0, **GATE)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["risk", "coverage", "max_risk", "min_coverage"])
def test_pass_probability_rejects_a_probability_outside_the_unit_interval(name: str) -> None:
    for value in (-0.1, 1.5):
        arguments = {"n_verify": 10, "risk": 0.1, "coverage": 0.5, **GATE, name: value}
        with pytest.raises(ValueError, match=rf"^{name} must be between 0 and 1$"):
            pass_probability(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["risk", "coverage", "max_risk", "min_coverage"])
def test_pass_probability_rejects_a_non_finite_or_boolean_probability(name: str) -> None:
    arguments = {"n_verify": 10, "risk": 0.1, "coverage": 0.5, **GATE, name: math.nan}
    with pytest.raises(ValueError, match=rf"^{name} must be finite$"):
        pass_probability(**arguments)  # type: ignore[arg-type]
    arguments[name] = True
    with pytest.raises(TypeError, match=rf"^{name} must be a number$"):
        pass_probability(**arguments)  # type: ignore[arg-type]


def test_pass_probability_rejects_an_alpha_outside_the_contract_domain() -> None:
    for alpha in (0.0, 1e-7, 1.0, 2.0):
        with pytest.raises(
            ValueError, match=r"^alpha must be between 1e-6 \(inclusive\) and 1 \(exclusive\)$"
        ):
            pass_probability(
                n_verify=10,
                risk=0.0,
                coverage=1.0,
                max_risk=0.3,
                min_coverage=0.2,
                alpha=alpha,
            )


def test_pass_probability_accepts_the_alpha_domain_corners() -> None:
    for alpha in (1e-6, math.nextafter(1.0, 0.0)):
        value = pass_probability(
            n_verify=50, risk=0.0, coverage=1.0, max_risk=0.3, min_coverage=0.2, alpha=alpha
        )
        assert 0.0 <= value <= 1.0


# --------------------------------------------------------------------------- #
# Documented behaviour of pass_probability
# --------------------------------------------------------------------------- #


def test_a_certain_act_with_no_limits_passes_surely() -> None:
    assert (
        pass_probability(
            n_verify=1, risk=0.0, coverage=1.0, max_risk=1.0, min_coverage=0.0, alpha=0.05
        )
        == 1.0
    )


def test_an_unreachable_coverage_floor_can_never_pass() -> None:
    assert (
        pass_probability(
            n_verify=100, risk=0.0, coverage=1.0, max_risk=1.0, min_coverage=1.0, alpha=0.05
        )
        == 0.0
    )


def test_a_zero_act_count_never_passes_even_without_a_coverage_floor() -> None:
    """``assess`` reports ``risk.no_accepted_cases`` and never PASSes at a == 0."""
    assert (
        pass_probability(
            n_verify=1, risk=0.0, coverage=0.0, max_risk=1.0, min_coverage=0.0, alpha=0.05
        )
        == 0.0
    )
    # With coverage 0.5 the only passing outcome is the single ACT, mass 0.5.
    half = pass_probability(
        n_verify=1, risk=0.0, coverage=0.5, max_risk=1.0, min_coverage=0.0, alpha=0.05
    )
    assert half == pytest.approx(0.5, abs=1e-12)


def test_a_risk_limit_the_tightest_interval_cannot_clear_never_passes() -> None:
    """At a == 1 the risk upper bound is 1 - tail, so a smaller limit is unreachable."""
    assert (
        pass_probability(
            n_verify=1, risk=0.0, coverage=1.0, max_risk=0.5, min_coverage=0.0, alpha=0.05
        )
        == 0.0
    )


def test_the_probability_falls_as_the_true_risk_rises() -> None:
    values = [
        pass_probability(
            n_verify=200,
            risk=risk,
            coverage=0.8,
            max_risk=0.2,
            min_coverage=0.5,
            alpha=0.1,
        )
        for risk in (0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.4)
    ]
    assert values == sorted(values, reverse=True)
    assert values[0] > 0.9
    assert values[-1] < 0.01


def test_the_probability_rises_with_the_true_coverage() -> None:
    values = [
        pass_probability(
            n_verify=200,
            risk=0.02,
            coverage=coverage,
            max_risk=0.2,
            min_coverage=0.5,
            alpha=0.1,
        )
        for coverage in (0.2, 0.4, 0.5, 0.6, 0.8, 1.0)
    ]
    assert values == sorted(values)


def test_the_largest_supported_sample_size_is_answered_promptly() -> None:
    value = pass_probability(
        n_verify=10_000, risk=0.02, coverage=0.85, max_risk=0.05, min_coverage=0.8, alpha=0.05
    )
    assert value == pytest.approx(1.0, abs=1e-9)
    hopeless = pass_probability(
        n_verify=10_000, risk=0.2, coverage=0.85, max_risk=0.05, min_coverage=0.8, alpha=0.05
    )
    assert hopeless == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# plan_sample_size
# --------------------------------------------------------------------------- #


#: One design point, reused so the planner and the probability agree on it.
DESIGN_MAX_RISK = 0.2
DESIGN_MIN_COVERAGE = 0.25
DESIGN_ALPHA = 0.1
DESIGN_RISK = 0.028
DESIGN_COVERAGE = 0.38


def plan(*, target: float = 0.8, max_n: int = 10_000) -> int | None:
    return plan_sample_size(
        max_risk=DESIGN_MAX_RISK,
        min_coverage=DESIGN_MIN_COVERAGE,
        alpha=DESIGN_ALPHA,
        expected_risk=DESIGN_RISK,
        expected_coverage=DESIGN_COVERAGE,
        target_pass_probability=target,
        max_n=max_n,
    )


def reached(size: int) -> float:
    return pass_probability(
        n_verify=size,
        risk=DESIGN_RISK,
        coverage=DESIGN_COVERAGE,
        max_risk=DESIGN_MAX_RISK,
        min_coverage=DESIGN_MIN_COVERAGE,
        alpha=DESIGN_ALPHA,
    )


def test_the_planned_size_is_the_first_schedule_entry_that_reaches_the_target() -> None:
    planned = plan()
    assert planned is not None
    assert planned <= 200  # inside the unit-step part of the schedule
    assert reached(planned) >= 0.8
    assert reached(planned - 1) < 0.8


def test_a_target_of_zero_is_reached_by_the_smallest_size() -> None:
    assert (
        plan_sample_size(
            max_risk=0.3,
            min_coverage=0.2,
            alpha=0.1,
            expected_risk=0.5,
            expected_coverage=0.0,
            target_pass_probability=0.0,
        )
        == 1
    )


def test_an_impossible_design_point_plans_no_size() -> None:
    assert (
        plan_sample_size(
            max_risk=0.01,
            min_coverage=0.9,
            alpha=0.05,
            expected_risk=0.05,
            expected_coverage=0.5,
        )
        is None
    )


def test_the_ceiling_is_respected_and_is_itself_a_candidate() -> None:
    assert plan(max_n=10) is None
    planned = plan()
    assert planned is not None
    assert plan(max_n=planned) == planned
    assert plan(max_n=planned - 1) is None


def test_plan_sample_size_rejects_an_out_of_range_ceiling() -> None:
    for ceiling in (0, -5, 10_001):
        with pytest.raises(ValueError, match=r"^max_n must be between 1 and 10000$"):
            plan(max_n=ceiling)
    with pytest.raises(TypeError, match=r"^max_n must be an integer$"):
        plan(max_n=10.0)  # type: ignore[arg-type]


def test_plan_sample_size_rejects_an_out_of_range_target() -> None:
    with pytest.raises(ValueError, match=r"^target_pass_probability must be between 0 and 1$"):
        plan_sample_size(
            max_risk=0.2,
            min_coverage=0.25,
            alpha=0.1,
            expected_risk=0.02,
            expected_coverage=0.5,
            target_pass_probability=1.5,
        )


# --------------------------------------------------------------------------- #
# Grid and case validation in select_threshold
# --------------------------------------------------------------------------- #


def select(**overrides: object) -> SelectionResult:
    arguments: dict[str, object] = {
        "grid": (0.3, 0.6, 0.9),
        "cases": CASES,
        "n_verify": 300,
        **GATE,
    }
    arguments.update(overrides)
    return select_threshold(**arguments)  # type: ignore[arg-type]


def test_the_grid_must_be_a_sequence_of_numbers() -> None:
    with pytest.raises(TypeError, match=r"^grid must be a sequence$"):
        select(grid=0.5)
    with pytest.raises(TypeError, match=r"^grid must be a sequence$"):
        select(grid="0.5")
    with pytest.raises(TypeError, match=r"^grid must be a sequence$"):
        select(grid={0.5: 1})
    with pytest.raises(TypeError, match=r"^grid must be a number$"):
        select(grid=(0.5, None))
    with pytest.raises(TypeError, match=r"^grid must be a number$"):
        select(grid=(True,))


def test_the_grid_size_is_bounded() -> None:
    with pytest.raises(ValueError, match=r"^grid must hold 1\.\.32 thresholds$"):
        select(grid=())
    too_many = tuple((index + 1) / (MAX_GRID_POINTS + 2) for index in range(MAX_GRID_POINTS + 1))
    with pytest.raises(ValueError, match=r"^grid must hold 1\.\.32 thresholds$"):
        select(grid=too_many)
    largest = tuple((index + 1) / (MAX_GRID_POINTS + 1) for index in range(MAX_GRID_POINTS))
    assert len(select(grid=largest).points) == MAX_GRID_POINTS


def test_the_grid_must_be_strictly_increasing_inside_the_unit_interval() -> None:
    for grid in ((0.0,), (0.5, 0.5), (0.6, 0.3), (-0.1,), (0.5, 1.5)):
        with pytest.raises(ValueError, match=r"^grid must be strictly increasing inside \(0, 1\]$"):
            select(grid=grid)
    assert select(grid=(1.0,)).points[0].threshold == 1.0


def test_the_cases_must_be_a_bounded_sequence_of_calibration_cases() -> None:
    with pytest.raises(TypeError, match=r"^cases must be a sequence$"):
        select(cases=CASES[0])
    with pytest.raises(TypeError, match=r"^cases must be a sequence$"):
        select(cases="scores")
    with pytest.raises(TypeError, match=r"^cases\[1\] must be CalibrationCase$"):
        select(cases=(CASES[0], (0.5, True)))
    with pytest.raises(ValueError, match=r"^cases must hold at most 10000 calibration cases$"):
        select(cases=[CalibrationCase(0.9, True)] * 10_001)


def test_select_threshold_rejects_a_selection_tail_outside_the_kernel_domain() -> None:
    for tail in (0.0, 0.5, 2.4e-7, 1.0):
        with pytest.raises(
            ValueError,
            match=r"^selection_tail must be between 2\.5e-7 \(inclusive\) and 0\.5 \(exclusive\)$",
        ):
            select(selection_tail=tail)


def test_select_threshold_rejects_an_out_of_range_target() -> None:
    with pytest.raises(ValueError, match=r"^target_pass_probability must be between 0 and 1$"):
        select(target_pass_probability=-0.5)


# --------------------------------------------------------------------------- #
# Selection behaviour of select_threshold
# --------------------------------------------------------------------------- #


def test_the_most_accepting_grid_point_that_reaches_the_target_is_selected() -> None:
    result = select()
    assert result.reason == REASON_SELECTED
    assert result.threshold == 0.6
    assert [(point.threshold, point.accepted, point.errors) for point in result.points] == [
        (0.3, 120, 26),
        (0.6, 80, 1),
        (0.9, 40, 0),
    ]
    predicted = [point.predicted_pass_probability for point in result.points]
    assert predicted[0] < 0.8  # the bottom band is too error-prone to select
    assert predicted[1] >= 0.8
    assert predicted[2] >= 0.8 or predicted[1] > predicted[2]


def test_the_most_accepting_of_two_qualifying_points_is_preferred() -> None:
    """When multiple grid points reach the target, the one accepting more wins.

    At ``max_risk=0.4`` both the bottom and middle bands clear the target, with
    120 and 80 accepted respectively: the selector must pick the larger
    acceptance (0.3), not settle for the smaller one just because it also
    qualifies.
    """
    result = select(max_risk=0.4)
    assert result.reason == REASON_SELECTED
    predicted = {point.threshold: point.predicted_pass_probability for point in result.points}
    assert predicted[0.3] >= 0.8
    assert predicted[0.6] >= 0.8
    accepted = {point.threshold: point.accepted for point in result.points}
    assert accepted[0.3] > accepted[0.6]
    assert result.threshold == 0.3


def test_a_tie_on_accepted_cases_goes_to_the_higher_threshold() -> None:
    result = select(grid=(0.65, 0.75), target_pass_probability=0.5)
    accepted = {point.accepted for point in result.points}
    predicted = {point.predicted_pass_probability for point in result.points}
    assert accepted == {40}
    assert len(predicted) == 1  # identical counts, so identical predictions
    assert result.threshold == 0.75
    assert result.reason == REASON_SELECTED


def test_no_grid_point_reaching_the_target_selects_nothing() -> None:
    result = select(max_risk=0.01)
    assert result.threshold is None
    assert result.reason == REASON_NO_THRESHOLD
    assert len(result.points) == 3
    assert all(point.predicted_pass_probability == 0.0 for point in result.points)


def test_an_empty_calibration_split_selects_nothing() -> None:
    result = select(cases=())
    assert result.threshold is None
    assert result.reason == REASON_NO_THRESHOLD
    assert [
        (point.accepted, point.errors, point.predicted_pass_probability) for point in result.points
    ] == [(0, 0, 0.0), (0, 0, 0.0), (0, 0, 0.0)]


def test_a_split_without_any_score_selects_nothing() -> None:
    result = select(cases=tuple(block(None, 40, 20)))
    assert result.threshold is None
    assert result.reason == REASON_NO_THRESHOLD
    assert all(point.accepted == 0 for point in result.points)


def test_a_threshold_above_every_score_accepts_nothing() -> None:
    result = select(grid=(0.95, 1.0))
    assert result.threshold is None
    assert [point.accepted for point in result.points] == [0, 0]
    assert all(point.predicted_pass_probability == 0.0 for point in result.points)


def test_a_scoreless_case_is_never_accepted_but_still_dilutes_coverage() -> None:
    padded = select(cases=tuple(block(None, 60, 30)) + CASES)
    plain = select()
    assert [point.accepted for point in padded.points] == [point.accepted for point in plain.points]
    assert [point.errors for point in padded.points] == [point.errors for point in plain.points]
    for padded_point, plain_point in zip(padded.points, plain.points, strict=True):
        assert padded_point.predicted_pass_probability <= plain_point.predicted_pass_probability


def test_a_smaller_selection_tail_is_never_less_conservative() -> None:
    wide = select(selection_tail=0.2)
    narrow = select(selection_tail=0.0125)
    for narrow_point, wide_point in zip(narrow.points, wide.points, strict=True):
        assert narrow_point.predicted_pass_probability <= wide_point.predicted_pass_probability


def test_the_default_selection_tail_is_inside_the_kernel_domain() -> None:
    assert 2.5e-7 <= DEFAULT_SELECTION_TAIL < 0.5
    assert select(selection_tail=DEFAULT_SELECTION_TAIL) == select()


def test_the_result_reports_every_grid_point_in_grid_order() -> None:
    grid = (0.2, 0.4, 0.6, 0.8)
    result = select(grid=grid)
    assert tuple(point.threshold for point in result.points) == grid


def test_the_evaluated_grid_is_reported_even_when_nothing_is_selected() -> None:
    result = select(target_pass_probability=1.0)
    assert result.threshold is None
    assert len(result.points) == 3
    assert max(point.predicted_pass_probability for point in result.points) < 1.0
