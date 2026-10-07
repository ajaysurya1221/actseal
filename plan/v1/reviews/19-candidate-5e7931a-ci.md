# REVIEW 19 — candidate hosted CI checkpoint

Observed 7 October 2026, approximately 13:36 IST.
Reviewed head: `5e7931a1ec8b0197d87ddc1e01a0835e011b470f`.
Verdict: REVISE / mandatory architecture incomplete; no main merge.

Both exact-head hosted runs completed with all five jobs failed in each:

- https://github.com/ajaysurya1221/actseal/actions/runs/37590464434
- https://github.com/ajaysurya1221/actseal/actions/runs/37590468512

Independent full-log review found only these two failing test identities:
`test_every_image_resolves_to_a_committed_implemented_asset` and
`test_committed_assets_match_regeneration_in_this_checkout`. Both identify the
same four missing architecture SVGs. No other test failure was found.

For each run, Linux 3.12/3.13 jobs report 2 failed, 4,086 passed, 13 skipped,
31 deselected; macOS 3.12/3.13 report 2 failed, 4,087 passed, 12 skipped,
31 deselected. The assets job reports 1 failed, 425 passed. Lint and typing pass.
Downstream build, packaging, evidence reproduction, hooks, authoring-tool setup,
agg probe and final asset validation were skipped, not independently established
by these runs. Prior component receipts remain separate evidence.

Required changes: deliver and review the four real architecture outputs, then
run the unchanged full gates at the new exact head. Any timed optional scope cut
requires its own source/compatibility review and does not waive this failure.
Follow-ups: Task13 remains blocked by the effective harness denial; the manual
Terminal request is pending. No additional automatic attempt is authorized.

Read-only publication preflight at approximately13:45IST confirms the existing
`pypi` environment has required reviewer `ajaysurya1221`, self-review allowed,
and custom deployment policies for branch `main` and tags `v*`. No settings
were changed. This confirms configuration only; no deployment is waiting and
no release/publication acceptance follows. Recheck at the actual release gate.
