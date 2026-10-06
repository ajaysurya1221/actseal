# REVIEW 04 — quota-interrupted draft

Verdict: REVISE. Base `84079e9017bb47c215ba1d7dba05ae44af6c4320`; no final task commit or REPORT04. Claude session `36334c93-ddb9-413b-a094-2549b02efef3` stopped at its subscription limit, resetting 7 October 2026 01:50 IST.

## Required change

**P1 — Mutation harness can delete a caller-owned directory.** `tools/check_mutations.py:880` accepts an existing `--workdir`, then line909 recursively deletes it, including after baseline setup failure. Create a newly owned temporary child beneath the supplied parent and clean only that child. Add regression coverage retaining an existing parent and sentinel through failure. Do not run the current harness with `--workdir`.

Valid statistical calculations and frozen goldens are unchanged. The oversized integer-tail error is the only public numerical behavior change. Deterministic Fraction/Decimal properties are appropriate. The eight mutations match the approved specification; baseline setup failures, import failures, skips, unexpected exceptions and timeouts do not qualify as kills.

## Already observed independent checks

- Statistics and available properties: **221 passed in 36.07 seconds**.
- Default freshly allocated temporary-directory mutation run: baseline **39 designated nodes** passed; **8 killed, 0 survived, 0 invalid, 0 unexecuted**, exit0. Each intended call-phase failure was `builtins.AssertionError`; module origins, distinct fingerprints and unchanged tracked source hashes were checked.
- Owned Ruff lint, format and strict mypy passed. Full hooks, hosted CI and immutable final review were not run.

These checks completed before the reviewer learned that Claude's compound harness command had been automatically denied for lacking an approval surface. After that notice, only source reads and hashes were inspected. The observed run is retained honestly; it does not authorize further attempts. A scoped permission request is pending for the repaired harness.

```text
src/actseal/stats.py: 9bba80d70a19722766c18970b26338d89f1216237f9c80ece96d88dfb875ea5c
tests/properties/test_gate_properties.py: d2a8a423ee3873a6ab59b7a8212a8caaf4fad16c33bd1fbdec146a918de7f247
tests/properties/test_interval_properties.py: 444791a56f3a37a396e7b97263b0903530ca6d5b5b1f520d3996d2f38b507484
tests/properties/test_tail_boundary.py: 9523c155fd9f79a8f893d1423a8b3151e81344330c124879dcbce1d44262a006
tools/check_mutations.py: a23152b5968b660392a654740db25149348bab7d318b5ef8c235dd188aeffade
```

Follow-up: resume Fable/high after reset, fix cleanup ownership, complete authorized checks, write REPORT04 retaining denial/interruption history, and commit only owned files. Backup inventory SHA256 `27103195418d613f36856061e84e025b1734ea1a8d26d77862318d49928cb90d` is retained under `/tmp/actseal-v1-orchestration/04-quota-interrupted-draft/`.
