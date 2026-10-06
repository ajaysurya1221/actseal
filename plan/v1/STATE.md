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
| 00 | Codex | Approval receipt persisted; commit and independent comparison next |
| 01 | Codex | NEXT: complete the full baseline before product changes |
| 02 | Claude A | Waiting for 01; first product task |
| 03–08 | Claude B/C/D | Waiting for frozen Task 02 contracts and specified dependencies |
| 09 | Codex | Ready after receipt commit; CI/packaging only |
| 10 | Claude V | Ready after receipt commit; may run in parallel with baseline/core |
| 11–18 | Claude V | Waiting for their specified dependencies |
| 19–22 | Claude A/D and Codex | Waiting for integration/release gates |

## Accepted commits and reports

No v1 implementation commits accepted yet. Historical v0.1 reports remain unchanged. The starting core/packaging baseline was checked during planning; six integration tests remain to run.

## Next action

Commit the exact approval receipt, run Task 01, and provide Task 02 and Task 10 verbatim packets for the user's separate Claude sessions. Do not launch Claude or substitute another product implementer.
