# Actseal — research reconciliation

**Decision date: 6 October 2026.** The user selected **focused Decision Contract**, named **Actseal**, for a two-day v1. This document records the research comparison and verification underlying that choice. It is not a claim that the product has been implemented or independently validated. Product-code execution remains governed by the user's explicit phase approval and the task/review gates in PLAN.md.

## Decision and resolution method

Actseal is a small, local-first contract layer for the application branch after a probabilistic decision: frozen policy and labelled evidence, explicit failure behavior, finite-sample risk bounds and offline replay. It is researcher B's pick, using researcher A's supported boundary/fault/regression concerns. It is **not a deviation from both recommendations**. A's OS-security proxy, speculative model port and broad continuous-evolution benchmark are rejected from v1. Both reports' broad scope is reduced to the user's focused two-day choice; the detailed final IN/OUT list is authoritative in PLAN.md.

Resolution follows the requested order: **a**, both agree → provisionally adopt; **b**, disagreement → prefer dated primary evidence; **c**, equally evidenced → prefer hard-constraint fit; **d**, unresolved or materially project-changing → escalate. Agreement never bypasses verification. Factual claims without independent support remain **UNVERIFIED and non-load-bearing**. User requirements override either report. The product choice reached **d** and the user chose focused Decision Contract; naming reached **d** and the user chose Actseal.

Every matrix row carries the original claimant/citation/date, the other researcher's position, independent evidence, status, and disposition. All independent checks are dated **2026-10-06**; linked [SOURCES.md](SOURCES.md) gives primary URLs, publication/status dates, immutable references and verification limits. “Undated” means the original report did not provide a source publication date, not that the source has no date. B's `turn…` references are original opaque citation IDs, not reconstructed URLs.

### Researcher A — one-page account

**Recommendation and user.** Frontier-Gate is a local execution proxy for developers running autonomous coding agents. It combines frontier-scout policies, Laya/Jev semantic classification, ARCI regression statistics and Dorian evidence. Its launch wedge is preventing destructive operations allegedly bypassing Claude Code hooks; its second promise is stopping continuous codebase regressions. It proposes subprocess-stream interception, MLX inference, post-task Newcombe gates and automatic rejection/revert behavior.

**Alternatives and scoring.** Milestone-Evaluator is the strongest runner-up, scored 4.15/5. Other candidates are StrictHook eBPF, Decision-Router, Pydantic-Deep-Clone, Dorian-Registry, Vision-Code-Reviewer and Flakiness-Hunter. Frontier-Gate scores 4.90/5, with 20% net-new work claimed. The weights emphasize demand and sprint feasibility at 25% each. These are subjective planning estimates, not validated measurements.

**Evidence and assumptions.** Claude Code #46537/#4669/#43407/#37210 and RTK #260 support historical execution-permission integration pain. SWE-Milestone supports long-horizon regression concerns. Existing portfolio components could provide policy/statistical/replay primitives, while a small Laya model could fit local hardware. The proposal assumes the hook bug remains unpatched, terminal interception mediates all important effects, Laya works through MLX below 50 ms, the components compose cheaply, ordinary pre/post test outcomes justify its statistics, and broad license/memory claims hold.

**Independent result.** The unpatched-bug assumption is contradicted by Claude Code's 2.1.90 changelog and RTK's merged fix; #37210's reporter corrected their own hook. A stream wrapper cannot establish the claimed OS containment. SWE-Milestone's Score is not a generic success rate and its study does not validate Newcombe gating as a cure. “Exact Newcombe,” “absolute certainty,” all-Apache dependency claims and stars-as-integrations require correction. Local Laya feasibility is verified through its native CPU runtime, with a serious published-checkpoint calibration caveat. A's sub-50ms and MLX-specific claims are not adopted.

**Retained contribution.** Fault-test consequential boundaries, keep failure handling deterministic and visible, preserve replay, and reuse proven public primitives. Those ideas support Actseal without promising a universal agent security boundary. Each rejected candidate is explicitly accounted for below.

### Researcher B — one-page account

**Recommendation and user.** Decision Contract CI targets developers putting probabilistic outputs into deterministic application branches. It freezes the model/question/policy/data, evaluates accepted-action risk and coverage, injects provider failures, and returns PASS/BLOCK/INCONCLUSIVE with reproducible evidence. The first demo is support-ticket routing with an attractive-looking candidate whose unsafe timeout behavior is exposed.

**Alternatives and scoring.** Generic stochastic-agent regression CI scores 4.53/5, AI-contribution evidence gate 4.50 and reproducible eval evidence pack 4.42. Other candidates concern permission compilation, context budgets, MCP drift, threshold fitting, local serving and cascades. The winner scores 4.92/5 and assumes 70–80% reuse. B argues that existing local serving, calibration and evidence-gate products make those standalone alternatives less differentiated.

**Evidence and assumptions.** Laya reports describe confident wrong routing, calibration defects, abstention and the path from evaluation to deployment. TypeSafe API behavior and terms motivate optional adapters and explicit failure policies. ARCI, evalopt and Dorian supply relevant existing concepts. The original implementation proposes fixture/local/optional-Jev providers, immutable identities, statistics, fault/replay, CLI, Action and Linux/macOS CI, while excluding hosting, training and a production proxy. Assumptions include usable upstream APIs/checkpoints, economical reuse, valid sampling, and differentiation durable enough to survive fast upstream development.

**Independent result.** Practitioner concerns are real but several cited issues have already been addressed; staged-rollout docs and an existing collect/shadow/live tool limit the “unserved” claim. Laya 0.3.24 is stale: 0.3.28 and a pinned checkpoint have passed a one-case native CPU smoke test. The checkpoint's training/calibration overlap remains material, so its scores must not be advertised as calibrated probabilities. Ollaya and AI PR Proof Gate are live competitors; sys1bench's indexed README was found, but current repository access returned 404. All four public portfolio repositories/licenses were verified; no private protocol material is copied.

**Adopted with cuts.** Use the application-contract direction, fixture-first demo, independent statistical tests and offline replay. Defer broad v1 features per PLAN.md. Override B's Python 3.11, basedpyright and Codex implementation lanes with Python 3.12+, mypy and Claude-only product implementation. A hash seal proves artifact consistency, not label truth, statistical independence, runtime enforcement or universal safety.

## Claims matrix

**Status:** VERIFIED = independently established within the stated limit; REFUTED = contrary primary evidence or invalid inference; UNVERIFIED = no sufficient independent evidence and not load-bearing; ESTIMATE = judgment/target/design requirement rather than measured fact. **Disposition:** adopt, correct, reject, defer. “V” below is the verification gate, not a replacement for resolution steps a–d. “a fails” means disagreement or silence, so agreement cannot resolve the row. In a conflict, later steps are shown only when earlier ones do not settle it.

### Demand, competition and choice — D01–D37

| ID | Material claim / original citation and source date | Other researcher | Independent evidence / status | Resolution and disposition |
|---|---|---|---|---|
| D01 | A: Claude hook denial universally broken now; A#1/#2/#33/#39, undated in A | B silent on this defect | [H01–H03](SOURCES.md#h01--claude-code-historical-issues); REFUTED current generalization | a unavailable; V rejects current universal premise. |
| D02 | A: #46537 proves unpatched October bug; A#1, undated | B silent | H01: Apr 11 report, Apr 14 duplicate closure; VERIFIED historical only | Correct to historical report; no October load-bearing claim. |
| D03 | A: #4669 confirms current failure; A#2, undated | B silent | H01: Jul 29 2025 report, Jan 5 2026 inactivity closure; VERIFIED historical | Correct; closure alone neither proves fix nor continued defect. |
| D04 | A: #43407 remains unpatched; A#33, undated | B silent | [H02](SOURCES.md#h02--official-claude-code-changelog); REFUTED, documented 2.1.90 fix | Reject current-bug wedge by V. |
| D05 | A: #37210 proves native denial defect; A#39, undated | B silent | H01 reporter correction Mar 21; REFUTED attribution | Correct to integration bug; current docs control protocol. |
| D06 | A: RTK #260 is ongoing bypass; A#40, undated | B silent | [H05](SOURCES.md#h05--rtk-permission-rewrite-defect-and-fix); REFUTED unresolved premise, merged fix | Keep historical failure class, reject current unsupported allegation. |
| D07 | A: four duplicates/high votes imply intense current demand; A#1/#33 and §2, undated | B silent | H01; UNVERIFIED frequency, votes and independent user count | Do not count duplicates as independent adoption/demand observations. |
| D08 | A: governance impossible/no workaround; A#1/#34 and §2, undated | B silent | [H03/H04](SOURCES.md#h03--current-hooks-protocol); REFUTED universal claim | Correct: controls exist with explicit trust boundaries. |
| D09 | A: continuous evolution accumulates regressions; A#3/#4, undated; B broadly values regression evidence | agree on problem | [E01](SOURCES.md#e01--swe-milestone), v4 Jul 21; VERIFIED within benchmark | a+V adopt motivation, not a product-effect claim. |
| D10 | A: >80%→<39% success rates; A#3, undated | B silent | E01; REFUTED metric label; composite Score ≤38.03%, separate Resolve Rate | Correct terminology; do not turn score into accuracy/success. |
| D11 | A: weakness across all frontier models; A#3 and §2, undated | B silent | E01; VERIFIED only 12 models/four frameworks tested | Correct scope; no universal extrapolation. |
| D12 | A: statistical gate mathematically solves regression snowballing; A#3/#27/#32, undated | B silent on causal effectiveness | E01 lacks evaluation of that intervention; UNVERIFIED | Reject as demonstrated efficacy; test only Actseal's defined contract. |
| D13 | A: CI/observability has no relevant gates; A#37/#41/#42, undated; B describes existing ARCI/model gates | disagree on breadth | [R01](SOURCES.md#r01--public-repository-identities-and-licenses), L01; REFUTED universal absence | a fails→b favors existing primary implementations; narrow claim. |
| D14 | B: Chinese routing issue #124; `turn12search1`, Sep 22 | A silent | [L04](SOURCES.md#l04--demand-reports-and-upstream-responses); VERIFIED 20-case reporter concern | Adopt qualitative pain, not population error estimate. |
| D15 | B: Romanian routing issue #35; `turn12search5`, Sep 20 | A silent | L04; VERIFIED 20-case reporter concern, closed Sep 23 | Same limit; do not label unresolved platform-wide defect. |
| D16 | B: #367 shows unserved rollout path; `turn12search6`, Sep 24 | A silent | L04; VERIFIED request but shipped guide and existing stuntd | Correct demand gap; own frozen evidence/fault semantics, not first rollout tooling. |
| D17 | B: #361 requests abstention; `turn12search9`, Sep 24 | A silent | L04; VERIFIED, implemented by Oct 1 | Adopt motivation; reject duplicative standalone fitter. |
| D18 | B: #186 leakage repaired; `turn12search3`, Sep 22 | A silent | L04/L02; VERIFIED notebook fix, checkpoint not refitted | Correct to retain checkpoint caveat explicitly. |
| D19 | B: #637 clamp inconsistency; `turn12search7`, Sep 27 | A silent | L04; VERIFIED notebook fix 0.3.23, remaining checkpoint caveat | Adopt robustness requirement; don't advertise calibrated checkpoint. |
| D20 | B: Sep 21 TypeSafe incidents motivate failure tests; `turn21search0/2/6`, Sep 21/Oct 6 | A agrees failure risk, silent incident | [U01](SOURCES.md#u01--unverified-non-load-bearing-claims); UNVERIFIED incident chronology | Adopt explicit failure testing as requirement; not outage claim. |
| D21 | B: 27 decision models by Oct 2; `turn18search2`, Oct 2 | A silent | U01; UNVERIFIED community count | Non-load-bearing; do not publish count. |
| D22 | B: Laya already has extensive calibration/evals/abstention; `turn14search0`, Oct 6 crawl | A silent on overlap | [L01/L04](SOURCES.md#l01--laya-packageruntime); VERIFIED general overlap, not every advertised metric | Correct stale version; avoid calibrate-Laya-only product. |
| D23 | B: Ollaya already supplies local daemon; `turn13search3`, early Oct | A silent | [C01](SOURCES.md#c01--ollaya); VERIFIED feature description | Adopt competitive limit, no performance/adoption inference. |
| D24 | B: AI PR Proof Gate directly overlaps; `turn11search13`, Oct 2 crawl | A silent | [C02](SOURCES.md#c02--ai-pr-proof-gate); VERIFIED narrative/features | Adopt differentiation reason; trust-model equivalence not asserted. |
| D25 | B: sys1bench available model benchmark; `turn18search0`, late Sep | A silent | [C03](SOURCES.md#c03--sys1bench-availability-qualification); UNVERIFIED current availability | Correct to historical indexed evidence; live 404 is not absence proof. |
| D26 | B: ReflexBench/paired papers crowd benchmarks; `turn18search11/4/academia47`, paper Oct 1 | A silent | U01; UNVERIFIED full comparative claims | Non-load-bearing; no leaderboard by scope decision. |
| D27 | B: AgentAssay duplicates generic CI; `turn7search0/6search8`, undated | A silent | U01; UNVERIFIED competitor detail | Defer generic CI because ARCI already exists, independently of this claim. |
| D28 | B: permission/MCP competitors cover feature space; `turn6search0/2/3/4`, undated | A silent | U01; UNVERIFIED full parity/adoption | Defer on integration scope, not assumed competitor superiority. |
| D29 | B: GitHub contribution discussion/controls; `turn9search9/6/0`, Jan 27/Feb/Jun | A silent | U01; UNVERIFIED chronology/features | Non-load-bearing market context. |
| D30 | B: GitHub security reports burden; `turn9search3`, Mar 16 | A silent | U01; UNVERIFIED | Non-load-bearing; no quantified maintenance claim. |
| D31 | B: Godot/Homebrew/PostHog policies; `turn8search10/9search1/8search5`, 2026 | A silent | U01; UNVERIFIED current wording | Exclude from Actseal launch claims. |
| D32 | B: Stack Overflow 66/46/33/3% figures; `turn17search2/3`, 2025 and Sep 30 2026 | A silent | U01; UNVERIFIED | Do not use as project demand validation. |
| D33 | B: JetBrains increasing agent adoption; `turn17search12/13`, Aug 2026 | A silent | U01; UNVERIFIED | Broad context only. |
| D34 | B: HN/X evidence insufficient; §Demand; Reddit `turn20search2`, undated | A cites no stronger direct evidence | Original report; VERIFIED research limitation, not ecosystem absence | Adopt honesty; no manufactured social proof. |
| D35 | A selects Frontier-Gate; B selects Decision Contract; both §Recommendation, Oct vantage | disagree | H01–H05/L01–L04/R01; ESTIMATE product judgment plus user decision | a fails→b weakens A wedge→c favors focused portability→d user selects Decision Contract/Actseal. |
| D36 | Both: 10× advantage; candidate tables, no empirical source/date | agree aspiration, differ product | [U02](SOURCES.md#u02--predictions-and-design-judgments); ESTIMATE | a cannot verify multiplier; correct to testable differentiation hypothesis. |
| D37 | A: SWE-Pro V2 September locked network/patch-fetch contamination; A#24, undated | B silent | [E03](SOURCES.md#e03--swe-bench-pro-v2), Sep 22; VERIFIED protocol update, detailed reproduction UNVERIFIED | Adopt reproducibility principle only. |

### Models, hardware and licenses — M01–M30

| ID | Material claim / original citation and source date | Other researcher | Independent evidence / status | Resolution and disposition |
|---|---|---|---|---|
| M01 | A: M5 Pro bandwidth 307 GB/s; A#5, undated | B silent | U01; UNVERIFIED | Non-load-bearing; local feasibility measured instead. |
| M02 | A: exactly 20.6 GB usable; A §eliminations, A#5/#9, undated | B silent | U01; UNVERIFIED | Reject fixed allocatable-memory premise. |
| M03 | A: Qwen2.5-Coder-14B optimal/Apache; A#5, undated | B prefers no coder dependency | U01; UNVERIFIED optimality/license here | a fails→b lacks comparison→c no generative coder in core; defer. |
| M04 | A: Q8 14.4 GB, 11 tok/s; A#5, undated | B silent | U01; UNVERIFIED | Defer; Q8 not user's approx ≤14B/4-bit envelope. |
| M05 | A: Qwen3.6 27B/35B footprints, swap <5 tok/s; A#7–9, undated | B silent | U01; UNVERIFIED | Excluded models; no performance claim. |
| M06 | A: concurrent vision must violate cap; A#45/#46, undated | B silent | U01; UNVERIFIED | Reject vision on scope, not this unsupported necessity. |
| M07 | A: MLX universally 20–87% faster; A#6, undated | B silent | U01; UNVERIFIED | Do not adopt universal backend/performance conclusion. |
| M08 | A: Ollama ≥0.19 integrates required MLX path; A#6, undated | B avoids inference server | U01; UNVERIFIED | c excludes unnecessary dependency; no availability assertion. |
| M09 | Both: vLLM/SGLang unnecessary; A#10–12; B `turn15search5`, undated/Sep | agree simplification | Design judgment; ESTIMATE | a+c adopt no inference-server requirement. |
| M10 | A: typed outputs inherently calibrated/parse-proof; A#13–17, undated; B warns confidence not correctness | disagree | [L02/J01](SOURCES.md#l02--exact-reference-checkpoint-and-material-calibration-caveat); REFUTED calibration inference | a fails→b empirical caveat/confidence docs; validate responses and own policy. |
| M11 | Both: small Laya 421M/322M Apache checkpoints; A#18; B `turn14search0/13search2`, Oct 6 | agree | L01/L02; VERIFIED chosen 421,293,830-param Apache checkpoint; 322M not needed | a+V adopt exact verified checkpoint only. |
| M12 | A: Laya launch Sep 18; A#18, date asserted | B broadly agrees timing | Original assertion; UNVERIFIED exact launch date | Non-load-bearing chronology. |
| M13 | A: sub-40/50ms/~1GB local; A#18; B says easy fit, Oct 6 | agree fit, silent exact latency | [L03](SOURCES.md#l03--independently-executed-local-feasibility-probe); VERIFIED ~1.87/2.92GB peak smoke, .276/.137s prediction | Correct: native CPU fits; no sub-50ms guarantee or quality inference. |
| M14 | B: latest Laya 0.3.24/features; `turn14search0/13search2`, Oct 6 | A silent version | L01; REFUTED latest claim, .28 uploaded Oct 5 | Correct pin to verified .28; don't blindly upgrade dependencies later. |
| M15 | Both: typed-decisions default exact license/checkpoint; A#18/#23; B `turn14search0`, undated/Oct 6 | agree family, identifiers imprecise | L02/L03; VERIFIED full id/revision, ungated; calibration caveat | a+V adopt pinned specialist; record caveat and independently test policy. |
| M16 | A: native MLX/mlx-lm Laya support; §Stack A#6; B native Python | disagree runtime | L01/L03; VERIFIED native Torch CPU, MLX port UNVERIFIED | a fails→b native source/smoke→c avoid custom port; reject MLX plan. |
| M17 | A: llama.cpp drop-in fallback for Laya; A#21, undated | B silent | U01; UNVERIFIED specific compatibility | Defer; native CPU reference supplies community path. |
| M18 | A: Clef27.4B/Qwen3.8, Flash9.4B/Qwen3.5/licenses; A#16/#20, undated | B silent | U01; UNVERIFIED | Exclude/defer; no inference from model-family names. |
| M19 | A: Julia144M/mmBERT/license/performance gap; A#16/#22, undated | B silent | U01; UNVERIFIED | Defer; no dependency. |
| M20 | B: Qwen3.5-9B Apache/hardware; `turn16search6`, Oct | A recommends other generative model | U01; UNVERIFIED here | a fails→b no comparison→c no comparator needed; defer. |
| M21 | B: gpt-oss20B/120B Apache plus usage policy; `turn15search0/1`, Sep/current | A silent | U01; UNVERIFIED here | Exclude outside needed envelope; no license reliance. |
| M22 | B: Qwen3 embeddings .6/4/8B/licenses; `turn16search4/5/16`, undated | A silent | U01; UNVERIFIED | Not needed; defer. |
| M23 | B: current speech/reranker leaders unverified; §Landscape | A silent | Original report explicitly UNVERIFIED | Preserve exclusion; do not invent choices. |
| M24 | Both: Jev hosted/proprietary/optional; A#13/#17; B `turn22view0`, Sep 15 | agree | [J01/J02](SOURCES.md#j01--jev-api-price-identity-and-confidence); VERIFIED hosted documented service, no open weight path adopted | a+user open-core constraint; defer adapter v2. A's RLCD/Brier architecture specifics remain UNVERIFIED/non-load-bearing. |
| M25 | Jev Sep15 launch/waitlist/GA; A#13; B `turn22view0`, Sep15 | agree early access; B qualifies current certainty | J02; VERIFIED announcement, current universal access UNVERIFIED | Correct availability; local path cannot depend on a key. |
| M26 | B: API0.2.0/endpoints/aliases/schema; `turn21search3/11`, Oct2–6 | A agrees optional adapter, silent details | J01; VERIFIED docs, no authenticated smoke | Future contract must pin identity/normalize probabilities; defer live adapter. |
| M27 | Both: Jev $.042/million input; A#14; B `turn22view0/21search13`, Sep15/Oct | agree | J01; VERIFIED documented price Oct6 | a+V cost basis only, not guarantee of access/total cost. |
| M28 | B: customer integration right/restrictions/API churn; `turn21search1`, Sep23 | A silent terms | J02; VERIFIED published wording, legal application is interpretation | Preserve restrictions; no proprietary core or public proxy. |
| M29 | A: entire stack Apache; B identifies MIT assets; original §Stacks | disagree | [R01](SOURCES.md#r01--public-repository-identities-and-licenses); REFUTED all-Apache | a fails→b license files; use compatible notices per component. |
| M30 | A: MLX mapping avoids cache disruption; §Risks A#6/#18, undated | B silent | U01; UNVERIFIED | Exclude hardware/cache guarantee. |

### Existing assets and statistical/enforcement claims — R01–R10, S01–S17

| ID | Material claim / original citation and source date | Other researcher | Independent evidence / status | Resolution and disposition |
|---|---|---|---|---|
| R01 | Both: ARCI gates/fault/replay available; A §Assets; B `turn3file0`, Oct6 | agree | [R01/R02](SOURCES.md#r02--independently-checked-statistical-reuse); VERIFIED public source and bounded tests | a+V reuse minimal primitives, not whole runtime. |
| R02 | B: ARCI .7/license/deps; `turn5file0`, Oct3 | A silent version | SOURCES R01/R02; VERIFIED audited commit/license; dependency envelope not final lock | Adopt immutable source attribution; resolve final dependencies separately. |
| R03 | A: SciPy-backed stats runtime; §Stack A#27; B stdlib-minimal | disagree | SOURCES R02; REFUTED SciPy necessity for selected CP kernel | a fails→b actual code; stdlib port within audited envelope. |
| R04 | B: 902 Jev decisions ~$0.018; `turn3file0`, Oct6 read | A silent exact campaign | U01; UNVERIFIED campaign details in this audit | Historical narrative only; don't claim independently rerun. |
| R05 | Both: frontier-scout policy assets reusable; A §Assets; B `turn1file0`, Oct6 | agree broadly | SOURCES R01/R03; VERIFIED policy context, not OS mediation | a+V concepts only; no security-wrapper inference. |
| R06 | B: released scout v2.1.0 false acceptance/unreleased fix; `turn1file0`, Oct6 | A assumes reliable enforcement | SOURCES R01/R03; VERIFIED pinned README warning | a fails→b primary warning; advisory only, never mandatory release gate. |
| R07 | Both: evalopt deterministic acceptance; B `turn4file0`, Oct3, MIT | agree | SOURCES R01/R03; VERIFIED | a+V adopt separation/canonicalization with notices, not nested dependency. |
| R08 | Both: Dorian warrants; B `turn2file0`, Sep30, warns code-executing checkers | disagree mandatory gate | SOURCES R01/R03; VERIFIED capabilities/limits | a fails→b trust boundary→c no mandatory extra verifier. |
| R09 | Both: 70–80%/80% reuse, readily composable; candidate tables, Oct vantage | agree optimism | U02; ESTIMATE; narrow CP reuse verified | a cannot establish percentage; record integration budget not measured reuse. |
| R10 | A: integrate four runtime packages; B: port minimum only; §Architecture/Reuse | disagree | SOURCES R01–R04; ESTIMATE architecture choice | a fails→b no performance comparison→c minimal public ports. Private shared-brain not copied. |
| S01 | A: Wald boundary coverage weaknesses; A#27, undated | B silent | [E02](SOURCES.md#e02--newcombe-interval-paper); VERIFIED general statistical distinction | Adopt rationale for appropriate method, not universal superiority slogan. |
| S02 | Both: exact conservative CP binomial interval; A#28; B `turn3file0`, undated/Oct6 | agree | SOURCES R02; VERIFIED implementation/oracles in envelope | a+V adopt with independent sampling and fixed policy assumptions. |
| S03 | A: Newcombe exact/absolute certainty; A#27/#31; B finite-sample uncertainty | disagree | E02, Apr30 1998; REFUTED | a fails→b primary statistics; no absolute assurance claims. |
| S04 | A: lower NI bound below margin proves regression; A#32, undated; B three-way verdict | disagree | E02/R02 and statistical inference; REFUTED interpretation | a fails→b interval meaning; preserve insufficient-evidence outcome. |
| S05 | A: ordinary suite pass rate supports binomial guarantees; §Evaluation | B silent exact sampling unit | Statistical inference; UNVERIFIED sampling assumptions | Reject load-bearing use absent predeclared estimand/unit; deterministic tests must pass directly. |
| S06 | A: pre/post same tests handled as independent proportions; A#27/#31 | B silent paired detail | E02 independent-proportion scope; UNVERIFIED independence | Do not silently apply independent test to paired/correlated outcomes; comparison deferred. |
| S07 | B: accepted-action error/coverage are useful contract metrics; §Statistical policy | A agrees statistical accountability, silent estimand | Design judgment, ESTIMATE; R02 supports calculation | Adopt explicit bounded estimand; avoid general safety interpretation. |
| S08 | B: critical-action/slice/baseline gates in v1; §Scope/Statistics | A silent multiplicity | Design requirement; simultaneous guarantee UNVERIFIED unless budgeted | Defer beyond focused scope; no unadjusted multi-gate assurance. |
| S09 | B: separate calibration/planning from verification; §Contract | A silent exact split policy | Method requirement; VERIFIED logical leakage risk, not dataset independence | Adopt locked policy/held-out identities; hashes alone do not create independence. |
| S10 | B: identity/data hashes prove exact evidence; §DoD | A agrees sealing | SOURCES R03; VERIFIED consistency mechanisms, stronger truth claim REFUTED | a+V adopt artifact integrity; explicitly exclude truth/authenticity/independence guarantees. |
| S11 | A: shell wrapper enforces OS containment; §Architecture | B excludes production proxy | [H04](SOURCES.md#h04--actual-os-enforcement-requirements); REFUTED proposed mechanism | a fails→b OS boundary docs→c no containment product. |
| S12 | A: semantic confidence yields safe permission; §Wedge | B confidence insufficient | L02/J01; REFUTED implication | a fails→b calibration/semantics→c deterministic application policy. |
| S13 | A: terminate subprocess/drop streams prevents effects; §Architecture | B silent | H04 plus execution-order reasoning; REFUTED as guarantee | Reject: effects may precede termination; wrapper only controls explicit owned dispatch. |
| S14 | A: 100 blocked examples prove hard security; §Evaluation | B asks bounded policy tests | Test interpretation; REFUTED extrapolation | Correct to measured fixture coverage, not universal safety. |
| S15 | A: SWE-Milestone evaluation near-zero budget; §Evaluation/Costs | B excludes big benchmark | E01; REFUTED full-run fit, ~$500 | a fails→b published cost→c no full campaign; subsets would require separate bounded claims. |
| S16 | A: recursive ARCI/evalopt CI gate; B: independent deterministic tests | disagree | R02/R03; ESTIMATE assurance architecture | a fails→b no benefit shown→c direct lint/type/test/oracle/replay checks. |
| S17 | Both: seeded failures and replay validate boundary behavior; §Tests | agree | Design requirement; source invariants R02/R03 VERIFIED, Actseal pending | a+V adopt bounded acceptance tests; not already-shipped evidence. |

### Delivery, cost, roadmap and current instruction overrides — P01–P25

| ID | Material claim / original citation and source date | Other researcher | Independent evidence / status | Resolution and disposition |
|---|---|---|---|---|
| P01 | Both: two/three-day fit and weighted rankings; scoring/schedule tables, Oct vantage | disagree winner | U02; ESTIMATE | a fails→b no measured effort comparison→c focused cuts→d user approved focused two-day direction. |
| P02 | A Python3.12; B3.11; stack tables | disagree | Current user standard; requirement | a fails→b both feasible→c user3.12+ controls. |
| P03 | A mypy; B basedpyright; stack/testing | disagree | Current user standard; requirement | a fails→b both plausible→c mypy required. |
| P04 | Both assign product implementation to Codex; lane tables | agree, conflict with user | Current user instruction; requirement | a overridden: Claude writes product code; Codex plans/reviews/gates. |
| P05 | A Pydantic/SciPy/MLX core; B stdlib small core; stacks | disagree | L01/R02 plus design; ESTIMATE | a fails→b unnecessary deps identified→c minimal core, native optional model path. |
| P06 | Exact dev versions/licenses; A stack; B `turn5file0` ranges, Oct3 | partial agreement | Final lock not created here; UNVERIFIED final dependency set | Require verified resolved lock and license inventory; never invent point releases. |
| P07 | B choice/binary/score/planner/baseline/slices all v1; §Scope | A different broad v1 | U02; ESTIMATE feasibility | a fails→b no effort evidence→c cut to focused scope→d user selected focused v1; PLAN defines retained interfaces. |
| P08 | Both optional Jev plus local fallback; A#13/#18; B API/Laya refs | agree | J01/J02/L03; VERIFIED local path, future adapter requirement | a+user adopt provider boundary; Jev v2, visible conservative failure behavior. |
| P09 | A live-model quickstart; B zero-key fixtures first; DoD | disagree | L03 first-download cost plus design | a fails→b cold setup not60s assured→c fixture-first; optional downloaded local smoke separately. |
| P10 | Both byte-replay and corruption rejection; DoD | agree | R03 source invariants, Actseal not yet implemented | a adopt testable requirement, not completed capability. |
| P11 | Both CI/lock/license/docs/tag/launch draft; DoD | agree | Current user checklist; requirement | a+user adopt; publication waits for green independent review. |
| P12 | A >90% coverage establishes quality; DoD | B emphasizes fault/oracle cases | U02; ESTIMATE adequacy | Correct: coverage alone no correctness proof; prioritize meaningful acceptance cases. |
| P13 | Both mandatory hosting $0; Costs | agree | No-service architecture; ESTIMATE future cost | a+c adopt no mandatory service; distinguish CI/local compute/labor. |
| P14 | A zero maintenance/user cost; B qualifies local compute/CI | disagree | Cost-accounting inference | a fails→b no labor evidence→c correct wording; no literally costless claim. |
| P15 | Both near-zero/<$20 sprint API cost; Costs | agree estimate | J01 price, audits $0 paid spend; ESTIMATE sprint forecast | a+user $100 escalation; no full benchmark; subscriptions not claimed free. |
| P16 | A50 stars equals50 integrations; §Success | B asks external real repos | disagree | Metric-definition inference; REFUTED equivalence | a fails→b different observables; use adoption evidence, not stars. |
| P17 | A/B30/90-day adoption numbers; Success sections | differing targets | U02; ESTIMATE | Preserve as optional goals, no forecast/achieved claim. |
| P18 | A MCP proxy/live forking roadmap; §Versions | B different direction | U02; ESTIMATE | Defer outside Actseal direction; no obligation to build security proxy. |
| P19 | B scores/shadow/diff/signing/cascades/registry roadmap; §Scope | A partly overlaps | U02; ESTIMATE | Defer; evaluate later demand before commitments. |
| P20 | Both GitHub-first launch/community posts; Distribution | agree | Current user authorizes draft; requirement | a adopt draft launch, no unsolicited external posting. |
| P21 | Both upstream/access/dependency risks; B leakage/privacy/absorption emphasis | agree broad risks | L01/L02/J02/R01; VERIFIED concrete examples | a adopt mitigation: minimal deps, local path, fixed policy, explicit sensitive-data boundary. |
| P22 | B name decision-contract availability unknown; §Open questions | A different name | User selected Actseal; availability UNVERIFIED in this audit | a fails→b names not evidence→c none→d user names Actseal; actual publishing identifier checks separate. |
| P23 | B six-field task template; §Repo structure | A different task layout | Current user's TASK/REPORT/REVIEW format | User format overrides both; every task retains exact required fields. |
| P24 | A two implementation lanes; B seven lanes; §Work breakdown | disagree | User2–4 independent lanes; ESTIMATE scheduling | a fails→b no measured throughput→c 2–4 frozen-owner lanes plus continuous verification; Claude-only product work. |
| P25 | New T00 dependency audit: PyPI torch2.14.1 Linux resolution pulls cuda-toolkit/nvidia-cublas13.1.1.3 with LicenseRef-NVIDIA-Proprietary; neither research supplied a distro-variant citation. Observation 2026-10-06. | A silent; B silent | [L05](SOURCES.md#l05--linux-torch-distribution-correction), PyPI and official PyTorch CPU metadata/uv docs checked 2026-10-06 by model-audit lane; VERIFIED default-graph license conflict and cp312/cp313 Linux x86-64 CPU metadata availability/direct requirements. Corrected uv resolution and live Linux runtime NOT RUN at observation. | a no shared variant claim→b dated metadata establishes incompatible default graph→c hard OSS constraint rejects default Linux GPU resolution; require explicit official torch2.14.1+cpu Linux markers/index, preserve tested macOS PyPI2.14.1→d not needed for this corrective implementation choice. Corrected lock/transitive license and Linux execution remain acceptance gates, not assumed facts. |

## All candidate dispositions

Scores and net-new shares below are the researchers' estimates, retained for accountability, **not independently measured rankings**. A/B source is each original Candidates and Scoring section. Reject means reject for this sprint, not that the idea has no value.

### Researcher A — eight candidates

| Candidate | Research score / net-new | Disposition and reason |
|---|---|---|
| A1 StrictHook eBPF | 3.20 /90% | Reject: cross-platform kernel containment does not fit Python-first two-day scope; impossible-to-bypass claim unproved. |
| A2 Decision-Router | 3.00 /80% | Reject standalone: broad routing/optimization adds integrations without the narrower action-contract wedge. Retain only necessary provider interface. |
| A3 Pydantic-Deep-Clone | 3.25 /60% | Reject: a maintained framework fork is unnecessary for bounded application policy and conflicts with minimal sprint scope. |
| A4 Milestone-Evaluator | 4.15 /40% | Defer: expensive full benchmark and substantial environment work. Retain regression motivation; do not claim a full SWE-Milestone result. |
| A5 Frontier-Gate Proxy | 4.90 /20% | Reject security-proxy v1: patched-bug premise, unproved containment and speculative MLX integration. Retain fault/policy/replay ideas in Actseal. |
| A6 Dorian-Registry | 2.75 /70% | Reject: IPFS/distributed storage adds infrastructure without demonstrated need; local evidence bundles cover current objective. |
| A7 Vision-Code-Reviewer | 2.70 /90% | Reject: low reuse and different user need. Rejection does not depend on A's unverified hardware-impossibility claim. |
| A8 Flakiness-Hunter | 2.95 /85% | Defer: separate trajectory/QA product with weaker current reuse; deterministic tests and explicit sampling remain mandatory here. |

### Researcher B — ten candidates

| Candidate | Research score / net-new | Disposition and reason |
|---|---|---|
| B1 Decision Contract CI | 4.92 /~25% | Adopt focused version as **Actseal**, user chosen. Its branch/fault/evidence scope fits verified public primitives and local CPU feasibility. |
| B2 AI-contribution evidence gate | 4.50 /~15% | Reject this sprint: verified narrative overlap with AI PR Proof Gate; stronger differentiation would require more provenance/integration work. |
| B3 Generic stochastic-agent regression CI | 4.53 /~10% | Defer to existing ARCI: duplicates an already public asset. AgentAssay details are not necessary for this rejection. |
| B4 Reproducible eval evidence pack | 4.42 /~20% | Absorb minimal bundle/replay capability; defer standalone product and signing. |
| B5 Cross-agent permission compiler | 4.25 /~35% | Defer: proving semantic equivalence across harnesses expands integration and enforcement claims beyond two days. |
| B6 Agent context-budget auditor | 4.08 /~75% | Defer: thinner directly verified demand and little reusable implementation; instrumentation is a separate project. |
| B7 MCP schema-drift/tool firewall | 4.08 /~50% | Defer: separate protocol security boundary and integration burden; no unsupported competitor-parity premise needed. |
| B8 Calibration/threshold fitter | 4.38 /~30% | Reject standalone: upstream features exist. Actseal accepts a frozen application policy; no claim to fix the checkpoint's calibration or automatic threshold search in focused v1. |
| B9 Local System-One daemon | 3.90 /~80% | Reject: verified Ollaya supplies serving/model-management role; Actseal does not need a new daemon. |
| B10 Decision cascade/router | 4.03 /~65% | Defer optimization/cascades: distinct selection/calibration problem. Keep only bounded, explicit conservative failure behavior. |

## Adopted limits and remaining verification

1. **No unsupported security or statistical guarantee.** Actseal checks a defined application policy against declared evidence; it does not sandbox agents, authenticate labels or prove production safety. Published model probabilities are not assumed calibrated. No Newcombe, baseline, slice or multi-stage assurance is added without a specified sampling/multiplicity contract.
2. **Open and reproducible core.** The native pinned Laya CPU path ran locally; a fixture path must remain model-free. Jev is optional future work under `JEV_API_KEY`. No service is required. P25 rejects the proprietary dependencies in the default Linux GPU resolution and requires an explicitly selected official CPU build; metadata availability is verified, but corrected lock/transitive license and Linux execution checks remain pending at that observation. Final Linux/package/CI checks and the actual Actseal port require their own execution evidence.
3. **Public reuse only.** All four portfolio repositories are public; retain their actual Apache/MIT notices. The private shared-brain protocol is not copied. Preserve ARCI's frozen files and use only the audited minimal statistical primitives/invariants.
4. **Scope and publication honesty.** Scores, reuse percentages and delivery/adoption goals remain estimates. Every UNVERIFIED fact is non-load-bearing. Reopen verification if it becomes required. Claims about the demo must use measured outputs; research's illustrative 200-ticket numbers are not results.
5. **Source preservation and ownership.** Keep the two full research originals local/untracked. This reconciliation and SOURCES are authored summaries, not private source dumps. Task owners and acceptance gates live in PLAN/tasks; no code or release success is asserted by these documents.
