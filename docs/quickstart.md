# Actseal v1 quickstart

**Implementation and quickstart verification pending.** The CLI/demo are release targets; these commands are not yet an executed success receipt. T50 and the release reviewer must replace this notice only after checking the final installed wheel, output paths and measured first-run timing. See [STATE](../plan/STATE.md) and the [release checklist](../plan/RELEASE_CHECKLIST.md).

The intended first run uses packaged synthetic fixtures. It requires Python 3.12+ and the pinned uv toolchain; no model download, credentials or hosted service is required for that path. This source-checkout preview assumes you are in the Actseal repository. It is not yet the final verified wheel-install quickstart.

```bash
uv sync --frozen --group dev
actseal_quickstart_root=$(mktemp -d "${TMPDIR:-/tmp}/actseal-quickstart.XXXXXX")
uv run --frozen actseal demo --out "$actseal_quickstart_root/demo" --json
```

The caller-selected `demo` destination above is new; Actseal must refuse an existing destination. The demo's **target** behavior is to evaluate a deliberately bad fixture as BLOCK, a sufficient corrected fixture as PASS and freshly replay both. Exit 0 is permitted only when those checks succeed. Actual counts, intervals, duration and internal output subdirectory names remain pending; none are asserted here. The release target is a measured fixture workflow within 60 seconds with prerequisites stated.

The demo is authored data with `evidence_scope=demo`. Its result cannot establish local-model accuracy, population performance or production reliability.

## Frozen command shapes

These are interface shapes, not commands with supplied files. Replace `PATH`, `DIRECTORY` and `HEX` with your real inputs. Braces indicate a provider choice; square brackets indicate optional arguments.

```text
actseal lock --contract PATH --calibration PATH --verification PATH
             --provider {fixture,laya} [--responses PATH] [--offline] --out PATH
actseal verify --lock PATH --calibration PATH --verification PATH
               --provider {fixture,laya} [--responses PATH] [--offline]
               --out DIRECTORY
actseal replay DIRECTORY [--expected-lock-sha256 HEX]
actseal demo --out NEW_DIRECTORY
```

All commands support `--json`; `python -m actseal` is the required installed-module entrypoint. For fixtures, `--responses` is required. For Laya it is forbidden. Inputs and exact fixture/TOML/JSONL schemas are in [CONTRACTS](../plan/CONTRACTS.md); native setup/pins are in [providers](providers.md) and [dependencies](dependencies.md).

`lock` binds an already chosen policy, labelled splits, observed provider identity and installed implementation. `verify` must reject input/identity mismatches before inference, collect exactly the scheduled cases once, run all six faults and write a new evidence bundle. Neither command may overwrite existing output.

Use an individual evidence-bundle path reported by the eventual demo/verify output when calling `replay`; this document does not guess the demo's final internal directory names. Replay needs no provider, model library, key or network. It must re-evaluate captured data, not rerun inference or simply print a stored verdict. Supply `--expected-lock-sha256` only with an expected lock digest obtained through your trusted channel.

## Interpreting results

| Exit | Status | Meaning |
|---|---|---|
| 0 | PASS | Valid statistical/fault evidence satisfies the frozen contract; lock/demo success also uses 0 as specified above. |
| 1 | BLOCK | Valid evidence establishes a declared limit violation or deterministic fault-contract failure. |
| 2 | INCONCLUSIVE | Valid evidence is insufficient to establish either PASS or BLOCK. |
| 3 | ERROR | Invalid/incomplete evidence, setup/usage failure or an invalidated native-worker experiment. |

Check the structured status and reasons, not only the shell exit. A regular Laya timeout/unavailable must produce `infrastructure.worker_invalidated` with zero counts and `[0,1]` intervals after integrity checks. Every scheduled terminal record remains diagnostic evidence. Such a bundle may replay correctly while remaining ERROR.

The collection protocol fixes normal requests at 30.0 seconds and startup at 120 seconds; there is no timeout override. Do not restart a worker, replace cases or discard ERROR attempts and retry until PASS. The [statistical contract](statistical-contract.md) applies to independent case outcomes over one fixed, prespecified attempt, with no uptime or run-completion-probability claim.

Before using a PASS in an application, verify the expected lock and deploy the same trusted policy/model/runtime. The package cannot force the application to honor its dispositions. Hash consistency and successful replay do not establish authenticity or label truth; read the [threat model](threat-model.md).
