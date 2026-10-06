# Actseal shared project state

Updated: 2026-10-06. Sole writer: Codex (planner/orchestrator/reviewer).

## Current objective and authorization

Ship a publishable focused OSS v0.1.0 in two days. The human selected Decision
Contract and the focused v1 scope, delegated naming, and explicitly requested
implementation on 2026-10-06. Product name: Actseal. No further "go" is needed.
Public launch posts remain drafts. Claude Fable 5.1/high writes all product code.

## Current state

- Planning artifacts: complete; 119 material claims and all 18 candidate dispositions recorded.
- Product implementation: T00 accepted and merged as 86dbca0; parallel lanes active.
- Executor: Claude Code 2.1.281; login independently confirmed, claude.ai Max subscription.
- Existing .env: contains JEV_API_KEY; value is not read or printed. Ignored.
- Preflight: source statistics suite passed in a separate verification lane;
  native pinned Laya CPU/cached-offline smoke passed. See VERIFICATION.md for scope.

## Task ledger

| Task | Owner | State | Accepted commit |
|---|---|---|---|
| Planning package | Codex | COMPLETE | ee99eee plus documented amendments |
| T00 foundation | Claude A | ACCEPT / MERGED | ebe11ff (merge 86dbca0) |
| T10 contract/policy | Claude A | REVISE_T10_01 | none |
| T20 statistics | Claude B | NUMERICAL_VERIFIED_WAITING_FOR_T10_T30 | none |
| T30 providers/faults | Claude C | PROVIDER_MILESTONE_RUNNING | none |
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

No authentication blocker remains. T00 PR1 is merged:
https://github.com/ajaysurya1221/actseal/pull/1. REVIEW T00-05 ACCEPT binds
commit ebe11ff947b366fa700bf0e1ecf6747fcebe970f; all four hosted jobs passed in
runs37434438049/37434442393. Root independently passed 587 tests, Ruff, mypy,
build and the three pre-commit hooks. Shared records/serialization/errors are frozen.

The human approved the three hooks and standing routine execution on 2026-10-06.
No pending permission question remains. Original scope/license/budget escalations
and the release quality gates still apply; public launch messages remain drafts.

T10 initial self-report DONE; independent review T10-01 requires three fixes:
bounded reads, consistent lock wire-size limits and standalone cross-split ID
checks. Root passed all four commands (738 tests), then reproduced each defect.
ADR0010 freezes the approved shared I/O/digest helpers before downstream use.
Next: resume T10 for fixes and a new immutable report T10-02.md.

Running: isolated Claude T30 provider work. T20 numerical milestone is
verified: 159 tests independently pass; all four CI jobs green at 7df7600.
PR2 stays draft/unmerged until full assessment acceptance. See T20-numeric-01.
T20 Claude session completed at $5.43887825 estimated subscription usage.
All three report actual model claude-fable-5-1; effort high was supplied at dispatch.
Local process/session receipts are in ignored plan/dispatch/active-lanes.json.
ADR0009/CHANGE_LOG correct permanent-worker-loss statistical dependence before
these dispatches. All lanes receive the new contract hash. No extra feature scope.
T20/T30 remain PARTIAL until accepted predecessor integration and full checks.

T00 Claude session25979d71-e2c8-4a20-932b-a18022ec31c7 completed. Model was
claude-fable-5-1/high. Cumulative meter $15.7246075 estimated subscription usage,
not a billed API charge. Raw receipts remain ignored under plan/dispatch.

## Budget and scope

Measured preflight API spend: $0. No Jev calls. No mandatory hosting. Subscription
billing uses the authenticated Max subscription; never silently switch to API billing. Escalate projected
incremental spend >$100 or if delivery requires using 8 October as more than buffer.
Optional Jev/Marketplace Action are excluded from the release critical path.
