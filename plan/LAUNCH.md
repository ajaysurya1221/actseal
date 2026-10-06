# Actseal launch draft

**DRAFT — not posted.** Publish only after the release checklist is complete and
an explicit request to send the post. The final report carries the release receipts.

## Proposed post

Actseal turns a model-driven action policy into a contract you can replay.
Freeze the question, allowed actions, threshold, labelled cases and model identity;
check accepted-action errors and coverage; test six provider-failure scenarios;
retain evidence that can be recomputed offline.

Its authored support-triage demo runs the same policy against two sets of answers:
32 wrong accepted actions out of 128 yields **BLOCK**; zero wrong out of 128 yields
**PASS**. Both bundles replay to their original verdicts. Those are synthetic
fixtures, not a repaired model or a population benchmark. Valid but insufficient
evidence stays **INCONCLUSIVE**; invalid evidence is **ERROR**.

The Python core is Apache-2.0 and needs no model library, key or hosted service.
An optional pinned local Laya adapter also ran through the complete CLI. All 128
synthetic cases abstained at its frozen threshold; verification and replay both
preserved **BLOCK for low coverage**. No threshold tuning or retry created PASS.

Replay makes the evidence inspectable. It does not prove the labels, inference
execution or response authenticity—even with a trusted lock hash. Population
interpretation requires independent cases and one prespecified fixed-policy attempt.

Try the model-free demo with uv installed and a fresh output directory:

```bash
uvx --python 3.12 --from https://github.com/ajaysurya1221/actseal/releases/download/v0.1.0/actseal-0.1.0-py3-none-any.whl actseal demo --out ./actseal-demo
```

[Repository](https://github.com/ajaysurya1221/actseal) ·
[v0.1.0 release](https://github.com/ajaysurya1221/actseal/releases/tag/v0.1.0) ·
[Verification and limitations](FINAL_REPORT.md)

Feedback sought: one application decision where a frozen policy, complete failure
record and offline replay would make a deployment decision easier to review.
