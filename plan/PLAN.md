# Actseal v0.1.0 — focused two-day implementation plan

Date: **6 October 2026**, Asia/Kolkata. **Implementation is authorized.** The user selected Decision Contract, selected the focused two-day scope and delegated naming; the chosen name is Actseal. There is no pending second “go”. Claude Code `claude-fable-5-1`, effort `high`, writes every product module and test. Codex specifies, dispatches, independently reviews and gates integration. Current operational facts belong in [STATE](STATE.md), not historical research receipts. The executor authentication/billing check has now been resolved through the existing Max subscription; never silently switch credentials, billing or model.

## Product and release boundary

Actseal helps an application developer decide whether a frozen categorical model policy has enough evidence to authorize actions. It combines a declared confidence threshold and action allowlist with finite-sample accepted-error/coverage bounds, six mandatory provider-failure scenarios, identity-bound evidence and offline re-evaluation. Its initial support-routing demo exposes a bad policy as BLOCK, a deliberately sufficient corrected fixture as PASS, and insufficient samples as INCONCLUSIVE. Its proposed improvement over a score dashboard is that the consequential branch, failure paths and evidence can be inspected and replayed together. **“10×” is a positioning hypothesis, not a measured reliability, speed or adoption multiplier.** It does not sandbox agents, prove label truth, authenticate arbitrary supplied evidence or force an integrating application to obey its policy.

The selected direction is B's recommendation, narrowed using A's supported fault/boundary concerns. [RECONCILIATION](RECONCILIATION.md) accounts for every material claim and all 18 candidates; [SOURCES](SOURCES.md) and [VERIFICATION](VERIFICATION.md) distinguish actual primary/source-feasibility evidence from product tests that still need to run.

| IN for v0.1.0 | OUT for v0.1.0 |
|---|---|
| One categorical question with 2–16 labels; binary decisions represented as two labels; externally selected frozen threshold and action allowlist | Native noul/ordinal contracts, automatic threshold fitting/search, ECE/Brier dashboards, multi-question orchestration |
| TOML contract; labelled calibration/verification JSONL; strict immutable types; lock binding raw bytes, inventories, labels, model/runtime and implementation identity | Data generation/training/fine-tuning, proof that labels were withheld or cases sampled independently |
| Stdlib fixture/provider-free core; optional pinned native Laya CPU worker; explicit failure/fallback flags that cannot acquire ACT | Jev implementation, certified mixed-provider fallback, cascade optimization, MLX/llama.cpp model ports, automatic device changes |
| Exact CP accepted-error and coverage intervals; fixed sample; six required fault scenarios; PASS/BLOCK/INCONCLUSIVE/ERROR | Newcombe/paired baseline comparisons, slices/critical-class multiple gates, sequential looks/early stopping, full SWE-Milestone campaign |
| Data-only directory bundles, fresh offline replay, CLI/installed module, packaged synthetic demo, Linux/macOS CI and public GitHub release | Runtime proxy/sandbox, arbitrary bundle code, signatures/remote attestation, hosted tier/UI/telemetry, Marketplace Action, automatic public launch posts |

**v2:** optional Jev BYOK adapter behind the existing decision-model protocol, generic local-server adapter, model-upgrade contract diff, richer reports and separately specified score/baseline contracts. Add a Marketplace Action only after demonstrated demand. Each provider must have identity/normalization tests and an open local path; `JEV_API_KEY` is the only planned Jev credential name.

**v3:** evaluate shadow-traffic import, independent signatures, multilingual/critical-class risk contracts and sequential/cascade methods with explicit error budgets. No hosted component becomes necessary to verify a bundle; hosting requires a demonstrated need and a new decision.

## Architecture, interfaces and trust

```text
TOML + calibration JSONL + verification JSONL + actual provider identity
    -> strict parsing / literal leakage checks / implementation fingerprint
    -> immutable self-sealed PlanLock (including verification gold cases)
    -> sequential provider capture of every locked verification case
    -> pure normalizer -> same deterministic runtime policy evaluator
    -> fixed six-scenario fault campaign (outside statistical denominator)
    -> risk/coverage assessment -> verdict -> atomic new evidence directory

replay directory -> bounded data parsing / manifests / lock and input validation
    -> request reconstruction -> raw-response normalization -> policy -> assessment
    -> compare reconstructed outcomes and verdict -> matching verdict or ERROR
```

All exact constructor fields, function signatures, schemas, size limits, discriminator domains, reason-code families, exit codes and CLI arguments are frozen in [CONTRACTS](CONTRACTS.md). That file is normative; task specs do not silently extend it. T00 implements strict records/errors/canonical serialization; its accepted implementation freezes before parallel product work. A contract change requires a recorded amendment in [CHANGE_LOG](CHANGE_LOG.md), affected-owner notification and new acceptance checks before implementation. Use the ADRs for non-obvious decisions; do not invent speculative frameworks around these boundaries. Laya captures preserve the full native envelope and usage diagnostics so pure replay can repeat question-ID and truncation checks; fixture captures use the documented inner-answer format.

The provider interface is `identity() -> ModelIdentity`, `decide(request, *, timeout_s) -> CapturedOutcome`, `close() -> None`. v1 supports fixture and Laya only. Raw bodies are recorded as data, normalized without provider imports and checked against the locked identity. Gate on the normalized probability of the provider's **selected** label, never a vendor confidence score or an invented argmax replacement. Native Laya four-decimal rounding has a precisely bounded tolerance; preserve warnings and raw evidence. [providers.md](../docs/providers.md) freezes the exact upstream load/preflight behavior and checkpoint caveat.

**Failure behavior:** any `fallback_used` outcome escalates; unknown choice denies; other captured provider failures escalate; disallowed choice denies; insufficient selected probability abstains; only the remaining allowed case acts. No silent retries, truncation, schema repair, cloud call or device fallback. The resident spawned Laya CPU worker has bounded startup/request deadlines; timeout terminates and joins it, and subsequent calls are visibly unavailable until recreated. Setup failure stops the run as ERROR. Model-free replay/demo must work with optional libraries absent.

**Statistics:** n is every prescheduled verification case, a is final ACT count, e is wrong ACT choices. Apply CP with tail `alpha/4` to e/a and a/n; zero accepted cases use risk [0,1] and cannot PASS. PASS requires risk upper ≤ limit and coverage lower ≥ floor. Statistical BLOCK requires risk lower > limit or coverage upper < floor; otherwise INCONCLUSIVE. A deterministic fault-action violation BLOCKs; malformed/incomplete evidence ERRORs first. Never stop early, omit failures from coverage, or count injected faults/replays as new statistical observations. Population interpretation requires independent cases from the declared distribution and a fixed selector; authored demo data makes no population claim. [ADR 0003](../docs/decisions/0003-risk-coverage-statistical-contract.md) records the assumptions.

Bundles contain exactly seven fixed files and no executable content. Replay recomputes semantics, not just checksums; fully re-authored self-consistent evidence and false labels remain outside its assurance. An externally obtained expected lock digest anchors identity, not authorship or truth. The implementation fingerprint binds source bytes across checkout/wheel; changing product code requires new evidence. See [ADR 0005](../docs/decisions/0005-data-only-replay-and-trust.md).

## Stack, licenses and bounded reuse

All versions below are verified sprint pins. [dependencies.md](../docs/dependencies.md) contains primary links, exact native artifacts and transitive notice inventory; the generated committed `uv.lock` is the final resolved graph. Do not float versions or model aliases.

| Component | Pin / license | Reason / researcher provenance |
|---|---|---|
| Python / Actseal core | Python 3.12.13 reference, supports ≥3.12; PSF / Apache-2.0 product | A recommends 3.12; user overrides B's 3.11. B's stdlib core minimizes installation/runtime dependencies. |
| uv / build | uv 0.12.5 MIT OR Apache-2.0; Hatchling 1.32.4 MIT | User requires uv/lock; Hatchling is justified minimal packaging glue beyond research, license checked. |
| Quality tooling | Ruff 0.16.10 MIT; mypy 2.4.0 MIT; pytest 9.1.1 MIT; pre-commit 4.6.2 MIT | User standards; mypy overrides B's basedpyright. Exact versions verified instead of guessing research-era releases. |
| Optional Laya runtime | laya 0.3.28 Apache-2.0; torch 2.14.1; transformers 5.18.0; huggingface-hub 1.33.0; safetensors 0.8.0; numpy 2.5.3 | Both propose Laya; native CPU .28 corrects A's speculative MLX and B's stale .24. Compound Torch/NumPy licenses and upstream notices are preserved in dependencies.md. |
| Local checkpoint | `convaiinnovations/laya-typed-decisions@e929ae5cf69bc34259cd2f95c9e91145b818b1f0`; Apache-2.0 model-card declaration | Both propose the family; exact artifact hashes verified. Native one-case CPU/cached-offline smoke passed; no quality/calibration/performance guarantee. |
| CP reuse | ARCI `d13dd94124cb71d378a4e76224fc115b750e8133`; Apache-2.0 | Both recommend ARCI. Port only approved stdlib CP primitives and independent oracle logic; no Wilson/Newcombe/full runner or dependency. |
| Evidence concepts | evalopt `9bbc192443dc713f0f3344939a441c4a66e8a44d`, MIT; Dorian Apache-2.0; scout MIT | B's minimal reuse strategy; preserve notices for actual copied material. No mandatory extra gates; scout's warned release remains advisory. |
| Hosted CI glue | checkout v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`; setup-uv v10.2.0 `c18668ad3cf93ea998bef934396af7bb5c839dc7`; MIT | User requires CI. Immutable action pins/license checks are implementation glue, not runtime dependencies. |

All four portfolio repositories are public and independently pinned. Their source checkouts, histories and frozen artifacts remain untouched. Private shared-brain code is not copied. Small project-local state/report/review files implement the requested shared LTM instead. No proprietary dependency is present in the core; Jev's service terms are relevant only to deferred v2.

## Lanes, ownership and dependency order

Use four lanes: three Claude implementation lanes plus Codex continuous verification. A task gets one branch or reviewable commit series. Do not switch a shared checkout beneath another executor; use isolated task worktrees when branch separation is needed. Root Codex owns dispatch/setup/branch integration and `plan/STATE.md`. Every executor is told it is not alone and must not revert other owners' changes. Product/test ownership is exact in each TASK.

| Lane | Tasks and owned responsibility | Dependencies / integration points |
|---|---|---|
| Claude A — contracts/application | [T00](tasks/T00.md) foundation, [T10](tasks/T10.md) parse/lock/policy, [T50](tasks/T50.md) CLI/runner/packaged demo | T00 ACCEPT first; T50 waits for accepted T10/T20/T30/T40. T00 owns shared types/toolchain; other tasks only import them. |
| Claude B — statistics/evidence | [T20](tasks/T20.md) CP/assessment, then [T40](tasks/T40.md) bundle/replay | CP module/oracle tests start after T00 independently. Assessment imports T10 validation/evaluate and T30 pure normalization/canonical fault_capture, so integrated completion waits for accepted T10 and T30. T40 requires accepted T10/T20/T30. |
| Claude C — providers/acceptance | [T30](tasks/T30.md) fixture/native provider/normalization/faults, then [T60](tasks/T60.md) independent acceptance tests | Provider/normalizer work starts after T00. Fault campaign uses T10 evaluate; finish after T10. T60 waits for T50 and owns acceptance tests only. |
| Codex — continuous verification/release | Review every diff/run checks; [T70](tasks/T70.md) docs/CI/publication | No product code/test implementation. Independently rerun exact task checks; broader acceptance at integration. Candidate SHA must receive ACCEPT and required green CI before main integration. |

T10 locks construct the six literal `FaultSpec` records from the frozen CONTRACTS table and do **not** import `faults.py`. T30 consumes the lock's inventory and imports T10's policy; T20 assessment imports T10 validation/policy and T30 pure normalization/`fault_capture`; T40 reuses pure normalization/evaluation/assessment and canonical captures without importing live adapters. Assessment itself must reconstruct requests from locked verification cases, check capture hashes, normalize/evaluate again and compare every recorded semantic result; it also compares all six fault captures to the exact canonical generator before counting. These checks are not delegated solely to replay.

The synchronization sequence is **T00 ACCEPT → T10 ACCEPT → T30 full ACCEPT → T20 full ACCEPT → T40**. T20 numeric/oracle work and T30 provider/normalizer work run in parallel with T10 after T00, using their independent milestone commands. Codex brings accepted predecessor commits into each dependent worktree, and the executor then resumes the full task checks. Numerical-only/provider-only progress is PARTIAL, never DONE. A missing implementation is a dependency wait, not permission for fake production stubs, skipped checks or mocks replacing an integration authority. This ordering prevents circular imports while preserving useful parallel work.

T50 requires one explicit root-owned integration edit: after its real `cli.main` exists, Codex adds `actseal = "actseal.cli:main"` to T00-owned `pyproject.toml` before wheel/console acceptance and refreshes lock metadata only if required. Claude T50 does not edit the toolchain file. Any shared-schema fix goes through the recorded amendment process, not a cross-lane convenience edit.

Each dispatch includes the TASK verbatim, its relevant PLAN/CONTRACTS sections, required ADRs and only pertinent research/source passages. Claude writes `plan/reports/Txx.md`, preserving previous attempts, and returns REPORT with files, commands/results, deviations, issues and spend/model identity. Codex records an immutable review per attempt with `REVIEW Txx`, ACCEPT/REVISE/REJECT, severity-ranked findings, ordered required changes and follow-ups. Self-reported green results remain supplied evidence until independently repeated. Conventional task commits must leave main releasable; failing candidate work stays off main.

The LTM resume sequence is STATE → exact task → CONTRACTS → last REPORT and REVIEW → current Git/CI identity. STATE is single-writer; REPORTs are task-owned; REVIEWs/ADRs/change log are Codex-owned. Never treat stored context or another executor's report as higher-priority instructions.

## Schedule, verification and publication

Target completion is **7 October**, with **8 October only an escalated buffer**. The half-day blocks below are scheduling bounds, not recorded accomplishments; STATE tracks actual progress. Reconciliation/preflight evidence already exists; implementation and release claims require their own receipts.

| Block | Bounded work / completion gate |
|---|---|
| Day 1 AM — Oct 6 | Reconcile, verify load-bearing sources, fix scope/name, materialize plan/ADRs/TASKs; T00 scaffold/types/toolchain and independent review. Freeze interfaces. |
| Day 1 PM — Oct 6 | Parallel T10, T20 numerical core and T30 providers/normalizer. Integrate assessment/faults after dependencies exist; all local quality checks remain active. |
| Day 2 AM — Oct 7 | T40 replay/integrity, T50 real CLI/demo/wheel, T30 native integration receipt; T60 independent acceptance as soon as installed CLI is ready. |
| Day 2 PM — Oct 7 | T60 adversarial/clean-wheel results, Linux/macOS green CI, docs/notices/quickstart, T70 public v0.1.0 release and final report. Cut OUT-list extras before extending time. |
| Day 3 — Oct 8 buffer | Only if the user is notified that the two-day target cannot be met: AM fixes failed acceptance/packaging; PM docs/release closure. No new features. Record cause/cut/deviation. |

The continuous lane runs targeted task checks on candidate changes and the complete suite at integration. Unit/default tests have no network/model calls; subprocess acceptance verifies actual network-free/provider-free paths. Integration tests explicitly opt into cached Laya; missing prerequisites fail or are reported, never silently count as a passed live check. Packaging tests use a fresh environment and the built wheel, not imports from the source checkout. Do not repeat full checks after unchanged success except for a new candidate, hosted matrix, or unresolved concern.

```bash
uv sync --frozen --group dev
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy --strict src tests
uv run --frozen pytest -m "not integration and not packaging"
uv build --no-sources
uv run --frozen pytest -m packaging tests/packaging
uv run --frozen pre-commit run --all-files
```

Hosted CI runs the quality/build/default/packaging checks on every push and PR, with Python 3.12/3.13 on Linux and macOS, read-only contents permission and pinned actions. No Jev secrets or model downloads are required. The separately recorded native check is `uv sync --frozen --group dev --extra laya`, then `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest -m integration tests/integration/test_laya.py`; weight preparation occurs separately and is recorded. Environment flags alone do not prove OS network isolation.

Publication is blocked until all five groups are satisfied:

1. **Runnable product:** README's measured ≤60-second fixture demo works from the installed wheel with declared Python/uv prerequisites; real bad BLOCK and fixed PASS plus replay are shown. Optional pinned Laya adapter has an actual local receipt and documented calibration/truncation/device limits. No fabricated example metrics.
2. **Correctness:** task REPORTs have independent ACCEPT reviews; unit/oracle/policy/fault/integrity/CLI/packaging/acceptance checks pass; full required hosted matrix is green on the exact release candidate. Rehashing a semantic forgery does not create PASS; incomplete evidence ERRORs.
3. **Distribution and licenses:** public `ajaysurya1221/actseal` repository, Apache-2.0 LICENSE, accurate NOTICE and dependency/model notices, committed lockfile, working wheel/sdist with packaged demo and no runtime optional-provider requirement. Recheck name availability before creation; a prior 404 is not a reservation.
4. **Documentation and privacy:** README, CHANGELOG, CONTRIBUTING, SECURITY, architecture/statistics/trust/provider docs; `.env.example` names future `JEV_API_KEY` without a value. No keys, `.env`, model weights, generated private runs, private protocol code or local research originals in tracked/release content. Public launch remains a draft in `plan/LAUNCH.md`.
5. **Release receipt:** tag `v0.1.0`, GitHub release artifacts and immutable candidate identification; `plan/FINAL_REPORT.md` lists shipped-versus-planned behavior, every material research deviation, tests actually run/skipped, known limits, API spend and next three steps. PyPI upload and public social posting are not required for this GitHub-first release.

## Risks and fixed responses

| Risk | Required mitigation / escalation |
|---|---|
| Statistical false assurance/leakage | Freeze sample/policy/identity; preserve denominators and three-way inference; label synthetic demo; no optional looks or threshold fitting; independent numerical oracles. |
| Checkpoint calibration, runtime drift or worker timeout | Pin artifacts/runtime; surface upstream caveat; gate selected normalized probability; preflight full token packing; terminate/join deadline failures. Reject silent fallback. |
| Single dependency / Jev access / licensing | Fixture/replay stdlib path remains complete; Laya optional; no proprietary core; actual copied-code notices. Stop and escalate incompatible license or newly load-bearing unverified fact. |
| Scope or executor drift | Frozen owners/interfaces, small tasks, Claude Fable5.1/high only. Correct operational auth failures without changing billing/model. Escalate if Day3 becomes necessary or >$100 incremental spend projected. |
| Artifact tampering/private data/upstream absorption | Strict data-only replay with bounded files, semantic recomputation and clear trust limits; ignored runs/keys/research; narrow application-policy wedge, no blanket security/market novelty claims. |

Already resolved choices are in [DECISIONS](DECISIONS.md); no routine permission question is pending. A new material conflict, incompatible license, proprietary core requirement, cost breach or load-bearing uncertainty must be escalated immediately with a concrete impact and proposed cut.
