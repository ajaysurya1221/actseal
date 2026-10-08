# ADR 0019: Supported platforms for v1.0

- Status: approved (plan/v1/PLAN.md section C, option (h); section G
  definition of done); recorded during Task 08 documentation and finalized
  for 1.0.0 in "Evidence and status" below.
- Date: 2026-10-07.

## Decision

Actseal 1.0 supports **Linux and macOS on Python 3.12 and 3.13**, the four
combinations exercised by the hosted CI matrix. The runtime core requires
Python >= 3.12 and has no third-party dependency; the published metadata
carries only the macOS and Linux operating-system classifiers.

**Windows is unsupported.** Exclusive evidence publication relies on
platform facilities (macOS `renamex_np(RENAME_EXCL)`, Linux
`renameat2(RENAME_NOREPLACE)`, [ADR 0012](0012-replay-errors-and-exclusive-publication.md))
that fail explicitly elsewhere. No Windows classifier, partial-support
statement or best-effort promise is made; documentation says "Windows is
unsupported" rather than "untested".

The optional native Laya adapter is supported only in the documented tested
CPU configurations ([ADR 0006](0006-tested-cpu-stack-and-licenses.md),
[providers](../providers.md)): the pinned stack on arm64 macOS and x86_64
glibc Linux, CPU FP32, four threads, eager backend. That contract is not a
universal device, accelerator, memory or performance guarantee, and it does
not establish Intel Mac, Linux ARM, musl, GPU or native Python 3.13
inference.

Security support follows [ADR 0015](0015-v1-stability-and-replay-compatibility.md)
and [SECURITY.md](../../SECURITY.md): the latest 1.x minor at its latest
patch. This ADR adds no exclusion, waiver or accepted risk.

## Rationale

The compatibility promise must match what is actually verified. Hosted CI
proves the deterministic core and fixture paths on the four matrix
combinations; it does not run native inference. Claiming Windows without
the exclusive-publication primitive would either weaken a security invariant
or promise behaviour that fails, and claiming broader native support would
exceed the receipts.

## Consequences

- Platform-specific details of exclusive publication remain outside the
  stable surface; a future Windows path would be a separately reviewed
  addition, not a patch.
- Hosted deterministic checks are not native evidence. A change to any
  native path requires its own cached-native receipt before release
  (plan section G) and is not satisfied by green hosted jobs. (Historical
  status, superseded: that receipt was pending when this ADR was first
  written; the completed Task 03 and Task 19 cached-native checks are
  recorded in "Evidence and status" below, with the final candidate gate
  kept separate.)
- Users on unsupported platforms receive explicit failures, not silent
  fallbacks.

## Evidence and status

- CI matrix: `.github/workflows/ci.yml` runs `ubuntu-latest` and
  `macos-latest` with Python 3.12 and 3.13; native checks run separately in
  `native.yml` on Python 3.12.
- Metadata: `pyproject.toml` declares `requires-python = ">=3.12"`, empty
  `dependencies`, and only MacOS and POSIX Linux classifiers;
  `tests/docs/test_policy_and_metadata.py` checks the installed metadata.
- Native receipts: the historical v0.1 milestones recorded in
  [providers](../providers.md) (the T30 provider/normalizer milestone with
  macOS cached-native tests and the Linux native workflow run, and the
  native CLI lock/verify/replay receipt); the v1 Task 01 baseline, which
  passed independently; the v1 Task 03 conformance acceptance at `212a1d6`
  (177 conformance/provider tests plus five cached-native tests); and the
  Task 19 integration, where the cached-native tests were repeated (six
  tests, no skips) on the 1.0.0 source. These complete the native checks for
  the changed paths in 1.0.0. They are 1.0.0 receipts: they do not establish
  native verification of the 1.0.1 patch, whose source fingerprint differs.
  The 1.0.1 patch's changed Laya reply-validation path has its own
  cached-native receipts, recorded in
  `plan/v1/reviews/2026-10-08-release-preparation-1.0.1.md`: the five
  integration tests passed on macOS (arm64, Python 3.12.13) and in the
  hosted Linux native workflow (run 37719743745, Python 3.12.3) against the
  1.0.1 source.
- Authoring platform: the pinned Linux x86_64 agg binary was actually
  executed in hosted CI at PR 18 head `0e32c6c` (runs 37581140052 and
  37581142565, all ten jobs green) with its hash verified before execution;
  that establishes Linux binary execution for the asset pipeline, not GIF
  rendering.
- Historical: exact-head hosted CI at the earlier candidate heads `b05aed8`
  and `5e7931a` failed. The only test failures were the four then-absent
  architecture figures, and lint and type steps passed, but the downstream
  build, packaging, reproduction and hook steps were skipped after the
  failure and were not run; those runs establish nothing about them. The
  figures were accepted at `77a13bd` and the README that references them at
  `95e17b4`.
- Integrated head: all ten hosted source and assets jobs (Linux and macOS,
  Python 3.12 and 3.13, both assets jobs) succeeded at the exact combined
  head `ff0f66c` (push run 37599734305, PR run 37599764080;
  `plan/v1/reviews/19-combined-static.md`), which merged to `main` as
  `277d729`. The non-publishing `publish-pypi.yml` rehearsal 37599844342 at
  the same head passed its four exact-artifact platform verify jobs with
  publish, post-publish and mirror intentionally skipped. The hosted matrix
  result for the tagged commit itself is a release pipeline receipt
  recorded in `plan/v1/RELEASE_NOTES.md`, not a claim of this ADR.
