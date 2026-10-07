<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 600px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-dark.svg">
  <img alt="Actseal wordmark with the tagline Test model-chosen actions. Replay the evidence. Beside it, one loop of three steps: freeze, run and replay. Caption: Replay cannot authenticate responses, prove inference occurred, or establish label truth." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-light.svg" width="100%">
</picture>

Actseal verifies model-chosen application actions for developers: freeze a policy, check its recorded decisions, and replay the evidence offline.

[![CI](https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml/badge.svg)](https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/actseal)](https://pypi.org/project/actseal/)
[![Python 3.12 and 3.13](https://img.shields.io/pypi/pyversions/actseal)](https://pypi.org/project/actseal/)
[![Apache-2.0 license](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/ajaysurya1221/actseal/blob/main/LICENSE)

<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 600px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-dark.svg">
  <img alt="How Actseal works in five stages. Freeze turns the frozen policy, labelled inputs and model identity into one lock. Run collects provider answers and six synthetic faults into decisions: ACT, ABSTAIN, ESCALATE or DENY. Verify applies the risk and coverage bounds and fault rules to one verdict with its exit code: PASS 0, BLOCK 1, INCONCLUSIVE 2 or ERROR 3. Seal writes one bounded evidence bundle. Replay recomputes the verdict offline with no model call." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-light.svg" width="100%">
</picture>

Run the packaged demonstration on macOS or Linux with
[uv](https://docs.astral.sh/uv/getting-started/installation/) installed. The
first command resolves the latest [Actseal release on PyPI](https://pypi.org/project/actseal/)
for Python 3.12; no source checkout, model or API key is needed, and
`./actseal-demo` must not already exist.

```bash
uvx --python 3.12 actseal demo --out ./actseal-demo
uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
```

The third command intentionally exits 1: replay faithfully reproduces the
deliberately bad run's BLOCK. Python and package installation time is
separate from the demo's own execution. The
[quickstart](https://github.com/ajaysurya1221/actseal/blob/main/docs/quickstart.md)
explains each output, the exit codes and how to pin one exact release.

**Guarantees**

- Complete scheduled-case and required fault evidence is checked.
- PASS requires the frozen risk/coverage bounds and fault rules to pass.
- Supported evidence is recomputed offline without calling a model.

**Limits**

- Hashes and replay cannot authenticate coherently rewritten responses.
- They cannot prove inference occurred or that labels are true.
- Population claims require the stated sampling assumptions; Actseal does not enforce application execution.

<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 600px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-dark.svg">
  <img alt="Actseal architecture in seven groups: the CLI and typed API; contracts and locks; providers; normalization and policy; assessment, statistics and faults; evidence; and replay. Replay reads the evidence bundle and never reaches a provider." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-light.svg" width="100%">
</picture>

| Read | What it covers |
|---|---|
| [Concepts](https://github.com/ajaysurya1221/actseal/blob/main/docs/concepts.md) | Frozen policy, selected-option probability, per-case decisions versus whole-run verdicts, evidence scope, one attempt |
| [CLI reference](https://github.com/ajaysurya1221/actseal/blob/main/docs/cli.md) and [Python guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/python-api.md) | Exact commands, exit codes, JSON receipts, public functions and runnable examples |
| [Stability manifest](https://github.com/ajaysurya1221/actseal/blob/main/docs/stability.md), [versioning](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md) and [migration](https://github.com/ajaysurya1221/actseal/blob/main/docs/migration.md) | The 1.x compatibility promise, what may change when, and the 0.1.0 evidence path |
| [Statistical contract](https://github.com/ajaysurya1221/actseal/blob/main/docs/statistical-contract.md) and [threat model](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md) | Bounds, verdict rules, sampling assumptions and the authenticity boundary |
| [Providers](https://github.com/ajaysurya1221/actseal/blob/main/docs/providers.md) and [FAQ](https://github.com/ajaysurya1221/actseal/blob/main/docs/faq.md) | Fixture and optional native Laya setup; answers to "why not PASS" |
| [Publishing](https://github.com/ajaysurya1221/actseal/blob/main/docs/publishing.md), [CHANGELOG](https://github.com/ajaysurya1221/actseal/blob/main/CHANGELOG.md), [release notes (draft until published)](https://github.com/ajaysurya1221/actseal/blob/main/plan/v1/RELEASE_NOTES.md) and [SECURITY](https://github.com/ajaysurya1221/actseal/blob/main/SECURITY.md) | Release pipeline and receipts, changes per version, the receipt-backed release notes, private vulnerability reporting and support |

## Read a result

An **ACT** is a per-case decision permitted by the frozen allowlist and the
selected-label probability threshold; it is not a statement that the answer is
correct. **Coverage** is ACT decisions over all scheduled cases and **risk** is
wrong ACT decisions over ACT decisions. A whole-run verdict bounds those rates:

| Exit | Verdict | Meaning |
|---|---|---|
| 0 | PASS | Valid evidence satisfies the frozen risk and coverage limits and the fault checks. |
| 1 | BLOCK | Valid evidence establishes a limit violation or a fault-check failure. |
| 2 | INCONCLUSIVE | Valid evidence proves neither PASS nor BLOCK. |
| 3 | ERROR | Invalid or incomplete evidence, a usage or setup failure, or an invalidated native-worker experiment. |

`lock` exits 0 on success. `demo` exits 0 only for its expected BLOCK/PASS
pair with matching replays; it never relabels the bad run. Every command
accepts `--json` for one versioned receipt.

## Scope

Actseal 1.x supports one categorical question with 2 to 16 labels, a frozen
action allowlist and threshold, recorded fixture responses and an optional
pinned native Laya CPU adapter. The runtime core depends only on the Python
standard library (3.12 or 3.13) on Linux and macOS; Windows is unsupported.
Replay never imports a provider. The packaged demonstration is synthetic
(`evidence_scope=demo`) and establishes no population or model-quality
result. Real interpretation requires independent cases and one prespecified
attempt under a fixed policy; do not retry until PASS.

Apache-2.0; see [LICENSE](https://github.com/ajaysurya1221/actseal/blob/main/LICENSE),
[NOTICE](https://github.com/ajaysurya1221/actseal/blob/main/NOTICE) and
[dependency notices](https://github.com/ajaysurya1221/actseal/blob/main/docs/dependencies.md).
Contributions: [CONTRIBUTING](https://github.com/ajaysurya1221/actseal/blob/main/CONTRIBUTING.md).
