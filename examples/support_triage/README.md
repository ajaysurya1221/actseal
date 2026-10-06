# Support-triage demonstration (authored, demo-only)

This directory holds the inputs behind `actseal demo`. They are byte-identical
to the copies packaged inside the wheel under `actseal/demo_data/`, and a test
(`tests/unit/test_runner.py`) enforces that parity and regenerates them from
`generate_demo_data.py` to prove the committed bytes follow the documented rules.

Everything here is **authored synthetic data** with `evidence_scope = "demo"`.
No model produced any label or probability. The demo shows the same frozen
policy evaluated against two different authored fixture outcomes. It is not a
population benchmark, not a trained or repaired model, not a paired model
comparison and not deployment certification ([ADR 0013](../../docs/decisions/0013-prespecified-synthetic-demo.md)).

## Files

| File | Role |
|---|---|
| `bad.toml`, `fixed.toml` | Two prespecified contracts with identical policy and limits; only name and population text differ. |
| `bad_calibration.jsonl`, `fixed_calibration.jsonl` | 12 labelled calibration cases per run (never sent to a provider in v1; the lock binds them). |
| `bad_verification.jsonl`, `fixed_verification.jsonl` | 128 labelled verification cases per run, indices 0..127. |
| `bad_responses.jsonl`, `fixed_responses.jsonl` | Recorded fixture responses, one per verification case. |
| `generate_demo_data.py` | The deterministic generator that produced all eight files. |

## Prespecified rules (frozen before the files were created)

- Ordered labels `billing`, `technical`, `sales`; all allowed; threshold 0.90;
  `max_risk` 0.05; `min_coverage` 0.50; `alpha` 0.05.
- The gold label of index `i` is label `i mod 3` in every dataset.
- The **fixed** fixture selects the gold label for every case.
- The **bad** fixture selects the next cyclic label for indices 0..31 and the
  gold label for indices 32..127: exactly 32 authored wrong accepted answers.
- Every selected label has probability 0.95, the label after it in cyclic order
  0.03 and the remaining label 0.02. This is an authored distribution, not a
  calibration claim. No provider confidence is recorded.
- Every case id and state text is unique across all four datasets. Each state
  embeds its own ticket identifier (for example `Ticket BAD-V-017: ...`) and
  cycles through four fixed templates per label. Semantic independence is
  neither established nor claimed.
- The generator uses no randomness, so there is no seed; rerunning it
  reproduces the committed bytes.

## What the demo computes

`actseal demo --out NEW_DIRECTORY` copies these inputs into `NEW_DIRECTORY/inputs`,
then for each run creates a lock bound to the installed implementation
fingerprint and the fixture file's identity (`NEW_DIRECTORY/<run>/lock.json`),
collects all 128 cases once in lock order, runs the six fault scenarios,
assesses, writes `NEW_DIRECTORY/<run>/evidence` and replays it with the lock's
digest. Every count, interval and verdict in its output is computed by that
pipeline at run time; nothing below is read from a file.

ADR 0013 predicts BLOCK for `bad` (lower risk bound about 0.169 > 0.05) and PASS
for `fixed` (upper risk bound about 0.0337 <= 0.05, lower coverage bound about
0.966 >= 0.50). The demo exits 0 only if the pipeline actually produces those
two statuses and both replays match.

## Regenerating

```bash
python examples/support_triage/generate_demo_data.py /tmp/regenerated
```

The script refuses to overwrite existing files. Compare the output with this
directory; any difference means the rules or the script changed and a review is
required before the committed fixtures move.
