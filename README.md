# Actseal

**Decision contracts you can replay.**

If your application uses a model to choose an action, a confidence score alone
does not tell you when that action is justified. Actseal freezes your policy,
checks its errors and coverage on labelled cases, exercises provider failures,
and saves evidence that you can replay without the model.

## Try the packaged demo

With [uv](https://docs.astral.sh/uv/getting-started/installation/) installed, run
this on macOS or Linux. It selects Python 3.12 and installs
[Actseal from PyPI](https://pypi.org/project/actseal/0.1.0/) in uv's tool environment;
no source checkout, model or API key is needed.

```bash
uvx --python 3.12 --from actseal==0.1.0 actseal demo --out ./actseal-demo
```

Choose an output directory that does **not** already exist. Its parent must
exist; Actseal refuses to overwrite an existing destination. Use a different
directory name for another demo run.

The demo evaluates the same policy against two authored sets of answers. The
independently tested wheel produced **bad: BLOCK**, **fixed: PASS**, with both freshly replayed.
The overall demo exits 0 only when those conditions hold. Here “fixed” names the
fixture whose authored answers match the labels; no model was trained or repaired.

```text
actseal-demo/
  inputs/          # copied contracts, labelled cases and recorded answers
  bad/lock.json
  bad/evidence/    # deliberately wrong authored answers
  fixed/lock.json
  fixed/evidence/  # authored answers that match the labels
```

| Authored demo | Verdict | Accepted actions | Wrong actions |
|---|---|---|---|
| Bad answers | BLOCK | 128 / 128 | 32 / 128 |
| Matching-label answers | PASS | 128 / 128 | 0 / 128 |

The installed demo took **0.17 seconds** on the reference Mac after environment
preparation. Both bundles replayed correctly, and all eight Linux/macOS CI jobs
produced identical evidence. [The quickstart](docs/quickstart.md) records exact
bounds and measurement scope. First-time uv/Python/wheel downloads are separate;
this is a synthetic fixture measurement, not an inference benchmark.

Replay an individual bundle in a separate command:

```bash
uvx --python 3.12 --from actseal==0.1.0 actseal replay ./actseal-demo/fixed/evidence
```

Replay reconstructs the policy decisions and verdict from recorded data; it
does not call a provider. Replaying `bad/evidence` should return BLOCK and exit 1,
even when replay correctly reproduces the result. See the
[detailed quickstart](docs/quickstart.md) for JSON output, individual lock/verify
commands and checking an externally obtained lock digest.

## Read the result

An **ACT** is a decision permitted by the frozen allowlist and selected-label
probability threshold. **Coverage** is ACT decisions divided by all scheduled
cases. **Risk** is wrong ACT decisions divided by ACT decisions. Actseal reports
bounds around those rates; a high score or zero observed errors alone is not PASS.

| Exit | Verdict | Meaning |
|---|---|---|
| 0 | PASS | The valid evidence satisfies the frozen risk/coverage limits and fault checks. |
| 1 | BLOCK | Valid evidence establishes a limit violation or a deterministic fault-check failure. |
| 2 | INCONCLUSIVE | Valid evidence cannot establish either PASS or BLOCK. |
| 3 | ERROR | Inputs/evidence are invalid or incomplete, setup/usage fails, or the native worker experiment is invalidated. |

`lock` also returns 0 on success. `demo` returns 0 for its expected BLOCK/PASS
pair plus matching replays; it does not turn the bad run into PASS. Append
`--json` to a command for structured output. Failures and warnings are surfaced.

## Use your own policy

v0.1.0 supports one categorical question with 2–16 labels, a frozen action
allowlist and threshold, recorded fixtures, and an optional pinned native Laya
CPU adapter. Start with the [quickstart](docs/quickstart.md),
[statistical contract](docs/statistical-contract.md) and
[provider setup and limitations](docs/providers.md). The core and replay require
no model package or hosted service. Jev is deferred, not a v0.1.0 dependency.

The native Laya CLI check at candidate `434c682` also preserved an honest result:
all 128 synthetic cases ABSTAINed at the fixed threshold, with no provider
failures. Verification and replay both returned BLOCK for insufficient coverage;
no accepted cases means risk remains unestimated, [0,1]. The policy was not
tuned or retried to obtain PASS. [Provider details](docs/providers.md) record
the environment, warnings and bounds; this is an integration check, not a
population or model-quality benchmark.

The demonstration is synthetic, marked `evidence_scope=demo`, and establishes no
population or model-quality result. For real data, the statistical interpretation
requires independent cases and one prespecified attempt under a fixed policy and
operating regime. Actseal does not enforce another application's behavior.

Hashes and replay check consistency. Even a trusted lock digest cannot
authenticate rewritten responses under that lock, prove inference occurred or
prove the labels true. Read the [threat model](docs/threat-model.md) before using
evidence to authorize actions.

Apache-2.0; see [LICENSE](LICENSE), [NOTICE](NOTICE) and
[dependency notices](docs/dependencies.md). Contributions:
[CONTRIBUTING](CONTRIBUTING.md). Changes: [CHANGELOG](CHANGELOG.md).
