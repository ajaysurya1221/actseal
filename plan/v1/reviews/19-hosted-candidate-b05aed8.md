# REVIEW 19 — hosted integration candidate

Verdict: **REVISE / release blocked** at `b05aed85ccba6efee204a79c4662643ce952c6d2`.

Codex read the completed push and pull-request CI results and all failed-test summary lines on 7 October 2026, approximately 12:06 IST. Runs [37581583411](https://github.com/ajaysurya1221/actseal/actions/runs/37581583411) and [37581585915](https://github.com/ajaysurya1221/actseal/actions/runs/37581585915) both report that head. All ten matrix/asset jobs failed. Lint and strict typing passed in every source-matrix job.

The only reported failed test identities across these jobs are:

- `tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset`
- `tests/visual/test_how_it_works.py::test_committed_assets_match_regeneration_in_this_checkout`

Both failures identify the same absent architecture outputs: `architecture-light.svg`, `architecture-dark.svg`, `architecture-mobile-light.svg`, and `architecture-mobile-dark.svg`. The assets jobs include only the second test. The previous stale provider-version assertion no longer fails at this head.

Each Linux matrix job reports 2 failed, 3,983 passed, 13 skipped, and 31 deselected. Each macOS matrix job reports 2 failed, 3,984 passed, 12 skipped, and 31 deselected. Each assets job reports 1 failed and 322 passed. These are failing hosted runs, not full-suite passes. Packaging, evidence reproduction, and repository-hook steps after the failed test step were skipped; their success cannot be inferred from this run. No test was excluded or weakened to turn this candidate green.

Required change: complete and independently accept Task13, including real generated outputs, module mapping, pixel review, and clean regeneration, then rerun exact-head full CI. Task13's local merge was separately denied by automatic approval review as Untrusted Code Integration. The separate human approval remains unanswered; no retry or alternate route is authorized by this review.

Other final gates remain: truthful final documentation/provider scope, exact-artifact release rehearsal, final visual acceptance, tag/publication, post-PyPI verification, genuine recording, and final receipts. Main remains `ae43065aeaedf84d589a1a7ac8293e84e7de2666`; no v1 tag or publication occurred.
