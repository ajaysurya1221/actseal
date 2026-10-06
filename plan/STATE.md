# Actseal shared project state

Updated: 2026-10-06. Sole writer: Codex (planner/orchestrator/reviewer).

## Current objective and authorization

Ship a publishable focused OSS v0.1.0 in two days. The human selected Decision
Contract and the focused v1 scope, delegated naming, and explicitly requested
implementation on 2026-10-06. Product name: Actseal. No further "go" is needed.
Public launch posts remain drafts. Claude Fable 5.1/high writes all product code.

## Current state

- Planning artifacts: complete; 119 material claims and all 18 candidate dispositions recorded.
- Product implementation: T00, T10, T20, T30 and T40 accepted and merged; T50 is next.
- Executor: Claude Code 2.1.281; login independently confirmed, claude.ai Max subscription.
- Existing .env: contains JEV_API_KEY; value is not read or printed. Ignored.
- Preflight: source statistics suite passed in a separate verification lane;
  native pinned Laya CPU/cached-offline smoke passed. See VERIFICATION.md for scope.

## Task ledger

| Task | Owner | State | Accepted commit |
|---|---|---|---|
| Planning package | Codex | COMPLETE | ee99eee plus documented amendments |
| T00 foundation | Claude A | ACCEPT / MERGED | ebe11ff (merge 86dbca0) |
| T10 contract/policy | Claude A | ACCEPT / MERGED | 9bdac25 (merge 28be58d) |
| T20 statistics | Claude B | ACCEPT / MERGED | b1eace7 (merge 6d6d7c4) |
| T30 providers/faults | Claude C | ACCEPT / MERGED | 8b1efd6 (merge 87d2cd1) |
| T40 evidence/replay | Claude B | ACCEPT / MERGED | 98297d5 (merge 7a2939e) |
| T50 CLI/demo | Claude A | REVISE | candidate046e4f6 |
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

T10 accepted at 9bdac251a76a22a30f8d3d5ab8b773e0200945a1 and merged through PR3
as 28be58d. REVIEW T10-02 records 755 root-run tests, lint/format/mypy, independent
regression probes and all eight hosted push/PR jobs green. All three original
findings fixed; ADR0010 helpers are frozen. Claude cumulative subscription meter
$12.1806425 is an estimate, not API billing.

T30-02 fixes all four milestone findings. Root independently passed 243 unit
tests in 4.12s, lint/format/mypy and 5 real cached-native Mac tests in 4.58s.
Separate review confirms stalled-send timeout and malformed-IPC cleanup. Original
REPORT preserved; corrective report acknowledges its earlier denial reroutes and
does not repeat them. Cumulative subscription meter $17.69608775.
Corrected provider milestone now ACCEPT at 17ed0875541ecfa6402991dc90e278beb2f4cc01
in REVIEW T30-02. Both four-job CI matrices pass; native Linux run37439327535
passes all 5 tests in 10.75s with Python3.12.3 and Torch2.14.1+cpu. Full T30 is now
ACCEPT at 8b1efd6314b5b65ecb51f292a5bc767ff8b93ed7 and merged as 87d2cd1 via PR4.
Root passed 279 full-task tests in 4.25s, lint/format/mypy; all eight final hosted
jobs pass in runs37440036303/37440043375. The native-tested provider code is
byte-unchanged; new pure fault code independently reviewed. REVIEW T30-03 files
one nonblocking T60 test-quality follow-up. Final Claude meter $20.95634925.

T20 full task ACCEPT at b1eace7009bc5bc966e4f600d756ff1802fd6e8e, merged6d6d7c4
through PR2. Root passed259 tests in25.41s, lint/format/mypy. Independent integrity
and statistical probes found no material defects. Both four-job hosted matrices
pass in runs37441967584/37441973261. REVIEW T20-02 records exact evidence.
Numerical source/tests remain unchanged from the accepted port. Final cumulative
session meter $11.50984675 is estimated subscription usage, not API billing.
T40 ACCEPT at 98297d5f79cfa62e348d722d8ae91ec59252eebd, merged7a2939e via PR5.
REVIEW T40-02 records all three corrections, root178 tests in1.72s, lint/format/
mypy, independent filesystem and semantic probes, and all eight hosted jobs green
in runs37447161362/37447188177. Real exclusive publication executes on both OSes.
CLI packaging/demo remain unrun T50 gates. Both REPORTs are preserved. Claude
session a02c2248-c36b-496c-b941-e4b806cc5247 completed; final cumulative subscription
meter $18.21350825, not paid API billing. T50 dispatched from integrated base b7f725e in .worktrees/t50.
Claude session61e69351-ebca-4990-bdc8-89b7915a3b79, modelclaude-fable-5-1/high,
acceptEdits; current Max authentication rechecked. Root owns console metadata and
CI guard removal, both completed on the candidate. No new dependencies approved.
REVIEW T50-01 requires sanitized usage, complete failure summaries, fixture
--offline compatibility and a genuinely healthy Laya pre-failure test case. Root
passed114 unit tests/8 clean-wheel tests plus exact lint/format/types/build/help.
Initial Claude meter $14.9410545 is subscription usage only. Future dispatches
disable automatic memory per ADR0007; only the Git-backed shared state is authoritative.

T00 Claude session25979d71-e2c8-4a20-932b-a18022ec31c7 completed. Model was
claude-fable-5-1/high. Cumulative meter $15.7246075 estimated subscription usage,
not a billed API charge. Raw receipts remain ignored under plan/dispatch.

## Budget and scope

Measured preflight API spend: $0. No Jev calls. No mandatory hosting. Subscription
billing uses the authenticated Max subscription; never silently switch to API billing. Escalate projected
incremental spend >$100 or if delivery requires using 8 October as more than buffer.
Optional Jev/Marketplace Action are excluded from the release critical path.
