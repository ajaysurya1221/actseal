# Native CLI integration receipt — 6 October 2026

Status: **PASS for integration; the frozen statistical verdict is BLOCK.**
Independent executor/reviewer: Codex. Candidate `434c682352d19e64c6349cb5a7aac44fa7554156` integrates accepted
T50 `286ae67` (merge `7e696c5`). Implementation fingerprint
`cd3a0976cf7886616f1fdf565c914f30d0c82cac530e7b9ffc4119e3a90300a7`.
This is a real cached native product run, not a fixture response or upstream-only
smoke. No policy, threshold, data or model change and no retry was made.

## Environment and preparation

macOS26.6.2 arm64 (build25G83), Python3.12.13, uv0.12.5. `uv sync --frozen
--group dev --extra laya` exited0; optional dependencies were installed from the
prepared cache separately from execution. Both offline environment flags were1.
The existing pinned checkpoint cache was used; no model download was part of the
run. Library offline flags are not OS network isolation.

Observed provider identity: `convaiinnovations/laya-typed-decisions` revision
`e929ae5cf69bc34259cd2f95c9e91145b818b1f0`, adapter/normalizer1. All five artifact
hashes match [the pinned inventory](../../docs/dependencies.md), including weights
`4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e`.
CPU/torch.float32/four threads/eager; compile=False, fast=False, max_len1024,
head_max_len256. Observed laya0.3.28, torch2.14.1, transformers5.18.0,
huggingface_hub1.33.0, safetensors0.8.0 and numpy2.5.3. The accepted T30 adapter,
normalizer and native-test source bytes remain unchanged; its separate macOS and
Ubuntu/Python3.12 receipts remain applicable. No native Python3.13 claim.

## Executed workflow

From the repository root, a fresh ignored parent was created at
`plan/local-receipts/T70-native-434c682`. The CLI received absolute equivalents
of these paths. Each command ran once; nonzero statistical exit1 was retained.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya actseal lock \
  --contract examples/support_triage/fixed.toml \
  --calibration examples/support_triage/fixed_calibration.jsonl \
  --verification examples/support_triage/fixed_verification.jsonl \
  --provider laya --offline --out plan/local-receipts/T70-native-434c682/lock.json --json

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya actseal verify \
  --lock plan/local-receipts/T70-native-434c682/lock.json \
  --calibration examples/support_triage/fixed_calibration.jsonl \
  --verification examples/support_triage/fixed_verification.jsonl \
  --provider laya --offline --out plan/local-receipts/T70-native-434c682/evidence --json

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya actseal replay \
  plan/local-receipts/T70-native-434c682/evidence \
  --expected-lock-sha256 9abbd4b0ef47bb05efff1df1d4d5deb974b40ee72be49b6afe806665367d4267 --json
```

| Command | Exit / result | Whole-process elapsed |
|---|---|---|
| lock | 0;12 calibration and128 verification cases | 6.445s |
| verify | 1; BLOCK | 13.821s |
| replay | 1; same BLOCK, counts, bounds and reasons | 0.093s |

All128 scheduled records contain valid model responses and ABSTAIN decisions;
selected normalized probabilities range0.47535246475352466 to0.8766, below the
fixed0.90 threshold. Thus total128/accepted0/wrong0, risk[0,1], coverage
[0,0.033655210093607835]. Reasons are `coverage.below_minimum` and
`risk.no_accepted_cases`. This is not zero-error evidence: no action was accepted.
All six canonical faults match their specified actions. No provider failures;
the checkpoint calibration warning remains visible on128 records and27 carry
normalize.renormalized. These are authored demo inputs, not a population/model
accuracy benchmark. Elapsed times are single workflow receipts, not latency claims.

Lock SHA256: `9abbd4b0ef47bb05efff1df1d4d5deb974b40ee72be49b6afe806665367d4267`.
The evidence contains exactly seven files. Local raw captures and command receipt
remain ignored; public file hashes below identify the checked bundle.

```json
{
  "calibration.jsonl": "9d14aaa72bc82d7abafb6d4f7f848407d8cf9f6559f89c9d85e5478ff11f6e2d",
  "faults.jsonl": "5d787e3257e2c8dc671b2555bbe3016e65b77f4c391c7e4817323d4a6f760548",
  "lock.json": "661b57c0017bd26879f1ab2533e3ff8d3b7af658e8cc248abbfb0d0fd6834997",
  "manifest.json": "dd984adfa5559e9c2f3509dbe53c42b6e4d8d5cd42e430631d980d8c04c38ddc",
  "records.jsonl": "538ea9388fc5e693a31b18dea1c1d9edc2014c223f48ae78c287980c0b7091e5",
  "verdict.json": "6ea989aa4101df87c79f637b249672099b741ffc3afd368fe801c9cad1ab3d2d",
  "verification.jsonl": "3a8d7f929afead3a27fe86c36fcba8c48f9c7803970c9c2935ee855eabf40fe4"
}
```

No paid inference API, Jev request or model training was used. Incremental paid
API spend: $0. This receipt closes native CLI integration only; T60 adversarial
acceptance, final artifacts/hosted CI and publication remain separate gates.
