# Actseal v1.0.0 shared execution state

Codex is the sole writer of this state and REVIEW records. Executors write their own REPORTs.

## Approved scope and authority

- Approved message: `bb3538db868f929c1f779dcbcd105936f521acba51fbfe7c08988fedcd0fdcaa`; received `2026-10-06T16:04:49.582Z`.
- Baseline commit: `332e1633f46975331f25f9af461f1220b6f36e8b`.
- Decisions: 1A, 2A, 3A adopted through approval of the recommended plan; see DECISIONS.md for exact provenance.
- Product code, product docs, tests and visual assets: user-run Claude Code, Fable 5.1, effort high. No automated Claude dispatch.
- Codex: planning receipts, review, checks, CI/packaging glue and release gates.
- Main must remain releasable. No task merges without ACCEPT and green CI.

## Immutable time gates (Asia/Kolkata)

| Gate | Deadline |
| --- | --- |
| Jev integrated and green, otherwise cut to 1.1 | 2026-10-07 14:00 |
| Static P1 visuals/social preview/recording procedure accepted | 2026-10-07 15:59 |
| Remaining optional work integrated and green, otherwise cut | 2026-10-07 17:59 |
| v1.0.0 publication target | 2026-10-07 23:59 |

## Task status

| Task | Owner | Status |
| --- | --- | --- |
| 00 | Codex | ACCEPT at b2332bff1dfb92bc63408e98ef1e699b6c6329d8 |
| 01 | Codex | REVISE: 2300 passed, 2 process-contamination failures; see Task 01R |
| 02 | Claude A | Held for 01R and independent full-baseline ACCEPT |
| 03–08 | Claude B/C/D | Waiting for frozen Task 02 contracts and specified dependencies |
| 09 | Codex | Asset dependency prerequisite in codex/v1-09-assets; review/CI pending |
| 10 | Claude V | Ready after assets dependency glue; independent of baseline repair |
| 11–18 | Claude V | Waiting for their specified dependencies |
| 19–22 | Claude A/D and Codex | Waiting for integration/release gates |

## Accepted commits and reports

Task 00 ACCEPT at b2332bff1dfb92bc63408e98ef1e699b6c6329d8. All 2302 baseline tests were exercised: 2300 passed and two shared-process isolation checks failed. Native inference passed; full baseline is not green. Historical v0.1 reports remain unchanged.

## Next action

Prepare manual Claude Task 01R for the baseline repair and Task 10 for visuals after the optional authoring dependency is reviewed. Do not dispatch Task 02 until the baseline is ACCEPT. Do not launch Claude or substitute another product implementer.
