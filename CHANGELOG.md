# Changelog

## v1.0.0 — unreleased candidate

No 1.0.0 tag has been pushed and no 1.0.0 distribution is on PyPI; this
entry describes the reviewed candidate and is finalized with the release
receipts. The [migration guide](docs/migration.md) and
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

- One shared provider conformance suite covers the fixture adapter and the
  mocked native Laya adapter; native inference remains explicitly marked.
- Bounded deterministic property tests and eight targeted semantic mutations
  guard the gate (tail allocation, scheduled denominator, zero-accepted
  handling, threshold boundary, risk and coverage bounds, fault blocking and
  ERROR precedence).
- Application action-gate example (`examples/action_gate/`): a local
  ticket-routing application that executes a queue operation only after
  ACT, with a recorded synthetic bundle. Final registration of its archived
  producer is pending integration review.
- Optional experimental Jev transport: prepared as a PROVISIONAL adapter
  behind an explicit experimental flag; inclusion, CLI opt-in integration and
  any live audit are pending decision and review. No live results exist.

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
- Reproducible README figures (hero, how-it-works, social preview) from a
  pinned authoring-only toolchain; the architecture figure and the genuine
  post-publication demo recording are pending.

Pending before this entry is final: Jev inclusion decision, architecture
figure, example registry approval, the blind README test, the candidate gate
and the publication receipts.

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
