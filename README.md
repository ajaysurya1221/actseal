# Actseal

**Test a model's action policy. Replay the evidence.**

A ticket router needs rules for when to act, abstain, escalate or deny.
Actseal measures accepted-action errors and coverage under a frozen policy.

**Recorded Jev audit: INCONCLUSIVE.**
580 of 639 verification cases received ACT; 24 disagreed with benchmark labels.
Fixed benchmark; unreleased producer. [Audit and offline replay](https://github.com/ajaysurya1221/actseal/blob/main/docs/results/jev-audit-2026-10-08/README.md)

**Boundary:** the application owns execution.
Replay checks consistency; it does not authenticate responses or prove label truth.

**Engineering:** [20 ADRs](https://github.com/ajaysurya1221/actseal/tree/main/docs/decisions) · [11 JSON Schemas](https://github.com/ajaysurya1221/actseal/blob/main/docs/schemas/README.md)
[Mutation harness](https://github.com/ajaysurya1221/actseal/blob/main/tools/check_mutations.py) · [1.0.0 release receipt](https://github.com/ajaysurya1221/actseal/blob/main/plan/v1/receipts/postpublish-receipt.json)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-dark.svg">
  <img alt="Actseal evidence card. Does this frozen action policy meet its declared risk and coverage limits? Freeze the policy, run it once against labelled cases, bound the errors among accepted actions, seal the evidence, replay it with no model call. Preregistered live audit, 639 verification cases, threshold 0.80: ACT 580 of 639, 24 errors; fixed benchmark, unreleased producer; risk [0.0250, 0.0639] against a limit of 0.05; coverage [0.879, 0.932]; verdict INCONCLUSIVE (exit 2); replay requires archived producer d3edbab. Source: docs/results/jev-audit-2026-10-08. Neither PASS nor BLOCK is claimed." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/hero-light.svg" width="100%">
</picture>

[![CI](https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml/badge.svg)](https://github.com/ajaysurya1221/actseal/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/actseal)](https://pypi.org/project/actseal/)
[![Python 3.12 and 3.13](https://img.shields.io/pypi/pyversions/actseal)](https://pypi.org/project/actseal/)
[![Apache-2.0 license](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/ajaysurya1221/actseal/blob/main/LICENSE)

## Try it

Synthetic demo. macOS/Linux + uv; use a new `./actseal-demo` directory.
```bash
uvx --python 3.12 actseal demo --out ./actseal-demo
uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
```

No model or API key is needed; [install uv](https://docs.astral.sh/uv/getting-started/installation/) first. The first command downloads the package if needed. Expected result from synthetic fixtures, showing selected output:

```text
[bad] expected BLOCK, observed BLOCK, replay BLOCK (match)
[fixed] expected PASS, observed PASS, replay PASS (match)
result: success
```

Demo exit: `0`. Fixed replay: `PASS` / `0`. Bad replay: `BLOCK` / `1`.
The third command intentionally exits 1. These fixtures demonstrate the workflow; they do not measure a live model.

[Use it in an application](https://github.com/ajaysurya1221/actseal/blob/main/examples/action_gate/README.md) · [Read the limits](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md) · [Quickstart](https://github.com/ajaysurya1221/actseal/blob/main/docs/quickstart.md)

## Use it in an application

> **[Before enabling automatic ticket routing](https://github.com/ajaysurya1221/actseal/blob/main/examples/action_gate/README.md)**
>
> Run the committed action-gate example to see the application boundary. It verifies a frozen policy, replays the recorded evidence, and routes authored tickets. Only ACT permits the example application’s local queue write; ABSTAIN, ESCALATE and DENY take non-execution paths.
>
> From a development checkout, run `uv run --frozen python examples/action_gate/run.py --check`.
>
> This is a synthetic integration example. The application owns execution; the result is not evidence of deployment performance.

The [action-gate example](https://github.com/ajaysurya1221/actseal/blob/main/examples/action_gate/README.md)
shows where Actseal sits in an application's control flow and draws that flow
from the ticket to the four decisions. A small ticket-routing application calls
the evaluator for every incoming ticket and executes its one action, a local
queue write, only when the decision is `ACT`. Actseal verifies the frozen policy
offline and replays the evidence; it does not execute, intercept or enforce the
application's action. The example uses authored synthetic data
(`evidence_scope=demo`) and runs without a key, model download or network.

## How it works

**Frozen policy. Measured risk and coverage. Offline replay.**

A model can choose the right label often and still act on the wrong cases. Actseal checks a frozen action policy against labelled cases, bounds errors among accepted actions and coverage across all scheduled cases, and saves evidence for offline replay.

Five stages: **Freeze** turns the frozen policy, labelled inputs and model
identity into one lock. **Run** collects provider answers and six synthetic
faults into decisions: ACT, ABSTAIN, ESCALATE or DENY. **Verify** applies the
risk and coverage bounds and fault rules to one verdict with its exit code.
**Seal** writes one bounded evidence bundle. **Replay** recomputes the verdict
offline with no model call. The stages are drawn in the
[how-it-works figure](https://github.com/ajaysurya1221/actseal/blob/main/docs/assets/how-it-works-light.svg)
([dark version](https://github.com/ajaysurya1221/actseal/blob/main/docs/assets/how-it-works-dark.svg)).

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
The released 1.0.0 adapter's accepted evidence uses mocked transports; the separate audit below used an unreleased benchmark producer.

A preregistered audit of Jev on a fixed 16-intent Banking77 subset returned INCONCLUSIVE: 580/639 verification cases received ACT, with 24 accepted errors. The complete [evidence and offline verification instructions](https://github.com/ajaysurya1221/actseal/blob/main/docs/results/jev-audit-2026-10-08/README.md) are published with the unreleased benchmark producer snapshot identified explicitly.
Its offline replay runs with that archived snapshot and exits 2 (INCONCLUSIVE); the published 1.0.0 package returns ERROR `integrity.lock` for this bundle because that producer is not in the compatibility registry.

Replay never imports a provider, and the packaged demonstration establishes no
population or model-quality result. The
[statistical contract](https://github.com/ajaysurya1221/actseal/blob/main/docs/statistical-contract.md)
states the bounds and sampling assumptions,
[providers](https://github.com/ajaysurya1221/actseal/blob/main/docs/providers.md)
the provider support, and the
[threat model](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md)
the authenticity boundary.

## Architecture

Seven groups: the CLI and typed API; contracts and locks; providers;
normalization and policy; assessment, statistics and faults; evidence; and
replay. Replay reads the evidence bundle and never reaches a provider. The
[architecture figure](https://github.com/ajaysurya1221/actseal/blob/main/docs/assets/architecture-light.svg)
([dark version](https://github.com/ajaysurya1221/actseal/blob/main/docs/assets/architecture-dark.svg))
names the `actseal` modules in each group.

## Watch the recorded demo

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/demo-dark.gif">
  <img alt="Terminal recording of the three quickstart commands run against the public PyPI actseal 1.0.0 release. The demo prints BLOCK for the bad run and PASS for the fixed run and exits 0; the fixed replay prints PASS and exits 0; the bad replay prints BLOCK with the reason risk.exceeds_limit and exits 1." src="https://raw.githubusercontent.com/ajaysurya1221/actseal/main/docs/assets/demo-light.gif" width="100%">
</picture>

This is an unedited capture of the three commands above against the
published 1.0.0 wheel, rendered from the raw cast with the pinned
authoring toolchain at speed 1; it shows the expected exits 0, 0 and 1. It
was recorded after the v1.0.0 publication and is absent from the immutable
v1.0.0 tag and that version's PyPI description. The recording illustrates the demo; it is not
authenticated model evidence.

## Documentation

| Read | What it covers |
|---|---|
| [Concepts](https://github.com/ajaysurya1221/actseal/blob/main/docs/concepts.md) | Frozen policy, selected-option probability, per-case decisions versus whole-run verdicts, evidence scope, one attempt |
| [CLI reference](https://github.com/ajaysurya1221/actseal/blob/main/docs/cli.md) and [Python guide](https://github.com/ajaysurya1221/actseal/blob/main/docs/python-api.md) | Exact commands, exit codes, JSON receipts, public functions and runnable examples |
| [Stability manifest](https://github.com/ajaysurya1221/actseal/blob/main/docs/stability.md), [versioning](https://github.com/ajaysurya1221/actseal/blob/main/docs/versioning.md) and [migration](https://github.com/ajaysurya1221/actseal/blob/main/docs/migration.md) | The 1.x compatibility promise, what may change when, and the 0.1.0 evidence path |
| [Statistical contract](https://github.com/ajaysurya1221/actseal/blob/main/docs/statistical-contract.md) and [threat model](https://github.com/ajaysurya1221/actseal/blob/main/docs/threat-model.md) | Bounds, verdict rules, sampling assumptions and the authenticity boundary |
| [Providers](https://github.com/ajaysurya1221/actseal/blob/main/docs/providers.md) and [FAQ](https://github.com/ajaysurya1221/actseal/blob/main/docs/faq.md) | Fixture and optional native Laya setup; the PROVISIONAL experimental Jev cloud adapter behind `--provider jev --experimental-provider` (bring your own key, mocked-transport evidence for released 1.0.0; separate benchmark audit above); answers to "why not PASS" |
| [Publishing](https://github.com/ajaysurya1221/actseal/blob/main/docs/publishing.md), [CHANGELOG](https://github.com/ajaysurya1221/actseal/blob/main/CHANGELOG.md), [release notes](https://github.com/ajaysurya1221/actseal/blob/main/plan/v1/RELEASE_NOTES.md) and [SECURITY](https://github.com/ajaysurya1221/actseal/blob/main/SECURITY.md) | Release pipeline and receipts, changes per version, the receipt-backed release notes, private vulnerability reporting and support |

## Related projects

Actseal is part of a set of tools for independent testing and evidence for agent controls. [ARCI](https://github.com/ajaysurya1221/agent-reliability-ci) gates repeated-trial agent regressions, injects faults and reduces failing fault sets; Actseal checks a frozen categorical policy’s accepted-action risk and coverage, with application-owned actions and offline replay. [Frontier Scout](https://github.com/ajaysurya1221/frontier-scout) compiles policies and verifies PR scope, [Dorian](https://github.com/ajaysurya1221/dorian) checks claim warrants, and [Evalopt Graph](https://github.com/ajaysurya1221/evalopt-graph) evaluates acceptance policies against supplied evidence.

## Development

The [mutation harness](https://github.com/ajaysurya1221/actseal/blob/main/tools/check_mutations.py)
applies eight prescribed changes to temporary copies of the gate: a wider
per-tail error allocation, the accepted count as the coverage denominator, a
zero-width risk interval when nothing is accepted, a threshold tie that
abstains, PASS read from the wrong risk bound or the wrong coverage bound,
faults that never block, and integrity errors outranked by a fault. A mutant
counts as killed only when every designated test fails with an assertion
error; import, setup or timeout failures invalidate the mutant instead.

Maintained by Ajay Surya Senthilrajan, with AI pair-programming recorded in commit trailers. See the tests, design records and release evidence linked here.

## License and contributing

Apache-2.0; see [LICENSE](https://github.com/ajaysurya1221/actseal/blob/main/LICENSE),
[NOTICE](https://github.com/ajaysurya1221/actseal/blob/main/NOTICE) and
[dependency notices](https://github.com/ajaysurya1221/actseal/blob/main/docs/dependencies.md).
Contributions: [CONTRIBUTING](https://github.com/ajaysurya1221/actseal/blob/main/CONTRIBUTING.md).
