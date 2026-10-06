# Actseal shared project state

Updated: 2026-10-06. Sole writer: Codex (planner/orchestrator/reviewer).

## Current objective and authorization

Ship a publishable focused OSS v0.1.0 in two days. The human selected Decision
Contract and the focused v1 scope, delegated naming, and explicitly requested
implementation on 2026-10-06. Product name: Actseal. No further "go" is needed.
Public launch posts remain drafts. Claude Fable 5.1/high writes all product code.

## Current state

- Planning artifacts: being materialized and reviewed.
- Product implementation: T00 dispatched in isolated task/t00 worktree.
- Executor: Claude Code 2.1.281; login independently confirmed, claude.ai Max subscription.
- Existing .env: contains JEV_API_KEY; value is not read or printed. Ignored.
- Preflight: source statistics suite passed in a separate verification lane;
  native pinned Laya CPU/cached-offline smoke passed. See VERIFICATION.md for scope.

## Task ledger

| Task | Owner | State | Accepted commit |
|---|---|---|---|
| Planning package | Codex | IN_PROGRESS | none |
| T00 foundation | Claude A | RUNNING | none |
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

No authentication blocker remains. Repository initialized; T00 dispatched from
`.worktrees/t00` at documentation base 38900e1. Finish remaining task specs/CI and
independently review T00 when its REPORT arrives. Raw local dispatch receipts are
ignored under plan/dispatch; publish only reviewed, credential-free REPORTs.

## Budget and scope

Measured preflight API spend: $0. No Jev calls. No mandatory hosting. Subscription
billing uses the authenticated Max subscription; never silently switch to API billing. Escalate projected
incremental spend >$100 or if delivery requires using 8 October as more than buffer.
Optional Jev/Marketplace Action are excluded from the release critical path.
