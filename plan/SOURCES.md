# Actseal — source and verification ledger

**Checked: 6 October 2026 (Asia/Kolkata).** This ledger distinguishes independently read primary sources, locally executed probes, research-only assertions, and planning decisions. A source's publication date is not its verification date. Live-source observations are time-bound. Repository metadata, issues, comments and source files were read through the GitHub plugin where available; official web, PyPI and Hugging Face endpoints supplied the remaining checks. No paid provider calls or secret reads were used for these audits.

## Original research

| ID | Original document | Citation convention and date limitations |
|---|---|---|
| A | `research/AI Agent OSS Sprint Plan.md` — *Frontier-Gate: An Enforced Zero-Trust Execution and Regression Proxy for AI Coding Agents* | A#1–A#50 refer to its numbered Works cited entries. The report uses an October 2026 vantage point but supplies no independently established creation date. Most cited sources have no publication date in A; mark those **undated in A**, rather than inventing a date. |
| B | `research/deep-research-report.md` — *Highest-Leverage Open-Source Project for a Three-Day AI Engineering Sprint* | B's `turn…` citation identifiers are preserved as original provenance. They are not portable hyperlinks. Its Sources table supplies dates that remain researcher-reported until matched below. |
| U | Current user instructions and subsequent decisions in this chat | User selected the focused two-day Decision Contract direction and the name **Actseal**. These are authority for scope/name, not external market evidence. Product implementation belongs to Claude Code; Codex plans, reviews and gates. |

The two research originals remain local and untracked; they are not copied into the public deliverable. Reconciliation paraphrases their claims and retains citation identifiers. No missing B URL has been reconstructed from an opaque identifier. Public source links below were actually observed or verified by a collaborating audit agent.

## Primary sources: execution boundaries and evaluation

### H01 — Claude Code historical issues

| Source | Source date/status observed | What it establishes and its limit |
|---|---|---|
| [#46537](https://github.com/anthropics/claude-code/issues/46537) | Created 2026-04-11; closed duplicate 2026-04-14 | Windows v2.1.101 user report; duplicate of #43407. Does not establish a current universal failure. Examples mix `block` and `deny`. |
| [#4669](https://github.com/anthropics/claude-code/issues/4669) | Created 2025-07-29; closed not_planned 2026-01-05 | v1.0.62 report; closure was inactivity housekeeping. Initial JSON uses top-level permissionDecision. Not independently reproduced. |
| [#43407](https://github.com/anthropics/claude-code/issues/43407) | Created 2026-04-04; closed completed 2026-04-17 | Reporter v2.1.87; [closing comment](https://github.com/anthropics/claude-code/issues/43407#issuecomment-4267595557) says fixed in v2.1.90. |
| [#37210](https://github.com/anthropics/claude-code/issues/37210) | Created/closed 2026-03-21 | [Original reporter's resolution](https://github.com/anthropics/claude-code/issues/37210#issuecomment-4104404599) attributes failure to their hook implementation and confirms wrapped JSON plus exit 0 works. Historical exit-code interpretation does not override current documentation. |

### H02 — official Claude Code changelog

[CHANGELOG.md, v2.1.90](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md#2190), retrieved file blob SHA `20657faf83be37bb5f51c2c47d398815adefbe78`, documents a fix for PreToolUse hooks emitting JSON to stdout and exiting 2 not blocking correctly. The changelog version is verified; an exact release day was not independently established from a release object. This is evidence of a published fix, not a fresh security reproduction.

### H03 — current hooks protocol

[Official hooks reference](https://code.claude.com/docs/en/hooks), current documentation checked 2026-10-06: wrapped `hookSpecificOutput.permissionDecision`, exit-2 blocking and multiple-hook precedence. `block` is a deprecated top-level decision value, not a supported value for `permissionDecision`. Documentation is a contract; this audit did not run a live Claude security test.

### H04 — actual OS enforcement requirements

[Official sandbox documentation](https://code.claude.com/docs/en/sandboxing), checked 2026-10-06: Seatbelt on macOS, bubblewrap on Linux/WSL2, and limitations of the Bash sandbox versus built-in tools/other processes. The source distinguishes command permission checks from OS enforcement and describes whole-process containment. The conclusion that merely piping terminal streams cannot mediate arbitrary syscalls is an engineering inference from these documented boundaries and A's proposed architecture.

### H05 — RTK permission rewrite defect and fix

[#260](https://github.com/rtk-ai/rtk/issues/260): created 2026-02-23, closed completed 2026-03-25, reporter RTK 0.22.2. [Fix PR #576](https://github.com/rtk-ai/rtk/pull/576) is merged, explicitly closes #260 and handles deny/ask rules before rewriting. Merge commit: `a051a6f5e56c7ee59375a365580bced634e29c02`. Historical incident is verified; continued failure after that fix was not established.

### E01 — SWE-Milestone

[Paper v4](https://arxiv.org/html/2603.13428v4), [submission history](https://arxiv.org/abs/2603.13428): submitted 2026-03-13, v4 revised 2026-07-21. The study evaluates 12 models and four frameworks over 98 milestones/seven itineraries; it distinguishes composite Score from strict Resolve Rate. It supports continuous-development regression concerns. It does **not** establish that Newcombe gates cure them. A full frontier-model evaluation is estimated in the paper at approximately $500; no such run was commissioned.

### E02 — Newcombe interval paper

[Robert G. Newcombe, *Interval estimation for the difference between independent proportions: comparison of eleven methods*](https://www.researchgate.net/publication/13687790_Interval_estimation_for_the_difference_between_independent_proportions_Comparison_of_eleven_methods), Statistics in Medicine, 1998-04-30; author-uploaded full text. Distinguishes score-based combinations from exact methods and evaluates coverage. Supports rejecting “exact Newcombe” and “absolute certainty.” It does not validate treating correlated software test cases as independent Bernoulli trials.

### E03 — SWE-Bench Pro V2

[Scale Labs official page](https://labs.scale.com/leaderboard/swe_bench_pro_public_v2), update 2026-09-22, checked 2026-10-06. A locked, refreshed protocol is relevant to reproducibility. It does not establish Actseal's effectiveness or Frontier-Gate's containment claim. The detailed contamination anecdote was not independently reproduced.

## Decision-model sources and feasibility probe

### L01 — Laya package/runtime

[Laya repository](https://github.com/NandhaKishorM/laya), [LICENSE](https://github.com/NandhaKishorM/laya/blob/main/LICENSE), [PyPI metadata](https://pypi.org/pypi/laya/json), checked 2026-10-06. Latest observed version **0.3.28**, uploaded **2026-10-05T18:05:12Z**; 0.3.24 exists but is no longer latest. Repository license is Apache-2.0. Native implementation uses Torch/Transformers with CPU/MPS/CUDA/XPU paths, not the speculative MLX port in A. Package release existence does not verify every advertised backend on every platform.

### L02 — exact reference checkpoint and material calibration caveat

[Pinned model card](https://huggingface.co/convaiinnovations/laya-typed-decisions/blob/e929ae5cf69bc34259cd2f95c9e91145b818b1f0/README.md), revision `e929ae5cf69bc34259cd2f95c9e91145b818b1f0`, model last modified 2026-10-03; public and ungated, Apache-2.0, **421,293,830 F16 parameters**, documented context **1024**. Weights size **842,609,220 bytes**; SHA-256 `4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e`.

The model card states calibration temperatures were fitted on training data; the notebook was corrected but these published weights/temperatures were not refitted. It is a four-synthetic-workflow specialist, not a validated general security guardrail. The pinned `rl_agent_config.json` retains a `choice:11+` temperature below the runtime clamp floor. Actseal must treat scores as uncalibrated model signals and validate its own frozen action policy on independent labelled data; no calibrated-probability quality claim is adopted.

### L03 — independently executed local feasibility probe

Executed by the decision-model audit agent on 2026-10-06: M5 Pro, 24 GiB, macOS 26.6.2, Python 3.12.13. Explicit load: `laya.load("convaiinnovations/laya-typed-decisions", revision="e929ae5cf69bc34259cd2f95c9e91145b818b1f0", device="cpu", backend="eager", compile=False, fast=False)` with `torch.set_num_threads(4)`.

| Probe | Load | One prediction | Peak RSS | Result |
|---|---:|---:|---:|---|
| Online load, dependencies/weights available through normal download path | 24.104 s | 0.276 s | 1,867,464,704 bytes | Exit 0; billing answer |
| Fresh subprocess, `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`, cached weights | 1.235 s | 0.137 s | 2,915,975,168 bytes | Exit 0; identical billing answer |

Resolved environment included laya 0.3.28, torch 2.14.1, transformers 5.18.0, huggingface_hub 1.33.0, safetensors 0.8.0, numpy 2.5.3. This is **one-case native CPU feasibility**, not a model-quality study, performance benchmark, MPS result, cross-platform test, final project lockfile or reproducible public campaign. No paid call or secret was used. Linux remains an implementation acceptance check. Installed safetensors wheel LICENSE was checked as Apache-2.0; the final dependency/notice audit remains part of release verification.

### L04 — demand reports and upstream responses

| Primary source | Date/status checked 2026-10-06 | B's citation | Verified interpretation |
|---|---|---|---|
| [#124](https://github.com/NandhaKishorM/laya/issues/124) | Created Sep 22; open | `turn12search1` | Chinese routing concerns; 20 manually labelled cases, not a general error-rate estimate. |
| [#35](https://github.com/NandhaKishorM/laya/issues/35) | Created Sep 20; closed Sep 23 | `turn12search5` | Romanian routing concerns; 20 manually labelled cases, same statistical limit. |
| [#186](https://github.com/NandhaKishorM/laya/issues/186) | Created Sep 22; closed Sep 23 | `turn12search3` | Calibration overlap notebook repair; [comment](https://github.com/NandhaKishorM/laya/issues/186#issuecomment-5784909034) says published temperatures remain unchanged. |
| [#367](https://github.com/NandhaKishorM/laya/issues/367) | Created Sep 24; closed Sep 25 | `turn12search6` | Docs-first staged adoption request; guide #415 shipped. [Comment](https://github.com/NandhaKishorM/laya/issues/367#issuecomment-5826925474) identifies existing [stuntd](https://github.com/bladedevoff/stuntd) collect/shadow/live workflows. Unserved-demand claim is too strong; stuntd itself was not fully audited. |
| [#361](https://github.com/NandhaKishorM/laya/issues/361) | Created Sep 24; closed Oct 1 | `turn12search9` | Abstention implemented using answer_confidence=max(p), not entropy confidence. |
| [#637](https://github.com/NandhaKishorM/laya/issues/637) | Created Sep 27; closed Oct 1 | `turn12search7` | Clamp mismatch notebook fix shipped in 0.3.23; checkpoint caveat remains. |

All dates in this table are 2026. These reports establish concrete practitioner concerns and upstream work; they do not establish market size or absence of alternatives.

### J01 — Jev API, price, identity and confidence

[OpenAPI](https://api.typesafe.ai/openapi.json), [API docs](https://docs.typesafe.ai/api), [models](https://docs.typesafe.ai/models), [confidence](https://docs.typesafe.ai/confidence), checked 2026-10-06. OpenAPI version 0.2.0 exposes POST `/v1/systemone` and GET `/v1/models`; documented Bearer authentication, request state/model/questions, response model/answers/usage, and 401/422/429/529 statuses. Current documented model is `jev-1.13.0`; mutable aliases must not substitute for stable observed identity. Documented price is $0.042 per million input tokens, output free. Jev Choice confidence uses `(max(p)-1/n)/(1-1/n)` and is **not interchangeable** with Laya max(p). No authenticated availability test was run.

### J02 — Jev access and service terms

[Launch announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev), 2026-09-15: early-access/waitlist wording. Universal current access remains **UNVERIFIED**. [Master Customer Agreement](https://typesafe.ai/legal/mca), dated 2026-09-23, permits customer integration subject to restrictions including standalone resale and using the service/output to develop similar or competing products. This audit confirms published wording, not a legal clearance for every proposed use. Optional Jev is deferred from the focused v1; future adapter uses `JEV_API_KEY` and must retain a fully open local path.

## Competitive sources

### C01 — Ollaya

[Live repository](https://github.com/ollaya-dev/ollaya), [README](https://github.com/ollaya-dev/ollaya/blob/main/README.md), [Apache-2.0 LICENSE](https://github.com/ollaya-dev/ollaya/blob/main/LICENSE), checked 2026-10-06. README file blob `308c669fb903e266b723ff2b9820dbe61167806a` describes local serving, Laya, CPU inference and TypeSafe compatibility. Establishes feature overlap, not independently tested performance or adoption. Exact current release was not frozen because Actseal does not depend on Ollaya.

### C02 — AI PR Proof Gate

[Live repository](https://github.com/zinchukandrii/ai-pr-proof-gate), [Marketplace](https://github.com/marketplace/actions/ai-pr-proof-gate), checked 2026-10-06. Listing showed v0.1.1; README blob `d1fe8a0ab28c376093543ffe2fbc48d212421b44` describes deterministic scope, required evidence, risky-file and human-approval checks through CLI/web/Action. Supports narrative overlap, not a claim of equivalent trust model or adoption.

### C03 — sys1bench availability qualification

[Research-cited repository](https://github.com/rssr25/sys1bench): a search index exposed the repository README describing calibration, selective prediction, robustness and offline derivability. Both live GitHub connector and web fetch returned **404** on 2026-10-06. Historical indexed existence is supported; current repository availability/installability is **UNVERIFIED**. No inference of deletion, privacy state or absent alternatives is made.

## Reuse sources and boundaries

### R01 — public repository identities and licenses

All four repositories were independently confirmed **public** using GitHub metadata, remote main and immutable-file reads on 2026-10-06. Their local HEADs matched the listed remote refs and remained clean after read-only checks.

| Repository / version | Frozen audited commit | License and public evidence |
|---|---|---|
| agent-reliability-ci 0.7.0 | `d13dd94124cb71d378a4e76224fc115b750e8133` | [Apache-2.0 LICENSE](https://github.com/ajaysurya1221/agent-reliability-ci/blob/d13dd94124cb71d378a4e76224fc115b750e8133/LICENSE), [README](https://github.com/ajaysurya1221/agent-reliability-ci/blob/d13dd94124cb71d378a4e76224fc115b750e8133/README.md) |
| evalopt-graph 0.1.0 | `9bbc192443dc713f0f3344939a441c4a66e8a44d` | [MIT LICENSE](https://github.com/ajaysurya1221/evalopt-graph/blob/9bbc192443dc713f0f3344939a441c4a66e8a44d/LICENSE), [README](https://github.com/ajaysurya1221/evalopt-graph/blob/9bbc192443dc713f0f3344939a441c4a66e8a44d/README.md) |
| frontier-scout 2.1.0 | `a28f27da0ae25492af3c3a9f61cb863543dab791` | [MIT LICENSE](https://github.com/ajaysurya1221/frontier-scout/blob/a28f27da0ae25492af3c3a9f61cb863543dab791/LICENSE), [README warning](https://github.com/ajaysurya1221/frontier-scout/blob/a28f27da0ae25492af3c3a9f61cb863543dab791/README.md#L58) |
| dorian 1.4.0 | `fb5323068e95e78d387eaa81718945a6725b961d` | [Apache-2.0 LICENSE](https://github.com/ajaysurya1221/dorian/blob/fb5323068e95e78d387eaa81718945a6725b961d/LICENSE), [README](https://github.com/ajaysurya1221/dorian/blob/fb5323068e95e78d387eaa81718945a6725b961d/README.md) |

### R02 — independently checked statistical reuse

At the ARCI commit above, the reuse audit located the minimal standard-library [Clopper–Pearson implementation](https://github.com/ajaysurya1221/agent-reliability-ci/blob/d13dd94124cb71d378a4e76224fc115b750e8133/src/arci/stats.py), exact integer-tail comparisons and finite 60-step bisection. Audited numerical envelope: n=1…10,000 and tail probability [2.5e-7, 0.5). The independent [Fraction/Decimal oracle](https://github.com/ajaysurya1221/agent-reliability-ci/blob/d13dd94124cb71d378a4e76224fc115b750e8133/tests/unit/stats/test_cp_reproducibility.py) and [known-answer gate tests](https://github.com/ajaysurya1221/agent-reliability-ci/blob/d13dd94124cb71d378a4e76224fc115b750e8133/tests/acceptance/test_stats_gate.py) were inspected. Executed from the ARCI checkout: `.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/unit/stats tests/acceptance/test_stats_gate.py`, exit 0. Separate collection counted **115 cases** (37 CP reproducibility, 14 basic CP, 22 Wilson, 42 gate). This validates the audited source/tests, not an as-yet unimplemented Actseal port.

The current ARCI `FROZEN.sha256` contains **48** entries, all matching during the audit; an older workspace note says 47. No frozen file was edited and no gate was run against committed stores. Preserve that boundary.

### R03 — evidence/replay reuse limits

The reuse audit inspected evalopt [canonical JSON](https://github.com/ajaysurya1221/evalopt-graph/blob/9bbc192443dc713f0f3344939a441c4a66e8a44d/src/evalopt_graph/attestation.py) and [deterministic acceptance/replay separation](https://github.com/ajaysurya1221/evalopt-graph/blob/9bbc192443dc713f0f3344939a441c4a66e8a44d/src/evalopt_graph/kernel.py), ARCI seal/recording mismatch semantics, and Dorian claim-warrant boundaries. Port only necessary public primitives with attribution/notices. ARCI replay imports the full runner, so copying its entire module is not a minimal dependency. Dorian executable checkers execute code; they are not an automatic safe verifier for arbitrary input. frontier-scout's pinned README warns its repaired verifier is unreleased and recommends advisory use; released 2.1.0 is not a mandatory acceptance authority for Actseal.

### R04 — private material exclusion

`shared-brain-protocol` is **private**, had no license located, and is **not copied** into Actseal or its public planning docs. Public memory/coordination files are authored for this sprint from current requirements. No private repository paths, contents or unpublished implementation are required to reproduce Actseal.

## Research-only evidence and negative knowledge

### U01 — unverified, non-load-bearing claims

These categories were not independently rechecked because they do not affect the selected v1: exact Apple bandwidth/allocatable-memory claims; large Qwen/Clef/Julia/vision-model footprints and comparative quality; MLX-vs-llama.cpp percentage speedups; Ollama backend/version claims; speech/reranker leaders; broader GitHub/Godot/Homebrew/PostHog policy chronology; Stack Overflow/JetBrains percentages; exact feature parity/adoption for every named competitor; TypeSafe historical outage details; detailed SWE-Pro contamination reproduction; ARCI's old Jev spending campaign.

The matrix retains each original citation identifier and researcher-reported date. **UNVERIFIED does not mean false.** These claims cannot justify a dependency, performance promise, security guarantee, market-size claim or publication assertion. If scope later requires one, reopen verification before relying on it.

### U02 — predictions and design judgments

Researcher scores, reuse percentages, implementation-time estimates, “10×” positioning, adoption targets and projected costs are **ESTIMATES**, not externally verified facts. No maintenance-cost-zero, no-security-failures, production-readiness or adoption guarantee is adopted. Plain design requirements are labelled as requirements rather than evidence of completed implementation.
