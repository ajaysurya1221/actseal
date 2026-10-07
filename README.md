<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 1279px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-mobile-dark.svg">
  <source media="(max-width: 1279px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-dark.svg">
  <img alt="Actseal. Test model-chosen actions. Replay the evidence. Three steps: freeze, run, replay." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-light.svg" width="100%">
</picture>

**Frozen policy. Measured risk and coverage. Offline replay.**

A model can choose the right label often and still act on the wrong cases. Actseal checks a frozen action policy against labelled cases, bounds errors among accepted actions and coverage across all scheduled cases, and saves evidence for offline replay.

[![CI](https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml/badge.svg)](https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/actseal)](https://pypi.org/project/actseal/)
[![Python 3.12 and 3.13](https://img.shields.io/pypi/pyversions/actseal)](https://pypi.org/project/actseal/)
[![Apache-2.0 license](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/ajaysurya1221/actseal/blob/main/LICENSE)

## Try it

On macOS or Linux, with [uv](https://docs.astral.sh/uv/getting-started/installation/) installed. No model or API key is needed.
`./actseal-demo` must be a new directory. The first command downloads the package if needed.

```bash
uvx --python 3.12 actseal demo --out ./actseal-demo
uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
```

Expected result from synthetic fixtures, showing selected output:

```text
[bad] expected BLOCK, observed BLOCK, replay BLOCK (match)
[fixed] expected PASS, observed PASS, replay PASS (match)
result: success
```

Demo exit: `0`. Fixed replay: `PASS` / `0`. Bad replay: `BLOCK` / `1`.
The third command intentionally exits 1. These fixtures demonstrate the workflow; they do not measure a live model.

[Use it in an application](https://github.com/ajaysurya1221/actseal/blob/main/examples/action_gate/README.md) · [Read the limits](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md) · [Quickstart](https://github.com/ajaysurya1221/actseal/blob/main/docs/quickstart.md)

## Use it in an application

The [action-gate example](https://github.com/ajaysurya1221/actseal/blob/main/examples/action_gate/README.md)
shows where Actseal sits in an application's control flow. A small
ticket-routing application calls the evaluator for every incoming ticket and
executes its one action, a local queue write, only when the decision is `ACT`;
`ABSTAIN`, `ESCALATE` and `DENY` take explicit non-execution paths. Actseal
verifies the frozen policy offline and replays the evidence; it does not
execute, intercept or enforce the application's action. The example uses
authored synthetic data (`evidence_scope=demo`) and runs without a key, model
download or network.

## How it works

<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 1279px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-mobile-dark.svg">
  <source media="(max-width: 1279px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-dark.svg">
  <img alt="How Actseal works in five stages. Freeze turns the frozen policy, labelled inputs and model identity into one lock. Run collects provider answers and six synthetic faults into decisions: ACT, ABSTAIN, ESCALATE or DENY. Verify applies the risk and coverage bounds and fault rules to one verdict with its exit code: PASS 0, BLOCK 1, INCONCLUSIVE 2 or ERROR 3. Seal writes one bounded evidence bundle. Replay recomputes the verdict offline with no model call." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/how-it-works-light.svg" width="100%">
</picture>

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

## Guarantees and limits

**Guarantees**

- Complete scheduled-case and required fault evidence is checked.
- PASS requires the frozen risk/coverage bounds and fault rules to pass.
- Supported evidence is recomputed offline without calling a model.

**Limits**

- Hashes and replay cannot authenticate coherently rewritten responses.
- They cannot prove inference occurred or that labels are true.
- Population claims require the stated sampling assumptions; Actseal does not enforce application execution.

ACT is a per-case policy decision, not a claim that its label is correct.
The application owns execution. Actseal is not an OS sandbox or permission firewall.
An externally trusted lock digest anchors policy identity; it does not authenticate responses.

Actseal supports one categorical question with 2–16 labels and a frozen allowlist
and threshold. The runtime core uses only the Python standard library on Python
3.12 and 3.13, macOS and Linux. Windows is unsupported. Native Laya support is
limited to the documented tested CPU configurations.

The packaged demo and action-gate example are synthetic (`evidence_scope=demo`).
Population interpretation requires independent cases and one prespecified attempt
under a fixed policy. Do not retry until PASS.

The Jev adapter is PROVISIONAL and requires explicit opt-in:
`--provider jev --experimental-provider`. It has no 1.x compatibility promise.
Its current accepted evidence uses mocked transports; no live audit result is accepted.

Replay never imports a provider, and the packaged demonstration establishes no
population or model-quality result. The
[statistical contract](https://github.com/ajaysurya1221/actseal/blob/main/docs/statistical-contract.md)
states the bounds and sampling assumptions,
[providers](https://github.com/ajaysurya1221/actseal/blob/main/docs/providers.md)
the provider support, and the
[threat model](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md)
the authenticity boundary.

## Architecture

<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 1279px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-mobile-dark.svg">
  <source media="(max-width: 1279px)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-dark.svg">
  <img alt="Actseal architecture in seven groups: the CLI and typed API; contracts and locks; providers; normalization and policy; assessment, statistics and faults; evidence; and replay. Replay reads the evidence bundle and never reaches a provider." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/architecture-light.svg" width="100%">
</picture>

## Watch the recorded demo

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/demo-dark.gif">
  <img alt="Terminal recording of the three quickstart commands run against the public PyPI actseal 1.0.0 release. The demo prints BLOCK for the bad run and PASS for the fixed run and exits 0; the fixed replay prints PASS and exits 0; the bad replay prints BLOCK with the reason risk.exceeds_limit and exits 1." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/demo-light.gif" width="100%">
</picture>

This is an unedited capture of the three commands above against the
published 1.0.0 wheel, rendered from the raw cast with the pinned
authoring toolchain at speed 1; it shows the expected exits 0, 0 and 1. It
was recorded after publication, so the tagged source and the package page
on PyPI do not contain it. The recording illustrates the demo; it is not
authenticated model evidence.

## Documentation

| Read | What it covers |
|---|---|
| [Concepts](https://github.com/ajaysurya1221/actseal/blob/main/docs/concepts.md) | Frozen policy, selected-option probability, per-case decisions versus whole-run verdicts, evidence scope, one attempt |
| [CLI reference](https://github.com/ajaysurya1221/actseal/blob/main/docs/cli.md) and [Python guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/python-api.md) | Exact commands, exit codes, JSON receipts, public functions and runnable examples |
| [Stability manifest](https://github.com/ajaysurya1221/actseal/blob/main/docs/stability.md), [versioning](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md) and [migration](https://github.com/ajaysurya1221/actseal/blob/main/docs/migration.md) | The 1.x compatibility promise, what may change when, and the 0.1.0 evidence path |
| [Statistical contract](https://github.com/ajaysurya1221/actseal/blob/main/docs/statistical-contract.md) and [threat model](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md) | Bounds, verdict rules, sampling assumptions and the authenticity boundary |
| [Providers](https://github.com/ajaysurya1221/actseal/blob/main/docs/providers.md) and [FAQ](https://github.com/ajaysurya1221/actseal/blob/main/docs/faq.md) | Fixture and optional native Laya setup; the PROVISIONAL experimental Jev cloud adapter behind `--provider jev --experimental-provider` (bring your own key, mocked-transport tests only, no accepted live receipt); answers to "why not PASS" |
| [Publishing](https://github.com/ajaysurya1221/actseal/blob/main/docs/publishing.md), [CHANGELOG](https://github.com/ajaysurya1221/actseal/blob/main/CHANGELOG.md), [release notes](https://github.com/ajaysurya1221/actseal/blob/main/plan/v1/RELEASE_NOTES.md) and [SECURITY](https://github.com/ajaysurya1221/actseal/blob/main/SECURITY.md) | Release pipeline and receipts, changes per version, the receipt-backed release notes, private vulnerability reporting and support |

## Related projects

Actseal is part of a set of tools for independent testing and evidence for agent controls. [ARCI](https://github.com/ajaysurya1221/agent-reliability-ci) gates repeated-trial agent regressions, injects faults and reduces failing fault sets; Actseal checks a frozen categorical policy’s accepted-action risk and coverage, with application-owned actions and offline replay. [Frontier Scout](https://github.com/ajaysurya1221/frontier-scout) compiles policies and verifies PR scope, [Dorian](https://github.com/ajaysurya1221/dorian) checks claim warrants, and [Evalopt Graph](https://github.com/ajaysurya1221/evalopt-graph) evaluates acceptance policies against supplied evidence.

## License and contributing

Apache-2.0; see [LICENSE](https://github.com/ajaysurya1221/actseal/blob/main/LICENSE),
[NOTICE](https://github.com/ajaysurya1221/actseal/blob/main/NOTICE) and
[dependency notices](https://github.com/ajaysurya1221/actseal/blob/main/docs/dependencies.md).
Contributions: [CONTRIBUTING](https://github.com/ajaysurya1221/actseal/blob/main/CONTRIBUTING.md).
