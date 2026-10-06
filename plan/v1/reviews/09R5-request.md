# REVIEW 09R5 — release schemas and documentation

Verdict: REVISE at006072fef31aa238265b51402297d2b16ffc9722. The accepted helper at0060f27 remains unchanged; full Task09 remains incomplete.

## Findings ordered by severity

1. The postpublication schema rejects duplicate classifier strings that the accepted helper can emit. A helper-generated final receipt was independently rejected at verification.postpublish.published_metadata.classifiers. Remove unsupported uniqueItems and align unconditional minItems with legacy0.x behavior, where the helper permits an empty array. Add generated-receipt parity tests. Do not arbitrarily tighten the accepted helper to fit the schema.
2. Restore the approved docs/schemas location for all three release schemas. V1-016 authorizes only an explicit three-name RELEASE_FILES tuple and exact combined eleven-schema-plus-README inventory in tests/unit/test_schemas.py. Preserve all eight product-schema checks. Update paths, index links and release tests; remove the sibling-directory rationale from the ADR.
3. Correct field descriptions: build and release receipts have lock_sha256 (uv.lock), while postpublication receipts do not. The final release wrapper has no ok field. Replace claims that schemas/checksums prove CI execution with conditional wording that a successful pipeline compares distribution hashes. Preserve the honest disclaimer that publisher inspection is not cryptographic attestation verification.

## Independent verification

131 passed, one packaging test deselected using:

```bash
uv run --frozen pytest tests/release/test_release_schemas.py tests/unit/test_schemas.py tests/unit/test_schema_validation.py -m 'not packaging' -q -p no:cacheprovider
```

No live or full packaging checks were rerun by this reviewer. Helper SHA256 remains8b00e2d801bbf2fb0c9c8e64ad20f34f6cf5f6d6e3039c08ff079e241a9a2d2d.

## Required changes and follow-ups

Apply the three bounded repairs, rerun Task09 release/schema checks, hooks and strict owned typing, and commit a truthful REPORT09R5. No product implementation change, publication, network authoring download, hosted asset job or permission change is authorized. Actual static assets and hosted rehearsal remain pending.
