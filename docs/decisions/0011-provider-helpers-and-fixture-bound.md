# ADR 0011: Provider helper boundaries and fixture file limit

Status: accepted. Date: 2026-10-06. Owner: Codex.

Accept the T30 package marker and the small request_sha256/validate_timeout
helpers described in CONTRACTS section 4. Request hashing stays in pure
normalization, so assessment/replay can reuse it without importing providers.
The private fake-worker constructor is a test seam, not a new public adapter API.
Observed package versions enter identity; supported install metadata already pins
the approved stack. No new unsupported-environment guard or dependency is needed.

Clarify the aggregate fixture-file ceiling as 128 MiB, checked with a bounded
read before decoding/splitting/hashing. The earlier contract specified individual
fixture rows but did not explicitly bound their aggregate. A 129-row file with
legal sub-1MiB rows was accepted at 135,071,791 bytes. The cap bounds this input
path consistently with generic input/bundle limits. The 10,000-case limit still
belongs to datasets; do not invent a new fixture-row count rule.

Existing worker requirements already demand end-to-end request deadlines and
invalidation after unusable IPC. T30 review requires implementation fixes for
blocking writes and escaping deep-JSON parse errors. Linux native tests must
expect exactly torch2.14.1+cpu; macOS keeps torch2.14.1. These are correctness
repairs under existing requirements, not a change to runtime pins or policy.

No shared record change, feature expansion, model substitution or billing change.
