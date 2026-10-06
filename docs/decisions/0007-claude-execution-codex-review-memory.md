# ADR 0007: Claude writes product code; Codex owns acceptance and shared state

- Status: accepted.
- Date: 2026-10-06.

## Decision

Claude Code is the product-code executor at the user-requested Fable 5.1 / high setting. Codex plans, specifies frozen contracts, delegates, reviews, independently re-runs checks, and gates integration. Codex may write planning documents and trivial scaffold/CI glue; it must not substitute itself as the product-code author when executor access is unavailable.

Send each task spec verbatim with only its necessary contract, plan, and research context. Use isolated branches/worktrees and frozen path ownership. Task reports follow the user's REPORT format; Codex reviews follow REVIEW with ACCEPT, REVISE, or REJECT. A report of green tests is supplied evidence until Codex independently executes the required commands on the exact candidate revision. Integration requires ACCEPT and green required CI; self-review does not substitute for that gate.

Use newly authored repository-local memory:

1. `plan/STATE.md`: Codex is the single writer of current objective, accepted decisions, task status, blockers, and next dispatch.
2. `plan/tasks/`: immutable task specifications and their dependency/ownership contracts.
3. Task-specific REPORT files: the owning executor may append its own report only; preserve prior attempts.
4. Task-specific REVIEW records and this ADR directory: Codex owns acceptance decisions and rationale.

State and review records identify the relevant base/candidate commit, interface revision, commands, observed results, deviations, and evidence locations. Unaccepted reports do not update a task to accepted. A new agent resumes from these records and verifies the checkout identity rather than treating historical text as authority.

The private shared-brain repository informed coordination principles only. Its implementation is not copied or installed: it has no verified public reuse license, has existing local changes, assumes different agent roles, and serializes mutable work differently. The sprint's memory format is a small new implementation of the user's requested task/report/review workflow.

## Operational state

The user has authorized implementation; there is no pending planning-permission question. Executor authentication failure is an operational blocker, not a reason to silently replace the requested executor/model or to request approval already given. Verify the requested model/settings through the available Claude mechanism before dispatch and report any unresolved mismatch. [DECISIONS](../../plan/DECISIONS.md) records user choices; [VERIFICATION](../../plan/VERIFICATION.md) separates actual preflight evidence from future product checks.

## Controlled-dispatch memory clarification — 6 October 2026

T50's raw receipt revealed automatic Claude notes written outside its owned
worktree paths. They are private executor notes, not shared acceptance authority
or release content. Preserve existing user-local notes; do not copy them into the
repository or rewrite them as task work. From T50's corrective dispatch onward,
set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` for that process only and instruct the
executor to write only its owned REPORT. Global Claude settings stay unchanged.

The [official environment reference](https://code.claude.com/docs/en/env-vars)
and [memory documentation](https://code.claude.com/docs/en/memory), checked on
6 October 2026, document that this setting disables automatic memory creation
and loading. The explicit Git-backed STATE/contracts/reports/reviews remain the
shared long-term memory. This setting does not bypass or relax permissions.
