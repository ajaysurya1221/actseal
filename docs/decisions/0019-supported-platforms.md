# ADR 0019: Supported platforms for v1.0

- Status: approved (plan/v1/PLAN.md section C, candidate (h); section G
  definition of done); recorded during Task 08 documentation.
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
  (plan section G); that gate is currently pending for the changed tests and
  is not satisfied by green hosted jobs.
- Users on unsupported platforms receive explicit failures, not silent
  fallbacks.

## Evidence and status

- CI matrix: `.github/workflows/ci.yml` runs `ubuntu-latest` and
  `macos-latest` with Python 3.12 and 3.13; native checks run separately in
  `native.yml` on Python 3.12.
- Metadata: `pyproject.toml` declares `requires-python = ">=3.12"`, empty
  `dependencies`, and only MacOS and POSIX Linux classifiers;
  `tests/docs/test_policy_and_metadata.py` checks the installed metadata.
- Native receipts to date are the historical v0.1 milestones recorded in
  [providers](../providers.md): the T30 provider/normalizer milestone (macOS
  cached-native tests and the Linux native workflow run) and the native CLI
  lock/verify/replay receipt. The v1 Task 01 baseline also passed
  independently before the later cached-native denial. The v1 Task 03 native
  rerun for the conformance changes is still pending, so the native gate for
  changed paths remains open; no v1 release has occurred.
