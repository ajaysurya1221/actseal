# Actseal v1 statistical contract

**Statistical core accepted; CLI/demo, final acceptance and release pending.** [T20's review](../plan/reviews/T20-02.md) records acceptance of the numerical kernel and complete-evidence assessment; [T40's review](../plan/reviews/T40-02.md) covers fresh replay. Exact APIs/verdict rules live in [CONTRACTS](../plan/CONTRACTS.md). [ADR 0003](decisions/0003-risk-coverage-statistical-contract.md) and [ADR 0009](decisions/0009-worker-loss-invalidates-statistical-run.md) explain the inference and worker-loss decisions.

## Target and assumptions

The target is the error rate among final ACT decisions and the fraction of cases receiving ACT under one fixed categorical policy and operating regime. The policy, label inventory, threshold, model/runtime identity and verification sample must be fixed before one prespecified attempt. Threshold selection is external; v1 does not fit or search it.

Population interpretation requires independent case outcomes sampled from the declared distribution under the fixed selector/regime. Independent input text alone is insufficient if provider state couples later outcomes to earlier requests. The binomial sampling requirements are discussed in the [NIST reference](https://www.itl.nist.gov/div898/handbook/eda/section3/eda366i.htm); the project-specific restriction is ADR 0009.

`evidence_scope=demo` identifies authored examples. More demo cases or repeated replay cannot turn those examples into a population study. Setting `evidence_scope=iid`, locking hashes or using separate filenames cannot establish IID sampling, label truth or whether labels were withheld. Even a trusted lock digest does not authenticate responses or execution; internally consistent same-lock response rewrites remain possible, as described in the [trust boundary](threat-model.md).

The pending demo uses different authored outcomes under the **same policy, threshold and limits**. Its prescribed correct/wrong choices are intended to produce PASS/BLOCK through the actual assessment; they are not model improvement, training or a paired-model experiment. [ADR 0013](decisions/0013-prespecified-synthetic-demo.md) contains the rules and explicitly separates planning calculations from product-run receipts. T50 must supply those receipts without hard-coded verdicts or metrics.

## Counts and intervals

First validate the entire lock, exact ordered case/fault inventories and reconstructed semantics. For every verification case, rebuild its request from the locked case, validate the capture hash, normalize the raw response and evaluate the policy again. Recorded outcomes/actions must match. Gold labels come from the locked verification cases, not a new caller-supplied list.

| Symbol | Definition |
|---|---|
| `n` | Every prescheduled verification case, with `1 <= n <= 10,000`. |
| `a` | Cases whose final disposition is ACT. |
| `e` | ACT choices that disagree with their single locked gold label. |
| Risk | Selected-population error, estimated by `e/a` when `a > 0`. |
| Coverage | Probability of ACT under the fixed case-level experiment, estimated by `a/n`. |

Abstentions, denials, escalations and nonfatal provider failures stay in `n`. The six injected faults never enter statistical counts. Do not stop at a desired ACT count, omit failures, extend a run after seeing its result or count replays as additional observations.

Compute Clopper–Pearson intervals for `e/a` and `a/n`, with tail probability `alpha/4` on each side. Four tails allocate at most `alpha` total interval noncoverage by the union bound under the stated assumptions; independence between the two estimated intervals is not required. The audited kernel's domain is `n=1…10,000` and tail `[2.5e-7, 0.5)`. It uses exact integer-tail comparisons and finite bisection; T20 acceptance includes independent numerical oracle and boundary checks for the Actseal implementation.

When `a=0`, risk is unestimated: report `[0,1]` and prohibit PASS. Zero accepted errors in a small accepted sample is not proof of zero risk. The provider's score need not be a calibrated probability; it selects cases under the frozen rule, while these bounds use observed labelled outcomes.

## Verdict rules

| Verdict | Required condition |
|---|---|
| PASS | `a > 0`, risk upper bound `<= max_risk`, and coverage lower bound `>= min_coverage`. |
| BLOCK | Risk lower bound `> max_risk`, or coverage upper bound `< min_coverage`, or a valid canonical fault violates its required action. |
| INCONCLUSIVE | Valid evidence proves neither the PASS nor BLOCK condition. |
| ERROR | Invalid/incomplete/inconsistent evidence, setup failure or the infrastructure invalidation below. Counts are zero and both intervals are `[0,1]`. |

Precedence is ERROR → BLOCK → INCONCLUSIVE → PASS. Risk's upper bound exceeding the allowed maximum alone does not prove BLOCK; it can mean insufficient evidence. Missing fault evidence is ERROR, not a skipped test. Policy dispositions such as ESCALATE describe individual cases; they are distinct from the aggregate verdict.

## Permanent worker loss

After complete integrity validation, any **regular Laya** capture with `failure_code=timeout` or `unavailable` forces ERROR with `infrastructure.worker_invalidated`. Preserve every scheduled terminal record, including later unavailable outcomes, as diagnostic evidence. Canonical synthetic faults do not trigger this rule. A recoverable provider error may remain a case outcome only while the worker and request/reply synchronization remain healthy.

No automatic restart, retry, replacement sample, post-failure resealing or deletion of ERROR attempts is permitted. A diagnostic ERROR bundle can replay consistently without becoming completed statistical certification.

The intended guarantee is unconditional over one prespecified attempt. Requiring completion only removes outcomes from the fixed-sample PASS event; it does not justify confidence statements conditioned on completion. These intervals provide no bound on persistent-process uptime or run-completion probability. Never discard failed attempts and retry until PASS; retain the attempted-run history. Hashes cannot prove that history is honest.

Baseline comparisons, sequential looks, slices, grouped guarantees, threshold sweeps and certified fallback chains are outside v1. Each would require a separately specified sampling rule and error budget.
