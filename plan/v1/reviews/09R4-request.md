# REVIEW 09R4 — required before receipt schema freeze

Verdict: REVISE for final Task09 completion at `e6c967a4cf558f7c7950abef7d3357a9b45c639f`. The earlier bounded repair ACCEPT remains historical; no hosted rehearsal or release acceptance has occurred.

## Findings, ordered

1. **P1 — Ambiguous receipt JSON is accepted.** `_read_json` at `tools/check_release.py:280` discards duplicate keys. A final receipt containing `"verify_matrix":"failure","verify_matrix":"success"` passes the mirror's pre-mutation validation. Reject duplicate keys recursively at decoding, before schemas see the object.
2. **P2 — Nonfinite values are accepted and emitted.** Validators accept unknown NaN fields and final `note: NaN`; extra smoke-check data containing Infinity survives `_write_json`. Reject JSON constants and nonfinite floating results, including exponent overflow `1e999`; encode with `allow_nan=False`. Errors must fail explicitly before mirroring.
3. **P2 — Complete strict version1 field/type validation.** Unknown fields currently pass at nine inspected object levels. Freeze exact required fields recursively in helper validation and the published schemas. Keep exact integer checks because JSON Schema treats numeric1.0 as an integer. Enforce positive ASCII decimal IDs/attempts, positive file sizes and truthful provenance counts. `.isdigit()` currently admits zero/non-ASCII IDs, and an attestation count1 with two publisher bundles currently passes.

These findings demonstrate invalid/ambiguous receipt promotion. They do not establish altered distribution acceptance or bypass of the human PyPI deployment gate.

## Exact object shapes

Every field below is required in the official promotion profile; unknown fields are rejected.

| Object | Fields |
| --- | --- |
| Build receipt | schema_version, kind, version, tag, ref, source_commit, lock_sha256, workflow_run, distributions |
| Build workflow | id, attempt |
| Postpublish receipt | schema_version, kind, version, index, ok, published_metadata, files, checks, note |
| Release receipt | schema_version, kind, version, tag, source_commit, lock_sha256, workflow_run, artifact, distributions, verification, note |
| Release workflow | id, build_attempt, verification_attempt, build_url, verification_url |
| Artifact | id, digest |
| Distribution | filename, size, sha256 |
| Verification | verify_matrix, postpublish |
| Embedded postpublish | index, published_metadata, files, checks, note |
| Published metadata | name, version, summary, classifiers, yanked |
| Published file | filename, url, size, sha256, declared_sha256, matches_build, provenance |
| Provenance | present, attestations, publishers, subject_sha256 |
| Publisher | kind, repository, workflow, environment |
| Smoke checks | version_output, demo_exit, fixed_replay_exit, bad_replay_exit, demo_bad_status, demo_fixed_status, installed_outside_checkout |

Preserve and exercise cross-field checks: version/tag/ref/source agreement; lowercase hashes; exactly one wheel and sdist; unique positive-sized files; actual/inventory/hash equality; matching run IDs and derived workflow URLs; build attempt no later than verification; exact0/0/1 and BLOCK/PASS smoke results; official PyPI/index/file URLs; stable metadata and yanked=false; expected publisher identities and subject hashes. Provenance count is positive and at least its publisher-bundle count. Final note is exactly `Contains no credentials.`; the attestation-inspection disclaimer remains exact and must not imply cryptographic verification.

## Required implementation and verification

- Own only Task09/V1-012 paths. Add `build-receipt.schema.json`, `postpublish-receipt.schema.json`, `release-receipt.schema.json` under `docs/schemas/`, schema index entries and a concise release-promotion ADR. No changes to core formats or product source.
- Validate actual generated receipt fixtures with the approved dev-only Draft2020-12 validator, local references and no network retrieval. The postpublish helper still runs in the clean Python container without third-party dependencies.
- Preserve separately documented inspection-only cases such as a standalone build with null workflow metadata or a local postpublish fixture lacking attestations. They remain unpromotable and must never match the official release schema/profile.
- Add negative tests for each strictness boundary above. Retain previous passing tests and supplied-artifact no-rebuild proofs. Rerun all release tests, workflow checks, owned typing, hooks and diff checks; write REPORT09R4 with actual results and commit.
- Do not publish, dispatch a hosted asset-download job, read credentials, change permissions, fetch authoring assets or edit another lane. Hosted rehearsal remains pending real accepted assets and authorized setup. No fixture substitutes for required P1 assets.

No new dependency is approved. Review hashes/source and final CI again after the repair.
