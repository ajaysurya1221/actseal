# Changelog

## Unreleased — prepared v0.1.0

**Pending final acceptance and publication.** This draft targets root CHANGELOG.md.
No final artifact hash or public download is asserted.
Move these entries to the released v0.1.0 section only after T50/T60/T70 gates
and exact release verification pass.

### Accepted core

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

### Accepted CLI and distribution

- `actseal lock`, `verify`, `replay` and `demo`, plus `python -m actseal`;
  structured JSON, explicit exit codes and surfaced warnings/failures.
- Packaged support-triage demonstration: the same prespecified policy against
  two different sets of authored answers, targeting bad BLOCK and fixed PASS
  with fresh replay. It does not demonstrate model repair or population quality.
- Dependency-free core wheel and source distribution, committed uv lock,
  Linux/macOS Python3.12/3.13 CI and public usage/statistics/trust documentation.
  Final release-artifact and publication checks remain gated.

The corrected installed-wheel candidate has an independent fixture-demo/replay
receipt; it is not a final-release receipt. The [native CLI receipt](plan/reports/T70-native.md) records a genuine BLOCK
result with zero accepted actions under the unchanged threshold. Final counts, timings, artifact identities and CI links belong in the
reviewed [final report](plan/FINAL_REPORT.md), not an inferred release entry.

### Scope limits

Jev, automatic threshold fitting, score/baseline/slice contracts, sequential
testing, certified fallback chains, signatures, hosted services, a Marketplace
Action and OS enforcement are outside v0.1.0. The statistical protocol concerns
one prespecified attempt; it provides no uptime or completion-probability bound.
