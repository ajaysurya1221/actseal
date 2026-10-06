# ADR 0003: Prespecified risk and coverage gates with a fixed sample size

- Status: accepted.
- Date: 2026-10-06.

## Decision

Freeze the categorical policy and one externally selected threshold before certification. Calibration and certification use separately identified datasets. The lock binds their content hashes and ordered case inventories. The v1 CLI locks an already chosen threshold; it does not optimize thresholds against certification results.

Prespecify `1 <= n_total <= 10_000`. Run each expected certification case once. Every case, including abstention, provider failure, malformed response, and fallback escalation, remains in the coverage denominator. An accepted case is one whose **final disposition is ACT**. Its classification error is disagreement with the case's single gold label. Never stop after obtaining a desired number of accepted cases or extend a run after observing its verdict.

At family alpha `0.05`, allocate one tail `0.0125 = alpha / 4` to each side of the risk and coverage intervals. Compute CP intervals for error risk `errors / n_accepted` and coverage `n_accepted / n_total`. The union bound controls simultaneous interval noncoverage at at most `0.05` under the stated sampling assumptions; independence between the two interval estimates is not required.

| Statistical verdict | Frozen comparison |
|---|---|
| PASS | Risk upper bound `<= maximum_risk` **and** coverage lower bound `>= minimum_coverage` |
| BLOCK | Risk lower bound `> maximum_risk` **or** coverage upper bound `< minimum_coverage` |
| INCONCLUSIVE | Neither condition above |

When `n_accepted == 0`, use risk bounds `[0, 1]`, report risk unestimated, and prohibit PASS. Invalid counts or an incomplete experiment are ERROR. A required deterministic fault-contract violation is BLOCK. Aggregate precedence is **ERROR, BLOCK, INCONCLUSIVE, PASS**. Missing required fault evidence is ERROR, not an omitted check.

## Interpretation

Population statements require independent cases sampled from the declared target distribution and a fixed selector before certification. The accepted-case count is random; under IID cases, the errors conditional on that count have the relevant selected-population binomial interpretation. Authored fixed suites report observed performance and demo behavior; their size alone does not justify population inference. Replaying a record creates no additional sample.

The fixture demo is explicitly **demo-only** and says nothing about Laya/Jev accuracy, deployment safety, or population calibration. Reusing certification labels to select thresholds, retrying unchanged candidates until one passes, or treating deterministic test repetitions as new observations invalidates the intended inferential interpretation. Hashes expose changes to recorded inputs; they do not prove that a user withheld labels or sampled IID cases.

Paired non-inferiority, sequential looks, threshold sweeps, grouped claims, and certified fallback chains are outside v1. Any later addition needs a separately specified error budget and independent validation. See [CONTRACTS](../../plan/CONTRACTS.md) for exact schemas and [PLAN](../../plan/PLAN.md) for acceptance commands.
