# Task06 collection and audit clarification — preparation only

This is a bounded task specification supplement, not an approved preregistration or permission to begin live calls. Read the exact immutable Task06 and approved PLAN section C first. Task05 must be ACCEPTed. Codex must review and commit the complete concrete preregistration before any Jev request. Claude Fable 5.1, effort high, owns all implementation/tests/docs in this task. No live requests have been made during this preparation.

## Bind the study before inference

The preregistration binds dataset revision and source bytes, attribution, exact ordered case inventories and input hashes, the 16 ordered criteria/instructions, provider identity, policy, metric definitions, collection ordering/deadline, package producer fingerprint and SHA-256 of benchmark scripts. The package fingerprint alone does not cover bench/jev_audit. --execute verifies the reviewed preregistration and rejects changed scripts, inputs or identities. State the human-readable protocol and machine fields together; strict parsing rejects duplicate keys/nonfinite numbers.

Keep the approved 320 calibration / 639 verification counts and selection rules, threshold0.80, risk0.05, coverage0.50, alpha0.05, evidence_scope=demo. Do not use observed outcomes to revise anything. No power, IID-population calibration or model-training-exclusion claim. Calibration is a descriptive cohort, never a threshold-fitting step in this audit.

## Separate cohorts; journal every attempted call

Collect calibration in its frozen order, then verification in its frozen order. Use one resident provider and sequential requests, with the existing fixed REQUEST_TIMEOUT_S per request. Freeze a monotonic 90-minute collection budget before starting; record its UTC start/deadline. Check the budget before every request. If a request starts before the cutoff, retain its terminal capture even if it returns after the cutoff; start no further request. Record budget_exceeded and make the overall audit receipt ERROR for a budget violation, even when the final959th capture is present. A valid complete verification bundle retains its independently computed verdict. Keep completeness and timeliness separate rather than claiming a universal hard wall-clock deadline.

Write a durable attempt-start entry before calling decide and a terminal capture entry immediately afterward. Bind every entry to cohort, case identity/request hash, run/preregistration hash and sequence. Preserve original raw bodies, including malformed response bodies that were actually captured. Do not record credentials or headers. An interruption partitions all959 scheduled cases into captured, started-without-capture, and unattempted. Never fabricate a failure capture for a missing response, retry an uncertain attempt, replace a case or reduce the scheduled inventory. --execute refuses an already-started run; --check-receipts is entirely offline. Tests simulate interruption in each journal phase.

The existing collect/verify_run path buffers records and only collects verification cases. Do not change that public API for this benchmark. Use an audit-owned journal wrapper/orchestrator with the unchanged DecisionModel/normalize/evaluate/assess interfaces. Ensure identity/exact-source/input validation precedes inference. No gold or case ID enters the HTTP inference body; gold remains evaluator metadata. Preserve the Task05 payload-isolation tests.

## Artifacts and incomplete evidence

Keep the320 calibration captures/decisions in a separate benchmark sidecar with an explicit benchmark schema version and offline checker. Publish the639 verification records through the ordinary complete evidence bundle only when its complete-inventory requirements are satisfied. Do not insert calibration decisions into the verification bundle or pool the cohorts.

The ordinary bundle writer rejects incomplete records even when a verdict is ERROR. Retain partial journals outside that seven-file bundle and issue a clearly identified incomplete/ERROR audit receipt. Report an available completed cohort separately without changing overall incomplete status. Never forge an ordinary bundle, reseal a reduced sample or fetch missing responses during checks. Recompute each captured outcome/decision and all summary metrics offline; a complete verification bundle must replay unchanged.

## Prespecified descriptive metrics

For each cohort separately, use every valid normalized ChoiceAnswer, including allowed below-threshold ABSTAIN and any valid disallowed DENY. Failure captures have no probability vector and contribute no invented probability. Report valid-answer count/denominator and every failure category. For a complete cohort, descriptive coverage is ACT/320 for calibration and ACT/639 for verification; accepted error is wrong ACT/all ACT, with null when ACT=0. For an incomplete cohort, clearly label available-answer metrics partial and leave full-cohort coverage/accepted error unavailable. Unattempted cases are not abstentions. The ordinary complete verification bundle keeps the approved scheduled-denominator and CP semantics unchanged.

- Reliability and descriptive ECE use selected-option probability and whether that selected option matches gold, never provider confidence or an assumed argmax.
- Use10 equal-width bins [0,0.1), ... [0.8,0.9), [0.9,1]. State exact floating-boundary comparisons and test endpoints. Report count, mean selected probability and selected-choice accuracy per bin.
- ECE is sum over nonempty bins of n_bin/n_valid times absolute(mean selected probability minus selected-choice accuracy).
- Multiclass Brier score is the mean over valid answers of sum over all16 options of (normalized_probability - one_hot_gold)^2. Do not divide the inner sum by16; document its [0,2] range.
- Empty-bin means/accuracy and metrics with n_valid=0 are null. Missing usage or unmeasured monetary/credit totals remain null/unknown, never zero by assumption. JSON never contains NaN/Infinity.

Before collection, tests must independently verify selection/counts/disjointness, metrics and endpoints, exact payload isolation, journal crash accounting, restart refusal, no network in receipt checking, and credential redaction. Codex reviews the preregistration commit and records its hash before authorizing the live phase. This is a review gate within Task06, not a reason to request a new product decision from the user.
