PLEASE IMPLEMENT THIS PLAN:
## A. AUDIT

**Read the three decisions in H first. This plan recommends a stability-focused v1.0.0, with Jev conditional on the deadline.**

**Audit state:** read-only; no files changed, Claude sessions started, credentials read or paid requests made. The checkout remains clean at `332e1633f46975331f25f9af461f1220b6f36e8b`.

The audit covered both research files in full, all requested documentation and ADRs, all 21 task/publication reports, open issues, all 1,515 lines of the `v0.1.0..main` diff, product interfaces and release workflows. GitHub and PyPI were also inspected as rendered pages.

### What shipped, and what remains

| Research or roadmap expectation | Verified state | v1.0 disposition |
|---|---|---|
| Researcher A: Frontier-Gate and enforcement-oriented tooling | That recommendation was explicitly rejected during reconciliation. Its containment premise exceeded what a wrapper could establish. | Remains rejected. No sandbox, security proxy or universal action-enforcement claim. |
| Researcher B: frozen decision policy, risk/coverage assessment, provider failures and replay | Shipped: categorical contracts, fixed thresholds, complete case accounting, four verdicts, six canonical faults, evidence bundles and offline replay. | Stabilize these capabilities. |
| Local/open-source execution | Fixture provider and optional pinned Laya CPU adapter shipped; core has no third-party runtime dependencies. | Preserve. |
| Application integration | Importable evaluator exists. The packaged support example is authored synthetic data, not a production dataset or deployed application. | Add one small application example showing the actual execution boundary. |
| Jev, provider comparison and broader evaluation | Jev, baseline comparisons, per-slice gates and automatic calibration were deferred. | Attempt optional Jev transport and a bounded recorded audit; keep broader statistics out. |
| v2/v3 roadmap | Paired comparisons, per-action/slice contracts, model-change comparisons, reusable Action, shadow ingestion, cascades, sequential designs and signed evidence remain unimplemented. | Continue deferral. A major version does not require consuming the roadmap. |
| Publication and reproducibility | GitHub/PyPI publication succeeded; distributions matched; clean-install and replay receipts exist. | Replace the release-specific promotion workflow with a repeatable, tested pipeline. |

**No unresolved v0.1.0 release blocker remains in the accepted reports.** Earlier PARTIAL reports, Linux-native uncertainty and the failed PyPI publisher attempt were subsequently resolved. Preserve those reports as history.

The remaining deviations are scope choices and limitations: synthetic example data, no Jev, narrow native-platform evidence, no migration promise, and no cross-release replay compatibility.

### Baseline independently run during this audit

| Check | Result |
|---|---|
| `uv run --frozen ruff check .` | PASS |
| `uv run --frozen ruff format --check .` | PASS; 137 files |
| `uv run --frozen mypy --strict src tests` | PASS; 44 files |
| Core/unit/acceptance suite, excluding integration and packaging | **2,282 passed**, 20 deselected; 48.42 seconds |
| Packaging suite | **14 passed**, 2,288 deselected; 4.28 seconds |
| `uv run --frozen pre-commit run --all-files` | PASS |
| Native/integration baseline | **Not run:** the active environment lacks the optional Laya stack. Six marked tests remain for Task 01. |
| Hosted CI at current main | Four Linux/macOS × Python 3.12/3.13 jobs succeeded. [Run](https://github.com/ajaysurya1221/actseal/actions/runs/37486480402) |

The slowest current test took 5.83 seconds and exercises the 10,000-case numerical boundary. No unresolved flake was observed. Keep these meaningful numerical and resource-limit tests.

### Concrete debt and defects

| Finding | Consequence | Planned treatment |
|---|---|---|
| Replay fingerprints every installed Python source file, including `__version__` | A version bump alone makes a new installation reject old locks/bundles. | Separate replay-engine compatibility from producer provenance. |
| CLI JSON has no receipt schema version | Machine consumers have no explicit compatibility discriminator. | Add receipt schema version 1 before promising stability. |
| Subparsers still accept abbreviated flags | Accidental CLI behavior could become an unintended promise. | Disable abbreviation consistently; document the major-version change. |
| Extremely large numeric input can make `clopper_pearson_tail` raise `OverflowError` instead of a documented domain error | Small public API inconsistency; no demonstrated false PASS. | Normalize that invalid-input failure before freezing the API. |
| A native test closes a shared module-scoped model | Test ordering can affect later users of that fixture. | Give the close/idempotence test its own model. |
| A worker test includes a two-second wall-clock assertion | Loaded CI may expose scheduling sensitivity. | Preserve substantive termination/deadline assertions; change timing tolerance only with evidence. |
| Packaging tests build separate wheels | Passing those tests does not prove the promoted wheel was tested. | Add acceptance against an explicitly supplied release artifact. |

### Proposed public-surface classification

**STABLE means compatible throughout 1.x.** It does not freeze model answers, filesystem paths supplied by callers, elapsed times or incidental English wording.

All existing documented core functions and non-private convenience exports will be explicitly enumerated in the stability manifest. This avoids quietly declaring inconvenient existing exports private.

| Surface | Proposed promise |
|---|---|
| `actseal` and `python -m actseal`; `lock`, `verify`, `replay`, `demo`; documented flags | STABLE |
| PASS/BLOCK/INCONCLUSIVE/ERROR and exit codes 0/1/2/3 | STABLE |
| Versioned CLI JSON field names, types and meanings | STABLE |
| Core record constructors, aliases, errors and canonical encodings | STABLE |
| Policy precedence, denominator rules, CP allocation, verdict precedence and six canonical faults | STABLE |
| `DecisionModel`, fixture adapter and Laya adapter’s constructor/method contract | STABLE; native support is limited to documented tested configurations |
| Contract schema 1; new lock/bundle schema 2; receipt schema 1 | STABLE |
| Supported 1.x replay engines and approved cross-release compatibility | STABLE |
| Jev transport | **PROVISIONAL**, under `actseal.experimental.providers.jev` and an explicit experimental CLI flag |
| Future experimental interfaces | PROVISIONAL only under `actseal.experimental` or an explicit experimental flag |

Human-readable output remains meaningful and accessible, but scripts must use versioned JSON. Demo inputs and timings are examples, not application interfaces or performance guarantees.

**Complete CLI inventory to freeze**

| Command | Required inputs | Optional inputs |
|---|---|---|
| `lock` | `--contract`, `--calibration`, `--verification`, `--provider`, `--out` | `--responses`, `--offline`, `--json` |
| `verify` | `--lock`, `--calibration`, `--verification`, `--provider`, `--out` | `--responses`, `--offline`, `--json` |
| `replay` | Bundle directory | `--expected-lock-sha256`, `--json` |
| `demo` | `--out` | `--json` |
| Global/help | `--version`; `-h`/`--help` at root and command level | No abbreviated flags |

Existing stable provider choices are `fixture` and `laya`. Jev requires `--provider jev --experimental-provider`; it is never selected implicitly.

Successful lock creation exits 0. Demo exits 0 only when its bad case BLOCKs, fixed case PASSes and both replays agree. Invalid usage remains ERROR/3.

**Python inventory to freeze**

| Module/group | Public names |
|---|---|
| Records, also root reexports | `Option`, `ChoiceQuestion`, `Case`, `CaseRef`, `ModelIdentity`, `DecisionRequest`, `CapturedOutcome`, `ChoiceAnswer`, `ProviderFailure`, `LockedPolicy`, `GateLimits`, `Contract`, `FaultSpec`, `PlanLock`, `PolicyDecision`, `DecisionRecord`, `FaultResult`, `Interval`, `Verdict`, `EvidenceBundle` |
| Aliases/errors | `Action`, `Status`, `EvidenceScope`, `Outcome`; `ActsealError`, `SchemaError`, `IntegrityError`, `ProviderSetupError` |
| Serialization, also root reexports | `canonical_json`, `sha256_bytes`, `strict_json_loads`, `to_data`, `from_data`, `implementation_fingerprint` |
| Contract/locking | `read_input_text`, `parse_contract`, `parse_cases`; `case_digest`, `lock_digest`, `create_lock`, `validate_lock`, `validate_inputs`, `parse_lock` |
| Decision/statistical path | `evaluate`; `normalize`, `request_sha256`, `laya_mass_tolerance`; `fault_capture`, `run_fault_campaign`; `clopper_pearson_tail`; `assess` |
| Evidence/replay | `write_bundle`, `read_bundle_files`, `decode_document`, `decode_rows`, `replay` |
| Runner/CLI | `ModelFactory`, `open_model`, `write_lock`, `collect`, `lock_run`, `verify_run`, `demo_run`, `DemoRun`, `DemoResult`; `main` |
| Providers | `DecisionModel`; `FixtureModel`, `validate_timeout`; `LayaModel` |

Constructor fields and signatures are frozen from the audited source and [current contract](/Users/ajay/Developer/not-yet-named/plan/CONTRACTS.md), with only the explicit deltas in E.

The stability manifest must also enumerate these exported constant groups: schema/option/case limits and failure/provider sets; serialization/row/lock/bundle limits; policy, assessment and replay reason constants; normalizer profiles; fault inventory; bundle filenames; runner/demo constants; CLI exit mappings; fixture/Laya identity and runtime constants. Their **documented meanings** are stable; identity/version values identify the actual implementation or model and may change only with a separately identified release.

### Legacy compatibility

Changing the version or adding an adapter already breaks replay under the current exact-source rule. Schema 2 also deliberately changes new lock/manifest formats.

The approved default is:

- **v0.1.0 locks and bundles remain unchanged.**
- Historical replay uses isolated, pinned `actseal==0.1.0`.
- v1 rejects schema-1 locks/bundles with an explicit migration explanation.
- There is no conversion that rewrites a seal and presents the result as the original evidence.
- Starting a v1 evaluation creates a new lock and a separately identified run.

Within 1.x, supported prior evidence must replay through an explicitly approved compatible engine.

### Publication audit

The current [workflow](/Users/ajay/Developer/not-yet-named/.github/workflows/publish-pypi.yml) safely promotes reviewed **0.1.0** bytes, but hardcodes that version, commit, CI run and distribution hashes.

| Gap | Required v1 behavior |
|---|---|
| Manual main-only workflow with 0.1.0 constants | Tag-triggered, version-checked release pipeline |
| No comprehensive tag/package metadata agreement check | Compare tag, source version, lock self-version, wheel METADATA and sdist PKG-INFO |
| No tested-artifact promotion boundary | Build once; test and promote those exact distribution bytes |
| No post-publication job | Fresh PyPI installation, demo and replay checks |
| No GitHub `SHA256SUMS` asset | Mirror distributions, checksums and release receipt |
| `pypi` environment allows only `main`, with no required reviewer | Permit release tags; require Ajay’s approval with solo-maintainer self-review allowed |

The existing action SHAs, uv and build-tool pins were rechecked; retain them. The workflow filename and `pypi` environment name remain unchanged, preserving trusted-publisher identity. GitHub distinguishes tag and branch deployment policies. [Environment documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)

### README and PyPI first screen

The current GitHub README explains the core accurately and shows a runnable PyPI command, but has no requested banner, diagrams, badges or recording. Its evidence limits appear well below the first screen.

The rendered PyPI page still contains the released description: GitHub-wheel installation, broken relative documentation links and the Alpha classifier. Updating main’s README did not alter that already-published metadata.

The literal requested opening sequence cannot all fit one ordinary viewport at readable sizes. This is Decision 1.

A genuine public-PyPI **v1.0.0** recording also cannot be committed eight hours before the publication that makes v1.0.0 available. This is Decision 2.

## B. v1.0 DEFINITION

After v1.0.0, developers can depend on a documented 1.x contract for Actseal’s CLI, typed Python interfaces, formats and verdict semantics; know exactly how historical evidence is replayed; and install a CI-tested, attested distribution whose release claims have receipts. They can integrate the same policy evaluator into an application and understand the evidence boundary immediately. This promises compatible software behavior and reproducible verification—not authenticated model responses, proof that inference occurred, correct labels, universal calibration or enforcement of surrounding application actions.

## C. SCOPE

### Must ship, in priority order

| Group | IN |
|---|---|
| Stability and compatibility | Exhaustive stability contract, versioned schemas/receipts, explicit legacy policy, compatible 1.x replay, deprecation and security-support policies |
| Release integrity | Hardened trusted publishing, exact-artifact smoke tests, post-PyPI verification, checksums, attestations inspection, Production/Stable classifier |
| Usability and evidence | PyPI quickstart, concepts, CLI/Python references, migration guide, verdict FAQ, one application example with recorded evidence |
| Visual communication | All P1 assets, social preview, regeneration checks and blind ten-second review, subject to the explicit recording exception in H |
| Verification | Existing full checks, provider conformance, native receipts for changed paths, adversarial compatibility/replay tests, release claim-to-receipt mapping |

### Should ship, in priority order

| Candidate | Decision and justification |
|---|---|
| **(a) Jev** | Attempt an optional **experimental** adapter, real recorded audit and local fault injection. Both researchers support this boundary; making a proprietary service necessary for v1 would contradict the project’s core. |
| **(d) Property/mutation tests** | Add bounded deterministic property tests and eight targeted mutations around the existing gate. This strengthens the stability promise without introducing a new statistical method. |
| P2 visuals | Produce after P1 acceptance; cut at the deadline if incomplete. |

### Candidate decisions

| Candidate | Disposition |
|---|---|
| **(b) Shared provider conformance** | **Must ship.** A stable provider protocol needs one shared behavioral test suite for fixture, mocked Laya and mocked Jev, with live checks separate. |
| **(c) Schema versioning/migration tooling** | **Versioning and compatibility must ship; automatic migration is OUT.** Rewriting historical seals adds risk and cannot preserve the original evidence claim. |
| **(e) Release hardening** | **Must ship in full.** Each listed gap is directly relevant to reliable publication. |
| **(f) Documentation** | **Must ship in full**, kept compact and backed by executable examples. |
| **(g) Realistic example** | **Must ship:** a local ticket-routing application that executes a queue operation only after ACT. Its fixture evidence remains explicitly synthetic. |
| **(h) Windows** | **Unsupported in v1.0.** The current exclusive bundle publication depends on macOS/Linux facilities. No Windows classifier or partial support claim. |

**OUT:** multiple questions, Score/Noul contracts, per-label thresholds, automatic threshold fitting, paired baseline gates, per-slice multiplicity, sequential testing, training/distillation, autonomous fallback, MCP/OS enforcement, hosted service, dashboard, telemetry and a Marketplace Action.

### Jev audit boundary

The verified API supports a pinned `jev-1.13.0` target and returns a versioned answering-model identifier. Vendor confidence differs from selected-option probability; Actseal must continue gating on the latter. [API](https://docs.typesafe.ai/api) · [Models](https://docs.typesafe.ai/models) · [Confidence](https://docs.typesafe.ai/confidence)

The official SDK is MIT, but the service remains proprietary. The current terms permit customer API integrations; an independently distributed BYOK adapter fits that model, as an interpretation of the terms—not a blanket OSS exemption. Fault injection will target our transport doubles, never the service. No credential sharing, service resale, distillation or model training from outputs. [SDK license](https://github.com/typesafe-ai/typesafe-sdk-python/blob/f078f1e208a0d885154dc758344ae4fce77ac168/LICENSE) · [Terms, updated 23 September](https://typesafe.ai/legal/mca)

**The available ARCI planner cannot size this gate:** it models two independent binomial arms, not accepted-action error with a random accepted denominator plus coverage. It will not be misused.

Recommended bounded substitute, requiring Decision 3:

- A preregistered **finite-benchmark descriptive audit**, without a power or population-calibration claim.
- Banking77 at commit `57ec275d8078af65b7731c2a98be812d844a6d6b`; **320 calibration and 639 deduplicated verification cases**, fixed before inference.
- Fixed example policy: threshold `0.80`, maximum risk `0.05`, minimum coverage `0.50`, alpha `0.05`; `evidence_scope="demo"`.
- One request per scheduled case; no retry, replacement, threshold adjustment or selection using model outputs.
- Report both cohorts separately, every failure, selected-probability reliability bins, Brier score and descriptive ECE. Empty bins use `null`, never NaN.

The selection uses the first 16 original label strings in Python’s case-sensitive sort. Calibration takes the first 20 unique training texts per label after excluding every normalized test text. Verification keeps first occurrences in original test order. Normalization is exactly `text.strip().casefold()`.

The source audit found train/test overlaps and one duplicate in the selected test cohort; this procedure removes them before inference. Model-training exposure and semantic near-duplicates remain unknown. Banking77 is CC-BY-4.0 and receives separate attribution; Actseal code remains Apache-2.0. [Pinned dataset and license](https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b)

## D. VISUALS LANE

The visuals lane starts at approval. Static P1 assets and the recording procedure must be accepted by **7 October, 15:59 IST**. The final PyPI recording follows the exception in Decision 2.

### Asset specification

| Priority / asset | Frozen content and correspondence |
|---|---|
| **P1 Hero** | Actseal wordmark; “Test model-chosen actions. Replay the evidence.”; one simple freeze/run/replay motif. Approximately 1600×400 SVG, outlined text, light/dark variants. |
| **P1 How it works** | Five groups: **Freeze → Run → Verify → Seal → Replay**. Include the specified inputs, four decisions, four verdicts/exit codes, bounded bundle and “offline; no model call.” |
| **P1 Architecture** | Seven groups maximum: CLI/typed API; contracts/locks; providers; normalization/policy; assessment/statistics/faults; evidence; replay. Trace every group to actual modules. Replay arrows never enter live providers. |
| **P1 Demo** | Genuine PyPI v1.0.0 demo, fixed replay and bad replay; original `.cast`; 20–40 seconds; unedited output; GIF below 3,000,000 bytes. Expected exits 0, 0, 1 remain visible. |
| **Required social preview** | 1280×640 PNG using the banner composition. Deliver the file; uploading through GitHub Settings → General → Social preview remains your manual step. |
| **P2 Where it sits** | Application → Actseal policy gate → application action execution. The application owns execution; no containment implication. |
| **P2 Decision/verdict matrix** | Two clearly separated levels: four per-case decisions and four whole-run verdicts with exit codes. No invented one-to-one mapping. |
| **P2 Evidence boundary** | Consistency/recomputation versus authenticity, inference occurrence and label truth. Those three limitations remain plain text even if this figure is cut. |

### README ordering and copy

Preserve your exact opening order:

1. Banner → one-sentence description → four badges.
2. How-it-works figure → three-command quickstart.
3. Three guarantees → three limitations.
4. Architecture figure → documentation/stability/threat-model/release links.

The description is:

> Actseal verifies model-chosen application actions for developers: freeze a policy, check its recorded decisions, and replay the evidence offline.

The quickstart uses PyPI, a fresh output directory and the same command shapes tested in CI:

```bash
uvx --python 3.12 actseal demo --out ./actseal-demo
uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
```

The third command intentionally exits 1. Python/tool installation time is reported separately from demo execution.

**Guarantees**

- Complete scheduled-case and required fault evidence is checked.
- PASS requires the frozen risk/coverage bounds and fault rules to pass.
- Supported evidence is recomputed offline without calling a model.

**Limits**

- Hashes and replay cannot authenticate coherently rewritten responses.
- They cannot prove inference occurred or that labels are true.
- Population claims require the stated sampling assumptions; Actseal does not enforce application execution.

### Visual quality and tooling

Use flat colors, one typography system, no padlocks/shields, no decorative gradients and no unsupported metrics. Limit each diagram to seven semantic groups. Labels must remain at least 14 rendered pixels; generate a vertical mobile variant where scaling would violate that requirement.

Use descriptive alt text and SVG `<title>/<desc>`. No scripts, external fonts or stylesheets inside SVGs. Banner text is outlined; other diagram text uses generic font stacks.

Authoring-only pins, kept outside the runtime:

| Tool | Pin / license | Purpose |
|---|---|---|
| fontTools | 4.66.1 / MIT | Outline pinned banner glyphs |
| JetBrains Mono | 2.304 / SIL OFL-1.1 | Licensed source font and terminal rendering |
| asciinema | 3.2.1 / GPL-3.0-or-later | Real recording |
| agg | 1.9.0 / GPL-3.0-or-later | GIF rendering |
| resvg | 0.48.1 / Apache-2.0 OR MIT | Social PNG rendering |

These pins and licenses were checked against primary sources. Rendering determinism remains an execution acceptance check. [fontTools](https://github.com/fonttools/fonttools/blob/4.66.1/LICENSE) · [Font](https://github.com/JetBrains/JetBrainsMono/blob/v2.304/OFL.txt) · [asciinema](https://github.com/asciinema/asciinema/releases/tag/v3.2.1) · [agg](https://github.com/asciinema/agg/releases/tag/v1.9.0) · [resvg](https://github.com/linebender/resvg/releases/tag/v0.48.1)

Sources, font notices, tool hashes and the raw recording live under `docs/assets/src/`. A single renderer supports:

```text
render.py --write [--only ASSET]
render.py --check [--only ASSET]
```

`--check` regenerates into temporary storage and compares committed outputs. It also verifies referenced local assets, dimensions, prohibited SVG content and recording size/duration. GIF rendering uses speed 1 and an idle limit longer than the entire recording; it must not silently trim pauses.

**Ten-second acceptance:** a fresh reviewer receives only a rendered README-first-screen image, no repository context, at 1366×900 starting at the README top. They provide two sentences describing purpose, audience and assurance. Codex compares that answer with the frozen stability/threat contract. A mismatch requires visual iteration. Save the prompt, screenshot hash and unedited answer in `plan/v1/reports/`.

## E. ARCHITECTURE DELTAS AND LANES

### Frozen deltas

**1. Replay compatibility**

Keep `implementation_sha256` as producer provenance. Append the required field:

```python
PlanLock.replay_engine_version: str
# Initial supported engine:
"actseal-choice-v1"
```

Separate version constants:

```text
Contract TOML: 1
PlanLock: 2
Bundle manifest and contained record encoding: 2
CLI JSON receipt: 1
Release provenance receipt: 1
```

Do not change canonical encoding, policy/statistical semantics or the six-fault inventory.

A packaged, reviewed compatibility registry maps exact producer source hashes to engine IDs:

```json
{
  "schema_version": 1,
  "implementations": {
    "<full source SHA-256>": "actseal-choice-v1"
  }
}
```

The loader rejects unknown fields, duplicate keys and malformed hashes.

Validation rules:

- An exact current-source lock may be validated under its supported engine.
- Cross-release replay requires **both** producer and running release to be explicitly registered for that engine.
- New collection requires the exact current producer hash, including direct `collect()` calls.
- Registry changes require review and archived-evidence regression tests; no wildcard/range approval.
- The registry is trusted verifier configuration, not proof of evidence authenticity.

Apply this consistently in shared lock validation, assessment and replay—not just the top-level replay function.

**2. Stable provider boundary**

```python
class DecisionModel(Protocol):
    def identity(self) -> ModelIdentity: ...
    def decide(
        self, request: DecisionRequest, *, timeout_s: float
    ) -> CapturedOutcome: ...
    def close(self) -> None: ...
```

Existing public signatures remain unchanged. `identity()` describes the immutable execution identity/target. Local artifact hashes and a cloud vendor-reported version must not be described as equivalent evidence.

Optional Jev boundary:

```python
# PROVISIONAL
actseal.experimental.providers.jev.JevModel(
    *, offline: bool = False
)
```

It implements the existing protocol. Freeze the endpoint and `jev-1.13.0`; read only `JEV_API_KEY`; reject offline/missing-key setup without a request; use one attempt, no redirects, retries or fallback. Use stdlib HTTP/TLS, with bounded response reads and explicit timeout behavior. Do not promise a universal hard wall-clock bound on OS/network operations.

Preserve successful raw response bodies. Pure normalization checks the answering model, exact question/options, finite probabilities and selected probability. Provider confidence never authorizes an action. Replay imports no transport module.

**3. Machine receipts**

Add `schema_version: 1` to each CLI JSON response, including errors. Preserve existing fields and meanings. Publish schemas for lock, manifest, captured/decision/fault/verdict records and CLI receipt variants.

The release receipt binds version, tag, source commit, lock hash, workflow run, immutable artifact ID, distribution filenames/sizes/hashes and verification results. It contains no credentials.

**4. Versioning**

Stable 1.x schemas and semantics remain supported throughout 1.x. Additive commands may arrive in minor versions; removal or incompatible stable behavior waits for 2.0. Deprecations require documentation and at least one minor release plus 90 days before removal.

Security support covers the latest 1.x minor at its latest patch. Legacy 0.1.0 replay availability is not a promise of indefinitely maintaining a 0.1 security branch.

### Six lanes

| Lane | Owner | Exclusive ownership |
|---|---|---|
| Core stability | Claude A | Records/codecs, contract/locking/evidence/replay/runner/CLI compatibility; stability/schema/migration docs; their approved fixture updates |
| Providers and live evidence | Claude B | Provider implementations, normalization, provider/conformance/native tests, Jev audit scripts/data/receipts |
| Statistical verification | Claude C | Numeric boundary correction, new property/mutation tests and mutation harness |
| Documentation and example | Claude D | README, general/API/CLI docs, SECURITY, CHANGELOG, application example, release notes and launch draft |
| Visuals | Claude V | `docs/assets/`, asset sources/renderer/tests and recording |
| Integration/release verification | Codex | Plan/state/reviews, independent checks, CI/packaging glue, registry approval, integration decisions, commits and release gate |

All Claude sessions receive: **“You are not alone in this repository. Edit only owned paths; do not revert another lane’s work. Request a contract amendment for cross-lane changes.”**

Shared interfaces freeze after Task 02 acceptance. Codex owns `plan/v1/STATE.md`, accepted-commit tracking and cut decisions. Reports remain claims until independently reviewed.

Jev must be integrated and green by **14:00 IST on 7 October**, allowing the final architecture to depict the actual release by 15:59. Otherwise it moves to 1.1 before the broader cut.

## F. TASKS

All tasks use branches named `claude/v1-<id>-<slug>` unless Codex owns execution. Claude uses **Fable 5.1, effort high**. No automated Claude dispatch.

Every REPORT goes to `plan/v1/reports/<id>.md` and uses:

```text
REPORT <id>
Status: DONE / PARTIAL / BLOCKED
Changes: files and summary
Tests: exact commands, results and exit codes
Deviations: with reasons
Open issues
Spend: API/credits and subscription-meter estimates kept separate
```

Every Codex review records the exact reviewed commit:

```text
REVIEW <id>
Verdict: ACCEPT / REVISE / REJECT
Findings ordered by severity
Required changes
Follow-ups filed
```

The existing pre-commit command runs Ruff lint, format checking and strict mypy. New product tests remain network-free unless explicitly marked integration.

### Foundation and contracts

**TASK 00: Persist the approved plan — Codex; 0.25 hour; first task**

- **Goal:** Create the approval receipt before implementation.
- **Context:** This complete approved message and your answers to H.
- **Interface contract:** `PLAN.md` contains the approved message verbatim; `AUDIT.md` contains A verbatim; `DECISIONS.md` preserves H plus separately recorded answers; each task file preserves its TASK block.
- **Files:** Create `plan/v1/{AUDIT,PLAN,DECISIONS,STATE}.md` and `plan/v1/tasks/00.md` through `22.md`. No product, existing research or historical-report edits.
- **Acceptance:** One commit; approval text, starting commit and answers recorded; no unresolved placeholders introduced.
- **Tests:** Compare persisted text with the approved message; inspect the staged path list.
- **Constraints:** This exact persistence is the operating-model exception to Claude-authored documentation.
- **Done when:** `git diff --check` passes; staged diff contains only the specified receipt/state files; commit `docs(v1): record approved release plan` exists.
- **Report format:** REPORT 00 using the format above.

**TASK 01: Complete the full baseline — Codex checks; 0.5 hour; depends 00**

- **Goal:** Cover the six integration tests omitted during planning.
- **Context:** A baseline table; existing native workflow and pinned provider documentation.
- **Interface contract:** Test the starting source before product changes; distinguish setup/download from offline execution.
- **Files:** Only report/check logs in `plan/v1/reports/`; no product edits.
- **Acceptance:** All 2,302 currently collected tests accounted for; native prerequisites verified or an explicit blocker reported.
- **Tests:** Existing full suite, including cached native integration.
- **Constraints:** No Jev call; no secrets; do not convert missing prerequisites into skips.
- **Done when:**
  ```bash
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 01, including any prerequisite preparation and exact environment.

**TASK 02: Freeze core stability and replay compatibility — Claude A; 3 hours; depends 01**

- **Goal:** Implement E’s compatibility model and publish the normative stable surface.
- **Context:** A public inventory; E deltas; current CONTRACTS and ADRs.
- **Interface contract:** Preserve all audited public signatures except the explicit `PlanLock` field addition; schema versions and registry rules exactly as E.
- **Files:** Core records/codecs/contract/locking/assessment/evidence/replay/runner/CLI; new compatibility module/registry; `docs/stability.md`, `docs/versioning.md`, `docs/migration.md`, `docs/schemas/`; relevant core tests and compatibility fixtures. Do not edit provider/normalizer code, statistical algorithms or visual assets.
- **Acceptance:** Cross-release replay can accept only approved compatible implementations; collection stays exact-source; schema-1 evidence is rejected with a useful legacy path; JSON receipts are versioned; abbreviated flags rejected.
- **Tests:** Unknown engines/hashes/versions, registry tampering, old schema rejection, prior-compatible bundles, direct collection against foreign producers, all CLI JSON variants and public signature snapshots.
- **Constraints:** Historical reports and numerical oracles remain unchanged. Existing tests may receive only reviewed schema/identity fixture amendments.
- **Done when:**
  ```bash
  uv run --frozen pytest -m "not integration and not packaging"
  uv run --frozen pytest -m packaging
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 02; include the public manifest and each intentional 0.1→1.0 break.

### Providers, verification and application example

**TASK 03: Shared provider conformance — Claude B; 1.5 hours; depends 02’s frozen types**

- **Goal:** Make provider behavior independently testable.
- **Context:** E provider contract; existing provider/native tests.
- **Interface contract:** Identity immutability, request binding, typed failures, raw capture preservation, timeout validation, close/idempotence and no import-time transport.
- **Files:** `tests/conformance/`, provider test helpers and `tests/integration/test_laya.py`. Do not change core records, policy, statistics, CLI or docs.
- **Acceptance:** Fixture and mocked Laya pass the same cases; the native close test owns its model; an adapter-specific failure cannot bypass shared tests.
- **Tests:** Closed provider, malformed capture, incorrect request hash, identity mismatch, timeout, raw body preservation and import/no-network checks.
- **Constraints:** Default tests use doubles; native inference remains explicitly marked.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/conformance tests/unit/test_providers.py
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest -m integration tests/integration/test_laya.py
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 03.

**TASK 04: Numerical properties and targeted mutations — Claude C; 1.5 hours; depends 02**

- **Goal:** Test the promised gate semantics and correct the numeric overflow boundary.
- **Context:** Statistical contract, existing exact vectors and independent acceptance oracle.
- **Interface contract:** No change to valid-input bounds or verdicts; invalid out-of-domain numeric conversion raises the documented error.
- **Files:** `src/actseal/stats.py`, new `tests/properties/`, `tools/check_mutations.py`. Do not edit frozen numerical goldens, core schema code or provider code.
- **Acceptance:** Deterministic generated cases cover interval ordering, monotonicity, endpoints and supported domains. Eight prescribed semantic mutations are killed.
- **Tests:** Mutate tail allocation, scheduled denominator, zero-accepted handling, threshold boundary, risk-bound selection, coverage-bound selection, fault blocking and ERROR precedence.
- **Constraints:** Stdlib generators plus pytest; no new runtime dependency; mutations operate on temporary copies and never alter tracked source.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/unit/test_stats.py tests/properties
  uv run --frozen python tools/check_mutations.py
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 04; name each killed/surviving mutation. A survivor is not a pass.

**TASK 05: Experimental Jev adapter — Claude B; 3 hours; depends 02 and 03; should-ship**

- **Goal:** Add live capture, recorded replay compatibility and local transport-failure tests.
- **Context:** C Jev findings; E provider/identity contract; official API documentation.
- **Interface contract:** `JevModel(*, offline=False)` implements `DecisionModel`; fixed endpoint/model; one attempt; no retry, redirect or fallback; pure normalization validates the returned version.
- **Files:** `src/actseal/experimental/providers/jev.py`, its package files, provider normalization and tests, `.env.example`. CLI/runner registration is handed to Claude A for Task 19. Do not edit policy/statistics.
- **Acceptance:** No-key/offline imports and tests are green; all raw successful bodies replay without importing the transport; credentials/headers never enter diagnostics or evidence.
- **Tests:** Exact request shape, 401/422/429/529, timeout, malformed/oversized body, duplicate keys, wrong model, option mismatch and selected-probability gating.
- **Constraints:** Stdlib transport; no live service fault attacks; no model-quality claim from smoke tests.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/conformance tests/unit/test_jev.py tests/unit/test_normalization.py
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 05; list unverified live behavior separately.

**TASK 06: Preregister and run the Jev audit — Claude B; 2 hours plus at most 90 minutes of collection; depends 05 and Decision 3**

- **Goal:** Produce honest live receipts under one frozen protocol.
- **Context:** C’s exact dataset selection, policy and interpretation.
- **Interface contract:** 320 calibration requests and 639 verification requests; immutable inventories before inference; no retry/replacement/tuning; separate cohort reports.
- **Files:** `bench/jev_audit/`, its tests and report/bundle references. Do not change product code or thresholds after observing responses.
- **Acceptance:** Source hashes/license verified; splits disjoint under the specified normalization; protocol committed and reviewed before calls; every attempt and missing attempt accounted for; full replay matches any valid completed bundle.
- **Tests:** Selection counts, overlap removal, metric arithmetic, empty bins, partial collection, failure accounting and credential redaction.
- **Constraints:** Public benchmark data only. A fixed benchmark is not IID population evidence. Deadline interruption yields an incomplete/ERROR receipt, not a reduced successful sample.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/bench/test_jev_audit.py
  uv run --frozen python bench/jev_audit/run.py --check-preregistration
  uv run --frozen python bench/jev_audit/run.py --execute
  uv run --frozen python bench/jev_audit/run.py --check-receipts
  uv run --frozen pre-commit run --all-files
  ```
  `--execute` requires the already-exported `JEV_API_KEY`; it must not print it.
- **Report format:** REPORT 06; include actual verdicts, request counts, token usage and measured credit change if available. Unknown spend remains explicitly unknown.

**TASK 07: Application action-gate example — Claude D; 1 hour; depends 02 and 03**

- **Goal:** Show where Actseal fits in real application control flow.
- **Context:** Existing support-triage example and threat model.
- **Interface contract:** The application calls the existing evaluator; only ACT invokes a local queue operation. ABSTAIN/ESCALATE/DENY take explicit non-execution paths.
- **Files:** `examples/action_gate/`, its README and `tests/examples/`. Do not alter product APIs or the packaged demo.
- **Acceptance:** Runnable without a key/model/network; includes one reproducible recorded bundle; clearly labels authored inputs and application-owned execution.
- **Tests:** All four decisions; threshold boundary; no execution on failure; recorded replay.
- **Constraints:** No external ticket service, framework or claims of deployed enforcement.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/examples
  uv run --frozen python examples/action_gate/run.py --check
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 07.

### Documentation and release machinery

**TASK 08: Documentation and README integration — Claude D; 2 hours; depends 02, 07 and accepted static P1 assets**

- **Goal:** Make the stable product understandable and its claims traceable.
- **Context:** A–D; accepted task reports; stability/schema documents owned by Claude A.
- **Interface contract:** README order/copy from D; absolute links; accurate support/migration/evidence statements.
- **Files:** README, CHANGELOG, SECURITY, CONTRIBUTING, AGENTS, general/provider/CLI/Python/FAQ/quickstart docs and draft release notes. Do not edit normative schemas, product code or generated images.
- **Acceptance:** Three quickstart commands match installed behavior; all documented public interfaces are covered; old operating-model instructions are superseded without rewriting history; Windows is explicitly unsupported.
- **Tests:** Executable documentation examples, link/asset validation and metadata rendering checks.
- **Constraints:** No unsupported calibration, safety, authenticity, speed or adoption claim. Production/Stable describes the compatibility promise.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/docs
  uv run --frozen python tools/check_release.py docs
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 08.

**TASK 09: Harden CI and publication — Codex CI/packaging glue; 2.5 hours; starts after 00, finalizes after 19**

- **Goal:** Promote exactly the artifacts that passed release acceptance.
- **Context:** A publication audit; current action pins and trusted-publisher registration.
- **Interface contract:** Keep `publish-pypi.yml` and environment `pypi`; tag/version agreement; immutable artifact promotion; OIDC only in the upload job.
- **Files:** Workflows, packaging metadata/lock glue, `tools/check_release.py`, release smoke helpers and their CI tests. No policy/provider/statistical implementation.
- **Acceptance:** Tag-triggered validation, four-platform source checks, exact-wheel smoke, strict metadata check, checksums, approval gate, post-PyPI container verification and identical GitHub assets.
- **Tests:** Wrong tag/version, wrong source SHA, missing/extra distribution, altered hash, stale artifact, wrong exit code and partial-publication recovery.
- **Constraints:** Build once per release; no checkout/build in the upload job; no API-token fallback; no automatic overwrite/re-upload.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/release
  uv run --frozen python tools/check_release.py workflow
  uv run --frozen pre-commit run --all-files
  ```
  Plus a successful non-publishing hosted workflow rehearsal.
- **Report format:** REPORT 09; independent review of Codex-authored glue is required.

### Visual tasks

**TASK 10: Reproducible asset toolchain — Claude V; 1 hour; depends 00**

- **Goal:** Establish one reusable, deterministic authoring path.
- **Context:** D’s pins, quality rules and asset inventory.
- **Interface contract:** `render.py --write/--check [--only ASSET]`; asset names `hero`, `how-it-works`, `architecture`, `demo`, `social`, `where`, `matrix`, `boundary`.
- **Files:** `docs/assets/src/`, font/license/tool manifests and `tests/visual/`. Dependency/workflow changes are handed to Task 09.
- **Acceptance:** Deterministic SVG serialization, bounded rendering, forbidden-content checks, font attribution, temporary regeneration and reference validation.
- **Tests:** Missing reference, external resource, script, wrong dimensions, missing license and nondeterministic output.
- **Constraints:** No runtime dependency; verify downloaded authoring-tool hashes before execution.
- **Done when:**
  ```bash
  uv run --frozen pytest tests/visual
  uv run --frozen --group assets python docs/assets/src/render.py --check
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 10.

**TASK 11: Hero banner — Claude V; 0.75 hour; depends 10**

- **Goal:** Communicate the project in one glance.
- **Context:** D hero copy; stable loop represented by `locking`, `runner`, `replay`.
- **Interface contract:** Approximately 1600×400 desktop SVG; outlined text; light/dark and readable mobile variants; no security symbolism.
- **Files:** Hero source and generated hero assets only.
- **Acceptance:** Exact approved wording, one motif, accessible description, no external resources.
- **Tests:** Structural/size/theme checks and rendered readability.
- **Constraints:** No invented claims or metrics.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only hero` passes, with light/dark rendered review.
- **Report format:** REPORT 11.

**TASK 12: How-it-works figure — Claude V; 0.75 hour; depends 10 and 02**

- **Goal:** Show the five-stage workflow.
- **Context:** `lock`, `verify`, `replay`; `policy`, `assessment`, `evidence`.
- **Interface contract:** Five groups exactly as D; include all four decisions/verdicts and exits without suggesting action authentication.
- **Files:** How-it-works source and generated assets only.
- **Acceptance:** Correct arrows, readable labels, provider-free replay and bounded evidence.
- **Tests:** Terminology/content checks; desktop/mobile rendering.
- **Constraints:** At most seven semantic groups.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only how-it-works` passes.
- **Report format:** REPORT 12.

**TASK 13: Architecture figure — Claude V; 1 hour; depends 02 and final provider inclusion decision**

- **Goal:** Depict the components that actually ship.
- **Context:** E’s seven groups; actual `cli`, `records`, `contract`, `locking`, adapters, `normalization`, `policy`, `assessment`, `stats`, `faults`, `evidence`, `replay`.
- **Interface contract:** Seven groups maximum; live-model boundary only around live provider execution; fixture and replay remain visibly distinct.
- **Files:** Architecture source and generated assets only.
- **Acceptance:** Module-to-node mapping included in REPORT; no absent Jev adapter depicted as shipped; replay never calls providers.
- **Tests:** Mapping/terminology checks and rendered arrow review.
- **Constraints:** Finalize after contracts/provider inclusion freeze; due by 15:59 IST.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only architecture` passes.
- **Report format:** REPORT 13.

**TASK 14: Real PyPI demo recording — Claude V; 0.75 hour preparation + 0.75 hour after publication; depends 10, 20 and Decision 2**

- **Goal:** Deliver a real, attributable terminal demonstration.
- **Context:** Published v1.0.0 and D’s three command outcomes.
- **Interface contract:** Untouched asciicast; real demo/fixed replay/bad replay; 20–40 seconds; speed 1; GIF under 3 MB.
- **Files:** Raw recording, recording receipt and generated demo GIF variants only.
- **Acceptance:** Resolved package version/hash recorded; real output and exits preserved; rendering reproduces from the original capture.
- **Tests:** Duration/size, cast hash, command outcomes, no credentials and rendering reproducibility.
- **Constraints:** Do not substitute a local wheel, prerelease or 0.1.0 recording and label it public v1.0.0. Prepare tools/procedure by T−8h.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only demo` passes and Codex reviews the raw capture.
- **Report format:** REPORT 14.

**TASK 15: Social preview — Claude V; 0.5 hour; depends 11**

- **Goal:** Deliver GitHub’s upload-ready image.
- **Context:** Approved hero composition and stability wording.
- **Interface contract:** Exactly 1280×640 PNG; original source composition; no additional claim.
- **Files:** Social source and generated PNG only.
- **Acceptance:** Correct dimensions, readable text, licensed source font and deterministic regeneration.
- **Tests:** PNG dimensions and byte comparison from repeated generation.
- **Constraints:** User uploads manually; do not claim upload completed.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only social` passes.
- **Report format:** REPORT 15; include the delivered file path.

**TASK 16: Where-it-sits figure — Claude V; 0.5 hour; P2; depends 07 and 10**

- **Goal:** Explain the application execution boundary.
- **Context:** `examples/action_gate`, `normalize`, `evaluate`.
- **Interface contract:** Application → gate → application execution; model recommendation and code execution are distinct.
- **Files:** Where-it-sits sources/assets only.
- **Acceptance:** No containment or automatic enforcement implication.
- **Tests:** Content/reference and rendered-boundary review.
- **Constraints:** Cut if incomplete at T−6h.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only where` passes.
- **Report format:** REPORT 16.

**TASK 17: Decision/verdict matrix — Claude V; 0.5 hour; P2; depends 02 and 10**

- **Goal:** Prevent confusion between a case decision and a run verdict.
- **Context:** `policy.evaluate`, `assessment.assess`, `cli.EXIT_CODES`.
- **Interface contract:** Two compact panels containing the four decisions and four verdicts; exits only on verdicts.
- **Files:** Matrix sources/assets only.
- **Acceptance:** No implied ACT→PASS or DENY→BLOCK mapping.
- **Tests:** Exact enum/exit mapping and readability.
- **Constraints:** Cut if incomplete at T−6h.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only matrix` passes.
- **Report format:** REPORT 17.

**TASK 18: Evidence-boundary figure — Claude V; 0.5 hour; P2; depends 02 and 10**

- **Goal:** Make the limits difficult to misread.
- **Context:** Threat model; `replay`, `evidence`, `implementation_fingerprint`.
- **Interface contract:** Distinguish consistency/recomputation from response authenticity, inference occurrence and label truth.
- **Files:** Boundary sources/assets only.
- **Acceptance:** Matches the approved threat model; no padlocks/shields or tamper-proof implication.
- **Tests:** Claim-by-claim mapping and rendered review.
- **Constraints:** Plain-text limitations remain even if this figure is cut.
- **Done when:** `uv run --frozen --group assets python docs/assets/src/render.py --check --only boundary` passes.
- **Report format:** REPORT 18.

### Integration, gate and publication

**TASK 19: Integrate the release candidate — Claude A; 1 hour; depends accepted 02–08 and static P1 assets**

- **Goal:** Integrate accepted lanes without changing their contracts.
- **Context:** Accepted commits/reviews and recorded cut decisions.
- **Interface contract:** E remains frozen; Jev registration is explicit/experimental; exact source hash is approved only after the final product source is fixed.
- **Files:** Approved integration points in runner/CLI/records, compatibility fixtures and registry; no new feature work. Codex performs version/classifier/lock packaging edits.
- **Acceptance:** No orphan experimental feature after cuts; public inventory matches shipped code; archived-compatible replay and exact-source collection both work.
- **Tests:** Complete core/packaging suite, native checks and conditional Jev offline tests.
- **Constraints:** No conflict resolution that changes policy, statistical goldens or evidence limits without a new review.
- **Done when:**
  ```bash
  uv run --frozen pytest -m "not integration"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --frozen --extra laya pytest -m integration
  uv run --frozen pre-commit run --all-files
  ```
- **Report format:** REPORT 19; identify every integrated commit and intentional cut.

**TASK 20: Independent release gate and publication — Codex; 2 hours plus approval wait; depends 09 and 19**

- **Goal:** Publish only the independently accepted candidate.
- **Context:** All REPORTs/REVIEWs, G’s definition of done and H’s approved exceptions.
- **Interface contract:** Exact reviewed commit/tag/artifacts; no product edits during release; final recording is the only approved post-publication media dependency.
- **Files:** Reviews, release receipts and approved CI/packaging glue only.
- **Acceptance:** Full hosted matrix green; changed native paths covered; blind ten-second test passed; exact distributions tested; package metadata correct.
- **Tests:** Independent lint/types/tests, malformed/foreign evidence, offline replay, no provider imports, clean supplied-wheel smoke and post-PyPI container smoke.
- **Constraints:** Nothing merges without ACCEPT and green CI. A failed mandatory gate stops publication; no moving tags or replacing distribution bytes.
- **Done when:**
  ```bash
  uv run --frozen ruff check .
  uv run --frozen ruff format --check .
  uv run --frozen mypy --strict src tests
  uv run --frozen pytest -m "not integration"
  uv run --frozen pre-commit run --all-files
  uv run --frozen python tools/check_release.py candidate
  ```
  Plus successful exact-commit hosted checks, trusted publication and post-publication verification.
- **Report format:** REPORT/REVIEW 20; notify you immediately when `pypi` awaits approval.

**TASK 21: Final documentation receipts — Claude D; 0.5 hour; depends 14 and 20**

- **Goal:** Publish the factual release record and draft launch material.
- **Context:** Actual release artifacts, CI jobs, test receipts, live audit and cuts.
- **Interface contract:** Each release-note claim maps to a receipt; “not run,” BLOCK, INCONCLUSIVE and ERROR remain visible.
- **Files:** `plan/v1/FINAL_REPORT.md`, `plan/v1/LAUNCH.md`, release-note text and README demo integration. No product or artifact changes.
- **Acceptance:** Shipped/planned comparison, research deviations, 1.1 cuts, spend, known issues and next three steps included.
- **Tests:** Receipt-link/hash checks and claim-to-evidence review.
- **Constraints:** Launch post remains a draft. Public release notes include the how-it-works figure.
- **Done when:** `uv run --frozen python tools/check_release.py receipts` and documentation/asset checks pass.
- **Report format:** REPORT 21.

**TASK 22: Close the publication checklist — Codex; 0.25 hour; depends 21**

- **Goal:** Verify the final public state and deliver the social-preview file.
- **Context:** G’s complete definition of done.
- **Interface contract:** GitHub and PyPI distributions remain byte-identical; published metadata and referenced visuals resolve.
- **Files:** Final REVIEW/state receipt only.
- **Acceptance:** GitHub release includes both distributions, `SHA256SUMS`, release receipt and final notes; PyPI shows the correct classifier and attestations; final demo is accepted.
- **Tests:** Live read-only public-page/artifact verification.
- **Constraints:** Do not describe the social preview as uploaded.
- **Done when:** Every definition-of-done item has a concrete receipt or an explicitly approved exception.
- **Report format:** REVIEW 22 with final ACCEPT or remaining blockers.

## G. SCHEDULE, DEFINITION OF DONE, RISKS

### Schedule

**Hard deadline: 7 October 2026, 23:59 IST.** Estimates total approximately 30 agent-hours across parallel lanes, plus 7–9 hours of Codex integration/review activity. The critical path is approximately 12–15 elapsed working hours, including handoffs.

| Block | Work and gate |
|---|---|
| Approval +0–2 hours | Persist receipt, finish baseline, freeze contracts, start visual toolchain and release-workflow changes |
| +2–5 hours | Core compatibility; provider conformance; statistical checks; hero/how-it-works drafts |
| +5–8 hours | Review core; application/docs; Jev implementation if still viable; pipeline rehearsal |
| +8–11 hours | Integration, optional preregistered Jev collection, static P1 acceptance and installed-artifact tests |
| By **14:00, 7 Oct** | Jev inclusion decision. If not integrated and green, cut it to 1.1 and finalize architecture accordingly. |
| By **15:59** | Static P1 figures, social preview and recording procedure accepted |
| **15:59–17:59** | Full matrix, independent review, README ten-second test and release-candidate hardening |
| **17:59: T−6h** | Cut every remaining optional unintegrated/non-green task; record each cut |
| **18:00–21:00** | Final candidate, exact-artifact tests, tag and trusted-publishing approval |
| **21:00–23:00** | Post-PyPI container verification, genuine recording, final media review and GitHub release notes |
| **23:00–23:59** | Final public-state checks and receipt closure; recovery buffer only |

The time-specific gates override relative estimates if approval arrives late. A threatened mandatory gate is escalated immediately. The date does not justify weakening the stability, evidence or verification requirements.

### Release sequence

1. Freeze the accepted commit, version `1.0.0`, Production/Stable classifier, lockfile and approved implementation registry.
2. Push the tag; validate tag/version/source identity; run required checks; build the wheel/sdist once and test those supplied bytes.
3. Preserve distributions and checksums in an immutable Actions artifact. The `pypi` job waits for your approval, then uploads with trusted publishing and attestations.
4. Download from PyPI, compare hashes, install outside the checkout in a clean Linux container, run demo/replays and inspect attestation identities/digests.
5. Capture/review the real recording, mirror identical artifacts/checksums on GitHub, publish receipt-backed notes and close the final report.

The clean-container image is pinned to the verified Linux/amd64 Python 3.12.13 image:

```text
python@sha256:d657ab0ade19f404a6ccc883ab399540de667aff751748ce23c07330c5a89e64
```

Attestation presence/identity inspection will be reported accurately; it will not be called independent cryptographic verification unless that verification is actually performed.

### Definition of done

| Gate | Required evidence |
|---|---|
| Stable contract | Complete surface inventory, schemas, compatibility/deprecation/security policies and 0.1 migration notes |
| Verified software | ACCEPT reviews, full hosted matrix, required native receipts, deterministic replay, supplied-wheel and post-PyPI smoke |
| Correct publication | Trusted publishing, attestations, Production/Stable metadata, absolute PyPI links, matching GitHub/PyPI artifacts and checksums |
| Legible release | Static P1 assets, accepted real recording under Decision 2, ten-second test, social PNG delivered, accessible light/dark visuals |
| Defensible record | CHANGELOG, receipt-backed release notes with how-it-works figure, final report, recorded cuts/spend and draft launch post |

### Risks and mitigations

| Risk | Mitigation / consequence |
|---|---|
| Jev access, rate limits or latency | One attempt per case; local fault doubles; fixed collection deadline; preserve failed/incomplete receipts; cut optional adapter/audit if not ready |
| Compatibility or migration mistakes | No historical resealing; explicit engine registry; archived-bundle tests; exact-source collection preserved |
| PyPI approval latency | Configure the tag policy/reviewer early; rehearse before release; notify you when the job actually waits |
| Sandbox/network/tool restrictions | Ask for the required approval when blocked; do not switch mechanisms to evade a denial |
| Clock and manual handoffs | Small branches, parallel ownership, early Jev cut, mandatory P1/stability protected from scope cuts |

ADRs during execution will record the stability/support policy, replay compatibility, experimental Jev boundary, benchmark interpretation, release promotion, platform scope and visual-toolchain choices.

## H. DECISIONS

| Decision | Recommended default | Alternative |
|---|---|---|
| **1. README first screen** | **A:** Preserve your exact order as a scrollable lead section. Apply the no-scroll ten-second test at the README top in a 1366×900 viewport; architecture/reference links may fall below the fold. The first screen must still communicate purpose and evidence limits. | **B:** Require the entire sequence in one viewport; revise the requested content/order before implementation. Readable text will not be shrunk to force it. |
| **2. Genuine PyPI recording** | **A:** Approve one explicit exception: prepare the recording by T−8h, but capture and merge the final video immediately after v1.0.0 reaches PyPI. Gate final release communication on its acceptance. The immutable tag will not contain that later media commit. | **B:** Require all final media before the tag; change the recording requirement to an honestly labelled prepublication candidate recording. |
| **3. Jev audit and power planning** | **A:** Attempt the preregistered 959-request finite-benchmark audit described above, with descriptive results and **no power claim**; defer a correctly powered selective-risk/coverage study to 1.1. | **B:** Require your intended compatible power planner first. Supply its location; if it cannot be verified and integrated by the Jev cut, defer Jev’s live audit to 1.1. |

**Next action: reply with `1A, 2A, 3A` to select the recommended defaults, or name the choices you want changed. No implementation has begun.**
