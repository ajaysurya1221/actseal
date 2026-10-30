# Task 61 — CA-bundle dependency readiness

Owner: Codex (packaging dependency lock and acceptance). Authorized 30 October
2026 as follow-up to the final readiness pass, after PR78 merged.

Base: `18471d69e1bbdabb40a5c11496462e8c9e350724`. Upgrade only the Certifi
record from 2026.7.22 to the minimum upstream-recommended 2026.10.19, with
hash-verified, non-yanked artifacts and unchanged MPL-2.0 license terms.
The advisory's range first excludes 2026.10.18, but its recommendation and
PyPI metadata require 2026.10.19, which restores unaffected CA roots.

Owned paths: `uv.lock`, `plan/v1/CHANGE_LOG.md`, this task and
`plan/v1/reviews/61-certifi-readiness.md`. Preserve all product source, tests,
direct/native pins, contracts, historical receipts, assets and releases.
No model calls, native inference, TLS interception, release or alert dismissal.

Review Certifi's path through the optional Hub/HTTPX download stack. Verify
artifact hashes, metadata/license and offline CA parsing; ordinary checks do
not establish native startup, inference or live TLS compatibility. Re-run frozen
setup/lock, hooks, ordinary tests, build, packaging, fixture demo/replay and
receipt/docs gates. Require independent ACCEPT, exact-head hosted CI before
merge, and separate verification of the resulting main tree and main CI.

Also record Setuptools alert15 accurately. Its upstream fix covers POSIX as
well as Windows; Windows exclusion alone is not a valid waiver. The affected
legacy `setup_requires` / `Wheel.install_as_egg` path is absent from Actseal's
configured Hatchling/PEP517 uv build and product source. Retain this bounded
non-actionability decision with its prerequisite, without claiming all possible
consumer workflows safe. No Setuptools upgrade is included without a separate
need arising from review.

Local gates and independent acceptance are recorded in
[review 61](../reviews/61-certifi-readiness.md). Exact-head hosted and merge
results belong to the PR and do not inherit PR78's earlier checks.
