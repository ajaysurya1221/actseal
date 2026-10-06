# REVIEW 09R4-glue

Verdict: ACCEPT — bounded CI-helper/test subset at `0060f27d5b71e7445636c1784c71c074e0a5e284`; not full Task09 or release acceptance.

Codex wrote the authorized CI glue and its regression tests. Independent read-only reviewer `/root/v1_receipt_review` inspected the diff over `a09b69f000c908a82f4b15c850f758c66aa911e0`, ran focused checks, and confirmed the immutable commit preserves the reviewed hashes. No product source or public documentation changed.

## Findings and verification

No blocking finding in this subset. Duplicate decisive keys, nested nonfinite numbers, unknown/missing fields, invalid identifier/size types, understated attestation counts and changed final disclaimers now fail before promotion. Existing source/artifact/inventory/workflow/PyPI/smoke/publisher checks are preserved. The official profile remains distinct from unpromotable inspection fixtures.

Parent:442 release tests passed12.32s; workflow checker, owned lint/type checks, pre-commit and diff checks pass. Initial failures are retained in REPORT09R4-glue rather than omitted.

Independent exact commands from the release worktree:

```bash
.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/release/test_strict_receipts.py tests/release/test_check_release_receipts.py tests/release/test_check_release_postpublish.py
.venv/bin/ruff check tools/check_release.py tests/release/test_strict_receipts.py
.venv/bin/ruff format --check tools/check_release.py tests/release/test_strict_receipts.py
.venv/bin/mypy --strict tools/check_release.py tests/release/test_strict_receipts.py
git diff --check
```

All exit0;319 focused tests passed3.63s. Immutable-commit confirmation required no rerun because bytes were unchanged.

Reviewed SHA256:

- `tools/check_release.py`: `8b00e2d801bbf2fb0c9c8e64ad20f34f6cf5f6d6e3039c08ff079e241a9a2d2d`
- `tests/release/test_strict_receipts.py`: `eb8ef045e4428a1daa052d35f982ccaba4f9e43fa93eae519696cd0149e16886`

## Required remaining work and follow-ups

Claude09R4 must finish the three public schemas, generated-receipt/schema tests, schema index, promotion ADR and precise uv.lock hash wording. Exact-head hosted checks, accepted final assets and an authorized nonpublishing rehearsal remain mandatory. PR18 stays draft/unmerged. No previously denied native/harness/render/download action was executed in this review.
