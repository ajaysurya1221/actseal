# Application action-gate example (authored, demo-only)

This directory shows where Actseal sits in an application's control flow. A
small ticket-routing application calls the existing evaluator for every
incoming ticket and executes its one action, a local queue write, **only when
the decision is `ACT`**. `ABSTAIN`, `ESCALATE` and `DENY` take explicit
non-execution paths. Actseal verifies the frozen policy offline and replays
the evidence; it does not execute, intercept or enforce the application's
action. The application owns execution.

Everything here runs without a key, model download or network. The only
provider is the recorded-response fixture, which stands in for a model. All
data is **authored synthetic data** with `evidence_scope = "demo"`: no model
produced any label, probability or failure, and nothing here is a population,
calibration or deployment claim. There is no external ticket service, no
framework and no deployed enforcement.

```text
                 application (gate.py)                     Actseal (public API)
ticket ──► DecisionRequest(ticket_id, text, question) ──► model.decide ──► CapturedOutcome
                                                             │
                                   normalize(capture, question, locked identity)
                                                             │
                                   evaluate(outcome, locked policy) ──► PolicyDecision
                                                             │
           ACT ───────────► queue.enqueue(choice, ticket_id)   (the only effect)
           ABSTAIN ───────► held for a person                  (no effect)
           ESCALATE ──────► escalated                          (no effect)
           DENY ──────────► rejected                           (no effect)
```

No gold label is needed at run time: a ticket row has exactly `ticket_id` and
`text`, and `expected_label` never enters a `DecisionRequest` or the fixture
file. Labelled `Case` fixtures exist only in the evaluation data below.

Before normalization the gate checks that the capture is bound to the exact
request it sent (`capture.request_sha256 == request_sha256(request)`). A
same-identity capture for a different ticket, whatever it says, is
`RequestBindingError`: nothing is evaluated and nothing is enqueued.

## Files

| File | Kind | Role |
|---|---|---|
| `gate.py` | application code | `ActionGate` (opens only on the expected lock, a validating lock, the locked model identity and a `PASS` verdict), `LocalQueue`, `Ticket`, `Disposition`, `route_all` |
| `run.py` | application code | `--check`, `--route`, `--record DIRECTORY --source-commit SHA` |
| `contract.toml` | authored evaluation data | Frozen policy: four known labels, three routed labels, threshold 0.90, `max_risk` 0.05, `min_coverage` 0.50, `alpha` 0.05 |
| `calibration.jsonl`, `verification.jsonl` | authored evaluation data | 12 and 160 **labelled** cases; bound by the lock and scored offline |
| `responses.jsonl` | authored stand-in for a model | Recorded fixture responses keyed by case id and ticket id; its file hash is the model identity |
| `tickets.jsonl` | application input | 8 **label-free** tickets routed at run time |
| `generate_data.py` | documentation | Deterministic generator of the five data files; a rerun reproduces the committed bytes |
| `recorded/<fingerprint prefix>/` | recorded evidence | One offline verification run: `PRODUCER.json`, `lock.json`, `evidence/` (the seven-file bundle) |

## Running

```bash
uv run --frozen python examples/action_gate/run.py --check
uv run --frozen python examples/action_gate/run.py --route
uv run --frozen pytest tests/examples
```

`--check` exits 0 only when all of the following hold: a fresh offline
verification of the authored data (lock, verify, replay) agrees with itself;
every active recorded run under `recorded/` passes the checks in the next
section; and, only then, the gate opens on the fresh lock and verdict and
routes the eight tickets to exactly the authored dispositions with exactly the
three `ACT` tickets in the queue journal. When any archive fails, the routing
demonstration is skipped: no queue operation happens.

`--route` performs the same fresh verification and archive checks and refuses
before any queue operation when anything fails. Otherwise it replays the
first recorded run, opens the gate on the replayed verdict and prints each
ticket's disposition and the queue journal.

## The eight tickets

| Ticket | Authored response | Decision and reason | Application path | Queue write |
|---|---|---|---|---|
| T-1001 | `billing` at 0.95 | `ACT`, `policy.allowed` | queued | `billing` |
| T-1002 | `technical` at 0.95 | `ACT`, `policy.allowed` | queued | `technical` |
| T-1003 | `sales` at exactly 0.90 (the threshold) | `ACT`, `policy.allowed` | queued | `sales` |
| T-1004 | `billing` at 0.8999 (just below) | `ABSTAIN`, `policy.low_confidence` | held for review | none |
| T-1005 | recorded `timeout` failure | `ESCALATE`, `provider.timeout` | escalated | none |
| T-1006 | `other` at 0.95 (known label, not routed) | `DENY`, `policy.disallowed_choice` | rejected | none |
| T-1007 | `legal` (not a question option) | `DENY`, `policy.unknown_choice` | rejected | none |
| T-1008 | body `{` (not JSON) | `ESCALATE`, `provider.malformed_response` | escalated | none |

The policy accepts a selected probability equal to the threshold and abstains
below it; both shapes sum to exactly 1.0 in binary floating point, so no
renormalization is involved. A recorded `fallback_used` flag always yields
`ESCALATE`, never `ACT` (covered by `tests/examples/test_gate.py`).

## Prespecified verification rules and the recorded result

The rules were frozen in `generate_data.py` before the run was recorded and
were not changed afterwards. Gold label of verification index `i` is routed
label `i mod 3`. Authored outcome: `i mod 20 == 7` selects the gold label at
0.85 (`ABSTAIN`); `i mod 20 == 13` is a `timeout` failure (`ESCALATE`);
`i mod 20 == 19` selects `other` at 0.95 (`DENY`); index 42 selects the next
routed label at 0.95 (one wrong accepted answer); every other index selects
the gold label at 0.95.

Prediction from the frozen statistical contract (each Clopper-Pearson tail is
`alpha / 4`): `n = 160`, `a = 136`, `e = 1`; risk upper bound about 0.0460,
coverage lower bound about 0.775; verdict `PASS`.

Recorded result (`recorded/a5fe090202f7/evidence/verdict.json`, recomputed by
`--check` on every run):

| Field | Value |
|---|---|
| status | `PASS`, reason `contract.satisfied` |
| total / accepted / errors | 160 / 136 / 1 |
| risk | [0.0001, 0.0460] |
| coverage | [0.7755, 0.9076] |
| six canonical faults | all at their required actions |

A `PASS` here says that this authored fixture satisfies this frozen policy on
these 160 authored cases. It is not evidence about any real model or
population.

## The recorded run and its producer identity

`recorded/a5fe090202f7/PRODUCER.json` records the implementation fingerprint
(`implementation_sha256` of the installed `actseal` source), the replay engine,
the lock seal, the verdict status, the actseal version, the source commit the
run was produced from, the `uv.lock` hash and the SHA-256 of the four authored
inputs. The directory name is the fingerprint prefix. The bytes under
`evidence/` are exactly what `verify` published; nothing was edited afterwards.

For every active recorded run (amendment V1-020), the example checks only
what is specific to it:

- `PRODUCER.json` describes the root `lock.json` (seal, producer fingerprint,
  replay engine);
- the root `lock.json` equals the bundle's `lock.json` byte for byte;
- the archived contract equals the frozen `contract.toml` and the archived
  model identity equals the current fixture identity;
- the bundle's datasets and the producer's recorded input hashes equal the
  committed authored inputs;
- `records.jsonl`, `faults.jsonl` and the verdict (apart from the lock seal)
  equal a fresh run.

Everything general is owned by the core `replay`: bundle structure and
hashes, the lock seal, replay-engine compatibility through the packaged
registry (exact running source, or producer and running fingerprints both
registered for the engine), inventories and semantics. Each active run must
replay to a non-`ERROR` verdict equal to its archived verdict
(`[ok] ... (exact implementation)` or `(registry-approved implementation)`).
Anything else is an `[error]`, whether the archive is damaged or its producer
is simply not supported by the running implementation, and it fails `--check`
and `--route` even beside a valid run. Nothing is skipped as benign, and
nothing is rewritten, resealed, moved or auto-approved.

An active archive whose producer is not the running source passes only
through an explicit compatibility review that registers both its producer
fingerprint and the running fingerprint for the engine in the packaged
registry. For `recorded/a5fe090202f7` that review is complete: amendment
V1-037 approved its producer (`a5fe0902...`, unreleased prerelease source
`76758d70...`) and the 1.0.0 source (`8f316f67...`) for `actseal-choice-v1`,
so the archive replays as `(registry-approved implementation)` under 1.0.0.
Amendment V1-055 added the reviewed 1.0.1 source (`dced01d7...`) beside both,
so the unchanged archive keeps replaying to its stored verdict under 1.0.1;
the [versioning policy](../../docs/versioning.md#registry-approval-process)
records all three entries. The registry approves producers for an engine, not
archives: it holds no lock digests. Any later packaged Python change needs
its own fingerprint and review before this archive passes again. Excluding an
archive from the active set requires a separately recorded amendment; none
exists. Adding a new run cannot make an older unsupported archive pass, and a
new run is never a repair, replacement or reseal of an older one; the older
archive's bytes stay as recorded in every case.

`--record` exists to produce a separately identified run for a new
implementation, alongside, not instead of, the existing archives:

```bash
uv run --frozen python examples/action_gate/run.py --record examples/action_gate/recorded/<new fingerprint prefix> --source-commit <40-hex commit>
```

## Where the trust actually sits

- The application must obtain the expected lock digest through a channel it
  trusts. `run.py` reads it from `PRODUCER.json` beside the bundle for
  convenience; that file is committed evidence, not a trusted channel for a
  deployed system, which should keep the digest in its own configuration.
- `ActionGate` refuses to open on a lock seal that differs from the expected
  digest, a lock that does not validate under the running implementation, a
  verdict for a different lock, a verdict other than `PASS`, or a model whose
  reported identity differs from the locked one.
- Consistent replay shows that the recorded evidence reproduces under the
  frozen engine. It does not prove who produced the bundle, that a model was
  called, that labels are true or that the application enforced anything at
  run time (see `docs/threat-model.md`).
- A provider exception, a binding failure or a queue failure propagates and
  stops routing at that ticket; nothing is retried, skipped or downgraded to
  another path, and no disposition is produced for it. Provider and binding
  failures happen before any effect. A queue operation that raises may have
  performed its write first (the example's enqueue-then-raise test shows the
  entry retained); handling that partial effect is the application's
  responsibility as the queue's owner. The example adds no transaction or
  compensation machinery.

Regenerate the data with `python examples/action_gate/generate_data.py DIRECTORY`
(it refuses to overwrite existing files) and compare with this directory; any
difference means the rules changed and the recorded run must be reviewed.
