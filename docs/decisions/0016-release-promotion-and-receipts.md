# ADR 0016: Release promotion of exact bytes with strict receipts

- Status: accepted with the v1.0.0 plan (Task 09, amendments V1-006 and
  V1-012) and REVIEW 09R2–09R4; recorded here after implementation. The
  static-asset inputs to the pre-upload gate are complete (see "Evidence and
  validation"); the tagged pipeline's own receipts are recorded in
  `plan/v1/RELEASE_NOTES.md`.
- Date: 2026-10-07.

## Decision

**Build once, promote the same bytes.** A `v*` tag push runs
`.github/workflows/publish-pypi.yml`. The build job validates that the tag,
`pyproject.toml`, `actseal.__version__`, the `uv.lock` self-entry, the wheel
METADATA and the sdist PKG-INFO agree, builds the wheel and sdist exactly once,
checks them with Twine, and uploads them as one immutable, run-unique Actions
artifact that contains only those two files. Every later job downloads that
artifact by its ID; nothing rebuilds, re-uploads or substitutes bytes. The four
Linux/macOS Python 3.12/3.13 verify cells run the packaging tests against the
downloaded wheel and directory (`ACTSEAL_TEST_WHEEL`, `ACTSEAL_TEST_DIST`) and a
shim proves no `uv build` runs when the artifact is supplied. `workflow_dispatch`
is a rehearsal that never reaches the publish job.

**Gates before upload.** Publication needs every verify cell, the regenerated
required static assets (hero, how-it-works, architecture, social; the demo
recording is the approved post-PyPI exception) and the human approval of the
`pypi` environment. The publish job alone holds `id-token: write`, checks out
nothing, re-checks `SHA256SUMS`, and uses the pinned PyPA action with
attestations and no token fallback or skip-existing. ADR 0014's pinned action
hashes, uv 0.12.5, workflow filename and environment name are retained.

**Verification after upload, then a draft mirror.** The pinned Linux/amd64
Python container installs the exact version from the official PyPI index outside
the checkout, compares the downloaded bytes with the build checksums and with
PyPI's declared digests, requires the published metadata to equal the wheel's
METADATA (non-yanked, Production/Stable for 1.x), runs the demo and both replays
expecting exits 0/0/1 with BLOCK/PASS, and inspects the PEP 740 provenance.
Only then does the mirror job bind the release receipt and create or update a
draft GitHub release with the identical distributions, `SHA256SUMS` and the
receipt, never overwriting a differing asset and never touching a published
release. Partial publication is a loud failure that preserves the original
bytes; missing receipts are never promoted.

**Strict receipts.** The build, post-publication and release receipts are
schema 1 documents with exact required field sets at every object level,
published as Draft 2020-12 schemas in `docs/schemas/`. Promotion decodes
receipts rejecting duplicate keys and nonfinite numbers, requires exact
integers, positive ASCII decimal identifiers and positive sizes, and enforces
the cross-field rules the schemas cannot express: version/tag/ref/commit
agreement, exactly the wheel and sdist with equal names, sizes and hashes across
the build receipt, the post-publication receipt, the artifact bytes and
`SHA256SUMS`, workflow URLs derived from the fixed repository, run and respective
attempts, build attempt not later than verification attempt, the official index
and file host, the expected trusted-publisher identity and the literal notes.
In the build and release receipts `lock_sha256` is the SHA-256 of `uv.lock` at
the source commit, not an Actseal decision lock; the post-publication receipt
has no such field, and the release receipt has no `ok` field. Inspection-only
receipts (rehearsal builds, local indexes, tolerated missing attestations)
never match the promotion profile.

**Attestation inspection is not verification.** The helper decodes each
attestation's in-toto statement and requires the PyPI Publish predicate type
with an empty predicate, subjects naming the downloaded file and its digest, the
expected publisher identity, and well-formed base64 signature and certificate
with non-empty transparency entries. Signatures and certificates are not
verified; the receipts say so verbatim.

## Consequences

When the pipeline succeeds, every job has compared the distribution hashes it
handled against the build checksums, so the bytes PyPI serves, the bytes on the
GitHub release and the bytes the verify matrix tested were checked to be the
same artifact; the receipts record those comparisons and do not by themselves
prove that the workflow ran. A release receipt can be checked offline against
its schema and against `SHA256SUMS`; a defective or ambiguous receipt stops the
pipeline before any GitHub mutation rather than being repaired. Independent
cryptographic verification of attestations remains a separate, unclaimed step.
The release schemas sit in `docs/schemas/` beside the product schemas under
amendment V1-016, which extends the exact inventory test without altering any
product schema check.

## Evidence and validation

Reports 09, 09R2, 09R3, 09R4-glue (Codex-authored CI-glue repair) and 09R4
record the implementation. `tests/release/` exercises the workflow contract,
every helper gate and its negatives, the supplied-artifact no-rebuild proof and,
in `test_release_schemas.py`, the schemas against receipts the helper actually
writes. The release workflow's own glue was exercised at PR 18 head `0e32c6c`
(runs 37581140052 and 37581142565, ten green hosted jobs, including the
hash-verified Linux agg execution); that was a rehearsal of the branch
workflow, not a tagged run.

Status on 7 October 2026: the four required static asset groups the
pre-upload gate regenerates (hero, how-it-works, architecture, social) are
committed and accepted at `77a13bd` (`plan/v1/reviews/13-readability.md`,
byte-identical regeneration of twelve SVGs and the social PNG) with the
README's responsive selection at `95e17b4`. The demo recording stays the
approved post-PyPI exception. The tagged build, verify, publish and
post-publication receipts are produced by the pipeline itself and recorded
in `plan/v1/RELEASE_NOTES.md`; this ADR claims none of them.
