# Actseal quickstart

Use Actseal to freeze an application decision policy, evaluate its accepted
errors and coverage, and retain evidence you can replay without rerunning a
model. The packaged fixture demonstration exercises that complete path with
authored support-triage data.

## Three commands

Prerequisites: macOS or Linux, [uv installed](https://docs.astral.sh/uv/getting-started/installation/)
and a writable working directory. Windows is unsupported in v1. The first
command selects Python 3.12 and runs the published
[PyPI package](https://pypi.org/project/actseal/) in uv's tool environment;
no source checkout, model or API key is needed.

```bash
uvx --python 3.12 actseal demo --out ./actseal-demo
uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
```

The third command intentionally exits 1: replay reproduces the deliberately
bad run's `BLOCK`. The first exits 0 only when the pipeline produces
`bad: BLOCK`, `fixed: PASS` and two matching replays; the second exits 0 by
reproducing `PASS`. `--offline` on the replays reuses the environment the
first command prepared and makes no network request; run the commands in this
order.

`./actseal-demo` must not already exist and its parent must. Do not create the
output directory first: Actseal refuses an existing file, directory or symlink
rather than overwriting it. Use a fresh name to repeat the demonstration.

uv may need to obtain Python and the wheel on the first invocation. That
installation time is reported separately from the fixture execution; the demo
itself uses no model, API key or optional library, and the replays call no
inference service.

**Which release runs.** Unpinned, `uvx` resolves the latest Actseal release
published on PyPI. To run one specific release, add `--from` with an exact
pin, for example `uvx --python 3.12 --from "actseal==1.0.0" actseal demo
--out ./actseal-demo`; the replay commands then take the same `--from`. The
commands, exit codes and JSON receipt shapes above are stable for every 1.x
release under the [stability manifest](stability.md), and security fixes
target the latest 1.x minor at its latest patch under the
[versioning policy](versioning.md). Evidence written by actseal 0.1.0 is not
converted by 1.x; the [migration guide](migration.md) describes the isolated
pinned replay path. Measured installation and demo timings are recorded in
each release's report, not here, and are measurements rather than
performance promises.

## What the demo writes

| Path under `actseal-demo/` | Contents |
|---|---|
| `inputs/` | `bad.toml`, `fixed.toml`; each run's calibration, verification and response JSONL files |
| `bad/lock.json`, `fixed/lock.json` | Frozen policy, input and identity locks (schema 2) |
| `bad/evidence/`, `fixed/evidence/` | Seven-file bundles: manifest, lock, labelled inputs, terminal records, faults and verdict |

Both runs use the **same policy and limits** against different authored
answers: labels billing/technical/sales, threshold 0.90, maximum risk 0.05,
minimum coverage 0.50, alpha 0.05, 128 verification cases each. The bad
fixture selects 32 wrong labels; the fixed fixture selects the gold label every
time. These are fixture construction rules, not observed model performance;
the [example README](../examples/support_triage/README.md) documents the
generator. Every count, interval and verdict is computed by the pipeline at
run time.

| Expected observation | Bad fixture | Fixed fixture |
|---|---|---|
| Status | BLOCK (exit 1) | PASS (exit 0) |
| ACT / total | 128 / 128 | 128 / 128 |
| Wrong ACT / ACT | 32 / 128 | 0 / 128 |
| Fresh replay | Matching BLOCK | Matching PASS |

## Read the result

`ACT` means the frozen policy permits the provider's selected label: it is
allowed and its normalized probability meets the threshold. It is not a
statement that the answer is correct. With `n` scheduled cases, `a` `ACT`
decisions and `e` wrong `ACT` decisions, coverage is `a / n` and
accepted-action risk is `e / a`. Every scheduled case stays in the denominator;
injected faults are separate checks. Zero `ACT` decisions cannot yield `PASS`.

`PASS` requires the upper risk bound at or below the maximum and the lower
coverage bound at or above the minimum, with valid fault evidence. `BLOCK`
uses the opposite bounds to establish a violation; insufficient evidence is
`INCONCLUSIVE`; invalid evidence is `ERROR`. The [concepts](concepts.md) page
explains decisions versus verdicts; the [FAQ](faq.md) answers the common
"why not PASS" questions.

| Exit | Status | Interpretation |
|---|---|---|
| 0 | PASS | Valid evidence satisfies the frozen contract. |
| 1 | BLOCK | Valid evidence establishes a limit violation or a fault-contract failure. |
| 2 | INCONCLUSIVE | Valid evidence proves neither PASS nor BLOCK. |
| 3 | ERROR | Invalid or incomplete evidence, usage or setup failure, or an invalidated native-worker experiment. |

`lock` returns 0 on success. `demo` returns 0 only for its expected
BLOCK/PASS pair with matching replays. Every command accepts `--json` for one
versioned JSON object on stdout; the [CLI reference](cli.md) lists each
receipt's fields. The installed package also supports `python -m actseal`.

## Lock and verify individually

These commands reuse the copied **fixed synthetic inputs**, so the outcome
remains demo evidence. Both output paths must be new.

```bash
uvx --offline --python 3.12 actseal lock \
  --contract ./actseal-demo/inputs/fixed.toml \
  --calibration ./actseal-demo/inputs/fixed_calibration.jsonl \
  --verification ./actseal-demo/inputs/fixed_verification.jsonl \
  --provider fixture \
  --responses ./actseal-demo/inputs/fixed_responses.jsonl \
  --out ./fixed-recheck.lock.json
```

```bash
uvx --offline --python 3.12 actseal verify \
  --lock ./fixed-recheck.lock.json \
  --calibration ./actseal-demo/inputs/fixed_calibration.jsonl \
  --verification ./actseal-demo/inputs/fixed_verification.jsonl \
  --provider fixture \
  --responses ./actseal-demo/inputs/fixed_responses.jsonl \
  --out ./fixed-recheck.evidence --json
```

```bash
uvx --offline --python 3.12 actseal replay ./fixed-recheck.evidence --json
```

For your own policy, choose the threshold and sampling plan before
evaluation, prepare the contract TOML and labelled JSONL splits described in
[CONTRACTS](../plan/CONTRACTS.md), then lock them. v1 does not fit thresholds
from calibration data. Verification rejects changed inputs or a changed
provider or implementation identity before any call, retains every scheduled
terminal outcome and writes one new bundle. A setup failure produces no
purported complete bundle.

For evidence whose expected identity you already trust, append
`--expected-lock-sha256` and the 64-character digest to `replay`. Obtain the
digest through a separately trusted channel; a digest read from the bundle you
are checking is not an anchor, and even a trusted digest does not authenticate
rewritten same-lock responses or prove execution took place.

## Optional native Laya

Follow [providers](providers.md) for the pinned optional CPU stack, checkpoint
preparation, calibration caveat and offline settings. That preparation is not
part of the fixture quickstart. Use `--provider laya` for native lock and
verify, omit `--responses`, and add `--offline` after preparing the pinned
cache. Collection fixes startup at 120 seconds and each request at 30 seconds
with no override; worker loss invalidates the attempt as `ERROR` while
retaining diagnostic records. The recorded native run on the fixed synthetic
inputs returned an honest `BLOCK` with every case abstaining and risk
unestimated; it was not tuned or retried.

## Limits

Synthetic demo evidence is not a population benchmark, a repaired model or
deployment certification. Real statistical interpretation requires independent
case outcomes under a fixed policy and operating regime over one prespecified
attempt. Hashes cannot establish those assumptions, label truth or response
authenticity, and Actseal cannot force another application to follow its
policy. Read the [threat model](threat-model.md) before using evidence to
authorize actions. Raw inputs and responses can contain private data: review
bundles before sharing them. Evidence from actseal 0.1.0 is not converted; see
the [migration guide](migration.md).
