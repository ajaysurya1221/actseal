# Actseal preflight verification receipt

Recorded **2026-10-06**, Asia/Kolkata. This is a pre-implementation/source-feasibility receipt. It is **not** proof that Actseal product tests, packaging, CI, or release acceptance pass.

## Provenance legend

- **PRIMARY TOOL — reuse-audit lane:** this document's author directly read local source, queried GitHub plugin tools, or executed the stated command.
- **SUPPLIED RECEIPT — model-verification lane:** another read-only verifier reported its actual commands/results; this document's author did not repeat them.
- **SUPPLIED RECEIPT — parent orchestrator:** the parent supplied captured user responses, availability checks, or an operational probe; this document's author did not repeat those checks.
- **NOT RUN:** no execution evidence is asserted here. Future product results belong in task REPORT/REVIEW records and [STATE](STATE.md).

## Source reuse checks

**PRIMARY TOOL — reuse-audit lane.** GitHub `get_repo`, `fetch` of `branches/main`, and `fetch_file` for pinned LICENSE/README resources independently established the following public inventory on 2026-10-06. Local clean checkout HEADs matched remote main at inspection time.

| Repository | Immutable commit | License | Metadata version |
|---|---|---|---|
| [agent-reliability-ci](https://github.com/ajaysurya1221/agent-reliability-ci/tree/d13dd94124cb71d378a4e76224fc115b750e8133) | `d13dd94124cb71d378a4e76224fc115b750e8133` | Apache-2.0 | 0.7.0 |
| [evalopt-graph](https://github.com/ajaysurya1221/evalopt-graph/tree/9bbc192443dc713f0f3344939a441c4a66e8a44d) | `9bbc192443dc713f0f3344939a441c4a66e8a44d` | MIT | 0.1.0 |
| [frontier-scout](https://github.com/ajaysurya1221/frontier-scout/tree/a28f27da0ae25492af3c3a9f61cb863543dab791) | `a28f27da0ae25492af3c3a9f61cb863543dab791` | MIT | 2.1.0 |
| [dorian](https://github.com/ajaysurya1221/dorian/tree/fb5323068e95e78d387eaa81718945a6725b961d) | `fb5323068e95e78d387eaa81718945a6725b961d` | Apache-2.0 | 1.4.0 |

Versions above come from local `pyproject.toml` at the matching clean commit; they do not independently establish package-index or release status. The public pinned Frontier README explicitly says the repaired verifier is unreleased and v2.1.0 has false acceptance and PR-directory Python-shadowing defects. Its existing release must not be Actseal's acceptance authority. The private shared-brain repository was inspected only for architecture: GitHub reports private visibility, no LICENSE was found locally, and its existing checkout was dirty. Its implementation is not approved for public copying.

ARCI `FROZEN.sha256` contained **48 entries**; independently recomputing all 48 SHA-256 hashes found **zero mismatches**. The parent workspace guidance still mentioning 47 is historical. No frozen files were changed, no `arci gate` command was run against a committed store, and the four public source checkouts remained clean after this audit.

### Independently executed source tests

Working directory: `/Users/ajay/Developer/agent-reliability-ci`, commit `d13dd94124cb71d378a4e76224fc115b750e8133`.

```bash
.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/unit/stats tests/acceptance/test_stats_gate.py
.venv/bin/python -B -m pytest --collect-only -q -p no:cacheprovider tests/unit/stats tests/acceptance/test_stats_gate.py
```

Both commands exited **0**. The executed suite completed at 100% without failures; independent collection reported **115 tests**:

| Source file | Collected |
|---|---:|
| `tests/unit/stats/test_cp_reproducibility.py` | 37 |
| `tests/unit/stats/test_stats.py` | 14 |
| `tests/unit/stats/test_wilson_quantile_pin.py` | 22 |
| `tests/acceptance/test_stats_gate.py` | 42 |

These are **existing ARCI source tests**, not Actseal tests. They establish the reuse baseline, including independent Fraction/Decimal checks and golden CP values. They do not validate the future port, the new risk/coverage gate, or hosted cross-platform reproduction. The intended minimal units are documented in [ADR 0002](../docs/decisions/0002-minimal-attributed-reuse.md).

## Native local-model feasibility

**SUPPLIED RECEIPT — model-verification lane.** The verifier reported a native online load/inference and a second fresh subprocess using cached files with offline library flags. No independent repetition by the reuse-audit lane is asserted.

| Field | Reported observation |
|---|---|
| Host | Mac M5 Pro, 24 GiB unified memory, macOS 26.6.2 |
| Python | 3.12.13 |
| Packages | `laya==0.3.28`, `torch==2.14.1`, `transformers==5.18.0`, `huggingface-hub==1.33.0`, `safetensors==0.8.0`, `numpy==2.5.3` |
| Inference | CPU FP32, four threads, eager backend, `compile=False`, `fast=False` |
| Model | `convaiinnovations/laya-typed-decisions` |
| Pinned revision | `e929ae5cf69bc34259cd2f95c9e91145b818b1f0` |
| Stored weights | 421,293,830 F16 parameters; model file 842,609,220 bytes |
| Model file SHA-256 | `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e` |
| Availability / license | Public ungated weights; Apache-2.0 model card |

| Run | Load seconds | Inference seconds | Peak process RSS bytes | Outcome |
|---|---:|---:|---:|---|
| Online native smoke | 24.104 | 0.276 | 1,867,464,704 | Billing category; exit 0 |
| Fresh cached/offline subprocess | 1.235 | 0.137 | 2,915,975,168 | Same billing category; exit 0 |

Offline subprocess flags were `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. These do not prove OS-level network isolation. The result is **one-case feasibility**, not a quality benchmark, latency distribution, calibration validation, full Actseal integration, or support on other machines. Peak RSS is the reported process metric, not whole-system peak memory.

The native returned probabilities were `0.8085`, `0.0877`, and `0.1039` (sum `1.0001`), requiring a precisely bounded, replayable rounding normalization. A native `choice:11+` warning says `0.10058` was clamped to `0.5` and surfaced on each load. The [pinned model card](https://huggingface.co/convaiinnovations/laya-typed-decisions/blob/e929ae5cf69bc34259cd2f95c9e91145b818b1f0/README.md) still reports calibration using training rows; a notebook fix is not evidence of a checkpoint refit. The verifier characterized the checkpoint as a specialist trained on four synthetic workflows. Preserve these limitations in [providers](../docs/providers.md).

The verifier reported primary checks against PyPI JSON, Hugging Face API/model card, Laya's upstream code license, and the installed safetensors wheel license. PyPI reportedly uploaded Laya 0.3.28 on 2026-10-05 at 18:05 UTC. [dependencies](../docs/dependencies.md) owns the full license inventory; this receipt does not upgrade unchecked transitive licenses to verified status.

## User choices, executor access, and cost

**SUPPLIED RECEIPT — parent orchestrator.** Captured option answers were `Decision Contract (Recommended)` and `Focused two-day v1 (Recommended)`. The user delegated naming; the parent selected Actseal after reported no-exact-match GitHub/web searches and a PyPI 404. No name reservation is claimed. The latest user request, `PLEASE IMPLEMENT THIS PLAN`, authorizes implementation; [DECISIONS](DECISIONS.md) records that approval.

The initial Claude authentication probe returned `loggedIn: false`. The user subsequently completed login; a fresh parent probe confirmed `loggedIn: true`, `authMethod: claude.ai`, `subscriptionType: max`. T00 was dispatched with `--model claude-fable-5-1 --effort high`; implementation acceptance is not established by authentication or dispatch. Record task results in [STATE](STATE.md) and the task REVIEW.

**Recorded paid inference API spend for these checks: USD 0.** The reuse-audit lane made no paid model calls; the model-verification lane reports no paid calls and no key reads. No live Jev call was made. This does not price existing coding-agent subscriptions, local electricity, or future execution.

## Checks not yet established for Actseal

At this receipt's creation, the following are **NOT RUN / NOT ESTABLISHED** for the new product:

1. Product unit/integration tests, Ruff, mypy, pre-commit, or secret scanning.
2. Product build, wheel installation, clean-environment fixture quickstart, or cross-platform CI.
3. Product-level Laya adapter tests, live Jev integration, or separately certified fallback behavior.
4. Reproducible Actseal bundle/replay acceptance, full lockfile/license audit, or source-to-wheel inclusion checks.
5. Public repository creation, green hosted CI, accepted product commits, release tag, and published release.

The earlier feasibility work was read-only with respect to product source and the audited public repositories; it was not filesystem-write-free, because disposable environments and model/cache artifacts may have been populated. This authorized documentation step creates the planning/ADR files. Future execution evidence must be added with its command, revision, environment, result, and provenance rather than retroactively describing this preflight as product acceptance. The authoritative interfaces are in [CONTRACTS](CONTRACTS.md).
