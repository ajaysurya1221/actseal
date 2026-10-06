# ADR 0013: Prespecify the authored demonstration before creating fixtures

- Status: accepted before T50 implementation.
- Date: 2026-10-06.

## Decision

The two support-triage runs use the same policy and limits, evaluated against
different authored outcomes. They are not a population benchmark or paired model
comparison. Both use the ordered labels billing, technical, sales; all allowed;
threshold0.90; max_risk0.05; min_coverage0.50; alpha0.05; evidence_scope=demo.

Each verification dataset has exactly128 scheduled cases, indexed0..127. Gold
labels cycle through the ordered labels at index modulo3. The fixed fixture
selects the gold label for every case. The deliberately bad fixture selects the
next cyclic label for indices0..31 and the gold label for indices32..127. Every
selected label has probability0.95; the next cyclic label has0.03 and the remaining
label0.02. This is an authored probability distribution, not a calibration claim.
Provider confidence metadata may be omitted; it never controls the policy.

Give each run12 calibration cases with the same cyclic label rule. All four
calibration/verification datasets have distinct IDs and exact state texts across
runs/splits. Use explicit synthetic support-ticket templates and unique identifiers;
semantic independence is neither established nor claimed. Bad/fixed contracts
may differ in name/population description but must retain identical policy/limits.
Freeze the generator's deterministic rules and seed (no randomness is necessary)
in the example README. Commit both packaged/example resource copies byte-identically.

## Expected behavior, not execution evidence

By design all128 decisions should ACT. Fixed has zero wrong actions; bad has32.
At alpha/4, the fixed upper risk bound is approximately0.03365521 and lower
coverage approximately0.96634479. The bad lower risk bound is approximately0.16876047.
These planning calculations show the intended PASS/BLOCK inequalities have a
margin; they are not a product-run receipt. T50 must compute and report the real
results through accepted locks, capture normalization, policy, assessment, bundle
writing and fresh replay. Do not hard-code verdicts or emitted metrics.

The inputs and limits are prescribed before fixture implementation. Do not adjust
a threshold after reading a real verification set. Public docs must describe the
same policy evaluated against different authored fixture outcomes, not claim a
trained model was repaired or certified. Insufficient evidence remains covered by
assessment/CLI tests; it is not an additional demonstration run.
