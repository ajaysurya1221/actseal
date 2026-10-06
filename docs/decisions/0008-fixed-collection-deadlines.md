# ADR 0008: Bind v1 collection deadlines through implementation identity

- Status: accepted before T50 implementation.
- Date: 2026-10-06.

## Decision

Every v1 evidence-producing runner uses a 30.0-second request timeout and the
120-second local-model startup bound. There is no CLI, environment or runner-API
deadline override. These constants are covered by the installed-source hash in
PlanLock. A changed implementation requires a new lock and new evidence.

The earlier proposed --timeout-seconds option was not represented in the lock.
Changing it can alter one failure and every later case after worker termination,
therefore changing coverage and the verdict under nominally identical inputs.
Removing this optional tuning surface is the smallest correction inside v1.

The low-level DecisionModel.decide timeout parameter remains useful for direct
calls and lifecycle tests. Such calls produce captured data; they do not by
themselves attest to execution of the official locked collection protocol.
Self-authored evidence cannot establish execution provenance. Configurable
deadlines can return only with a separately versioned locked execution schema.

T50 tests assert 30.0 is passed for every ordinary request and reject the removed
CLI flag. T30 still tests finite-positive low-level timeouts and worker cleanup.
