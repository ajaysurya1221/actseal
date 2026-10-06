# Actseal v0.1.0 release evidence checklist

**COMPLETE — v0.1.0 published6October2026.** All checks below have independent
receipts in [REPORT T70](reports/T70.md), [FINAL_REPORT](FINAL_REPORT.md) and
[REVIEW T70-02](reviews/T70-02.md). Tag83fd04a, final CI37456279878, audited assets
and exact public-wheel quickstart verified. Historical task reviews remain preserved.

## Definition-of-done mapping

| PLAN publication group | Required evidence and exact check block | Publication gate / current state |
|---|---|---|
| 1. Runnable product | T50 REPORT/ACCEPT; installed-wheel console and module receipt; real bad BLOCK/fixed PASS plus both replays; README commands and measured ≤60-second fixture workflow with prerequisites; T30 accepted native adapter receipt. Blocks A, B, C. | COMPLETE: final installed/public-wheel workflow and unchanged native receipt applicability verified. |
| 2. Correctness | T00–T60 ACCEPT on identified commits; independent oracles/policy/fault/integrity/CLI/acceptance suites; all four Linux/macOS × Python3.12/3.13 release-candidate jobs green. Blocks A, D; explicit ADR0009 assertions below. | COMPLETE: all task ACCEPTs, final local suites and all four exact-candidate jobs green; packaging/demo actually ran. |
| 3. Distribution and licenses | Public repository; Apache-2.0 LICENSE/actual reuse NOTICE; committed resolved lock; stdlib core; corrected official Linux CPU graph and license inventory; wheel/sdist contents and hashes. Blocks E, G. | COMPLETE: final36-file wheel/150-file sdist audited; unchanged53-third-party-record license inventory and official CPU graph checked. |
| 4. Documentation and privacy | README, CHANGELOG, CONTRIBUTING, SECURITY, architecture/statistical/trust/provider/quickstart docs; placeholder-only `.env.example`; reviewed tracked/release inventory; launch remains draft. Blocks F and claim review. | COMPLETE: final docs and89local links verified; tracked/history/archive privacy checks scoped in REPORT T70. |
| 5. Release receipt | Accepted candidate; immutable v0.1.0 tag; non-draft GitHub release with matching wheel/sdist; FINAL_REPORT's shipped/planned comparison, research deviations, known limits, actual checks, incremental spend and next three steps. Block G. | COMPLETE: public release/tag/assets and downloaded hashes verified; launch draft retained, no PyPI upload. |

## A — complete local product checks

Run from the release-candidate checkout after accepted T10 → T30 → T20 → T40 → T50 integration and T60 acceptance work. T10 and full T30 have passed their gates; T20 has also passed local checks, independent review and both hosted matrices. Historical numerical-only/provider-only milestones do not substitute for full task or integrated release checks. Preserve relevant task REPORTs and independent REVIEWs.

```bash
git rev-parse HEAD
git status --short
uv sync --frozen --group dev
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy --strict src tests
uv run --frozen pytest -m "not integration and not packaging"
uv build --no-sources
uv run --frozen pytest -m packaging
uv run --frozen pre-commit run --all-files
git diff --check
```

- [x] Record final candidate identity and explain any working-tree changes; release artifacts must correspond to accepted committed product bytes.
- [x] Record actual test outcomes, including skips and integration exclusions. Unresolved false PASS, semantic forgery, incomplete evidence or cleanup failures block release.
- [x] Confirm frozen CP domain/tail allocation, independent expected-value tests, all scheduled-case denominators, zero-ACT behavior, four verdicts and fixed 30.0-second collection/120-second startup constants.

## B — clean wheel, demo and documented first run

```bash
uv build --no-sources
uv run --frozen pytest -m packaging
uv run --frozen pytest tests/unit/test_cli.py tests/unit/test_runner.py tests/acceptance
```

- [x] T50 packaging receipt identifies a fresh environment outside the source checkout, installation of the built wheel without dependencies, both `actseal` and `python -m actseal`, packaged resource parity and optional-provider absence.
- [x] Execute README's final exact quickstart through that installed-wheel path. Record prerequisites, platform, elapsed time, real statuses/counts/bounds and fresh output locations. The declared fixture workflow must finish within 60 seconds on the reference setup; model download time is not hidden inside this claim.
- [x] Record both genuine demo verdicts and successful fresh replay. Label authored data `evidence_scope=demo`; no population or live-model accuracy claim follows.
- [x] Confirm repeated generated bundles are byte-identical on the same implementation and record the CI demo digest. Different implementation fingerprints require regenerated evidence.

The final output subdirectory names and quickstart text belong to T50/README. This checklist deliberately does not invent them before implementation. The commands above exercise the packaged workflow through the owned acceptance test; attach the actual CLI transcript before checking this gate.

## C — optional local adapter product receipt

Accepted macOS and Linux **Actseal adapter** receipts are available above. Before checking the final release gate, bind those receipts to the final candidate's relevant source/test/runtime identities and rerun when changes require it. For an execution, prepare only the approved pinned public artifacts separately, record preparation/dependency identities, and use the product command below rather than the earlier upstream script:

```bash
uv sync --frozen --group dev --extra laya
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest -m integration tests/integration/test_laya.py
```

- [x] Actual cached-native test runs rather than skipping; receipt records OS/Python, model revision, weights hash, runtime pins, CPU execution, warnings and worker cleanup. Preserve the published checkpoint calibration caveat.
- [x] Record the verified macOS and Ubuntu/Python 3.12.3 native environments separately from artifact metadata and ordinary CI. Do not infer native Python 3.13, broader hardware support or performance from those bounded receipts.
- [x] Product ordinary tests verify truncation preflight, full native envelope/usage checks, timeout termination/join, unavailable-after-worker-loss and no silent restart/device fallback. Offline environment flags alone are not proof of OS network isolation.
- [x] **Completed native CLI integration smoke:** [T70-native](reports/T70-native.md) records the actual run. For reproduction, run the real CLI `lock` → `verify` → `replay` using T50's committed synthetic support-triage inputs and the pinned cached Laya snapshot. Use `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, with the documented Laya/offline options for lock and verify. Capture the exact candidate, committed input paths, commands, exit codes, model/runtime identity, output bundle identity and replay result. This checks the provider factory and runner integration in addition to the accepted direct-adapter tests.

The exact executed native CLI transcript is in REPORT T70-native. Preserve the actual statistical status, including BLOCK or INCONCLUSIVE, and require replay to reproduce it. Do not change the policy/data or retry until PASS to make this smoke look successful. Preserve and investigate any ERROR according to the contract. This is a bounded integration check on authored synthetic inputs, not a model-quality, hardware or latency benchmark; its independent receipt preserves the actual BLOCK result.

## D — ADR0009 and hosted CI

The exact semantics are in [ADR 0009](../docs/decisions/0009-worker-loss-invalidates-statistical-run.md), [ADR 0008](../docs/decisions/0008-fixed-collection-deadlines.md) and [CONTRACTS](CONTRACTS.md). Inspect the tests and their executed results; merely naming the scenario is insufficient.

```bash
uv run --frozen pytest tests/unit/test_assessment.py tests/unit/test_providers.py tests/unit/test_replay.py tests/unit/test_runner.py tests/acceptance
```

- [x] After complete integrity checks, a regular Laya timeout/unavailable capture causes ERROR with `infrastructure.worker_invalidated`, zero counts and [0,1] intervals; scheduled terminal records remain diagnostic evidence. Canonical injected faults are excluded from this rule; nonfatal failures remain in a valid run's denominator.
- [x] Worker death/EOF/unusable IPC invalidates the instance. No retry, restart, replacement sample, post-failure resealing or discarded-ERROR-attempt retry-until-PASS path is accepted.
- [x] Replay independently reproduces infrastructure invalidation and distinguishes a diagnostic ERROR bundle from a completed statistical certification.
- [x] Documentation states independent case outcomes under a fixed operating regime and selector, unconditional over one prespecified attempt. No persistent-process uptime or run-completion-probability bound, and no confidence claim conditioned on completion.

The following commands reproduce hosted status queries; REPORT T70 records the actual final-candidate run and inspected logs:

```bash
actseal_candidate_sha=$(git rev-parse HEAD)
gh run list --repo ajaysurya1221/actseal --commit "$actseal_candidate_sha" --workflow ci.yml --limit 20 --json databaseId,headSha,status,conclusion,url
gh api "repos/ajaysurya1221/actseal/commits/$actseal_candidate_sha/check-runs" --jq '.check_runs[] | {name, status, conclusion, html_url, head_sha}'
```

- [x] All four required Linux/macOS Python3.12/3.13 jobs complete successfully on the exact reviewed SHA; record URLs. Do not inherit a prior commit's green status.
- [x] Inspect logs: real clean-wheel acceptance and fixture reproduction execute; the former existence guards were removed by accepted T50 and must not return. Compare demo digests across runs/platforms and resolve discrepancies.
- [x] Workflow still uses pinned actions/uv, push and PR triggers, read-only permissions, locked tooling and no secret/model-download requirement for ordinary CI.

## E — artifacts, graph and licenses

```bash
git ls-files --error-unmatch LICENSE NOTICE uv.lock pyproject.toml
uv run --frozen python -m zipfile -l dist/actseal-0.1.0-py3-none-any.whl
tar -tzf dist/actseal-0.1.0.tar.gz
shasum -a 256 dist/actseal-0.1.0-py3-none-any.whl dist/actseal-0.1.0.tar.gz
rg -n '^name = "(cuda-toolkit|nvidia[^\"]*|triton)"' uv.lock
```

The final `rg` check is expected to return **1 with no matches**; 0 means a package requiring investigation, not a passed exclusion check. It is a narrow regression check, not a complete license audit.

- [x] Inspect the complete resolved native graph and [dependency notices](../docs/dependencies.md), preserving actual copied-code/license obligations. Linux uses official `torch==2.14.1+cpu`; macOS keeps the tested PyPI pin. No proprietary NVIDIA resolution is accepted.
- [x] Wheel contains entrypoints, package data, typing marker and required license notices; sdist contains the intended build inputs. Core wheel installs and runs without optional model packages.
- [x] Record exact wheel/sdist hashes and file inventories. No `.env`, original research, private protocol material, cached weights or private generated evidence appears in either distribution.

## F — documentation and privacy review

```bash
git ls-files --error-unmatch README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md .env.example docs/architecture.md docs/statistical-contract.md docs/threat-model.md docs/providers.md docs/quickstart.md plan/LAUNCH.md
git ls-files -- .env research .cache models weights runs plan/dispatch
git diff --check
```

The second command prints filenames only and must show no excluded private/secret/generated inputs. Review the full tracked inventory and both archive inventories too; directory names alone do not prove absence of sensitive content. Stage approved docs before testing that they are tracked. Never print secret values during inspection.

- [x] README/quickstart match accepted syntax/statuses; `.env.example` contains placeholders only and identifies Jev as future optional `JEV_API_KEY` support.
- [x] Audit final claims against receipts: no unsupported “10×”, calibrated-model, security-sandbox, production reliability, adoption, zero-maintenance, uptime or completion-probability assertions. State replay's integrity/provenance limits and the synthetic demo's scope.
- [x] FINAL_REPORT covers shipped versus planned, every material research deviation, exact successful/failed/unrun checks, known issues, incremental API spend separately from subscription metering and next three steps. Keep [LAUNCH](LAUNCH.md) marked draft until an explicit posting request.

## G — release identity and closure

Only Codex performs publication after groups 1–4 pass. Never move an existing tag or overwrite a conflicting release. This checklist contains read-only verification commands; it does not hide publication inside a verification step.

```bash
gh repo view ajaysurya1221/actseal --json nameWithOwner,visibility,url
git rev-parse HEAD
git rev-list -n 1 v0.1.0
git ls-remote origin refs/tags/v0.1.0 'refs/tags/v0.1.0^{}'
gh release view v0.1.0 --repo ajaysurya1221/actseal --json tagName,isDraft,isPrerelease,url,assets
```

- [x] Public repository, exact accepted tag target, non-draft/non-prerelease v0.1.0 release, matching wheel/sdist and release notes are independently verified. Compare annotated tags using the peeled commit, not the tag-object hash.
- [x] Release asset hashes match the audited local artifacts. Record stable release/run links and final REVIEW ACCEPT in T70/FINAL_REPORT.
- [x] All preceding gates have receipts or a user-approved recorded scope change. A missing required gate means release remains pending; a missing optional Linux inference receipt means no Linux-inference claim, not an invented test result.

No open publication prerequisites. Post-release receipts are committed on main after
the immutable tag; they do not alter the tested product or published artifacts.
