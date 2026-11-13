# Actseal 2.0 — release proposal

> **Status:** approved by the maintainer on 13 Nov 2026. Roles, deadline and scope order are amended by `plan/v2/CHANGE_LOG.md` (V2-001, V2-002); where the owner columns below say Codex, read Claude Code.

**One line:** Actseal 2.0 answers "how much of this decision can a model make alone at my error limit?" for any decision model, with evidence anyone can replay offline.

**Launch centrepiece:** the first public, replayable comparison of open-weight decision models on that question.

## Context

Actseal 1.0.1 is well engineered and unused: 0 stars, 0 issues, never announced. It answers a narrow question ("does the threshold I already chose pass?") for three providers. The maintainer wants 2.0 to be a release AI builders adopt unprompted, built only by AI agents, without rebuilding what exists.

Decisions already made by the maintainer:

1. Direction: independent qualifier for decision models.
2. A public comparison of open-weight decision models ships in 2.0.
3. Local models only. No paid API runs.
4. Codex plans, reviews and releases. Claude Code builds.

### Why this direction (checked 12 Nov 2026)

| Finding | Consequence |
|---|---|
| Decision models are mainstream: Laya (about 35k stars), Jev, Cloudflare Clef, OpenAI Decisions API, Amazon Strands Decider | v1 bet on the right category |
| Clef and the local server Ollaya are Jev-API compatible | One wire protocol reaches several models |
| No independent comparison exists (sys1bench is gone) | The comparison is an open slot |
| MAPIE 1.6.0 selects thresholds with guarantees but has no CI gate and no evidence file | Actseal does not become a statistics library |
| No tool combines threshold selection, a CI gate and replayable evidence | That combination is the product |

These findings came from web checks on 12 Nov 2026 and were not re-verified in code. Treat external model, server and licence facts as leads until M0 confirms them.

The deep research report (`research/` holds earlier ones; the latest is `~/Downloads/actseal_report_deep_research.md`) was used as a list of leads only. It gave no links, misdescribed v1, and was wrong on LangChain's version and the EU AI Act date.

### What the design review found

A retrospective check on the archived Jev audit (320 calibration cases, 639 verification cases; exploratory only, those splits are spent and must never be published as a result):

| Risk limit | Result |
|---|---|
| 5% | Picking the threshold closest to the limit gives INCONCLUSIVE (17/562, upper bound 5.07%). A slightly stricter threshold passes (16/548, 4.97%) |
| 2% | No threshold passes at this sample size |
| 1% | Unreachable at this sample size, at any threshold (2/427 at threshold 1.0 has upper bound 1.89%) |

Also measured: 205 of the 320 calibration scores are exactly 1.0, with only 39 distinct values.

Three consequences shape the design:

1. The selector must aim for a PASS on the verification split, not for the threshold nearest the limit.
2. A sample-size planner is required, not optional.
3. Stock v1 cannot replay the README's headline audit (`ERROR integrity.lock`). With both fingerprints in an in-memory registry, the current engine reproduces the recorded INCONCLUSIVE (24/580, identical intervals). The engine is compatible; only the registry blocks it.

## What 2.0 ships

### 1. Threshold selection and planning

- `actseal plan`: sample sizes needed for a risk limit, before any model call.
- `actseal calibrate`: picks the threshold from the calibration split.
- `actseal qualify`: plan check, calibrate, verify, report, in one command.
- Existing `lock`, `verify`, `replay`, `demo` stay.

Selection rule: maximum coverage among thresholds whose predicted chance of a verification PASS is at least 0.8 at the locked verification size. The grid (at most 32 points) and the rule are written into the lock before calibration data exists. A grid derived from observed calibration scores is not allowed. If no threshold qualifies, the result is INCONCLUSIVE `calibration.no_threshold` and the verification split is not touched.

What a PASS means: unchanged from v1. Conditional on the calibration data and the selected threshold, with verification cases independent and identically distributed from the declared distribution, independent of calibration, and one prespecified attempt: the chance of a PASS when true risk exceeds `max_risk` is at most alpha/4, and likewise for coverage. This holds for any deterministic selector, so selection adds no new statistics to the PASS.

Public wording: "pre-registered selection, fixed-sample verification". Not "guaranteed", not "certified". The calibration risk-coverage curve is descriptive only.

Not licensed by the design: re-selecting after seeing a verdict; reusing a verification split across limits without accounting for it.

### 2. Any decision model

- `decision-api` profile: the Jev-compatible wire format, with configurable endpoint and model. Built from the existing Jev adapter.
- Native Laya stays.
- `recorded` profile: bring a file of `case_id, choice, score`. Works with any model. Every report marks it "recorded: provider faults not tested".
- Answer shape relaxes to "chosen label plus a score in [0, 1]"; full probabilities become optional.

Rules that keep the relaxed shape safe:

1. The score source is locked per profile, with no per-response fallback.
2. The gating score is never renormalised (v1 divides by the total at `normalization.py:283-286`; at a loose tolerance that can lift a score over the threshold).
3. If probabilities are present, the score must equal the chosen label's probability.
4. New canonical faults cover missing, out-of-range and mismatched scores.

Providers are transport only. `ModelIdentity.provider` becomes free-form provenance. Replay dispatches on a closed `profile` list owned by core and never loads provider code. `verify_run` already takes a `ModelFactory` (`runner.py:127,301`), so no plug-in entry point is needed in 2.0.

### 3. Engine v2 without the replay tax

- `engine_sha256` hashes only the decision kernel (statistics, policy, normalisation, assessment, faults, selection, canonical encoding). Today `__version__` sits in `__init__.py`, so a version bump alone changes the fingerprint.
- The reviewed registry and exact-match collection stay, keyed on `engine_sha256`.
- A golden evidence corpus under `tests/golden/` replays byte-for-byte in CI. Every mutant in `tools/check_mutations.py` must flip at least one golden replay.
- New locks and bundles are schema 3 (nine files: v1's seven plus calibration records and the calibration result). Engine id `actseal-choice-v2`.
- Schema-2 evidence is replayed with `uvx actseal==1.0.2 replay`, the same pattern v1 used for 0.1.0 (`LEGACY_GUIDANCE`).

### 4. Evidence people can show

- `actseal report`: static HTML, Markdown, and a badge JSON file.
- `action.yml`: a GitHub Action that runs `qualify` or `replay`, writes the job summary, uploads the bundle and fails the job on BLOCK.
- Signing uses GitHub artifact attestation (`actions/attest` v4, `gh attestation verify`). No new cryptography.
- Reports print "attested" only when a verified attestation reference is supplied. Local runs say "checksummed".

### 5. The public comparison

- Models: whatever the feasibility spike proves runs locally. Laya natively; Clef 9B and Strands Decider through a local Jev-compatible server if they run and their licences allow.
- Datasets: two or three with at most 16 labels and licences that allow redistribution. Chosen in the spike.
- One primary risk limit per dataset (5% by default; 2% only if the planner shows it is reachable; no 1%). Other limits are labelled secondary.
- Preregistration is sealed and committed before the first capture. Every attempt is published. Draws are fresh and seeded.
- Wording: one statement per cell, no table-wide claim, no "best" or "wins", possible training exposure and non-determinism disclosed.

Headline number per cell: the lower bound on the share of cases the model handled alone at the risk limit.

`actions/attest` attests only what runs in Actions. Bundles collected on the local machine are published as checksummed; the CI job that replays them may attest the replay result.

## What 2.0 does not build

| Need | Reused instead |
|---|---|
| Exact bounds | `src/actseal/stats.py` (existing kernel) |
| Cross-check of selection | MAPIE 1.6.0, optional dev dependency, non-blocking |
| Signing | `actions/attest`, `gh attestation verify`, in-toto Test Result predicate |
| Model serving | Ollaya or the vendor's own server |
| Per-model adapters | One Jev-compatible adapter |

Deferred to 2.1 or later: single-split selection, sequential mode, per-label thresholds, `compare`, plug-in entry points, `actseal.gate` in the package, OpenAI Decisions API adapter, agent tool-call gating, an SVG result card, Windows.

Stability rule: 2.0 removes no STABLE name or flag. `docs/versioning.md` requires a deprecation in a minor release plus 90 days before any removal, and 1.0.0 shipped on 7 Oct 2026. If M1 finds a removal unavoidable, it becomes a deprecation in 1.1.0 and waits.

## Milestones

Packets, reports and reviews go under `plan/v2/`, in the v1 packet format (`plan/v1/tasks/04.md`). Branches: `claude/v2-<id>-<slug>`. Times are agent working time, estimated from v1's pace (three days for a build of similar size).

### Phase A: foundations (about 2.5 days)

| ID | Goal | Owner | Done when |
|---|---|---|---|
| M0 | Feasibility spike in scratch, no product code: which models run on the M5 Pro (24 GB), throughput, licences, dataset shortlist, repeat-request determinism | Codex + Claude | `plan/v2/receipts/spike.json` lists the model and dataset roster |
| M1 | Freeze v2 interfaces: selector signature, calibration result, profile list, schema 3, CLI verbs, receipt keys. Amend `AGENTS.md` (active state path, executor pin) | Codex | `tests/unit/test_schemas.py` and rewritten `tests/unit/test_stability.py` pass |
| M2 | `engine_sha256`, engine v2, golden corpus. Separate 1.0.2 patch registering the audit producer `167038cb…` | Claude | Golden replays byte-equal; `uvx actseal==1.0.2 replay docs/results/jev-audit-2026-10-08/evidence` exits 2 |

### Phase B: engine (about 4 days)

| ID | Goal | Owner | Done when |
|---|---|---|---|
| M3 | New `src/actseal/selection.py` (imports `stats` only): `select_threshold`, `plan_sample_size` | Claude lane 1 | Fraction oracle matches; at the planner's design point, verification PASS rate ≥ 0.75 over 2,000 seeded draws; new mutants killed |
| M4 | Profiles and adapters: `normalization.py`, `faults.py`, `adapters/decision_api.py`, `adapters/recorded.py` | Claude lane 2 | Mock-server conformance tests pass; replay imports no adapter |
| M5 | Wire it together: `locking.py`, `runner.py`, `evidence.py`, `replay.py`, `assessment.py`, `cli.py` | Claude | Replay recomputes the selection; a tampered calibration record gives ERROR |

M3 and M4 run in parallel (no shared files).

### Phase C: proof and launch (about 3 days plus machine time)

| ID | Goal | Owner | Done when |
|---|---|---|---|
| M6 | `src/actseal/report.py`, `action.yml`, docs | Claude lane 1 | Render is byte-deterministic; the action's self-test workflow is green |
| M7 | `bench/` harness (ported from the archived audit producer) and sealed preregistration | Claude lane 2 | Dry run on fixtures passes; the seal precedes the first capture in the journal |
| M8 | Run the comparison, publish bundles as release assets, build the results page | Codex | Every bundle replays offline in CI to its stored verdict |
| M9 | Release 2.0.0 and prepare the launch kit | Codex | `tools/check_release.py`, `uv build --no-sources`, `pytest -m packaging` pass |

M6 and M7 run in parallel. M8's machine time (one to three days) is set by the throughput M0 measures.

### Automatic gates

1. After M0: fewer than two distinct models run locally → the comparison becomes Laya across versions and datasets, the decision-API adapter ships PROVISIONAL with mock-transport evidence only, and the README claim narrows to "Laya natively; Jev-compatible servers provisionally; any model via recorded predictions".
2. After M3: simulated PASS rate below 0.75 → the selection rule is redesigned before anything is wired.
3. Before M8: no capture without a committed preregistration seal.

## Files

Changed: `src/actseal/{records,serialization,compatibility,normalization,faults,locking,runner,evidence,replay,assessment,cli}.py`, `compatibility_registry.json`, `docs/stability.md`, `docs/schemas/`, `tools/check_mutations.py`, `tests/unit/test_stability.py`, `AGENTS.md`.

New: `src/actseal/selection.py`, `src/actseal/report.py`, `src/actseal/adapters/{decision_api,recorded}.py`, `tests/golden/`, `action.yml`, `bench/`, `plan/v2/`.

Code seams that constrain the work:

- Provider names are a hard-coded set checked in seven places (`records.py:100`, `runner.py:119-175`, `normalization.py:321-338`, `faults.py:102-113`, `assessment.py:91,173`, `cli.py:73-77`, `tests/unit/test_stability.py:640`).
- Every response must carry a probability for every label summing to 1 (`records.py:270-288`, `normalization.py:248-287`).
- The calibration split is hashed and stored but never collected (`locking.py:290`, `runner.py:242-252`).
- The fingerprint hashes every packaged `.py` file (`serialization.py:565-579`; checks at `compatibility.py:224-258`).
- The bundle is exactly seven files, enforced on read (`evidence.py:390-398`).

Existing code to reuse:

- `src/actseal/stats.py`: `clopper_pearson_tail` drives the selector and the planner.
- `src/actseal/serialization.py`: `canonical_json`, `strict_json_loads`, `_fingerprint_tree` (parameterise by module list).
- `src/actseal/experimental/providers/jev.py`: bounded reads, status mapping, credential-echo guard, `request_body`.
- `src/actseal/adapters/fixture.py`: basis for recorded rows.
- `docs/results/jev-audit-2026-10-08/producer-source.tar.gz` (`bench/jev_audit/`) and `calibration_sidecar.json`: benchmark harness and a real calibration fixture.

## Verification

No human testing. Every claim is checked by a command.

Standing gate for every milestone:

```
uv run --frozen pytest -m "not integration and not packaging"
uv run --frozen mypy --strict src tests
uv run --frozen pre-commit run --all-files
uv run --frozen python tools/check_mutations.py
```

Checks tied to the main risks:

| Risk | Check |
|---|---|
| Selection mostly yields INCONCLUSIVE | Seeded simulation test (gate 2) |
| Selector sees verification data | `selection.py` imports only `stats`; replay recomputes the threshold from calibration records alone |
| Silent engine drift | Golden corpus plus the mutant-flips-golden gate |
| Relaxed shape admits a bad ACT | Property test: no response with a missing, mismatched or out-of-range score evaluates to ACT; the gating score equals the raw value bit for bit |
| Overclaiming | Docs test bans "safe", "best", "guarantees" in README and report templates |

End to end before release:

1. Install the built wheel in a clean container and run `actseal qualify` on the packaged demo.
2. Run `actseal replay` on every published bundle and compare with the stored verdict.
3. Run `gh attestation verify` on one bundle produced by the action's self-test.

## Not yet verified (M0 settles these)

- Whether Clef 9B and Strands Decider run in 24 GB, and Strands Decider's licence.
- Whether Ollaya accepts the adapter's request body unchanged. The machine has `ollama` but no `ollaya`, `llama-server` or `mlx_lm` binary.
- Dataset licences and label counts.
- Whether MAPIE's risk definition matches Actseal's (it is a cross-check only either way).

## Needs the maintainer

1. Approve the `AGENTS.md` amendment: active state moves to `plan/v2/`, and the executor pin is restated.
2. Approve the PyPI publishes (1.0.2 and 2.0.0) in the existing release pipeline.
3. Post the launch (Show HN and one thread) from the launch kit. v1 was never announced.

Success is read from public counters 14 days after launch (stars, clones, PyPI downloads, issues). No surveys.
