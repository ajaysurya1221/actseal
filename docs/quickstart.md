# Actseal quickstart

Use Actseal to freeze an application decision policy, evaluate its accepted
errors and coverage, and retain evidence you can inspect without rerunning a
model. The packaged fixture demonstration exercises that complete path with
authored support-triage data.

## One-command first run

Prerequisites: macOS or Linux, [uv installed](https://docs.astral.sh/uv/getting-started/installation/),
and a writable working directory. This command selects Python 3.12 and uses a
wheel from the GitHub release, not an assumed PyPI package:

```bash
uvx --python 3.12 --from https://github.com/ajaysurya1221/actseal/releases/download/v0.1.0/actseal-0.1.0-py3-none-any.whl actseal demo --out ./actseal-demo
```

`./actseal-demo` must not already exist, and its parent must exist. Do not create
the output directory first. Actseal refuses an existing file, directory or
symlink rather than overwriting it. Choose a fresh name to repeat the authored
demonstration.

uv may need to obtain Python and the wheel on the first invocation. That package
and runtime preparation is separate from the fixture execution measurement.
The fixture demo uses no model, API key or optional model library. Its package
installation may use the network; the fixture computation and replay do not
call an inference service. The release target is ≤60 seconds for the fixture
workflow after prerequisites are ready, not a bound on downloading them.

For repeated commands below, set this convenience variable in the same shell:

```bash
actseal_wheel_url='https://github.com/ajaysurya1221/actseal/releases/download/v0.1.0/actseal-0.1.0-py3-none-any.whl'
```

## Outputs and result meaning

The demo copies its inputs, creates fresh locks bound to the installed
implementation and fixture identities, collects each scheduled case once,
exercises all six faults, assesses the evidence and freshly replays both bundles.

| Path under `actseal-demo/` | Contents |
|---|---|
| `inputs/` | `bad.toml`, `fixed.toml`; each run's calibration, verification and response JSONL files |
| `bad/lock.json`, `fixed/lock.json` | Frozen policy, input and identity locks |
| `bad/evidence/`, `fixed/evidence/` | Seven-file bundles containing manifest, lock, labelled inputs, terminal records, faults and verdict |

The two runs use the **same policy and limits** with different authored outputs.
Both use labels billing/technical/sales, threshold 0.90, maximum risk 0.05,
minimum coverage 0.50 and alpha 0.05. Each authored verification set has 128
cases: the bad fixture deliberately selects 32 wrong labels; the fixed fixture
selects the gold label for every case. These are fixture construction rules,
not observed model performance. The [example README](../examples/support_triage/README.md)
documents the deterministic generator and the distinct calibration sets.

The independently accepted T50 wheel produced bad BLOCK, fixed PASS and matching
replays. The demo exits 0 only if the actual pipeline produces those results.
Counts and intervals are computed by that pipeline.

| Accepted T50 observation | Bad fixture | Fixed fixture |
|---|---|---|
| Status; ACT/total count | BLOCK; 128 / 128 | PASS; 128 / 128 |
| Wrong ACT/ACT count | 32 / 128 | 0 / 128 |
| Risk interval | [0.1687604663492846, 0.346264539835876] | [0, 0.033655210093607835] |
| Coverage interval | [0.9663447899063922, 1] | [0.9663447899063922, 1] |
| Fresh module replay | Matching BLOCK / exit 1 | Matching PASS / exit 0 |

Root measured the installed console at **0.170645 seconds wall time**, after
a separate **0.046136-second cached environment/install step**, on its macOS
Python 3.12.13 reference environment. [REVIEW T50-02](../plan/reviews/T50-02.md)
accepts `286ae67e252ecbb77e9c330ebe1f66cc375bfbab`; it merged as `7e696c5`.
Tested candidate wheel SHA-256:
`b3633a3a0d2977d1250b0cf3a4e0078903744ec181d977ccce82013f85ad6128`.
This is the T50 candidate artifact, not the final release artifact. See the
[release report](../plan/FINAL_REPORT.md) for final artifact and installation
receipts. This timing does not measure a public download.

ACT means the policy permits the provider's selected label: it is allowed and
its normalized probability meets the threshold. It is not a statement that the
answer is correct. With `n` scheduled cases, `a` ACT decisions and `e` wrong ACT
decisions, coverage is `a/n` and accepted-action risk is `e/a`. Every scheduled
case remains in coverage's denominator. Injected faults are separate checks,
not extra samples. Zero ACT decisions cannot yield PASS.

PASS requires the upper risk bound at or below the maximum and the lower
coverage bound at or above the minimum, with valid fault evidence. BLOCK uses
the opposite bounds to establish a violation; insufficient evidence remains
INCONCLUSIVE. See the [statistical contract](statistical-contract.md) for the
exact interval construction and assumptions.

## Replay separately

```bash
uvx --python 3.12 --from "$actseal_wheel_url" actseal replay ./actseal-demo/fixed/evidence --json
```

To inspect the deliberately failing evidence, run this as a separate command:

```bash
uvx --python 3.12 --from "$actseal_wheel_url" actseal replay ./actseal-demo/bad/evidence --json
```

The expected exit for that second command is **1 (BLOCK)**. Successful replay
preserves the statistical verdict; it does not always return 0. In a shell or
CI system that stops on nonzero exits, explicitly inspect the recorded status
instead of discarding that expected result. A diagnostic ERROR bundle can also
replay faithfully while retaining ERROR/exit 3.

Replay reconstructs requests, normalization, policy outcomes, fault checks and
assessment from bounded data. It neither imports a live provider nor reruns
inference. Use the same released implementation that produced the bundle;
source changes alter the implementation fingerprint.

For evidence whose expected identity you already trust, append
`--expected-lock-sha256` followed by that 64-character digest. Obtain it through
your trusted channel: reading the digest from the bundle you are checking does
not establish an independent trust anchor. Even a trusted lock digest does not
authenticate rewritten same-lock responses or prove execution took place.

## Run lock and verify individually

The following commands reuse the copied **fixed synthetic inputs** from the
demo, so the outcome remains demo evidence. Both output paths must be new.

```bash
uvx --python 3.12 --from "$actseal_wheel_url" actseal lock \
  --contract ./actseal-demo/inputs/fixed.toml \
  --calibration ./actseal-demo/inputs/fixed_calibration.jsonl \
  --verification ./actseal-demo/inputs/fixed_verification.jsonl \
  --provider fixture \
  --responses ./actseal-demo/inputs/fixed_responses.jsonl \
  --out ./fixed-recheck.lock.json
```

```bash
uvx --python 3.12 --from "$actseal_wheel_url" actseal verify \
  --lock ./fixed-recheck.lock.json \
  --calibration ./actseal-demo/inputs/fixed_calibration.jsonl \
  --verification ./actseal-demo/inputs/fixed_verification.jsonl \
  --provider fixture \
  --responses ./actseal-demo/inputs/fixed_responses.jsonl \
  --out ./fixed-recheck.evidence --json
```

```bash
uvx --python 3.12 --from "$actseal_wheel_url" actseal replay ./fixed-recheck.evidence --json
```

For your own use, choose the policy and sampling plan before evaluation, prepare
the TOML and labelled splits described in [CONTRACTS](../plan/CONTRACTS.md), then
lock them. v1 does not fit thresholds from calibration data. Verification
rejects changed inputs or provider/implementation identity before calls, retains
all scheduled terminal outcomes and writes one new bundle. Setup failure does
not produce a purported complete bundle.

## CLI outcomes and diagnostics

| Exit | Status | Interpretation |
|---|---|---|
| 0 | PASS | Valid evidence satisfies the frozen contract. |
| 1 | BLOCK | Valid evidence establishes a statistical limit violation or deterministic fault-contract failure. |
| 2 | INCONCLUSIVE | Valid evidence is insufficient to establish either PASS or BLOCK. |
| 3 | ERROR | Invalid/incomplete evidence, setup/usage failure or an invalidated native-worker experiment. |

`lock` returns 0 on success. `demo` returns 0 only for its expected bad BLOCK and
fixed PASS with matching replays. `--help` and `--version` also return 0; argument
errors return 3. All four commands support `--json`; Actseal emits one JSON
object on stdout, including warnings/failures where relevant. Without that flag,
the result is human-readable and warnings/failures are surfaced on stderr.
uv's package/runtime preparation messages are separate from Actseal's output.
The installed package also supports `python -m actseal` in its Python environment.

## Optional native Laya and trust limits

Follow [providers](providers.md) and [dependency notices](dependencies.md) for
the pinned optional CPU stack, checkpoint preparation, calibration caveat and
offline settings. That heavier preparation is not part of the fixture quickstart.
Use `--provider laya` for native lock/verify, omit `--responses`, and use
`--offline` after preparing its pinned cache. Fixtures require `--responses`
and accept `--offline` as a no-op; no model-specific setting is needed. Offline
library settings are not a network firewall.

Root's native CLI run at candidate `434c682352d19e64c6349cb5a7aac44fa7554156`
used the committed fixed synthetic inputs, the pinned cached model and both
offline environment flags on macOS 26.6.2 arm64, Python 3.12.13, uv 0.12.5.
Lock succeeded (exit 0; 6.445 seconds). Verification returned **BLOCK**
(exit 1; 13.821 seconds): all 128 cases ABSTAINed, no provider failures were
recorded, risk was [0, 1] and coverage [0, 0.033655210093607835]. Reasons were
`coverage.below_minimum` and `risk.no_accepted_cases`. Replay with the expected
lock digest reproduced BLOCK (exit 1; 0.093 seconds). All six fault actions
matched; warning counts retained the calibration warning 128 times and
`normalize.renormalized` 27 times. These are captured-warning occurrences, not
counts of distinct model loads.

That native result used one fixed attempt without policy tuning or retry.
Zero accepted cases do not establish zero risk; they leave risk unestimated.
The test exercises integration on authored inputs, not model accuracy or a
general latency benchmark. See the [provider receipt](providers.md#native-cli-integration-receipt)
for exact identities and the [release report](../plan/FINAL_REPORT.md) for the
final publication checks.

Native collection fixes startup at 120 seconds and normal requests at 30 seconds,
with no deadline override. Worker loss retains scheduled diagnostic records but
invalidates the statistical attempt as ERROR. Do not restart a worker, replace
cases or retry discarded attempts until PASS. There is no uptime or
completion-probability guarantee.

Synthetic demo evidence is not a population benchmark, a repaired model or
deployment certification. Real statistical interpretation requires independent
case outcomes under a fixed operating regime over one prespecified attempt.
Hashes cannot establish those assumptions, label truth or response authenticity;
Actseal cannot force another application to follow its policy. Read the
[threat model](threat-model.md). Raw inputs and responses can contain private
data: review bundles before sharing them.
