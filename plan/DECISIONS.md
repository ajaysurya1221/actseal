# Actseal decisions

Date: **2026-10-06**, Asia/Kolkata. Phase: implementation authorized.

## User decisions already answered

| Decision | Recorded answer | Consequence |
|---|---|---|
| Product direction (`product_direction`) | `Decision Contract (Recommended)` | Build the focused decision-contract product; do not build the process-wrapper proxy. |
| Sprint scope (`scope_contract`) | `Focused two-day v1 (Recommended)` | Keep the narrow categorical core, fixture demo, and optional provider paths; do not expand into general enforcement or a hosted platform. |
| Product naming and engineering responsibility | User delegated naming and responsibility; parent selected **Actseal**. | Use Actseal consistently; the observed name availability is not a reservation. |
| Implementation | Latest user request: **PLEASE IMPLEMENT THIS PLAN**. | Phase 2 is authorized. Do not wait for another planning approval or a second literal “go”. |

The choices above are reported from the parent orchestrator's captured user responses. Their exact selected option strings are preserved; this document does not infer an answer from silence.

## Pending decisions

**None.** Routine implementation choices are recorded in [the ADRs](../docs/decisions/) and [CONTRACTS](CONTRACTS.md). New escalation is required only if a material constraint changes: incompatible license, load-bearing unverified fact, proprietary core requirement, projected spend above $100, or inability to finish inside the approved sprint/buffer.

## Operational blockers are separate

Claude authentication was repaired by the user and independently rechecked as `loggedIn: true`, `authMethod: claude.ai`, `subscriptionType: max`. T00 dispatch has begun. Do not silently substitute Codex-authored product code or a different model. Current execution status belongs in [STATE](STATE.md); this file records the approved decisions.

No repository/package name has been reserved by these decisions. Public repository creation, CI status, release tag, and publication remain execution steps whose results must be recorded when actually performed.
