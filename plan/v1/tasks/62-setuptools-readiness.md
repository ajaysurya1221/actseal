# Task 62 — bounded Setuptools lock maintenance

Owner: Codex (packaging dependency lock, planning and acceptance).
Authorized by the operator's 2 November 2026 repository-readiness plan.
Base: `12945e92f28d27a1984af7ee5bad1ae618f8c748`.

Update only the Setuptools lock record from 84.0.0 to 84.1.0, the first
patched version named by GHSA-xmj3-9gf7-h52w. Verify the upstream change,
exact non-yanked wheel/sdist hashes, metadata and license before accepting it.
Retain the Task61 bounded reachability assessment: the legacy wheel-to-egg
installation sink is absent from the configured Hatchling/uv build and
product code. This maintenance removes an affected optional dependency pin;
it does not assert a reproduced Actseal exploit. The upstream fix also
validates POSIX namespace paths, so Windows exclusion is not a general waiver.

Owned paths: `uv.lock`, `plan/v1/CHANGE_LOG.md`, this task and
`plan/v1/reviews/62-setuptools-readiness.md`. Preserve product code, tests,
schemas, direct/native pins, provider identity, frozen plans, prior receipts,
assets, releases and tags. No native inference, model downloads or live calls.

Done when: a one-package lock diff is reviewed; exact artifacts and license
are checked; frozen setup/lock, lint/format/types, hooks, ordinary tests,
build, packaging, fixture demo/replay and release-receipt gates pass.
Independent ACCEPT and green exact-head hosted CI are required before merge;
record main-tree and main-CI verification separately. Native startup/inference
remains unrun; do not reuse historical native success as fresh validation.
