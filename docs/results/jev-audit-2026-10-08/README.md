# Preregistered Jev audit — 8 October 2026

Collection: COMPLETE.
Verification: INCONCLUSIVE (`evidence.insufficient`).
Evidence scope: demo; finite public benchmark.

## Producer and identity

Produced by the unreleased benchmark snapshot
`d3edbab2dfbd44a0e9e272e1671143517832e3b4`, using Python 3.12.13.

This is not evidence produced by the published Actseal 1.0.0 package.
The snapshot reports package metadata 0.1.0 but is not the released
0.1.0 artifact either. Its lock and manifest use schema 2.

Producer fingerprint:
`167038cb709ff839f26a21ef55cc63ebd988d797ac56e82d0227ecad1a08eb7c`
Replay engine: `actseal-choice-v1`

Preregistration seal:
`c7bbc52585acb7b2029aff846f4432659d4026134bd0828ab695fb0cf7901a2c`
Lock seal:
`e901ad5ebdfdb2b81b97517a72b320eb29cda1588c2b7496e4cc43091034a87a`

Provider target: `jev-1.13.0`.
The returned model version is a vendor claim; weights are not attested.

Run id: `ec3877960b376021ce4c81110dad353c` (`run.json`).
Fingerprint, engine and provider target are recorded in `evidence/lock.json`
(`implementation_sha256`, `replay_engine_version`, `model_identity`).

## Frozen protocol

Banking77 revision `57ec275d8078af65b7731c2a98be812d844a6d6b`.
First 16 labels in case-sensitive sort; frozen selection and deduplication.
320 calibration cases, followed by 639 verification cases.
One attempt per case; no retries, replacement or threshold fitting.

Threshold 0.80; maximum risk 0.05; minimum coverage 0.50.
Family alpha 0.05; each CP tail 0.0125.
90-minute collection budget.

The protocol is [ADR 0018](../../decisions/0018-finite-benchmark-audit.md);
the verdict rules are in the [statistical contract](../../statistical-contract.md#verdict-rules).
The frozen inputs are in `inputs/`.

## Results

Per-cohort counts and descriptive metrics. Source: `audit_receipt.json`,
`cohorts.calibration` and `cohorts.verification` (the calibration summary is
repeated in `calibration_sidecar.json`, `summary`). The two cohorts are never
pooled.

| Metric | Calibration | Verification |
|---|---:|---:|
| Scheduled / captured | 320 / 320 | 639 / 639 |
| Started without capture / unattempted | 0 / 0 | 0 / 0 |
| Valid normalized answers | 316 | 634 |
| Failures (`malformed_response`) | 4 | 5 |
| ACT / ABSTAIN / ESCALATE / DENY | 293 / 23 / 4 / 0 | 580 / 54 / 5 / 0 |
| Wrong ACT | 12 | 24 |
| Coverage (ACT / scheduled) | 0.915625 | 0.9076682316118936 |
| Accepted error (wrong ACT / ACT) | 0.040955631399317405 | 0.041379310344827586 |
| ECE | 0.03363924050632909 | 0.030173501577286977 |
| Multiclass Brier | 0.10820316455696202 | 0.11178990536277601 |
| Input / output tokens | 236,050 / 59,275 | 471,217 / 118,394 |

Verification risk: 24/580;
CP interval [0.02498087158203282, 0.06393316057415596].

Verification coverage: 580/639;
CP interval [0.8787825228681747, 0.9316794056630708].

Source for both intervals: `evidence/verdict.json` (repeated in
`audit_receipt.json`, `verification_bundle.verdict`).

The risk upper bound exceeds 0.05, so PASS is unavailable. The risk lower
bound is below 0.05 and the coverage upper bound exceeds 0.50, so statistical
BLOCK is unavailable. The six synthetic fault scenarios reproduce their
required actions.

The frozen policy acted on 580 of 639 verification cases, making 24
label-disagreement errors among those actions. Its observed accepted error
rate was 4.14%.

The gate nevertheless cannot establish the requested maximum risk of 5%: its
risk interval extends from 2.50% to 6.39%. It also cannot establish that risk
exceeds 5%, because the lower bound remains below that limit. Coverage clears
its requirement.

**INCONCLUSIVE means the completed evidence supports neither PASS nor BLOCK
under the frozen rule.** It does not mean the collection failed, that the
policy passed because its point estimate was below 5%, or that the model was
demonstrated to violate the limit.

This is useful public evidence because it exposes the complete result,
including abstentions, rejected responses and uncertainty, without changing
the threshold or enlarging the sample after seeing the outcome. Its scope
remains a fixed 16-intent Banking77 subset, with `evidence_scope: demo`. The
CP calculations do not turn that subset into IID deployment evidence. No
permission-calibration, label-truth, training-exclusion or safety claim
follows.

## Reliability and failures

All ten reliability bins for each cohort, copied from `audit_receipt.json`
(`cohorts.<cohort>.reliability_bins`). Empty bins keep `null` mean and
accuracy.

Calibration (316 valid normalized answers):

| Bin | Range | Count | Mean selected probability | Accuracy |
|---:|---|---:|---:|---:|
| 0 | [0.0, 0.1) | 0 | null | null |
| 1 | [0.1, 0.2) | 0 | null | null |
| 2 | [0.2, 0.3) | 0 | null | null |
| 3 | [0.3, 0.4) | 1 | 0.36 | 0.0 |
| 4 | [0.4, 0.5) | 2 | 0.43000000000000005 | 0.5 |
| 5 | [0.5, 0.6) | 7 | 0.5528571428571428 | 0.2857142857142857 |
| 6 | [0.6, 0.7) | 7 | 0.6442857142857142 | 0.42857142857142855 |
| 7 | [0.7, 0.8) | 6 | 0.7333333333333334 | 0.8333333333333334 |
| 8 | [0.8, 0.9) | 20 | 0.8404999999999999 | 0.7 |
| 9 | [0.9, 1.0] | 273 | 0.9902564102564102 | 0.978021978021978 |

Verification (634 valid normalized answers):

| Bin | Range | Count | Mean selected probability | Accuracy |
|---:|---|---:|---:|---:|
| 0 | [0.0, 0.1) | 0 | null | null |
| 1 | [0.1, 0.2) | 0 | null | null |
| 2 | [0.2, 0.3) | 1 | 0.24 | 1.0 |
| 3 | [0.3, 0.4) | 1 | 0.36 | 0.0 |
| 4 | [0.4, 0.5) | 3 | 0.4666666666666666 | 0.6666666666666666 |
| 5 | [0.5, 0.6) | 17 | 0.5411764705882353 | 0.5882352941176471 |
| 6 | [0.6, 0.7) | 17 | 0.6582352941176471 | 0.5882352941176471 |
| 7 | [0.7, 0.8) | 15 | 0.7553333333333333 | 0.7333333333333333 |
| 8 | [0.8, 0.9) | 27 | 0.8444444444444444 | 0.7037037037037037 |
| 9 | [0.9, 1.0] | 553 | 0.9914828209764918 | 0.9710669077757685 |

ECE uses selected-option probability and selected-choice correctness
over all valid normalized answers, including below-threshold answers.
Bins are [0,0.1), ..., [0.9,1], using the frozen float comparisons.

Brier is the mean sum of squared errors across all 16 probabilities;
it is not divided by 16 and has range [0,2].

ECE and Brier were recomputed from the stored records (`evidence/records.jsonl`,
`calibration_sidecar.json` and the labels in `inputs/`) without the producer's
metric code. The recomputed bin counts are identical, ECE agrees within 2e-15
and Brier within 1e-16; the differences are floating-point summation order.

Four calibration and five verification responses failed the frozen
probability-mass check. They remain in coverage denominators and are
excluded from probability-based descriptive metrics.

All nine failures are `malformed_response`: the returned probabilities sum to
approximately 0.99, outside the frozen `1e-12` tolerance, so each became
ESCALATE. The gate uses the selected option's probability (at least 0.80),
never vendor confidence or a substituted argmax.

The six fault cases are synthetic checks, separate from live requests.

## Collection accounting and cost

959 captured; zero started-without-capture; zero unattempted.
Journal: 1,920 complete rows; no torn tail.
Recorded duration: 336.150245708 seconds.
Budget exceeded: false; late captures: zero.

Input tokens: 707,267. Output tokens: 177,669.
Measured monetary spend / account-credit change: unknown.

Source: `audit_receipt.json` (`partition`, `journal`, `budget`, `spend`);
recorded collection start `2026-10-07T19:55:14Z` (`run.json`, collector clock).
The 1,920 journal rows are 959 attempt-start/capture pairs plus the
budget-start and run-end rows (`journal.jsonl`).

At the vendor’s published rate of USD 0.042 per million input tokens, with output tokens free, the recorded usage corresponds to an estimated USD 0.029705214, approximately USD 0.03. Account-credit change was not measured; this is not a billing receipt.

Tariff source: the vendor's [model documentation](https://docs.typesafe.ai/models),
as checked at review on 8 October 2026.

## Verification

From the actseal checkout containing the published result directory:

```bash
# Interpreter setup; may require a download.
uv python install 3.12.13
audit_python="$(uv python find 3.12.13)"

audit="$(pwd)/docs/results/jev-audit-2026-10-08"
(cd "$audit" && shasum -a 256 -c SHA256SUMS)

snapshot="$(mktemp -d)"
tar -xzf "$audit/producer-source.tar.gz" -C "$snapshot"

"$audit_python" -B -c \
  'import sys; assert sys.version_info[:3] == (3, 12, 13)'

PYTHONPATH="$snapshot/src" "$audit_python" -B \
  "$snapshot/bench/jev_audit/run.py" \
  --check-receipts "$audit"

PYTHONPATH="$snapshot/src" "$audit_python" -B -m actseal \
  replay "$audit/evidence" \
  --expected-lock-sha256 \
  e901ad5ebdfdb2b81b97517a72b320eb29cda1588c2b7496e4cc43091034a87a \
  --json
```

Expected: checksum success; receipt checker **exit 0**, `COMPLETE`,
`consistent: true`; replay **exit 2**, `INCONCLUSIVE`. Replay's `ok: false`
reflects the verdict and is not evidence of reconstruction failure.

For independent upstream selection verification, after obtaining the public
source:

```bash
source_repo="$(mktemp -d)"
git clone https://github.com/PolyAI-LDN/task-specific-datasets "$source_repo"
git -C "$source_repo" checkout --detach \
  57ec275d8078af65b7731c2a98be812d844a6d6b

source_cache="$(mktemp -d)"
cp "$source_repo/LICENSE" "$source_repo/README.md" "$source_cache/"
cp "$source_repo/banking_data/"{categories.json,train.csv,test.csv} \
  "$source_cache/"

PYTHONPATH="$snapshot/src" "$audit_python" -B \
  "$snapshot/bench/jev_audit/run.py" \
  --check-preregistration \
  --data "$audit/inputs" \
  --source "$source_cache"
```

Expected: **exit 0**, `source_verified: true`, findings `[]`. These commands
reconstruct stored evidence; they do not repeat live collection.

Replaying `evidence/` with the published Actseal 1.0.0 package instead of
the snapshot returns ERROR `integrity.lock` (exit 3): this producer
fingerprint is not in the compatibility registry. No registry entry is
added for this publication. A future cross-release entry needs a separate
exact-producer/verifier compatibility review and archived-evidence regression
tests, as [ADR 0015](../../decisions/0015-v1-stability-and-replay-compatibility.md)
requires. Generic bundle replay would still not check the journal, receipt
and sidecar; only the snapshot's `run.py --check-receipts` does.

## Package contents

| Path | Content |
|---|---|
| `run.json` | Run id, seals, recorded start, interpreter version |
| `journal.jsonl` | Attempt-start and capture rows for every request, plus budget rows |
| `audit_receipt.json` | Overall receipt: partition, budget, per-cohort metrics, verdict |
| `calibration_sidecar.json` | Calibration cohort records and summary |
| `evidence/` | Ordinary verification bundle: `lock.json`, `manifest.json`, `records.jsonl`, `calibration.jsonl`, `verification.jsonl`, `faults.jsonl`, `verdict.json` |
| `inputs/` | Frozen inputs: `preregistration.json`, `lock.json`, `contract.toml`, `calibration.jsonl`, `verification.jsonl`, `BANKING77_LICENSE` |
| `producer-source.tar.gz` | Producer and checker source from `d3edbab` |
| `ATTRIBUTION.md` | Banking77 attribution, citation and selection changes |
| `SHA256SUMS` | Publication-time inventory of every other file here |

The 17 run files (`run.json`, `journal.jsonl`, `audit_receipt.json`,
`calibration_sidecar.json`, `inputs/`, `evidence/`) are byte-for-byte copies
of the accepted run directory: 4,337,368 bytes.

`producer-source.tar.gz` contains only tracked bytes of commit `d3edbab`
(`LICENSE`, `NOTICE`, `src/actseal/`, `bench/jev_audit/`, paths preserved),
built with
`git archive d3edbab LICENSE NOTICE src/actseal bench/jev_audit | gzip -n`.
SHA-256 of the archive:
`17cec4aa8bd9abc54476522ec997ad2a6a3fcaec8834d4b741a44fe4737eef76`; of the
uncompressed tar stream:
`7026872b912de74a957847eb45fde0b7c1a3b0ddd2b53f681cf2a7a9d3a8c4a9`. Another
`gzip` implementation may compress the same tar stream to different bytes.

`SHA256SUMS` is a **publication-time inventory**, written when this directory
was assembled. It is not part of the original preregistration and is not an
authentication mechanism.

## Limits and provenance

Fixed benchmark; no IID deployment, permission-calibration, safety,
label-truth or model-training-exclusion claim.
Calibration and verification are reported separately, never pooled.

Hashes and offline reconstruction establish consistency with supplied
records, not authenticated execution or absence of undisclosed calls.

The journal has no hash chain: each attempt-start or capture row binds sequence,
run, preregistration and request identity but not the previous row. The receipt is reconstructed
from the records and compared with the stored bytes; it is not independently
signed. The single-attempt property is verified within the recorded schedule
and the inspected collector only.

## Attribution

Banking77 attribution, citation and the selection changes are in
[ATTRIBUTION.md](ATTRIBUTION.md); the dataset's CC-BY-4.0 license is
[inputs/BANKING77_LICENSE](inputs/BANKING77_LICENSE).

`ATTRIBUTION.md` is copied unchanged from
`bench/jev_audit/data-revision3/ATTRIBUTION.md` at `d3edbab`, where the license
and data files sat beside it; here they are in `inputs/`. Banking77-derived
text also appears in `evidence/`, `journal.jsonl` and
`calibration_sidecar.json`, under the same license. The source archive's code
is Apache-2.0 (its `LICENSE` and `NOTICE`).
