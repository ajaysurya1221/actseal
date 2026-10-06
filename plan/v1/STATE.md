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
| 09 | Codex | Prerequisites ACCEPT and merged via PR #9 at e4bf59a; publication workflow hardening remains pending |
| 10 | Claude V | Ready for manual Claude in /Users/ajay/.codex/worktrees/actseal-v1-visuals/not-yet-named; dispatch/10.md |
| 11–18 | Claude V | Waiting for their specified dependencies |
| 19–22 | Claude A/D and Codex | Waiting for integration/release gates |

## Accepted commits and reports

Task 00 ACCEPT at b2332bff1dfb92bc63408e98ef1e699b6c6329d8. All 2302 baseline tests were exercised: 2300 passed and two shared-process isolation checks failed. Native inference passed; full baseline is not green. Historical v0.1 reports remain unchanged.

## Next action

Run manual Claude Task 01R in /Users/ajay/.codex/worktrees/actseal-v1-baseline/not-yet-named and Task 10 in the visuals worktree concurrently. Both start from merged main e4bf59a. Return each committed branch and REPORT for independent review. Do not dispatch Task 02 until the baseline is ACCEPT. Do not launch Claude or substitute another product implementer.

## Latest integration receipt

PR #9 head 8d368593b9ff8a8fde786e10088e963de6c03eea received independent ACCEPT and all eight push/PR matrix jobs passed (runs 37495186182 and 37495194314). Merge commit e4bf59ae98f6eaee22556ec14d32969f53c52d1c. This state-only checkpoint is on codex/v1-execution-state pending its next reviewed integration; it does not change product code.
