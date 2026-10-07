# REPORT 09R4-glue

Status: PARTIAL — CI helper/test repair complete; Task09 schemas, documents, final assets and hosted rehearsal remain pending.

## Changes

Authored by Codex under Task09's explicit CI/packaging-glue ownership while Claude's subscription quota was unavailable. No product source, public schema/documentation, authoring assets, permissions or dependencies changed.

- `tools/check_release.py`: receipt decoding rejects duplicate keys at every object depth, nonfinite constants and exponent overflow; encoding rejects nonfinite data before touching an existing output. Promotion validates exact required object fields, positive exact-integer sizes, positive ASCII decimal identifiers, provenance counts and the literal final note. Existing identity/hash/inventory/smoke/index/publisher checks and diagnostic precedence are retained.
- `tests/release/test_strict_receipts.py`:158 deterministic CI-helper regression cases cover valid receipts, missing/unknown fields at every receipt object level, ambiguous/nonfinite JSON, exact types, IDs/sizes/counts, and rejection before any GitHub command. Existing tests were not edited.

Reviewed file SHA256:

- Helper: `8b00e2d801bbf2fb0c9c8e64ad20f34f6cf5f6d6e3039c08ff079e241a9a2d2d`
- New tests: `eb8ef045e4428a1daa052d35f982ccaba4f9e43fa93eae519696cd0149e16886`

## Tests

On the repaired files in the Task09 worktree:

```text
uv run --frozen pytest tests/release -q
442 passed in12.32s; exit0

uv run --frozen ruff check tools/check_release.py tests/release/test_strict_receipts.py
All checks passed; exit0

uv run --frozen mypy --strict tools/check_release.py tests/release/test_strict_receipts.py
Success:2 source files; exit0

uv run --frozen python tools/check_release.py workflow
exit0

uv run --frozen pre-commit run --all-files
Ruff lint, format and strict mypy passed; exit0

git diff --check
exit0
```

The initial full run had7 failures/435 passes: six reflected changed diagnostic precedence/wording, and one exposed the new test helper using a deliberately removed field as its reference inventory. The implementation now preserves existing diagnostics, and the test uses an unmodified reference inventory. Initial owned lint/type errors were corrected. No existing check or assertion was weakened.

Independent read-only reviewer `/root/v1_receipt_review` returned scoped ACCEPT at the hashes above, with319 focused tests plus lint/format/strict typing/diff checks passing. The immutable commit and hosted jobs still require confirmation. The helper remains stdlib-only.

## Deviations and open issues

Codex performed this bounded CI-glue repair instead of waiting for Claude; this is within the approved Task09 role. Claude will author the remaining schemas/documentation and their validation tests. The task's full completion cannot be claimed from this report. No native model tests, mutation harness, SVG rasterizer, asset download, paid call, credential read, hosted publishing job or permission alteration occurred here. Previously denied operations remain pending explicit scoped permission.

Spend: no API/Jev requests or incremental billed service was used; subscription meter cost is not measured.
