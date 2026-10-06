# Actseal v0.1.0 — final report draft

**PENDING RELEASE — progress snapshot, 6 October 2026.** T00, T10, T20, T30 and
T40 are independently accepted and merged. T50 CLI/demo is running; T60 acceptance
and T70 publication are pending. This is not a release receipt or a validated
quickstart. The [public repository](https://github.com/ajaysurya1221/actseal)
exists; that does not establish a published v0.1.0. [STATE](STATE.md) records
subsequent progress.

| Final release field | Status / receipt still required |
|---|---|
| T50 and T60 ACCEPT | **PENDING** — exact reviewed commits and independent checks |
| Final candidate and required hosted CI | **PENDING** — full commit SHA and four successful Linux/macOS × Python3.12/3.13 jobs, with packaging/demo guards removed |
| Installed-wheel quickstart and demo | **PENDING** — actual commands, statuses, counts/bounds, replay results, platform and elapsed time; no timing or metrics claimed here |
| Native CLI integration | **PENDING** — pinned cached Laya `lock` → `verify` → `replay`, preserving the actual verdict |
| Tag, release and distributions | **PENDING** — v0.1.0 target, release URL, wheel/sdist inventories and SHA-256 hashes |
| Final spend and publication review | **PENDING** — complete session ledger and T70 ACCEPT; launch post remains a draft |

## Accepted implementation versus planned release

The accepted core freezes an application decision policy and its labelled inputs,
records provider outcomes, checks failure behavior, calculates accepted-action
error and coverage bounds, and independently replays bounded evidence. The
complete user-facing workflow remains a release target until T50/T60 pass.

| Planned component | Accepted implementation / remaining work |
|---|---|
| T00 foundation | Immutable typed records, strict serialization, errors, pinned tooling and lockfile. [ACCEPT](reviews/T00-05.md), [PR 1](https://github.com/ajaysurya1221/actseal/pull/1), candidate `ebe11ff947b366fa700bf0e1ecf6747fcebe970f`. |
| T10 contract and policy | Categorical TOML/JSONL validation, input/identity lock and deterministic ACT/ABSTAIN/ESCALATE/DENY policy. [ACCEPT](reviews/T10-02.md), [PR 3](https://github.com/ajaysurya1221/actseal/pull/3), candidate `9bdac251a76a22a30f8d3d5ab8b773e0200945a1`. |
| T20 statistics and assessment | Exact-integer CP kernel; full-evidence reconstruction; risk/coverage bounds and PASS/BLOCK/INCONCLUSIVE/ERROR. [ACCEPT](reviews/T20-02.md), [PR 2](https://github.com/ajaysurya1221/actseal/pull/2), candidate `b1eace7009bc5bc966e4f600d756ff1802fd6e8e`. |
| T30 providers and faults | Fixture and pinned native Laya CPU adapters, strict normalization, bounded worker lifecycle and six canonical failure scenarios. [ACCEPT](reviews/T30-03.md), [PR 4](https://github.com/ajaysurya1221/actseal/pull/4), candidate `8b1efd6314b5b65ecb51f292a5bc767ff8b93ed7`. |
| T40 evidence and replay | Bounded seven-file bundles, exclusive atomic publication and provider-free semantic replay. [ACCEPT](reviews/T40-02.md), [PR 5](https://github.com/ajaysurya1221/actseal/pull/5), candidate `98297d5f79cfa62e348d722d8ae91ec59252eebd`. |
| T50–T70 completion | CLI/runner, packaged synthetic demonstration, installed-wheel acceptance, adversarial acceptance, final documentation/artifact audit and GitHub release are **PENDING**. |

Claude Code Fable 5.1/high implemented product code and tests; Codex specified,
reviewed, independently checked and gated each accepted task. Project-local
[STATE](STATE.md), contracts, ADRs and preserved REPORT/REVIEW records provide
the shared long-term context. No private orchestration implementation was copied.

## Checks actually completed

These are task-specific independent Codex results at the candidates above, not
additive test totals or a final integrated release run. Each review records the
exact task commands, findings and applicable source identities. Ruff lint,
formatting and strict mypy passed for each accepted task.

| Scope | Independent local result | Hosted push / PR evidence |
|---|---|---|
| T00 foundation | 587 tests; wheel/sdist build; all three approved pre-commit hooks | [Push](https://github.com/ajaysurya1221/actseal/actions/runs/37434438049), [PR](https://github.com/ajaysurya1221/actseal/actions/runs/37434442393) |
| T10 contract/policy | 755 tests; bounded-read, Unicode/CRLF, lock-size and resealed-overlap probes | [Push](https://github.com/ajaysurya1221/actseal/actions/runs/37438835505), [PR](https://github.com/ajaysurya1221/actseal/actions/runs/37438865469) |
| T20 assessment/statistics | 259 tests; denominator, tail allocation, boundary and integrity-precedence probes | [Push](https://github.com/ajaysurya1221/actseal/actions/runs/37441967584), [PR](https://github.com/ajaysurya1221/actseal/actions/runs/37441973261) |
| T30 providers/faults | 279 tests; independent canonical-fault and worker-lifecycle review | [Push](https://github.com/ajaysurya1221/actseal/actions/runs/37440036303), [PR](https://github.com/ajaysurya1221/actseal/actions/runs/37440043375) |
| T40 evidence/replay | 178 tests; semantic forgery, raw-input preservation, incremental bounds and filesystem probes | [Push](https://github.com/ajaysurya1221/actseal/actions/runs/37447161362), [PR](https://github.com/ajaysurya1221/actseal/actions/runs/37447188177) |

Each linked hosted run passed four Linux/macOS × Python3.12/3.13 jobs. T40's jobs
executed the real exclusive-publication operation on both operating systems.
Existing guards skipped the future CLI packaging/demo checks; those skips do not
satisfy release requirements. Earlier REVISE reports remain preserved; their
required product corrections were resolved before the listed ACCEPTs.

The [native product receipt](reviews/T30-02.md) separately records **five cached
offline macOS tests in 4.58 seconds** and **five Ubuntu/Python3.12.3 tests in 10.75
seconds**, with Laya0.3.28 and Linux torch2.14.1+cpu. The
[Linux run](https://github.com/ajaysurya1221/actseal/actions/runs/37439327535)
prepared the fixed snapshot separately. These checks bind provider candidate
`17ed0875541ecfa6402991dc90e278beb2f4cc01`; full T30 review confirmed its adapter,
normalization and native-test bytes were unchanged. They establish bounded
product-adapter execution, not model quality, general hardware compatibility,
network isolation or final CLI integration. The earlier upstream one-case smoke
and ARCI source tests remain distinct [preflight evidence](VERIFICATION.md).

Still unrun as final release gates: the complete candidate checks in
[RELEASE_CHECKLIST](RELEASE_CHECKLIST.md), installed console/module execution,
measured fixture quickstart, real demo and cross-platform artifact comparison,
native CLI smoke, T60 adversarial acceptance, final license/privacy inventories
and tag/release verification. Native CLI results must retain BLOCK or
INCONCLUSIVE if observed; no policy adjustment or retry-until-PASS is permitted.

## Material deviations from the research

The [reconciliation](RECONCILIATION.md) retains all **119 material claims** and
**18 candidate dispositions**, with original citations, verification status and
the ordered agreement/evidence/constraint/escalation rules. [SOURCES](SOURCES.md)
holds the dated primary evidence. The grouped changes below cover the material
departures; unsupported peripheral claims remain non-load-bearing rather than
being silently converted into facts.

| Change | Reason and accountable references |
|---|---|
| Focused Decision Contract, named Actseal, instead of Frontier-Gate | The user selected B's direction and focused scope. A's supported fault/regression concerns remain; this is not a departure from both picks. Current unpatched-hook claims were corrected against fixes and reporter clarification. A shell stream wrapper cannot establish OS containment. D01–D13/D35, S11–S14; [ADR0001](../docs/decisions/0001-focused-actseal-v1.md). |
| One categorical policy; no broader agent platform | Score/planner contracts, threshold fitting, slice/baseline gates, sequential looks, cascades, daemon, proxy, registry, hosted UI and Marketplace Action are excluded or deferred to fit two days. Binary is a two-label choice. All rejected/absorbed alternatives have individual reasons in the candidate tables. P07/P18–P19; [PLAN scope](PLAN.md#product-and-release-boundary). |
| Finite-sample risk/coverage rather than absolute regression assurance | “Exact Newcombe,” certainty, misread noninferiority bounds, ordinary-test binomial assumptions and unexamined paired comparisons were rejected. Four CP tails use alpha/4; insufficient evidence stays INCONCLUSIVE. No full SWE-Milestone campaign: its composite Score was mislabelled, causal efficacy was unproved and the full reported campaign cost did not fit. D09–D12/D37, S01–S09/S15; [ADR0003](../docs/decisions/0003-risk-coverage-statistical-contract.md). |
| Native pinned Laya0.3.28 CPU instead of speculative MLX or a coder/server stack | The audited native path exists and ran; research's latest0.3.24 claim was stale. Generic family labels, alternative-model licenses, fixed memory budgets and sub-50ms/~1GB claims were not adopted. Published checkpoint temperatures retain the training-data calibration caveat. No calibrated-probability or universal speed claim follows. M01–M23/M30; [Laya sources](SOURCES.md#l01--laya-packageruntime), [ADR0006](../docs/decisions/0006-tested-cpu-stack-and-licenses.md). |
| Correct licenses and Linux CPU distribution | The assets are not all Apache-2.0; actual Apache/MIT and compound dependency notices apply. Default Linux PyPI Torch pulled proprietary NVIDIA packages, so the lock selects official torch2.14.1+cpu; macOS retains the tested PyPI build. Metadata verification and later real Linux execution are distinct receipts. M29/P25; [dependency notices](../docs/dependencies.md), [L05](SOURCES.md#l05--linux-torch-distribution-correction). |
| Jev deferred; no proprietary core or required service | Documented price is not proof of universal access. Terms and API identity/normalization require a separately reviewed optional adapter; future key name is JEV_API_KEY. v1's fixture/local path is sufficient. Failures remain visible and conservative; no automatic provider switch or retry inherits ACT. M24–M28/P08/P13; [Jev sources](SOURCES.md#j01--jev-api-price-identity-and-confidence), [ADR0004](../docs/decisions/0004-identity-normalization-fallback.md). |
| Minimal public reuse instead of composing four runtimes | Port the audited ARCI CP primitives and use evidence/replay invariants; do not add SciPy or recursive framework gates. Scout's release warning prevents treating it as an authoritative gate; Dorian's code-executing checks add a different trust boundary. All four assets were verified public, but private unlicensed shared-brain code was excluded. Claimed 70–80% reuse was not measured. R01–R10/S16; [ADR0002](../docs/decisions/0002-minimal-attributed-reuse.md). |
| Honest demand, competition and success claims | Several cited upstream needs already received fixes/guides; Ollaya and AI PR Proof Gate overlap was verified. Unavailable sys1bench and unverified surveys/incidents/model counts do not establish absence or market demand. “10×,” adoption forecasts, star-to-integration equivalence, coverage-as-proof and zero-maintenance/cost claims are not publication facts. D14–D34/D36, P12/P14–P17; [research-only limits](SOURCES.md#research-only-evidence-and-negative-knowledge). |
| Fixture-first demonstration with a prespecified policy | Research's illustrative ticket counts were not results. The pending demo uses different authored outputs under the same fixed policy, not a repaired model, tuned threshold or population benchmark. Native preparation and execution are separate from the ≤60-second fixture target. P09/P10; [ADR0013](../docs/decisions/0013-prespecified-synthetic-demo.md). |
| Explicit execution, replay and resource limits | One fixed attempt uses case-level, unconditional assumptions; worker loss invalidates statistical assessment while retaining scheduled terminal evidence. Shared bounded readers, canonical faults and exclusive publication replace underspecified mechanics. A trusted lock anchors identity, not response execution or truth. These corrections make the chosen scope reviewable, not broader. S10/S17; [ADR0005](../docs/decisions/0005-data-only-replay-and-trust.md), [ADR0008](../docs/decisions/0008-fixed-collection-deadlines.md), [ADR0009](../docs/decisions/0009-worker-loss-invalidates-statistical-run.md), [ADR0010](../docs/decisions/0010-shared-bounded-input-helpers.md), [ADR0011](../docs/decisions/0011-provider-helpers-and-fixture-bound.md), [ADR0012](../docs/decisions/0012-replay-errors-and-exclusive-publication.md). |
| User engineering and publication rules override research defaults | Python3.12+/mypy, Claude-only product implementation, three implementation lanes plus Codex verification, frozen dependent interfaces and the requested TASK/REPORT/REVIEW format replace conflicting proposals. GitHub release is required; PyPI upload and promotional posting are not. No final delivery or cost forecast is reported as achieved. P01–P06/P11/P20–P24; [ADR0007](../docs/decisions/0007-claude-execution-codex-review-memory.md). |

## Known limitations and remaining issues

- Population interpretation requires independent cases under a fixed operating
  regime and selector, unconditional over one prespecified attempt. Literal
  overlap checks and hashes do not establish sampling independence or label truth.
  There is no uptime or completion-probability guarantee. Regular native worker
  loss produces diagnostic ERROR after integrity validation, with complete
  terminal records retained; it is not a completed statistical certification.
- Replay checks bounded data and recomputes semantics without provider imports or
  network calls. A trusted lock does **not** authenticate rewritten responses
  under that same lock, actual inference or authorship. A fully self-consistent
  forgery remains possible without an external authenticity mechanism.
- Native execution is a specialist pinned CPU path with a calibration caveat and
  strict truncation/deadline handling. The recorded macOS and Ubuntu/Python3.12
  receipts do not establish other hardware, native Python3.13 or model accuracy.
- Exclusive atomic publication uses macOS/Linux system APIs and rejects
  unsupported platforms/filesystems. It promises no power-loss durability or
  defense against a hostile process controlling ancestor directories. Input and
  bundle sizes are deliberately bounded; details are in [CONTRACTS](CONTRACTS.md).
- No material product defect remained at the accepted task heads. Release still
  requires T60's actual injected policy-violation/completeness test and rehashed
  fallback-flag forgery through public replay, plus the pending integration gates
  above. Sensitive raw inputs/responses need caller-controlled handling; generated
  runs are ignored by default, not automatically anonymized.

## Spend and execution accounting

**Recorded incremental paid inference API spend to this snapshot: USD 0.** No Jev
call or paid hosting was required. Claude used the existing authenticated
claude.ai Max subscription. Existing subscriptions, local compute and labour
are not claimed free. The completed-session meters below are estimates, not API
invoices; successive reports from one session are cumulative and must not be
added together. Final T50/T60 and full-session reconciliation remain pending.

| Completed execution session | Latest recorded estimated subscription meter |
|---|---|
| T00 foundation | $15.7246075 — [STATE receipt](STATE.md) |
| T10 contract/policy | $12.1806425 — [T10 review](reviews/T10-02.md) |
| T20 complete session | $11.50984675 — [T20 review](reviews/T20-02.md); includes the earlier $5.43887825 numerical milestone |
| T30 complete session | $20.95634925 — [T30 review](reviews/T30-03.md); replaces earlier milestone meter |
| T40 complete session | $18.21350825 — [T40 review](reviews/T40-02.md); includes corrective work |

Root checked the ignored raw result metadata: T20's numerical and assessment
attempts share session `14d9398c-146f-40cf-827d-a3c6a79632f1`; their cumulative
meters are not separate spend. All completed dispatches report the requested
`claude-fable-5-1` model. No final sprint total or invoice is asserted. The $100 projected incremental
spend escalation and two-day target remain in force; 8 October is only an
escalated buffer, not an already-used extension.

## Next three steps after v0.1.0

1. Record one independently reproduced external application integration using a
   prespecified policy and genuinely held-out data; publish its exact scope and
   limitations with permission, and use its friction points to prioritize v0.2.
2. Specify and test model/runtime upgrade comparison while retaining both locked
   identities and replayable evidence; do not introduce baseline or sequential
   statistical claims without a new sampling and error-budget contract.
3. Reassess demand and access for the optional Jev BYOK adapter, then specify its
   identity, normalization and conservative failure tests if warranted. Preserve
   the open local path and provider-free replay; hosting remains unnecessary
   unless a separately verified need changes that decision.
