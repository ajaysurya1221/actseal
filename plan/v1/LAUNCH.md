# Actseal 1.0.0 launch draft

**DRAFT — not posted.** The release is public (PyPI and the GitHub release
below); send this post only on an explicit request. The
[final report](FINAL_REPORT.md) and [release notes](RELEASE_NOTES.md) carry
the receipts; this post adds no claim they do not support.

## Proposed post

Actseal 1.0.0 turns a model-chosen application action into a contract you can
replay. Freeze the question, the allowed actions, the threshold, the labelled
cases and the model identity; collect the decisions once; check the
accepted-action risk and coverage bounds and six provider-failure rules; seal
one bounded evidence bundle; recompute the verdict offline with no model call.

1.0 is the first release with a documented 1.x contract: a stability manifest
for the CLI and typed Python surface, published JSON Schemas for the lock,
evidence-bundle, CLI-receipt and release-receipt formats (the TOML contract
is specified separately), a reviewed compatibility registry for
cross-release replay, and an isolated path for 0.1.0 evidence that is never
converted.

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
[v1.0.0 release](https://github.com/ajaysurya1221/actseal/releases/tag/v1.0.0) ·
[Release notes](RELEASE_NOTES.md) ·
[Verification and limitations](FINAL_REPORT.md)

Feedback sought: one application decision where a frozen policy, a complete
failure record and offline replay would make a deployment review easier.

## Not to be added before posting

No live Jev result, performance number or adoption claim. The recorded demo
is on the repository README and may be linked from there; it is an
illustrative receipt, not model evidence.
