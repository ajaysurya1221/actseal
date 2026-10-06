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

No authentication blocker remains. Repository initialized; T00 dispatched from
`.worktrees/t00` at documentation base 38900e1. Finish remaining task specs/CI and
independently review T00 when its REPORT arrives. Raw local dispatch receipts are
ignored under plan/dispatch; publish only reviewed, credential-free REPORTs.

Public repository created: https://github.com/ajaysurya1221/actseal. Initial docs
are published. No product release or green product CI is claimed. Claude's
permission layer denied creating the sensitive .pre-commit-config.yaml in its
non-interactive session; explicit approval for the three proposed local hooks is
pending with the user. Other product work continues.

T00 initial REPORT is PARTIAL. Codex independently repeated sync, Ruff lint/format,
strict mypy, both owned test files (485 passed) and build. Constructor probes still
accepted invalid normalized distributions, unsupported providers and zero-case
PASS, and numeric overflow escaped SchemaError. Linux CUDA/proprietary resolution,
generic JSON cap and sdist contents also require correction. No product has been
accepted or merged. Initial Claude meter: $9.3913315 estimated usage, not a billed
API charge; actual incremental paid API spend remains $0 on the Max subscription.

## Budget and scope

Measured preflight API spend: $0. No Jev calls. No mandatory hosting. Subscription
billing uses the authenticated Max subscription; never silently switch to API billing. Escalate projected
incremental spend >$100 or if delivery requires using 8 October as more than buffer.
Optional Jev/Marketplace Action are excluded from the release critical path.
