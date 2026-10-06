# Actseal concepts

This page explains the vocabulary that the [CLI reference](cli.md), the
[Python guide](python-api.md) and the [FAQ](faq.md) rely on. Exact rules live
in the normative documents it links to: the [stability manifest](stability.md),
the [statistical contract](statistical-contract.md), the
[threat model](threat-model.md) and [CONTRACTS](../plan/CONTRACTS.md). Where
this page and a normative document differ, the normative document wins.

## The frozen question and policy

An Actseal **contract** is one TOML file (schema 1) that fixes, before any
evidence is collected:

- one **choice question**: a `question_id`, `instructions` and an ordered list
  of 2 to 16 options, each with a `label` and a `description`;
- one **policy**: the subset of labels an application may act on
  (`allowed_labels`) and the probability `threshold` the selected label must
  reach;
- the **gate limits**: `max_risk`, `min_coverage` and `alpha`;
- an **evidence scope** (`demo` or `iid`) and a free-text `population`
  description.

`actseal lock` seals the contract together with the labelled calibration and
verification splits, the provider's observed identity, the implementation
fingerprint of the installed package and the six-scenario fault inventory into
a **lock** (schema 2). The lock digest, `lock_sha256`, identifies that frozen
plan. Nothing in the lock can be changed after sealing without changing the
digest; `actseal verify` refuses inputs or a provider that do not match it.

Threshold selection is external. v1 does not fit, search or tune a threshold
from calibration data; the calibration split is bound into the lock so that it
is on record, not consumed by a fitting step.

## Selected-option probability

A provider answers a decision request with one **selected label** and a
probability for every label. Actseal normalizes that answer (finite
probabilities in `[0, 1]`, the frozen label inventory, a bounded mass
tolerance) and then gates on the normalized probability of the label the
provider **selected**. It does not substitute the highest-probability label, and
it ignores any provider "confidence", "action" or suggestion field as a source
of authority. A provider's own confidence score is preserved as evidence
(`ChoiceAnswer.provider_confidence`) but never authorizes an action.

## Per-case decisions

Every scheduled verification case receives exactly one **decision** from the
frozen policy, in this precedence order:

| Order | Condition | Action | Reason code |
|---|---|---|---|
| 1 | The outcome carries a fallback flag | `ESCALATE` | `policy.fallback_used` |
| 2 | Provider failure `unknown_choice` | `DENY` | `policy.unknown_choice` |
| 3 | Any other provider failure | `ESCALATE` | `provider.<failure_code>` |
| 4 | Selected label is not in `allowed_labels` | `DENY` | `policy.disallowed_choice` |
| 5 | Selected probability is below `threshold` | `ABSTAIN` | `policy.low_confidence` |
| 6 | Otherwise | `ACT` | `policy.allowed` |

Only `ACT` carries a choice. `ACT` means the frozen policy permits the
application to execute the selected label; it is not a statement that the label
is correct. `ABSTAIN`, `DENY` and `ESCALATE` are explicit non-execution paths
that the integrating application must handle itself. Actseal does not execute
or block application actions; see the [threat model](threat-model.md).

## The scheduled denominator

With `n` scheduled verification cases, `a` final `ACT` decisions and `e` `ACT`
decisions whose choice differs from the locked gold label:

- **coverage** is estimated by `a / n`;
- **accepted-action risk** is estimated by `e / a` when `a > 0`.

Every scheduled case stays in `n`. Abstentions, denials, escalations and
nonfatal provider failures are not removed from the denominator, and a run
cannot stop early, drop a case or add a replacement sample. The six injected
faults are separate checks and never enter `n`. When `a = 0`, risk is
unestimated: the interval is `[0, 1]` and `PASS` is impossible. Zero observed
errors in a small accepted sample is not evidence of zero risk.

Both rates receive Clopper-Pearson intervals with tail probability `alpha / 4`
on each side, so the four tails together spend at most `alpha`. The
[statistical contract](statistical-contract.md) states the exact construction
and its assumptions.

## Whole-run verdicts

A **verdict** is a statement about the whole run, not about any single case.
There are exactly four, with fixed CLI exit codes:

| Verdict | Exit | Required condition |
|---|---|---|
| `PASS` | 0 | `a > 0`, the risk upper bound is at most `max_risk`, the coverage lower bound is at least `min_coverage`, and every canonical fault produced its required action. |
| `BLOCK` | 1 | The risk lower bound exceeds `max_risk`, or the coverage upper bound is below `min_coverage`, or a valid canonical fault violated its required action. |
| `INCONCLUSIVE` | 2 | Valid evidence proves neither the `PASS` nor the `BLOCK` condition. |
| `ERROR` | 3 | Invalid, incomplete or inconsistent evidence, a setup or usage failure, or an invalidated native-worker experiment. Counts are zero and both intervals are `[0, 1]`. |

Precedence is `ERROR` over `BLOCK` over `INCONCLUSIVE` over `PASS`. There is no
one-to-one mapping between the four per-case actions and the four verdicts: a
run full of `ACT` decisions can `BLOCK` on risk, and a run with many
`ESCALATE` decisions can still `PASS` if enough cases `ACT` correctly.
`ESCALATE` describes one case; it is never a verdict.

## The six canonical faults

`actseal verify` always runs six deterministic fault scenarios against the
locked policy, in this order: `timeout`, `rate_limit`, `malformed_response`
and `identity_mismatch` must `ESCALATE`; `unknown_choice` must `DENY`;
`low_confidence` must `ABSTAIN`. They are generated by the package, not by the
provider, and they test that the policy handles failure shapes as frozen. A
fault that produces the wrong action is a `BLOCK`; missing fault evidence is an
`ERROR`, never a skipped test.

## Evidence scope: demo versus population

The contract's `evidence_scope` labels what the evidence can mean:

- `demo` marks authored or illustrative inputs. The packaged demonstration and
  the native Laya receipt in [providers](providers.md) use this scope. More
  demo cases or repeated replay cannot turn authored examples into a population
  study.
- `iid` asserts that the verification cases are independent outcomes sampled
  from the declared population under the fixed policy and operating regime,
  over one prespecified attempt.

Setting `iid` is a claim by the author, not something Actseal verifies.
Locking hashes, separate file names and consistent replay cannot establish
independent sampling, label truth or that failed attempts were not withheld.
Those assumptions are the reader's to check.

## Evidence bundles and replay

`actseal verify` writes one seven-file **evidence bundle**: a manifest
(schema 2), the lock, both raw input splits, one terminal record per scheduled
case, the six fault results and the verdict. Publication is exclusive: an
existing destination is refused, never overwritten.

`actseal replay` reconstructs every request, re-normalizes every captured
response, re-evaluates the policy, re-checks the fault captures and recomputes
the verdict from those bundle bytes. It imports no provider and makes no
network call. A successful replay reproduces the recorded verdict, which may be
`BLOCK` (exit 1) or a diagnostic `ERROR` (exit 3); exit 0 only means `PASS`
was reproduced.

Replay establishes **consistency**, not authenticity. Someone who can rewrite
a whole bundle can choose new responses and recompute every hash. An expected
lock digest obtained through a separately trusted channel anchors the locked
identity only: even with a trusted lock, a coherent same-lock response rewrite
is undetectable, and replay cannot prove that inference occurred or that the
labels are true. The [threat model](threat-model.md) states these limits.

## One attempt, no retries to PASS

The statistical guarantee is stated over one prespecified attempt. Do not
discard a `BLOCK`, `INCONCLUSIVE` or `ERROR` attempt and run again until a
`PASS` appears, do not adjust the threshold after seeing outcomes, and do not
restart a failed native worker inside an attempt. Each of those actions
invalidates the stated error budget, and hashes cannot detect that the history
was edited. Keep the attempted-run history; a `BLOCK` is a legitimate result.

## Producer provenance versus replay engine

A lock records two separate facts: `implementation_sha256`, the fingerprint of
the exact installed source that produced it, and `replay_engine_version`, the
replay semantics it was produced under (`actseal-choice-v1` throughout 1.x).
The running release replays its own evidence directly. Evidence from a
different 1.x source tree replays only when both fingerprints are registered
for the engine in the packaged compatibility registry; see the
[versioning policy](versioning.md). New collection always requires the exact
running fingerprint. Evidence from actseal 0.1.0 (schema 1) is never converted;
the [migration guide](migration.md) explains the isolated pinned replay path.
