# Task 06 source verification — no inference

Status: source verification complete. Task 06 implementation, concrete preregistration and live collection remain pending. No provider was called.

Codex retrieved the public dataset through the GitHub API and checked each size and Git blob SHA-1 against the exact pinned tree. The bytes are cached outside the repository. A separate reviewer recomputed all five blob hashes and SHA-256 values, read the full README and LICENSE, and independently reproduced the selection. This is source evidence, not model evaluation evidence. The separately denied font/tool downloads were not retried or bypassed.

## Source identity

- Repository: https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b
- Commit: `57ec275d8078af65b7731c2a98be812d844a6d6b`.
- Tree: `05eb3f1c7b43a6e1f2b8576b882115423e9031e3`.
- Source committer date: `2022-04-29T12:23:20Z`; observation: 6 October 2026 UTC / 7 October IST.
- Local cache: `/tmp/actseal-v1-orchestration/banking77-source-57ec275d/`.

LICENSE and README.md are repository-root files. The other three original paths are under `banking_data/`.

| Cached file | Bytes | SHA-256 |
| --- | ---: | --- |
| `LICENSE` | 18,650 | `7e7170e3cebf88a9f60c7b8421418323c09304da1af4d5e90f4da1dc1c8a2661` |
| `README.md` | 4,735 | `7b9ce9069931cc2de89dce8c7ffb53d07806cf413601ccf133b9af5227b3a373` |
| `categories.json` | 2,036 | `53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63` |
| `test.csv` | 239,961 | `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d` |
| `train.csv` | 839,073 | `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b` |

## License and attribution

The README applies the repository license to the datasets. LICENSE is CC-BY-4.0. Task 06 must retain the license, attribution and disclaimer, identify the selection/deduplication, and include the requested citation: Casanueva et al. (2020), *Efficient Intent Detection with Dual Sentence Encoders*, https://arxiv.org/abs/2003.04807. The dataset license is separate from Actseal's Apache-2.0 code license.

## Selection independently reproduced

The approved rule yields exactly **320 calibration and 639 verification cases**. Original data contains 10,003 training rows, 3,080 test rows and 77 labels. Each selected label contributes 20 calibration cases. Verification has 40 cases per selected label except `atm_support`, which has 39.

```text
Refund_not_showing_up
activate_my_card
age_limit
apple_pay_or_google_pay
atm_support
automatic_top_up
balance_not_updated_after_bank_transfer
balance_not_updated_after_cheque_or_cash_deposit
beneficiary_not_allowed
cancel_transfer
card_about_to_expire
card_acceptance
card_arrival
card_delivery_estimate
card_linking
card_not_working
```

The selected test cohort has 640 original rows and one normalized duplicate, removed at test data-record 1462. Across the entire source, six distinct normalized texts overlap training and test. Selected training records 3104, 3117 and 4577 match test texts and are excluded.

The resulting calibration and verification cohorts each have globally unique normalized texts. Their overlap is zero; calibration also has zero overlap with the entire original test set. No normalized source text carries conflicting labels. Normalization is exactly `text.strip().casefold()` and must not rewrite the original text sent as state.

## Remaining preregistration gate

Freeze the complete calibration order (sorted label order above, then original training-record order within each label), original text bytes, case IDs, question/criteria, provider and producer identities, script hashes, policy and all 959 ordered schedule entries before any request. Verification keeps original test order. Actual journal entries are created only for attempt-start and terminal-capture events; do not fabricate them during preregistration.

These source checks do not establish label truth, absence from model training, population representativeness or statistical power. No live requests or provider spend occurred.
