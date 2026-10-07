# Changelog

## Unreleased

- Repository automation: weekly Dependabot updates for `uv` and GitHub Actions, CodeQL Python analysis, pull-request dependency review and full-history Gitleaks scanning.
- `CI / required` aggregate check that passes only when every CI job succeeds; a failed, cancelled or skipped job fails it.
- Package metadata project URLs for the quickstart documentation, repository, issue tracker and changelog.
- `CITATION.cff` software citation metadata for the 1.0.0 release.
- Corrected GitHub README figure selection to use dark or light desktop variants at every viewport width. This supersedes the v1.0.0 statement that the README selects vertical variants below 1280 px. Mobile SVGs remain committed; phone text legibility remains a known limitation.

## v1.0.1 — unreleased

### Fixes

- Iterate LF-delimited JSONL rows without first building a list of every
  row. Preserve row boundaries, validation order, diagnostics and existing
  limits; the fixture adapter still has no row-count limit.
- Require native Laya worker reply sequences to be JSON integers matching
  the pending request. Boolean, floating-point and missing sequences
  invalidate the worker and return `unavailable` with `laya.unavailable:ipc`.

### Replay compatibility

- Add the reviewed 1.0.1 implementation fingerprint to the
  `actseal-choice-v1` registry, retaining both existing mappings.
  The retained action-gate archive remains unchanged and replays to its
  stored verdict. New collection continues to require an exact-source lock.

### Documentation

- Correct the numerical-kernel exception guide: `clopper_pearson_tail`
  raises built-in `TypeError` or `ValueError`, not `ActsealError`.
  This documentation correction changes neither numerical behaviour nor
  results.

## v1.0.0 — 2026-10-07

This entry describes the 1.0.0 implementation as reviewed and accepted before
the tag (source fingerprint
`8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3`). The
tag, distribution and publication receipts are recorded in
[plan/v1/RELEASE_NOTES.md](plan/v1/RELEASE_NOTES.md) as the release pipeline
produces them, not here. The [migration guide](docs/migration.md) and
[stability manifest](docs/stability.md) are normative for the changes below.

### Stability and compatibility

- The public surface is enumerated in `docs/stability.md`: STABLE means
  compatible throughout 1.x; PROVISIONAL surfaces live only under
  `actseal.experimental` or an explicit experimental flag. Deprecations
  require documentation, one minor release and 90 days before removal in 2.0.
- `PlanLock` gains a final required field `replay_engine_version`
  (`actseal-choice-v1`); lock documents are schema 2 and bundle manifests
  schema 2. Producer provenance (`implementation_sha256`) is separated from
  replay semantics; a reviewed compatibility registry approves exact source
  fingerprints for cross-release replay within 1.x. New collection still
  requires the exact running implementation.
- Every CLI JSON receipt, including errors, carries `schema_version: 1`;
  `lock --json` adds `replay_engine_version` and `replay --json` adds
  `notes`. Published JSON Schemas cover the lock, manifest, records, verdict,
  receipts and registry.
- Abbreviated long options are rejected on the root parser and every
  subcommand; `--version` is root-only.
- actseal 0.1.0 locks and bundles are rejected with `integrity.legacy_schema`
  and operator guidance; they are never converted or resealed and replay under
  an isolated pinned `actseal==0.1.0`.
- `clopper_pearson_tail` raises the documented `SchemaError` for out-of-domain
  numeric input instead of `OverflowError`; valid-input bounds are unchanged.

### Providers, verification and examples

- One shared provider conformance suite covers the fixture adapter, the
  mocked native Laya adapter and the mocked experimental Jev adapter; native
  inference remains explicitly marked, and the accepted cached-native checks
  (Task 03, repeated at the Task 19 integration) cover the changed native
  paths.
- Bounded deterministic property tests and eight targeted semantic mutations
  guard the gate (tail allocation, scheduled denominator, zero-accepted
  handling, threshold boundary, risk and coverage bounds, fault blocking and
  ERROR precedence).
- Application action-gate example (`examples/action_gate/`): a local
  ticket-routing application that executes a queue operation only after
  ACT, with a retained recorded synthetic bundle. Its original producer and
  the 1.0.0 source are the two approved entries of the packaged compatibility
  registry (amendment V1-037), so the unchanged archive replays under this
  release.
- Experimental Jev cloud transport, `actseal.experimental.providers.jev`:
  PROVISIONAL, selectable only as `--provider jev --experimental-provider`
  (or `open_model("jev", ...)`), bring-your-own `JEV_API_KEY`, one attempt
  per request, no retry, redirect or fallback, no 1.x promise. Its tests use
  mocked transports only. The optional preregistered live audit was not run
  for 1.0.0: no key was read, no request was made, and no journal, request
  count or verdict exists; no live Jev result is accepted as evidence.

### Platforms, release and documentation

- Supported platforms are Linux and macOS on Python 3.12 and 3.13; Windows is
  unsupported. The runtime core has no third-party dependency.
- Security support covers the latest 1.x minor at its latest patch.
- Tag-triggered release pipeline: build once, verify the exact bytes on the
  four-platform matrix, regenerate the static assets, publish through Trusted
  Publishing after human approval, verify the public copy in a clean container,
  and mirror identical files with `SHA256SUMS` and a release receipt to a
  draft GitHub release. Branch runs are rehearsals that never upload.
- Concepts, CLI reference, Python guide, FAQ, version-neutral quickstart and
  a rewritten publishing guide, with executable documentation tests.
- Reproducible README figures from a pinned authoring-only toolchain: hero,
  how-it-works and architecture, each as light/dark desktop and vertical
  mobile SVGs validated against the measured GitHub README image widths
  (838 px desktop, 254 px mobile, 14 px label floor), plus the 1280×640
  social preview; the README selects the vertical variants below a 1280 px
  viewport. The where-it-sits, decision/verdict-matrix and evidence-boundary
  figures are not part of 1.0.0; the evidence limits stay in plain text. The
  genuine demo recording is captured from the published PyPI release after
  publication (Decision 2A) and is not in the tagged tree.

## v0.1.0 — 2026-10-06

### Core

- Frozen categorical contracts for 2–16 labels, an action allowlist and a
  prespecified threshold; labelled inputs and model/runtime/implementation
  identity bound into an immutable lock.
- Explicit ACT, ABSTAIN, DENY and ESCALATE policy, including conservative
  fallback handling and unknown-choice denial.
- Accepted-action error and coverage bounds with simultaneous CP tail allocation;
  distinct PASS, BLOCK, INCONCLUSIVE and ERROR verdicts.
- Model-free fixture provider and optional pinned Laya CPU adapter, strict
  response normalization, token-layout preflight and bounded worker lifecycle.
  The optional Linux stack selects official CPU Torch without CUDA dependencies.
- Six canonical provider-failure checks; complete evidence validation before
  assessment. Regular native worker loss invalidates the statistical attempt
  while preserving terminal diagnostic records.
- Bounded seven-file evidence bundles, exclusive publication on supported
  macOS/Linux filesystems and provider-free semantic replay. A trusted lock
  anchors identity, not response or execution authenticity.

### CLI and distribution

- `actseal lock`, `verify`, `replay` and `demo`, plus `python -m actseal`;
  structured JSON, explicit exit codes and surfaced warnings/failures.
- Packaged support-triage demonstration: the same prespecified policy against
  two different sets of authored answers, targeting bad BLOCK and fixed PASS
  with fresh replay. It does not demonstrate model repair or population quality.
- Dependency-free core wheel and source distribution, committed uv lock,
  Linux/macOS Python3.12/3.13 CI and public usage/statistics/trust documentation.


The [native CLI receipt](plan/reports/T70-native.md) preserves BLOCK with zero
accepted actions under the unchanged threshold. The [release report](plan/FINAL_REPORT.md)
records exact review, CI, artifact and publication receipts. Demo fixtures are
synthetic evidence, not model-quality or deployment certification.
