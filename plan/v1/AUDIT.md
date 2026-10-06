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

