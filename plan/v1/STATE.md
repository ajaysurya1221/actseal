# Actseal v1.0.0 shared execution state

Codex is the sole writer of this state and REVIEW records. Executors write their own REPORTs.

## Approved scope and authority

- Approved message: `bb3538db868f929c1f779dcbcd105936f521acba51fbfe7c08988fedcd0fdcaa`; received `2026-10-06T16:04:49.582Z`.
- Baseline commit: `332e1633f46975331f25f9af461f1220b6f36e8b`.
- Decisions: 1A, 2A, 3A adopted through approval of the recommended plan; see DECISIONS.md for exact provenance.
- Product code, product docs, tests and visual assets: Claude Code CLI, Fable 5.1, effort high, orchestrated by Codex under the latest explicit human authorization (V1-005).
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
| 01 | Codex | ACCEPT after 01R: independent 2302 passed incl. native; PR #10 merged at aaaf6c9 |
| 02 | Claude A | REVISE at22220b5: schema/docs corrections plus dev-only JSON Schema validation; session55bc88af-619e-4aff-97ac-4d7c42d31418 |
| 03–08 | Claude B/C/D | Waiting for frozen Task 02 contracts and specified dependencies |
| 09 | Codex | Prerequisites ACCEPT and merged via PR #9 at e4bf59a; REVISE at78c4afd: publication identity, receipts, supplied artifacts and asset gate; sessionb3ff94c7-3730-4f74-8c97-51ca08412f31 |
| 10 | Claude V | Local ACCEPT at 030ef840 after deterministic platform-test repair; PR13 new hosted CI running; session 6d75b60a-06d9-4a39-a69b-fbe105277f4a |
| 11–18 | Claude V | Waiting for their specified dependencies |
| 19–22 | Claude A/D and Codex | Waiting for integration/release gates |

## Accepted commits and reports

Task 00 ACCEPT at b2332bff1dfb92bc63408e98ef1e699b6c6329d8. The original complete baseline produced 2300 passes and two shared-process failures; that historical attempt is retained. Task 01R at d4bb8475ab5f6d9756bcfde1c2942a6dbb14d9c9 repaired the isolation checks and received independent ACCEPT: all 2302 tests, including native inference and packaging, passed in 57.79 seconds. PR #10 passed all eight push/PR matrix jobs and merged at aaaf6c97a551b1ec8a9166e652ed2dc0779f7af3. Historical v0.1 reports remain unchanged.

## Next action

Monitor continuations 02R2/09R2 and PR13 hosted CI at 030ef840. Visual repair 10CI is terminal and locally ACCEPT. Earlier processes 39528/82253/14887 are terminal, not live. Do not restart the current processes while running. Original Task02/09 interrupted drafts are retained locally. Direct Fable reimplementations now have REPORTs and commits22220b5/78c4afd, both requiring the recorded repairs. Task10/10R required repairs; Task10R2 received local ACCEPT. Hosted Linux failed only a macOS-specific test expectation; PR13 cannot merge before the repair and new CI pass. All three resumed sessions expose no Agent/Task tools and use Fable5.1/high. Independently review completed diffs, run checks and obtain exact-head hosted CI before merge. After02 ACCEPT launch03/04. After10 hosted acceptance, start figure work; actual hero/social rendering awaits approved pinned font/tool downloads.

## Latest integration receipt

PR12 reviewed head95d2efd8bebb6e49a6c2f9500e96379cfbebed3f passed all eight push/PR matrix checks (runs37503534894 and37503587655), and merged atd2570718411e8186c4bcd87c67196d0f81e52f57. Main contains accepted baseline repair and reviewed execution receipts. This next checkpoint is on codex/v1-checkpoint-03; it changes no product code.

## Live execution handles — revalidate, never assume terminal

| Task | Claude session | Tool exec handle | Worktree |
| --- | --- | --- | --- |
| 02 | 55bc88af-619e-4aff-97ac-4d7c42d31418 | 57407 | /Users/ajay/.codex/worktrees/actseal-v1-core/not-yet-named |
| 09 | b3ff94c7-3730-4f74-8c97-51ca08412f31 | 25815 | /Users/ajay/.codex/worktrees/actseal-v1-release/not-yet-named |
| 10 (terminal) | 6d75b60a-06d9-4a39-a69b-fbe105277f4a | 58170 (exit 0) | /Users/ajay/.codex/worktrees/actseal-v1-visuals/not-yet-named |

Current continuations run claude-fable-5-1 with effort high, Agent/Task unavailable, and normal acceptEdits controls. Earlier02/09 drafts included other-model workers and were interrupted before completion; see V1-007. Local prompts/stream logs/status are under /tmp/actseal-v1-orchestration; do not commit raw session logs. Tool handles were confirmed live after dispatch. Observation timeouts are not terminal results. Task02/09 REPORTs remain REVISE. Task10R2 has local ACCEPT and corrected provenance receipts. Task10CI at 030ef840 repairs the Linux-only expectation; independent 204 visual tests and hooks pass. New hosted runs 37507765648/37507769585 remain the merge gate.

The pypi environment now permits v* tags plus existing main, requires reviewer ajaysurya1221 and permits solo-maintainer self-review. No release tag or package upload was attempted. JEV_API_KEY is not exported in the current Codex process; no secret file was inspected. Claude's configured curl deny rule blocked asset-fetch attempts; no permission rule was removed. Record any asset setup still needed in Task10's report.

An async, narrowly scoped approval request is pending for official pinned font/renderer downloads because Claude settings explicitly deny curl. No alternate download mechanism or settings change has been used. Other work continues.
