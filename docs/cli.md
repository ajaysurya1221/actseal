# Actseal command-line reference

## v2 provider options (unreleased)

`lock`, `verify`, `calibrate` and `qualify` accept:

- `--provider recorded --responses FILE --model NAME --revision REV`: read
  predictions locally; optional `--offline`; no experimental flag.
- `--provider decision-api --experimental-provider --endpoint URL --model NAME
  --revision REV [--api-key-env NAME]`: use the PROVISIONAL configurable
  Jev-compatible transport. All four identity/endpoint arguments are required;
  `--api-key-env` names a variable, never a credential. `--responses` and
  `--offline` are rejected.

Recorded captures carry `recorded: provider faults not tested`. Replay prints
that warning in its existing JSON `notes` array or on stderr in text mode.
All six local synthetic checks still execute. Receipt fields and exit codes
stay unchanged. See [provider formats and endpoint constraints](providers.md#recorded-predictions-v2).

The console script `actseal` and `python -m actseal` are the same program.
The original commands are `lock`, `verify`, `replay` and `demo`; v2 adds
`plan`, `calibrate`, `qualify`, `replay-selection` and `report`. The
[stability manifest](stability.md) preserves the 1.x interfaces and records
the opt-in additions. Existing receipts are described by
[cli-receipt.schema.json](schemas/cli-receipt.schema.json); selection command
receipts and `demo --qualify` use
[qualification-cli-receipt.schema.json](schemas/qualification-cli-receipt.schema.json).

## Static reports (v2, unreleased)

```sh
actseal report qualification --out qualification-report
actseal report evidence --out evidence-report
```

`DIRECTORY` is either a complete qualification root (including `calibration/`,
`evidence/`, `lock.json` and `qualification.json`) or an ordinary evidence
bundle. Report generation reuses offline bundle replay, replays selection
when present, and checks the receipt and plan against the verification lock.
Invalid or incomplete evidence exits 3 without publishing a report. A valid
diagnostic ERROR bundle can be reported; its recorded verdict stays ERROR.
A calibration-only result without verification evidence is not a report input.

The new output directory contains exactly `report.html`, `report.md` and
`badge.json`. It must be outside the evidence and calibration directories;
existing destinations are refused. HTML is self-contained, with inline CSS
and SVG, no scripts or external resources. Markdown is suitable for a GitHub
job summary. The badge follows the shields endpoint shape. Outputs contain
no generated timestamps or filesystem paths and are byte-identical for the
same validated inputs and attestation reference. Calibration curves are
labelled **descriptive, not verified**; verification intervals are copied
from the replayed verdict.

Successful rendering exits 0 regardless of the displayed verdict. With
`--json`, its receipt has `schema_version` (1), `command` (`report`),
`exit_code` (0), `ok` (true), `status` (the replayed verdict) and `out`.
Errors use the ordinary error fields with `command=report` and exit 3.
This opt-in report receipt is documented here; it does not extend either
existing published CLI receipt schema.

Without `--attestation-ref TEXT` the report says **checksummed, not attested**.
With a reference it attributes the attestation claim to the caller. Actseal
verifies no signature. The [GitHub Action guide](github-action.md) explains
the separate attestation and verification steps and their limits.

## Signatures

```text
actseal [-h] [--version] COMMAND ...
actseal lock [-h] --contract PATH --calibration PATH --verification PATH
             --provider {fixture,laya,recorded,jev,decision-api}
             [--responses PATH] [--model NAME] [--revision REV]
             [--endpoint URL] [--api-key-env NAME] [--offline]
             [--experimental-provider] --out PATH [--json]
actseal verify [-h] --lock PATH --calibration PATH --verification PATH
               --provider {fixture,laya,recorded,jev,decision-api}
               [--responses PATH] [--model NAME] [--revision REV]
               [--endpoint URL] [--api-key-env NAME] [--offline]
               [--experimental-provider] --out DIRECTORY [--json]
actseal replay [-h] [--expected-lock-sha256 HEX] [--json] DIRECTORY
actseal demo [-h] [--out NEW_DIRECTORY] [--qualify] [--json]
actseal plan [-h] --max-risk FLOAT --min-coverage FLOAT --alpha FLOAT
             --expected-risk FLOAT --expected-coverage FLOAT
             [--target-pass-probability FLOAT] [--json]
actseal calibrate [-h] --contract PATH --calibration PATH --verification PATH
                  --provider {fixture,laya,recorded,jev,decision-api}
                  [--responses PATH] [--model NAME] [--revision REV]
                  [--endpoint URL] [--api-key-env NAME] [--offline]
                  [--experimental-provider] --out DIRECTORY
                  [--grid FLOAT [FLOAT ...]] [--target-pass-probability FLOAT]
                  [--selection-tail FLOAT] [--json]
actseal qualify [-h] --contract PATH --calibration PATH --verification PATH
                --provider {fixture,laya,recorded,jev,decision-api}
                [--responses PATH] [--model NAME] [--revision REV]
                [--endpoint URL] [--api-key-env NAME] [--offline]
                [--experimental-provider] --out DIRECTORY
                [--grid FLOAT [FLOAT ...]] [--target-pass-probability FLOAT]
                [--selection-tail FLOAT] [--json]
actseal replay-selection [-h] [--json] DIRECTORY
actseal report [-h] --out OUTDIR [--attestation-ref TEXT] [--json] DIRECTORY
```

| Command | Required | Optional |
|---|---|---|
| `lock` | `--contract PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya,recorded,jev,decision-api}`, `--out PATH` | `--responses PATH`, `--model NAME`, `--revision REV`, `--endpoint URL`, `--api-key-env NAME`, `--offline`, `--experimental-provider` (PROVISIONAL, required with `jev` or `decision-api`), `--json` |
| `verify` | `--lock PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya,recorded,jev,decision-api}`, `--out DIRECTORY` | `--responses PATH`, `--model NAME`, `--revision REV`, `--endpoint URL`, `--api-key-env NAME`, `--offline`, `--experimental-provider` (PROVISIONAL, required with `jev` or `decision-api`), `--json` |
| `replay` | `DIRECTORY` (positional bundle directory) | `--expected-lock-sha256 HEX`, `--json` |
| `demo` | `--out NEW_DIRECTORY` unless `--qualify` | `--qualify`, `--json` |
| `plan` | `--max-risk FLOAT`, `--min-coverage FLOAT`, `--alpha FLOAT`, `--expected-risk FLOAT`, `--expected-coverage FLOAT` | `--target-pass-probability FLOAT`, `--json` |
| `calibrate` | `--contract PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya,recorded,jev,decision-api}`, `--out DIRECTORY` | `--responses PATH`, `--model NAME`, `--revision REV`, `--endpoint URL`, `--api-key-env NAME`, `--offline`, `--experimental-provider`, `--grid FLOAT [FLOAT ...]`, `--target-pass-probability FLOAT`, `--selection-tail FLOAT`, `--json` |
| `qualify` | `--contract PATH`, `--calibration PATH`, `--verification PATH`, `--provider {fixture,laya,recorded,jev,decision-api}`, `--out DIRECTORY` | `--responses PATH`, `--model NAME`, `--revision REV`, `--endpoint URL`, `--api-key-env NAME`, `--offline`, `--experimental-provider`, `--grid FLOAT [FLOAT ...]`, `--target-pass-probability FLOAT`, `--selection-tail FLOAT`, `--json` |
| `replay-selection` | `DIRECTORY` (positional calibration directory) | `--json` |
| `report` | `DIRECTORY` (qualification root or bundle), `--out OUTDIR` | `--attestation-ref TEXT`, `--json` |
| root | `COMMAND` | `--version` (root only), `-h`/`--help` |

Rules that apply to every command:

- **No abbreviated options.** `--ou` is never `--out`; an abbreviation is a
  usage error on the root parser and on every subcommand. Spell options in
  full in scripts.
- `-h`/`--help` is accepted at the root and at every command and prints text.
  `--version` is accepted only at the root (`actseal --version`); after a
  command it is a usage error.
- `--provider fixture` requires `--responses PATH`; `--provider laya` and
  `--provider jev` reject `--responses`. `--offline` is accepted by both
  stable providers: for `laya` it selects the prepared offline cache, for
  `fixture` it states the adapter's existing network-free behaviour and
  changes nothing.
- The **stable** provider choices are `fixture`, `laya` and (in v2) `recorded`; they need no
  opt-in and reject `--experimental-provider` as a usage error. `jev` is the
  PROVISIONAL experimental cloud adapter: collection commands accept it only
  as `--provider jev --experimental-provider`. Without the flag the command is
  a usage error (`ERROR` 3) raised before any provider is built, any
  environment variable is read or any request is made. `jev` with `--offline`
  is a setup error (`ProviderSetupError`, `ERROR` 3) raised by the adapter
  before it reads `JEV_API_KEY`; the adapter has no offline mode. `replay`
  and `demo` do not accept `--experimental-provider` at all and never load the
  adapter. The flag adds no receipt field: the recorded `model_identity`
  already names the provider. The adapter, its flag and its behaviour may
  change or be removed in any release; see [providers](providers.md) and the
  [stability manifest](stability.md).
- Output paths must be **new**. `lock --out`, `verify --out`, `calibrate --out`,
  `qualify --out` and `demo --out`
  refuse an existing file, directory or symlink and never overwrite; the parent
  directory must already exist.
- Usage diagnostics name options, metavars and accepted choices. They never
  echo a command-line value, a path supplied by the operating system, a raw
  response body or arbitrary exception text.

## Exit codes

| Exit | Status | Meaning |
|---|---|---|
| 0 | `PASS` | Valid evidence satisfies the frozen contract. |
| 1 | `BLOCK` | Valid evidence establishes a risk or coverage limit violation, or a canonical fault violated its required action. |
| 2 | `INCONCLUSIVE` | Valid evidence proves neither `PASS` nor `BLOCK`. |
| 3 | `ERROR` | Invalid or incomplete evidence, a usage or setup error, an existing destination, an operating-system failure or an invalidated native-worker experiment. |

Commands without a verification verdict have separate success semantics:

- `lock` has no verdict; it exits 0 when the lock was sealed and written.
- `demo` exits 0 only when its deliberately bad run is `BLOCK`, its fixed run
  is `PASS` and both fresh replays equal the recorded verdicts. Any other
  outcome is `ERROR` 3; the demo never relabels its bad run as a success.
- `plan` exits 0 when a scheduled verification size reaches the target, or 2
  with `planning.not_reachable` when none does through 10,000.
- `calibrate` and `replay-selection` exit 0 when a threshold is selected, or 2
  with `calibration.no_threshold` when none qualifies. Successful selection
  has status `SELECTED`; only verification can supply PASS.
- `qualify` and `demo --qualify` return the verification verdict's exit code,
  or 2 before verification when no threshold qualifies.

`verify` and `replay` map the verdict directly to the exit code. A faithful
replay of `BLOCK` evidence therefore exits 1, and a faithful replay of a
diagnostic `ERROR` bundle exits 3. In a shell or CI step that stops on a
nonzero exit, inspect the recorded status instead of treating that exit as a
tool failure. Usage errors always exit 3, never argparse's default 2.

## Text and JSON output

Without `--json`, the report is human-readable text on stdout; warnings,
captured failure counts and advisory notes go to stderr. That wording is not a
stable interface. With `--json`, exactly one JSON object is written to stdout
and nothing else; warnings and failures become fields of that object.

Every JSON receipt, including every error and usage error, carries
`schema_version` (the integer `1`) and `command` (`lock`, `verify`, `replay`,
`demo`, or `actseal` when no command could be parsed). The field set of each
receipt shape is frozen for 1.x; no field is added to an existing shape within
1.x. The new v2 commands use their own command names and schema document;
existing receipt field sets remain unchanged.

| Receipt | Fields |
|---|---|
| any error | `schema_version`, `command`, `exit_code` (3), `ok` (false), `status` (`"ERROR"`), `error` (sanitized message) |
| `lock` | `schema_version`, `command`, `exit_code` (0), `ok`, `lock_sha256`, `implementation_sha256`, `replay_engine_version`, `evidence_scope`, `contract`, `model_identity` {`provider`, `model`, `revision`, `adapter_version`, `normalizer_version`}, `verification_cases`, `calibration_cases`, `out` |
| `verify` | `schema_version`, `command`, the verdict fields (`status`, `reasons`, `total`, `accepted`, `errors`, `risk` {`lower`, `upper`}, `coverage` {`lower`, `upper`}, `evidence_scope`, `lock_sha256`), `failures` (failure code to count), `warnings` (warning code to count), `faults` (scenario id to {`action`, `expected_action`}), `exit_code`, `ok`, `out` |
| `replay` | `schema_version`, `command`, the verdict fields, `exit_code`, `ok`, `bundle`, `expected_lock_sha256` (string or null), `notes` (array of advisory strings; the actseal 0.1.0 legacy guidance when applicable, otherwise empty) |
| `demo` | `schema_version`, `command`, `exit_code`, `ok`, `status` (`PASS` or `ERROR`), `evidence_scope` (`demo`), `demo_only` (true), `note`, `out`, `duration_s`, `runs` {`bad`, `fixed`}; each run holds the verdict fields, `failures`, `warnings`, `faults`, `expected_status`, `as_expected`, `lock`, `evidence`, `replay` (a verdict object) and `replay_matches`, and has no `exit_code`, `ok` or `out` of its own |

`ok` is always `exit_code == 0`. Path-valued fields (`out`, `bundle`, `lock`,
`evidence`) echo the caller's own arguments; their formatting is not frozen.
`duration_s` is a measurement, not a performance promise.

### New qualification receipts

Each carries `schema_version`, `command`, `exit_code` and `ok`.

| New receipt | Additional fields |
|---|---|
| `plan` | `status` (`PLANNED` or `INCONCLUSIVE`), `verification_cases` (integer or null), `max_verification_cases` (10000), `target_pass_probability`, `assumptions` (risk/coverage limits, alpha, expected risk/coverage), `reason` |
| `calibrate` | `status` (`SELECTED` or `INCONCLUSIVE`), `out`, `calibration`, `contract` (path or null), `calibration_manifest_sha256`, `selection` (threshold or null, reason, every grid point's counts and predicted probability) |
| `qualify` | All calibration fields plus `lock_sha256`, `evidence`, `qualification`, `verdict` (existing verdict, failure/warning counts and fault summary); the four added fields are null when selection finds no threshold |
| `replay-selection` | `status` (`SELECTED` or `INCONCLUSIVE`), `out`, `selection` |
| `demo --qualify` | All qualification fields plus `mode` (`qualify`), `demo_only` (true), `evidence_scope` (`demo`) and `note` |

New-command errors retain the same six error fields listed above, using the
new command name. `ok` still means `exit_code == 0`. See the
[new receipt schema](schemas/qualification-cli-receipt.schema.json) for the
exact nested fields and types.

## `plan`

```bash
actseal plan --max-risk 0.05 --min-coverage 0.5 --alpha 0.05 \
  --expected-risk 0.01 --expected-coverage 0.8 --target-pass-probability 0.8
```

Reports the first scheduled verification size reaching the target pass
probability under the supplied expected risk and coverage, or "not reachable
within 10,000". The default target is `0.8`. No files are written and no
provider is constructed. The schedule is every size through 200, steps of 5
through 500, steps of 25 through 2,000, then steps of 100 through 10,000.
Because integer counts make the pass probability nonmonotone, the scan does
not claim a minimum among skipped sizes. This is a planning calculation.

## `calibrate` and `qualify`

Both accept the same contract, input split and provider options as `lock`,
plus `--grid FLOAT [FLOAT ...]`, `--target-pass-probability FLOAT` and
`--selection-tail FLOAT`. The default grid is `0.5 0.6 0.7 0.8 0.9 0.95 1.0`,
the target is `0.8`, and the selection tail is `0.05`. A supplied grid must
contain 1..32 strictly increasing values in `(0, 1]`. Choose it before
calibration, never from observed scores. The input contract remains ordinary
TOML: its required threshold is ignored during selection and replaced only
in the derived `contract.toml`.

The commands validate both splits and their separation before collection,
then write and hash `selection_plan.json` in a sibling staging directory
before capturing calibration responses. The completed calibration output is
published with an exclusive atomic rename; failed staging is removed.
Verification size is the supplied verification split's case count.
The selector uses calibration labels and outcomes only. The selected point
accepts the most calibration cases among candidates reaching the target;
ties choose the higher threshold.

Under the new `--out` directory, `calibration/` contains exactly
`selection_plan.json`, `calibration.jsonl`, `records.jsonl`, `selection.json`
and `manifest.json`. On successful selection, `contract.toml` contains the
selected threshold. No qualifying threshold produces exit 2 with
`calibration.no_threshold`, no derived contract and no verification responses.

`qualify` continues with the existing lock and verify flow on the verification
cases, creating `lock.json`, the seven-file `evidence/` bundle and
`qualification.json`. The last file links the exact calibration manifest file
SHA-256, the ordinary lock self-seal and the verdict. This adds no statistic to
PASS. All five providers work through the same interface. Fixture and recorded
inputs must cover both splits in one response file so their complete identity
stays unchanged. Provider setup and input changes fail explicitly.

## `replay-selection`

Reads the five-file calibration directory, validates its strict manifest,
rebuilds requests and outcomes from captured records, recomputes all grid
counts and calls the pure selector again. It imports no adapter and collects
no response. The plan's engine must be supported; the running implementation
fingerprint must equal the plan's producer fingerprint, or both fingerprints
must be registered for that engine in the existing packaged registry. New
calibration collection still requires the exact running fingerprint. Counts,
reason and selected threshold must match exactly.
Predicted probabilities use absolute tolerance `1e-10` and relative tolerance
`1e-9` for platform differences in `math.lgamma`; a different selected
threshold always fails. Invalid evidence exits 3. Like verification replay,
this establishes internal consistency, not authentication or proof of when
the selection plan existed.

## `lock`

```text
actseal lock [-h] --contract PATH --calibration PATH --verification PATH
             --provider {fixture,laya,jev} [--responses PATH] [--offline]
             [--experimental-provider] --out PATH [--json]
```

Reads and validates the contract TOML and both labelled JSONL splits, builds
the provider only to observe its identity, closes it, seals the lock and writes
one canonical lock document to the new file `--out`. No decision request is
sent. The receipt reports `lock_sha256`, the producer `implementation_sha256`,
`replay_engine_version` (`actseal-choice-v1`), the contract name and scope,
the observed model identity and both case counts.

## `verify`

```text
actseal verify [-h] --lock PATH --calibration PATH --verification PATH
               --provider {fixture,laya,jev} [--responses PATH] [--offline]
               [--experimental-provider] --out DIRECTORY [--json]
```

Decodes the lock, validates its seal and replay-engine compatibility, checks
that the supplied splits match the locked inventories, requires the requested
provider to equal the locked provider and the running package to be the exact
producer implementation, builds the provider, compares its complete observed
identity with the locked identity, captures every locked verification case
exactly once in lock order at the fixed 30-second request deadline, runs the
six canonical faults, assesses and publishes one new bundle under `--out`.

A setup failure before collection exits 3 without a bundle. Captured provider
failures during collection are terminal case records, not setup failures; the
run continues and the verdict decides their meaning. There is no deadline
override, retry, restart or replacement sample.

## `replay`

```text
actseal replay [-h] [--expected-lock-sha256 HEX] [--json] DIRECTORY
```

Recomputes the verdict of the bundle in `DIRECTORY` from its seven files
without importing a provider, loading a model or contacting a network. The
exit code is the recomputed verdict's code. Invalid evidence is an `ERROR`
verdict whose `reasons` name the violated invariant (for example
`integrity.bundle_hash` or `integrity.legacy_schema`); wrong Python-level
argument shapes such as a malformed digest are also exit 3.

`--expected-lock-sha256 HEX` compares the bundle's lock digest with a
64-character lowercase hex digest you obtained through a separately trusted
channel. A mismatch is `ERROR` with reason `integrity.expected_lock`. Reading
the digest out of the bundle you are checking provides no independent anchor,
and even a matching trusted digest does not authenticate response records or
prove execution took place.

A bundle written by actseal 0.1.0 (schema 1) is `ERROR` with reason
`integrity.legacy_schema`; the receipt's `notes` carry the pinned-replay
guidance from the [migration guide](migration.md).

## `demo`

```text
actseal demo [-h] [--out NEW_DIRECTORY] [--qualify] [--json]
```

Copies the packaged authored support-triage inputs into `NEW_DIRECTORY/inputs`,
then for each of the runs `bad` and `fixed` creates a lock bound to the
installed implementation, collects all 128 cases once, runs the six faults,
assesses, writes `NEW_DIRECTORY/<run>/evidence` and replays it against the
lock's digest. Every count, interval and verdict in the output is computed at
run time. The data is synthetic (`evidence_scope=demo`): it is not a population
benchmark, a trained or repaired model, or deployment certification. The
[example README](../examples/support_triage/README.md) documents the authored
rules.

With `--qualify`, runs the packaged synthetic calibration/verification
example instead. Its 64 calibration cases and 100 separate verification
cases have authored labels and responses; the default grid selects `0.95`
and the existing verifier computes PASS under maximum risk `0.2`, minimum
coverage `0.5` and alpha `0.05`. `--out` is optional only in this mode: when
omitted, the command chooses and prints a new temporary directory, retaining
the evidence for replay. Without `--qualify`, `--out` remains required and the
original demo behavior and receipt are unchanged.

## Related

- [Quickstart](quickstart.md): the three commands against the published
  package.
- [Concepts](concepts.md): what decisions, verdicts and scopes mean.
- [Python guide](python-api.md): the same protocol from Python.
- [Providers](providers.md): fixture and native Laya setup and limits.
