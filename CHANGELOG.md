# Changelog

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
