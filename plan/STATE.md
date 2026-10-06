# Actseal shared project state

Updated: 2026-10-06. Sole writer: Codex (planner/orchestrator/reviewer).

## Current objective and authorization

Ship a publishable focused OSS v0.1.0 in two days. The human selected Decision
Contract and the focused v1 scope, delegated naming, and explicitly requested
implementation on 2026-10-06. Product name: Actseal. No further "go" is needed.
Public launch posts remain drafts. Claude Fable 5.1/high writes all product code.

## Current state

- Planning artifacts: complete; 119 material claims and all 18 candidate dispositions recorded.
- Product implementation: T00 under revision in isolated task/t00 worktree; no product merged.
- Executor: Claude Code 2.1.281; login independently confirmed, claude.ai Max subscription.
- Existing .env: contains JEV_API_KEY; value is not read or printed. Ignored.
- Preflight: source statistics suite passed in a separate verification lane;
  native pinned Laya CPU/cached-offline smoke passed. See VERIFICATION.md for scope.

## Task ledger

| Task | Owner | State | Accepted commit |
|---|---|---|---|
| Planning package | Codex | COMPLETE | ee99eee plus documented amendments |
| T00 foundation | Claude A | REVISE | none |
| T10 contract/policy | Claude A | WAITING_FOR_T00 | none |
| T20 statistics | Claude B | WAITING_FOR_T00 | none |
| T30 providers/faults | Claude C | WAITING_FOR_T00 | none |
| T40 evidence/replay | Claude B | WAITING_FOR_ACCEPTED_INTERFACES | none |
| T50 CLI/demo | Claude A | WAITING_FOR_T10_T20_T30_T40 | none |
| T60 acceptance | Claude C | WAITING_FOR_T50 | none |
| T70 publication | Codex | WAITING_FOR_T60 | none |

## Resume pointers

Read PLAN.md, CONTRACTS.md, DECISIONS.md, then the exact task spec. Read the latest
REVIEW as well as the executor REPORT; only ACCEPT authorizes integration. Shared
types freeze after T00 ACCEPT. Recheck worktree/commit identity and auth before
dispatch; never assume a status inherited from memory is still current.

## Blockers and next action

No authentication blocker remains. Public repository:
https://github.com/ajaysurya1221/actseal. Draft foundation PR:
https://github.com/ajaysurya1221/actseal/pull/1. Candidate af116adbebbfc30ddcc4bc2fe209c91e665a0991
includes the Unicode correction a70f7c1 and synchronized documentation receipts.
Root independently passed all six T00 commands (587 tests, lint/format, mypy,
sync and build). Hosted Linux/macOS Python3.12/3.13 at run37433262328 passes all
implemented checks except Repository hooks: its config file is absent.

REVIEW T00-04 closes the Unicode constructor finding. All known T00 product
findings are fixed, including parser, domain validation, CPU-only Linux dependency
resolution and packaging. Claude revision04 has completed; no executor is running.
The sole immediate blocker is the pending hook approval. T10/T20/T30 still wait
for T00 ACCEPT and green CI. Shared types are not yet frozen by acceptance.

Claude's permission layer denied creating sensitive .pre-commit-config.yaml
because its non-interactive session has no approval surface. The one pending
human question requests approval for three local hooks: Ruff lint, Ruff format
check, and strict mypy. Do not retry or route around that write without approval.
Raw local dispatch receipts remain ignored under plan/dispatch.

Claude session25979d71-e2c8-4a20-932b-a18022ec31c7, actual model claude-fable-5-1,
effort high. Cumulative meter after revision04: $15.7246075 estimated subscription
usage, not a billed API charge. Incremental paid API spend remains $0 on Max.

## Budget and scope

Measured preflight API spend: $0. No Jev calls. No mandatory hosting. Subscription
billing uses the authenticated Max subscription; never silently switch to API billing. Escalate projected
incremental spend >$100 or if delivery requires using 8 October as more than buffer.
Optional Jev/Marketplace Action are excluded from the release critical path.
