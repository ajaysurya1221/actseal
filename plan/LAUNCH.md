# Actseal launch draft

**DRAFT / NOT FOR PUBLICATION — 6 October 2026.** Prepared for plan/LAUNCH.md.
Tasks T00–T50 are accepted; T50 `286ae67` merged as `7e696c5`. Root also executed
the native CLI at `434c682`, preserving its BLOCK result. T60 and final
publication gates remain pending; the public wheel URL is not yet available.
Public posting requires a separate explicit instruction. Relative links target
the eventual plan/LAUNCH.md location.

## Proposed post

I'm building Actseal for developers whose applications turn categorical model
answers into actions. It freezes the policy and labelled cases, checks
accepted-action error and coverage, exercises six provider-failure scenarios,
and saves evidence that can be replayed without calling the model.

The accepted T50 installed-wheel candidate demonstrates the **same policy against
two sets of authored support-triage answers**. One has 32 wrong accepted answers
out of 128 and produces BLOCK. The other has zero out of 128 and produces PASS.
Both evidence bundles replay to their original verdicts. These are two synthetic
fixture runs, not a trained or repaired model and not a population benchmark.
INCONCLUSIVE remains a separate outcome when valid evidence is insufficient.

The Python core requires no model library, key or hosted service. A separate
native Laya CLI check on those synthetic inputs ABSTAINed on all 128 cases at
the frozen threshold and BLOCKed for low coverage. Replay preserved that result;
no policy tuning or retry turned it into PASS. That checks the integration,
not population performance. The statistical interpretation requires independent
case outcomes over one fixed, prespecified attempt; it does not certify worker
uptime or completion probability.

Replay makes policy evidence inspectable. Even a trusted lock cannot authenticate
rewritten responses under that same lock or prove inference, labels or sampling
history. Actseal does not enforce another application's actions.

Repository: [ajaysurya1221/actseal](https://github.com/ajaysurya1221/actseal).
The verified v0.1.0 release link and final installed-wheel quickstart are pending.

## Candidate receipt for editorial review

Root's 6 October corrected installed-wheel receipt records the following actual
results, accepted in [REVIEW T50-02](reviews/T50-02.md) at
`286ae67e252ecbb77e9c330ebe1f66cc375bfbab`, merged as `7e696c5`. These remain
**candidate evidence only**; do not silently promote them to the final release
artifact or add a cold-download performance claim.

| Observation | Bad authored answers | Fixed authored answers |
|---|---|---|
| Verdict | BLOCK | PASS |
| ACT / scheduled | 128 / 128 | 128 / 128 |
| Wrong ACT / ACT | 32 / 128 | 0 / 128 |
| Risk interval | [0.1687604663492846, 0.346264539835876] | [0.0, 0.033655210093607835] |
| Coverage interval | [0.9663447899063922, 1.0] | [0.9663447899063922, 1.0] |
| Fresh module replay | BLOCK / exit 1 | PASS / exit 0 |

The installed console demo exited 0. Root measured wall time **0.170645 seconds**
after a separately measured **0.046136-second cached environment/install step**.
This is one candidate fixture execution, not an inference, general-hardware or
fresh GitHub-download benchmark. Preserve the final platform/runtime and setup
boundary when replacing it with the final release receipt.

Internal receipt: `plan/local-receipts/T50-02-installed.json` (not a public release
artifact). Recorded candidate base: `3e51ca2dacd5e05d96768208710c7fdb3ce118f0`;
this is a base reference, not an assertion that all candidate changes were
committed at that SHA. Actual tested wheel SHA-256:
`b3633a3a0d2977d1250b0cf3a4e0078903744ec181d977ccce82013f85ad6128`.

The separate native CLI receipt at
`434c682352d19e64c6349cb5a7aac44fa7554156` used macOS 26.6.2 arm64,
Python 3.12.13, uv 0.12.5, the pinned cached model and both offline library flags.
Lock exited 0 in 6.445306 s; verify returned BLOCK/1 in 13.820518 s; replay returned
the same BLOCK/1 in 0.092522 s. All 128 outcomes were ABSTAIN, with no provider
failures, risk [0, 1] and coverage [0, 0.033655210093607835]. Reasons:
`coverage.below_minimum` and `risk.no_accepted_cases`. All six faults matched;
warning counts were 128 retained calibration warnings and 27 renormalizations.
There was one fixed attempt with no tuning or retry. Risk is unestimated when
ACT count is zero; the result is not zero-error model performance.

Native implementation fingerprint:
`cd3a0976cf7886616f1fdf565c914f30d0c82cac530e7b9ffc4119e3a90300a7`.
Native lock:
`9abbd4b0ef47bb05efff1df1d4d5deb974b40ee72be49b6afe806665367d4267`.
Internal receipt: `plan/local-receipts/T70-native-434c682/receipt.json`.
These elapsed times exclude prior model/runtime preparation and are not general
latency claims. Final release identity, T60 and publication remain pending.

## Required edits before publication

- Complete the [release checklist](RELEASE_CHECKLIST.md), including T60,
  final required CI and artifact audit. Preserve T50/native receipts and verify
  their applicability if source/runtime identity changes.
- Replace candidate language only with the corresponding accepted final receipts.
  Add the verified release URL and public-wheel command after checking that exact
  asset. Keep runtime/package preparation separate from measured fixture execution.
- Recheck the post against the [final report](FINAL_REPORT.md),
  [ADR0009](../docs/decisions/0009-worker-loss-invalidates-statistical-run.md) and
  [ADR0013](../docs/decisions/0013-prespecified-synthetic-demo.md). Keep the two-run,
  same-policy distinction; do not add model-repair, calibrated-checkpoint,
  production-reliability, adoption, security-sandbox or quantitative “10×” claims.
- Keep this document a draft until the user explicitly requests posting. A GitHub
  release does not authorize a social or community message.
