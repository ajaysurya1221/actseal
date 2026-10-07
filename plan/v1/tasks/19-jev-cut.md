# TASK 19C: Apply the conditional Jev scope cut

Owner: Claude A, existing Task19 session; Fable 5.1, effort high.
Estimate: 1.5 hours plus independent compatibility review.
Status: PREPARED, NOT DISPATCHED. Codex must record the 14:00 IST gate result
before this task becomes active. Base: `5e7931a1ec8b0197d87ddc1e01a0835e011b470f`.

## Goal

If the complete candidate lacks exact-head green hosted CI at 14:00 IST on
7 October, defer optional Jev to 1.1 without leaving an orphan provider profile.
Preserve the accepted implementation and unstarted audit on their existing
branches/history. This is the approved scope cut, not a test bypass.

## Context

Read `plan/v1/PLAN.md` sections C/E/G, `plan/v1/STATE.md`, amendments V1-036,
V1-037 and V1-047, `plan/v1/reviews/19-candidate-5e7931a-ci.md`, and the original
Task19. Do not change Task13's denied merge or retry Task06's denied preflight.
The paired documentation task has separate ownership.

## Interface contract (frozen)

Remove only the unreleased Jev transport, CLI opt-in, identity/profile and fault
envelope. Preserve all stable fixture/Laya interfaces, normalized probability
semantics, six faults, policy precedence, statistics and replay rules. Preserve
`open_model(provider, *, responses, offline)` with explicit provider branches
and rejection before factory/environment/network access. No fall-through to Laya.
Contract remains schema 1, lock/bundle 2, CLI receipt 1. All existing non-Jev
flags and versioned ERROR/3 usage semantics remain unchanged.

## Files to create/modify; files NOT to touch

Delete only the deferred adapter and now-empty package markers:

```text
src/actseal/experimental/providers/jev.py
src/actseal/experimental/providers/__init__.py
src/actseal/experimental/__init__.py
tests/unit/test_jev.py
```

Modify only the Jev slices in:

```text
src/actseal/cli.py
src/actseal/runner.py
src/actseal/records.py
src/actseal/normalization.py
src/actseal/faults.py
docs/schemas/lock.schema.json
docs/schemas/captured-outcome.schema.json
docs/schemas/decision-record.schema.json
docs/schemas/fault-result.schema.json
docs/schemas/cli-receipt.schema.json
docs/stability.md
docs/schemas/README.md
tests/unit/test_cli.py
tests/unit/test_runner.py
tests/unit/test_normalization.py
tests/unit/test_faults.py
tests/unit/test_stability.py
tests/unit/test_schema_validation.py
tests/provider_support.py
tests/conformance/test_provider_contract.py
tests/conformance/test_provider_isolation.py
```

Add only your REPORT at `plan/v1/reports/19-jev-cut.md`. Do not edit stats,
policy, assessment, compatibility algorithms/registry, schema numbers, package
version, dependencies, lockfile, archive files, current docs owned by Claude D,
assets, other tests, old REPORTs or planning state. Do not mechanically revert
earlier commits: they contain accepted controls. Keep credential-exclusion
sentinels in visual/release tests even though they mention JEV_API_KEY.

## Acceptance criteria (testable)

- No importable Jev adapter, accepted Jev identity or executable Jev CLI choice
  remains; removed flag/provider are rejected before setup or transport.
- Fixture/Laya shared conformance and all native ownership fixes remain intact.
- All five schema provider enums agree with the runtime provider set.
- Every removed test is specifically tied to deferred Jev behavior; account for
  test-count changes. Never remove a shared regression to obtain a green result.
- Every original action-gate archive byte remains unchanged.
- Freeze the new packaged source and report its exact fingerprint. Do not insert
  a new registry mapping or alter tests to pretend compatibility was approved.

## Tests to add

Negative CLI/provider/schema cases for the removed profile/flag, including
factory/environment/network sentinels; retain unsupported-provider and
never-fall-through cases, shared fixture/mocked-Laya checks and all six faults.

## Constraints

You are not alone in this repository. Edit only owned paths; do not revert
another lane's work. Use a new branch `claude/v1-19-jev-cut` from the stated base,
preserving the preparation branch. Normal permissions and hooks stay enabled.
No network/model/key access, billing/model substitution, broad revert, test
exclusion or scope expansion. An actual harness denial stops that outcome.

The source fingerprint will change. Full example/compatibility checks may then
fail until Codex independently approves the new exact producer. Record PARTIAL
and the failures; do not weaken tests or self-authorize that approval. The later
registry task will be separately specified after the source is frozen.

## Done when (exact commands)

Run each command separately and record its real exit code:

```bash
uv run --frozen pytest tests/unit/test_cli.py tests/unit/test_runner.py tests/unit/test_normalization.py tests/unit/test_faults.py tests/unit/test_stability.py tests/unit/test_schema_validation.py tests/conformance
uv run --frozen pytest -m "not integration"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest -m integration
uv run --frozen pre-commit run --all-files
git diff --check
```

Known missing architecture and not-yet-approved producer failures must remain
visible. Task ACCEPT requires later integrated green checks, not a focused pass.

## Report format

REPORT 19C
Status: DONE / PARTIAL / BLOCKED
Changes: files and summary; exact source commit/fingerprint; removed-test counts
Tests: exact commands, results and exit codes
Deviations: with reasons
Open issues: include pending registry approval and missing architecture
Spend: distinguish API/credits from subscription estimates
