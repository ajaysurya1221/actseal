# Actseal launch draft

**DRAFT / NOT FOR PUBLICATION — 6 October 2026.** v0.1.0 is not complete. T00 foundation is accepted; the product lanes are in progress. The text below describes release targets, not verified shipped capabilities. Keep this marker until the [release evidence checklist](RELEASE_CHECKLIST.md) is complete and Codex reviews the final wording. Public posting requires its own explicit instruction.

## Proposed post

I'm building Actseal for developers who need to decide when a categorical model output may trigger an application action.

The v0.1.0 target is a small Python tool that freezes a decision policy, its labelled verification cases and model identity, then checks accepted-action error and coverage against declared limits. The release is intended to include six deterministic provider-failure scenarios and a data-only evidence bundle that can be re-evaluated offline.

The planned first demo uses authored support-routing fixtures: an intentionally bad policy should produce BLOCK, a sufficient corrected fixture should produce PASS, and insufficient evidence should remain INCONCLUSIVE. Actual outputs and a timed, installed-wheel quickstart will replace this description only after the release checks pass.

The core is intended to run without model libraries, keys or a hosted service, with a separately tested optional local Laya CPU adapter. The statistical claim concerns independent case outcomes under one fixed, prespecified attempt. It makes no claim about persistent-worker uptime or run-completion probability. Worker loss must invalidate the statistical run; retrying until PASS is outside the protocol.

Actseal's evidence is intended to make a specific policy decision inspectable. It cannot prove label truth, authenticate wholly rewritten evidence or enforce an application's actions. The synthetic demo will not establish production reliability.

Repository: [ajaysurya1221/actseal](https://github.com/ajaysurya1221/actseal). The release link, demonstrated result and final quickstart remain pending verification.

## Required edits before publication

- Replace future-tense capability statements only where the release candidate has a corresponding ACCEPT review, green required CI and executed receipt.
- Add the verified v0.1.0 release link and exact installed-wheel quickstart; include only measured demo results and timing with prerequisites/platform stated.
- Recheck the wording against [ADR 0009](../docs/decisions/0009-worker-loss-invalidates-statistical-run.md), the statistical/trust docs and the final shipped scope. Do not add uptime, completion-probability, calibrated-checkpoint, security-sandbox, adoption or quantitative “10×” claims.
- Preserve this as a draft until the user explicitly requests public posting. Preparing a GitHub release does not authorize a social or community message.
