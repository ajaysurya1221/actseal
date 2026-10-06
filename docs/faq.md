# Actseal FAQ: reading verdicts and results

Short answers to the questions that come up when reading a verdict. The
[concepts](concepts.md) page defines the terms; the
[statistical contract](statistical-contract.md) and
[threat model](threat-model.md) are normative.

## My run says BLOCK. Is the tool broken?

No. `BLOCK` (exit 1) is a legitimate, valid result: the evidence establishes
that the frozen policy violates a limit, or a canonical fault produced the
wrong action. The packaged demo's `bad` run is designed to `BLOCK`, and the
native Laya receipt in [providers](providers.md) is a genuine `BLOCK` with
zero accepted cases. Read `reasons`: `risk.exceeds_limit`,
`coverage.below_minimum`, `risk.no_accepted_cases` and `fault.<scenario>`
each name the violated rule.

## Can I rerun until it passes?

No. The error budget is stated over one prespecified attempt. Discarding a
`BLOCK`, `INCONCLUSIVE` or `ERROR` attempt and trying again, changing the
threshold after seeing outcomes, or restarting a failed native worker inside
an attempt all invalidate the guarantee. Hashes cannot detect an edited
history; keep every attempt on record.

## What does INCONCLUSIVE mean?

Valid evidence that proves neither `PASS` nor `BLOCK`. Typically the sample is
too small for the Clopper-Pearson bounds to clear the limits in either
direction. The remedy is a larger, prespecified verification set in a new
lock, not a rerun of the same one.

## Zero wrong actions, but not PASS?

Two common causes. If no case reached `ACT` (`accepted` is 0), risk is
unestimated: the interval is `[0, 1]` and `PASS` is impossible, with reason
`risk.no_accepted_cases`. If some cases did `ACT` but few, the upper risk bound
of a small accepted sample stays above `max_risk` even with zero observed
errors. Zero errors in a small sample is not evidence of zero risk.

## Why is coverage so low when the model answered every case?

Coverage counts `ACT` decisions over **all** scheduled cases. An answer whose
selected probability is below the threshold is an `ABSTAIN`; a selected label
outside the allowlist is a `DENY`; a provider failure is an `ESCALATE`. All of
those stay in the denominator. The native receipt in
[providers](providers.md) shows 128 answers and coverage `[0, 0.0337]` because
every answer fell below the fixed threshold.

## ACT means the answer is correct, right?

No. `ACT` means the frozen policy permits the application to execute the
selected label: the label is allowed and its normalized probability met the
threshold. Risk is exactly the rate at which `ACT` decisions disagree with the
gold label. A `PASS` bounds that rate; it does not certify any single answer.

## Is a decision the same as a verdict?

No. `ACT`, `ABSTAIN`, `DENY` and `ESCALATE` are per-case decisions.
`PASS`, `BLOCK`, `INCONCLUSIVE` and `ERROR` are whole-run verdicts with exit
codes 0 to 3. There is no mapping between the two lists: a run of all `ACT`
decisions can `BLOCK` on risk, and a run with many `ESCALATE` decisions can
`PASS`.

## Replay exits 1. Did replay fail?

No. A successful replay reproduces the recorded verdict, and the exit code is
that verdict's code. Replaying `BLOCK` evidence exits 1; replaying a
diagnostic `ERROR` bundle exits 3. Replay has failed only when the recomputed
status differs from the recorded one or the `reasons` carry `integrity.*`
codes. In a CI step that stops on nonzero exits, inspect the JSON `status`
instead of treating exit 1 as a tool error.

## What does ERROR tell me?

That no statistical statement was made. `ERROR` covers invalid, incomplete or
inconsistent evidence, usage and setup failures, an existing output path, and
an invalidated native-worker experiment (`infrastructure.worker_invalidated`).
Counts are zero and both intervals are `[0, 1]`. The `reasons` (for replay) or
`error` (for usage and setup) field names the invariant. A worker-loss bundle
is retained as diagnostic evidence; replaying it preserves `ERROR`.

## Replay matched. Is the evidence authentic?

Replay establishes consistency: the recorded decisions and verdict follow
from the recorded inputs and responses under the recorded lock. It cannot
prove who wrote the bundle, that a real provider was called, that the labels
are true, that cases were independently sampled, or that failed attempts were
not hidden. Someone who can rewrite a whole bundle can recompute every hash.

## Does `--expected-lock-sha256` fix that?

It anchors the locked identity, if the digest came from a channel you trust
separately from the bundle. It does not authenticate responses: an author can
keep the same lock, replace responses and recompute consistent records and
hashes. Reading the digest from the bundle you are checking anchors nothing.

## What is evidence_scope and why does the demo say "demo"?

`demo` marks authored or illustrative inputs; `iid` is the author's assertion
that verification cases are independent samples from the declared population
under the fixed policy and regime, over one attempt. Actseal records the
scope; it does not verify sampling. The packaged demo and the native receipt
are `demo` and make no population claim.

## Why does the demo exit 0 if one run is BLOCK?

`demo` is a self-check of the pipeline, not a verdict. It exits 0 only when
the deliberately bad run is `BLOCK`, the fixed run is `PASS` and both fresh
replays match. Anything else is `ERROR`. Replaying `bad/evidence` on its own
exits 1, as expected.

## Can I use my own provider?

The current stable providers are `fixture` (recorded responses) and `laya`
(the optional pinned native CPU adapter). In the v1.0 scope
`ModelIdentity.provider` accepts only those two, so a provider of your own
cannot be sealed into a lock through the stable runner today. A later 1.x
release may add a provider as an additive, explicitly selected option. A Jev
transport is conditional experimental preparation, not shipped, and would be
selectable only under an explicit experimental flag; see
[providers](providers.md).

## Does Actseal run on Windows?

No. Windows is unsupported in v1. Exclusive bundle publication uses macOS and
Linux filesystem operations, and no Windows classifier or partial-support
claim is made. The native receipts also do not establish Intel Mac, Linux ARM,
musl or GPU support.

## Does the core need any third-party package?

No. The runtime core depends only on the Python standard library (Python 3.12
or 3.13). The optional `laya` extra installs the pinned native stack; replay
never imports it.

## Can 1.0 replay evidence from 0.1.0?

No, and it does not convert it. Schema-1 locks and bundles are rejected with
`integrity.legacy_schema` and guidance to replay them under an isolated pinned
`actseal==0.1.0`. The [migration guide](migration.md) explains why a reseal
would not be the original evidence.

## Will a later 1.x release replay my 1.0 evidence?

Only when both the producing and the running source fingerprints are
registered for the `actseal-choice-v1` engine in the packaged registry. Until
then the result is `ERROR` with reason `integrity.lock`, which is a
verifier-configuration limit, not a statement that the evidence is invalid.
The [versioning policy](versioning.md) describes registry approval.

## Is PASS a safety or calibration guarantee?

No. `PASS` says the frozen policy's accepted-action risk and coverage bounds
and fault rules held on the locked verification set under the stated
assumptions. It is not a calibration claim about the provider's probabilities,
not a guarantee about other inputs or distributions, and not enforcement of
anything the surrounding application does.
