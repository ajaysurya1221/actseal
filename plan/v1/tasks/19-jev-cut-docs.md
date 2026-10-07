# TASK 19D: Align current documentation with the conditional Jev cut

Owner: Claude D, existing Task08 session; Fable 5.1, effort high.
Estimate: 0.75 hour. Status: PREPARED, NOT DISPATCHED. Requires Codex's recorded
14:00 IST gate result. Base: `5e7931a1ec8b0197d87ddc1e01a0835e011b470f`.

## Goal

If the approved cutoff is triggered, describe fixture/Laya-only v1.0 honestly
while retaining the accepted experimental work and audit preregistration as
history for 1.1.

## Context

Read `plan/v1/PLAN.md` C/D/G, STATE, V1-047, original Task08, Task19C and
`plan/v1/reviews/19-candidate-5e7931a-ci.md`. The reason is the complete candidate
missing its integration gate; do not portray successful offline adapter checks
as failures. No Jev live run, key read, journal, request or spend occurred.

## Interface contract (frozen)

Keep the approved README order, stable interfaces, guarantee/limit wording,
absolute links and runnable fixture quickstart. Remove executable Jev guidance
and shipped-feature claims. Record the conditional cut to 1.1 as a dated fact
only after activation. Normative schema/stability files belong to Claude A.

## Files to create/modify; files NOT to touch

```text
README.md
CHANGELOG.md
plan/v1/RELEASE_NOTES.md
docs/providers.md
docs/python-api.md
docs/cli.md
docs/faq.md
docs/architecture.md
docs/dependencies.md
docs/threat-model.md
tests/docs/test_policy_and_metadata.py
tests/docs/test_readme.py
tests/docs/test_cli_reference.py
.env.example
docs/decisions/0004-identity-normalization-fallback.md
docs/decisions/0017-experimental-decision-provider.md
docs/decisions/0018-finite-benchmark-audit.md
plan/v1/reports/19-jev-cut-docs.md
```

Append dated ADR status addenda; preserve earlier evidence and decisions. Remove
only the unused placeholder assignment in `.env.example`; never access `.env`.
Do not edit product code, normative schemas/stability, assets, other tests,
historical reports, benchmark candidates, archive files, planning state or CI.

## Acceptance criteria (testable)

- Current public instructions match the fixture/Laya release scope and preserve
  the exact three-command PyPI quickstart.
- No live Jev result, credit consumption, released v1.0 or completed mandatory
  gate is invented. Explain deferral without asserting provider malfunction.
- Documentation assertions match the shipped interface; preserve negative
  checks and all missing-image gates. Historical narratives stay historical.
- The architecture text requires fixture/Laya only; creating the missing image
  remains Task13, and this task does not unblock its denied operation.

## Tests to add

Replace assertions requiring shipped Jev with explicit deferral/current-provider
checks. Preserve no-output-before-rejection and all fixture/Laya examples.
Remove only adapter-specific import/SSL test setup if no longer necessary.

## Constraints

You are not alone in this repository. Edit only owned paths; do not revert
another lane's work. Use `claude/v1-19-jev-cut-docs` from the stated base. No key,
network/model calls, paid transactions, permission bypass or product changes.
Do not claim the source cut is integrated until its reviewed commit is consumed.

## Done when (exact commands)

```bash
uv run --frozen pytest tests/docs
uv run --frozen python tools/check_release.py docs
uv run --frozen pre-commit run --all-files
git diff --check
```

Run separately; record known missing architecture or not-yet-integrated source
failures honestly. No skipped test or altered asset gate substitutes for a pass.

## Report format

REPORT 19D
Status: DONE / PARTIAL / BLOCKED
Changes: files and summary
Tests: exact commands, results and exit codes
Deviations: with reasons
Open issues: integration and mandatory gates
Spend: API/credits and subscription estimates kept separate
