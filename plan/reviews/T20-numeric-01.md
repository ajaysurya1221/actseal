# REVIEW T20-NUMERIC — independent numerical milestone

Verdict: **ACCEPT for the numerical milestone only. T20 remains PARTIAL.**

Reviewed candidate: 7df76007e96ed721fedba21ca92cee13dfdf37bf.
Product commit: ad67ac6. Date: 2026-10-06.
Draft PR: https://github.com/ajaysurya1221/actseal/pull/2.

## Findings ordered by severity

No material numerical or test-oracle finding. The approved ARCI integer-tail
comparison, reflection and fixed bisection arithmetic are preserved, with explicit
attribution and modification notices. Added type/finiteness checks do not widen
the numerical domain. Omitting unused confidence/Wilson/Newcombe wrappers fits
minimal reuse. No new dependency or shared-interface edit.

Fraction tests compute independent direct binomial sums. Decimal closed forms,
hand-derived cases and pinned upstream golden vectors provide separate references.
Sharing the specified bisection schedule checks that schedule's semantics; it is
not the only oracle. Finite-grid coverage tests are evidence, not a universal proof.
Documentation distinguishes exact tail comparisons from approximate returned roots.

## Independent verification

Root read the product/report and reviewed the oracle design, with a separate
read-only audit of all numerical test source. Root ran the exact commands:

```bash
uv run --frozen ruff check src/actseal/stats.py tests/unit/test_stats.py
uv run --frozen ruff format --check src/actseal/stats.py tests/unit/test_stats.py
uv run --frozen mypy --strict src/actseal/stats.py tests/unit/test_stats.py
uv run --frozen pytest tests/unit/test_stats.py
```

All exit zero: **159 tests passed in 24.92 seconds** on macOS/Python3.12.13.
All four Linux/macOS Python3.12/3.13 jobs passed at the exact candidate:

- https://github.com/ajaysurya1221/actseal/actions/runs/37436612961
- https://github.com/ajaysurya1221/actseal/actions/runs/37436745808

## Required changes before full T20 acceptance

Integrate accepted T10 and T30, implement assessment.py and its tests, enforce
complete semantic reconstruction, canonical faults, all denominators and ADR0009,
then run full T20 checks and repeat review/CI. Keep PR2 unmerged until then.
No skipped tests or replacement production authorities may satisfy dependencies.

## Follow-ups filed

STATE records the verified numeric milestone and predecessor wait. Claude session
14d9398c-146f-40cf-827d-a3c6a79632f1 completed using claude-fable-5-1/high.
Cumulative estimated subscription meter: $5.43887825, not a billed API charge.
Incremental paid API spend remains $0.
