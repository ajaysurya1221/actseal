# ADR 0018: Interpret the Jev audit as a finite-benchmark descriptive study

- Status: approved protocol (plan/v1/PLAN.md section C, Decision 3A;
  supplement in plan/v1/tasks/06-collection-supplement.md, amendment V1-013);
  offline implementation and preregistration candidate 3 accepted; live
  collection not performed (attempt stopped by a harness denial before any
  key read or call).
- Date: 2026-10-07.

## Decision

The optional live audit of the experimental Jev provider is a
**preregistered finite-benchmark descriptive audit**. It makes no power
claim, no population-calibration claim and no IID-sampling claim.

Frozen protocol, exactly as approved:

- Banking77 at commit `57ec275d8078af65b7731c2a98be812d844a6d6b`; the first
  16 original label strings in Python's case-sensitive sort.
- Calibration: the first 20 unique training texts per label after excluding
  every normalized test text (320 cases). Verification: first occurrences in
  original test order after deduplication (639 cases). Normalization is
  exactly `text.strip().casefold()`. Both inventories are fixed before any
  inference; 959 requests in total.
- Fixed example policy: threshold `0.80`, `max_risk` `0.05`,
  `min_coverage` `0.50`, `alpha` `0.05`, `evidence_scope="demo"`.
- One request per scheduled case, one attempt, in frozen order; no retry,
  replacement, threshold adjustment or selection using model outputs.
- Calibration is a descriptive cohort and is **never** used to fit or tune
  the threshold; it is collected and reported separately from verification,
  and the two cohorts are never pooled.
- The verification cohort keeps the ordinary scheduled-denominator and
  Clopper-Pearson semantics: every scheduled case stays in `n`; abstentions,
  denials, escalations and failures are not removed.
- Each cohort reports every failure category, selected-probability
  reliability bins, descriptive ECE and multiclass Brier score, with `null`
  for empty bins and unmeasured totals, never NaN or zero by assumption.
- Completeness and timeliness are separate. An incomplete audit or a
  collection-budget violation makes the overall audit receipt ERROR, with
  every scheduled case accounted for. An incomplete verification inventory
  cannot produce an ordinary verification bundle. A complete, valid
  verification inventory may produce its ordinary bundle and retains its
  independently computed verdict even if the wider audit is incomplete or
  late. Never shrink or reseal the schedule, fabricate missing captures, or
  replace the bundle verdict with the overall audit status. This eligibility
  depends on the 639 verification records, not on all 959 cohort captures.

The supplement further binds the 90-minute monotonic collection budget
frozen before the first request, a durable attempt-start/terminal-capture
journal for every call, separate calibration sidecar artifacts with an
offline checker, and the exact bin boundaries and metric formulas. Those
details are normative as written there and are not restated here.

## Rationale

The available ARCI planner models two independent binomial arms; it cannot
size an accepted-action error rate with a random accepted denominator plus a
coverage bound, so it is not used and is not misused as if it could. A
fixed public benchmark is not a sample from any deployment population: the
source audit found train/test overlaps and a duplicate, which the procedure
removes, but model-training exposure and semantic near-duplicates remain
unknown. The honest claim is therefore descriptive: what this provider did
on these 959 fixed cases under this frozen policy, reported through the same
unchanged assessment, with a correctly powered study deferred.

## Consequences

- Results, when they exist, are labelled `demo` scope and may not be quoted
  as calibration, accuracy or safety guarantees for user workloads.
- No label-truth claim: Banking77 labels are taken as given. No
  training-exclusion claim is made for the vendor model.
- Banking77 is CC-BY-4.0 and receives separate attribution; Actseal code
  remains Apache-2.0. Benchmark data is not redistributed as product code.
- The audit changes no public API, schema, threshold rule or statistical
  semantics; the ordinary complete verification bundle must replay unchanged.

## Evidence and status

- The protocol above is approved planning (Decision 3A; the supplement
  received planning-only ACCEPT at the hash recorded in plan/v1/STATE.md).
- Offline preparation accepted (7 October 2026): the benchmark
  implementation, journal validator and tests received offline ACCEPT at
  `d3edbab`, and preregistration candidate 3 (seal `c7bbc525…a2c`) is
  approved for the fixed 959-case protocol; candidates 1 and 2 are preserved
  byte-for-byte as history.
- Live collection not performed: the one dispatched live attempt was stopped
  by a harness permission denial on its `.env` existence preflight, before
  any key was read or any `--execute` call was made. No retry or alternate
  credential route is authorized after that denial. No journal, model
  result, request count, token usage or spend exists to report, and none is
  invented; the operational details are in the Task 06 receipts, not here.
- Related: [ADR 0003](0003-risk-coverage-statistical-contract.md),
  [ADR 0017](0017-experimental-decision-provider.md),
  [statistical contract](../statistical-contract.md).
