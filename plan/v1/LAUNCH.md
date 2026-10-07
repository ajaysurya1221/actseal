# Actseal 1.0.0 launch draft

**DRAFT — not posted.** Publish only after Task 22 closes the publication
checklist (accepted media, green exact-head CI, the published GitHub release)
and an explicit request to send the post. The [final report](FINAL_REPORT.md)
and [release notes](RELEASE_NOTES.md) carry the receipts; this post adds no
claim they do not support.

## Proposed post

Actseal 1.0.0 turns a model-chosen application action into a contract you can
replay. Freeze the question, the allowed actions, the threshold, the labelled
cases and the model identity; collect the decisions once; check the
accepted-action risk and coverage bounds and six provider-failure rules; seal
one bounded evidence bundle; recompute the verdict offline with no model call.

1.0 is the first release with a documented 1.x contract: a stability manifest
for the CLI and typed Python surface, published JSON schemas for every wire
format and receipt, a reviewed compatibility registry for cross-release
replay, and an isolated path for 0.1.0 evidence that is never converted.

Try it with uv installed and no `./actseal-demo` directory:

```bash
uvx --python 3.12 actseal demo --out ./actseal-demo
uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
```

The third command exits 1 on purpose: replay faithfully reproduces the
deliberately bad run's BLOCK. The demo is synthetic evidence under a
prespecified policy, not a repaired model or a population result.

What it does not do: replay cannot authenticate responses, prove inference
occurred, or establish label truth, even with a trusted lock hash. The runtime
core has no third-party dependency and needs no key or service; an optional
pinned local Laya CPU adapter is supported on documented configurations, and
an experimental Jev cloud adapter ships behind an explicit opt-in with
mocked-transport tests only and no live evidence.

[Repository](https://github.com/ajaysurya1221/actseal) ·
[PyPI 1.0.0](https://pypi.org/project/actseal/1.0.0/) ·
[Release notes](RELEASE_NOTES.md) ·
[Verification and limitations](FINAL_REPORT.md)

Feedback sought: one application decision where a frozen policy, a complete
failure record and offline replay would make a deployment review easier.

## Not to be added before posting

No GitHub release link until the draft is published; no recording link until
the Task 14 activation is accepted; no live Jev result, performance number or
adoption claim.
