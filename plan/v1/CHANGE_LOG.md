# Actseal v1 execution amendments

The approved PLAN.md and original task blocks remain immutable. These entries record bounded implementation clarifications and observed defects.

## V1-001 — Full baseline import-isolation repair (6 October 2026)

Evidence: REPORT/REVIEW 01. The exact approved all-tests invocation produced 2300 passes and two module-absence failures after genuine native tests imported Laya/NumPy. Isolated reproduction passes.

Decision: Add Task 01R, a prerequisite to Task 02, owned by manual Claude A. Ownership is temporarily limited to the two named test files and its REPORT; no statistical algorithm, oracle, schema or runtime change is authorized. Preserve the original full-suite Done-when command. This is a necessary repair inside the approved verification scope, not permission to weaken a test.

## V1-002 — Task 10 dependency prerequisite

Task 10's approved `--group assets` commands require an assets dependency group absent from the baseline. Codex Task 09 will add only `fonttools==4.66.1` to a non-runtime `assets` group and regenerate uv.lock using uv 0.12.5, with independent review and hosted CI before integration. Claude V does not own pyproject.toml or uv.lock.

## V1-003 — Approved Task 02 frozen-contract amendment

The approved v1 plan section E explicitly authorizes PlanLock.replay_engine_version, separate format-version constants, schema-2 locks/manifests, versioned CLI receipts and the reviewed compatibility registry. These changes supersede conflicting v0.1 freeze language only for Task 02's owned implementation and schema/identity fixtures. Preserve numeric goldens, policy/statistical semantics, canonical encoding rules and historical evidence. Task 02 remains held until Task 01R is ACCEPT.

## V1-004 — Preserve the verbatim approval receipt during formatting

Hosted CI runs 37494066475 and 37494420609 rejected only the line wrapping of a Python fence in plan/v1/PLAN.md. Task 00 requires that file to preserve the approved message verbatim. Add an exact-file formatter exclusion, not a lint or product-code exclusion. Continue running the unchanged repository-wide Ruff commands; verify the approval receipt SHA-256 remains bb3538db868f929c1f779dcbcd105936f521acba51fbfe7c08988fedcd0fdcaa. The pre-commit format hook checks only Python files, so its earlier success did not cover this Markdown fence.

## V1-005 — Autonomous Claude CLI orchestration authorized

The latest human goal explicitly says: "Call Claude Code via CLI and handle the Orchestration" and authorizes autonomous continuation while AFK. This replaces the earlier manual-session restriction only. Claude Code Fable 5.1/high still writes all product code, product docs, tests and visual assets; Codex reviews and gates. Existing ownership, normal permission controls, no-secret rules, immutable approval text and publication approvals remain in force. No alternate provider or API billing is authorized by this amendment.

## V1-006 — Task 09 implementation delegation and supplied-wheel acceptance

Codex retains release ownership and independent review, delegating Task09 CI/packaging implementation to Claude CLI for parallel throughput. Its exclusive scope includes an ACTSEAL_TEST_WHEEL absolute-path override in tests/packaging/test_wheel.py and tests/acceptance/test_acceptance_wheel_receipts.py. The override must fail on invalid inputs and must never rebuild the supplied wheel; default source-CI behavior and existing assertions remain unchanged. This closes the audit's tested-artifact promotion gap, not a relaxation of acceptance. Codex handles hosted rehearsal, environment changes, merging and publication.

## V1-007 — Recover interrupted executor sessions without model substitution

Observed02 and09 print processes exited while background workers were incomplete; CLI results explicitly record killed background workers and no final REPORT. Logs also record Sonnet/Opus worker usage outside the requested Fable5.1 executor. These drafts are not accepted. Codex saved tracked binary diffs and untracked bytes with hashes under the task-local orchestration directory before recovery. Fable is instructed to restore only its task-owned interrupted drafts to baseline and reimplement directly; the parent-authored09 workflow may remain. No draft is relabelled as original Fable work. A correction in each REPORT must preserve the deviation. Subsequent CLI launches expose only Bash/Read/Write/Edit/Glob/Grep built-ins, so Agent/Task delegation is unavailable. Normal permissions, user settings and hooks remain enabled; personal memory writes are forbidden by the task packet. No other lane's edits are reverted.

Task10 was directly authored by the required model. Its first REPORT incorrectly says manual user-run and estimates1h10m; the observed CLI duration was1529830ms. REVIEW10 requires a separate correction receipt plus eight bounded fixes (seven validator defects and receipt provenance). Assets/fonts remain unfetched pending the explicit exception to the configured curl deny rule.

## V1-008 — Validate published JSON Schemas with a maintained dev-only validator

The Task02 review reproduced a real demo receipt rejected by its advertised schema while the structural key-set tests passed. Add jsonschema==4.26.0 (MIT) and types-jsonschema==4.26.0.20261006 (Apache-2.0) only to the locked development group. This replaces the need to invent a partial JSON Schema validator and exercises Draft2020-12 references/allOf against actual output. ClaudeA temporarily owns this exact pyproject.toml/uv.lock addition in Task02 repair; Task09 must not edit those files concurrently. Core runtime dependencies remain empty. Primary PyPI metadata verified6Oct2026 also reports MIT for attrs26.1.0,jsonschema-specifications2025.9.1,referencing0.37.0,rpds-py2026.9.1; typing-extensions is already locked. Recheck actual resolved versions/licenses and record them. Register all local schemas in referencing.Registry and reject unknown retrievals so unit tests cannot fetch network schemas. No optional format extras are authorized.

## V1-009 — Workflow figure wiring after accepted toolchain

Task10 is accepted and merged at6ad1e91 after exact-head eight-job CI. Task12 now owns its workflow renderer/source, generated light/dark/mobile SVGs, relevant visual tests and the minimal shared asset-inventory registration/dimension update. No concurrent visual author may change that inventory. This is necessary integration glue for the already-approved figure, not new product scope. Use generic font stacks and no font/binary downloads while the exception is pending. Readability remains subject to actual rendered Codex review; a bootstrap renderer pass does not establish visual completeness. Task02 interfaces are independently accepted at84079e9 and frozen for dependent work while its hosted CI runs; no dependent task merges before that gate passes.

## V1-010 — Strict stable formats and opt-in additions

Final normative review found Task02 docs permit additive JSON fields despite strict unknown-field rejection. Clarify that existing strict schema versions/default receipt shapes stay unchanged through1.x; additive formats or engines require separately versioned explicit opt-in interfaces preserving existing stable behavior. This tightens documentation to the approved stability promise; no runtime/schema change. ClaudeA owns the two normative docs and ADR0015 for this correction; all dependent source contracts stay frozen.

## V1-011 — Atomic experimental-provider wiring

Before Task05 dispatch, assign ClaudeB these narrow shared-file deltas together: admit `jev` in `records.PROVIDERS`; implement its pure normalization profile; emit Jev-native envelopes for the existing six canonical faults; and add an explicit fail-loud `runner.open_model` guard for an admitted but unregistered provider before any Laya import/construction. The existing non-fixture branch otherwise silently routes a newly admitted provider to Laya. Actual experimental CLI/runner registration remains Task19.

ClaudeB also temporarily owns only the matching ModelIdentity provider enum in `docs/schemas/{lock,captured-outcome,decision-record,fault-result,cli-receipt}.schema.json`, profile wording in `docs/schemas/README.md`, additive tests, and the three existing invalid-provider sentinel replacements in record/normalization/runner unit tests. `jev` can no longer stand for an unsupported provider in those tests. Keep the separate `open_model("jev")` rejection until Task19 and prove no Laya import/construction. No other lane edits those shared files concurrently.

Fields, schema versions, public signatures, six fault IDs/order/dispositions, fixture/Laya behavior and policy/statistical semantics remain frozen. Cloud identity has an empty artifact-hash tuple and a fixed configured vendor target; returned version is a vendor claim, not a weight attestation. Identity cannot mutate after a response. This is integration required by the approved experimental adapter, not a wider policy model. No live calls are authorized in Task05.

## V1-012 — Freeze the release receipt before promising version1

Task09's remaining schema work includes exact build, postpublication and final release receipt shapes. Independent probes at e6c967a4 found duplicate decisive keys and nonfinite numbers accepted by the helper. Repair decoding/encoding and recursive field/type validation before the schema is published. Retain all existing artifact, source, workflow, official-index and attestation-identity checks. A JSON Schema cannot detect duplicate keys already discarded during decoding.

Claude's Task09 ownership expands to the three release-related JSON schemas, their schema-index entries, release-format/promotion documentation and a release-promotion ADR. Use the already-approved development-only jsonschema validator for real generated-receipt fixtures with a local nonfetching registry. The helper's clean-container commands remain stdlib-only and do not import product code. Inspection-only/local-fixture outputs stay explicitly unpromotable; do not weaken the official release profile. This completes the approved version1 receipt promise; it is not a new runtime dependency or new release feature.

## V1-013 — Complete benchmark accounting before live calls

Read-only integration review found that the ordinary collector buffers verification records and does not capture the calibration cohort. Task06's supplemental specification binds scripts plus both inventories before inference, separates calibration sidecars from the ordinary verification bundle, and durably journals attempt starts/terminal captures. An incomplete run keeps started-without-capture and unattempted cases visible and cannot become a reduced evidence bundle. It freezes descriptive metric denominators/formulas and a90-minute sequential collection budget. A budget overrun makes the overall audit receipt ERROR while any complete valid verification bundle retains its independently computed verdict. No core API/statistical/schema change, threshold fitting, power claim or live request is introduced.

The supplement in tasks/06-collection-supplement.md received independent planning ACCEPT; this does not approve a future implementation, concrete preregistration or execution. Claude remains its implementer. Codex must review the committed concrete preregistration before calls. Original Task06/PLAN remain verbatim.

## V1-014 — Codex-owned release-helper strictness during quota pause

The approved Task09 explicitly assigns CI/packaging glue and its CI tests to Codex; V1-006 delegated implementation for parallel throughput without removing that authority. During Claude's subscription pause, Codex repaired only tools/check_release.py and new CI-helper regressions in tests/release/test_strict_receipts.py. No product code/tests/docs/visuals were authored by Codex. Independent review ACCEPTed commit0060f27d5b71e7445636c1784c71c074e0a5e284, with442 parent release tests and319 independent focused tests passing. The three public receipt schemas/docs and their schema validation remain Claude's task. Full Task09 acceptance still requires these, actual accepted assets, and an authorized hosted rehearsal.

## V1-015 — Prepare fixture-only Task07 while native receipt is pending

Task03 at45a633c61f7df834b45a293b4ffcbfd5b24304c3 has independent scoped implementation ACCEPT,177 provider/conformance tests and owned lint/typing passing; its required native test remains permission-blocked. Product interfaces/source are unchanged. A separate reviewer confirmed Task07 uses only the accepted fixture, normalization, evaluator and replay boundaries. Start Task07 in an isolated branch from accepted main to use the sprint time while the native receipt is pending. This changes scheduling only: do not merge or fully accept Task07 before its stated dependencies and independent/hosted gates pass. No native inference, skipped gate, changed API, permission override or new assurance claim is authorized. Other Task03-dependent work retains its original dependency gate.

## V1-016 — Extend schema inventory without weakening product validation

Task09 at006072fef31aa238265b51402297d2b16ffc9722 placed the three release schemas in a sibling directory because the accepted product-schema inventory test requires exactly eight files. Restore the approved docs/schemas location. Claude09 temporarily owns only the explicit release-file tuple and exact combined inventory assertion in tests/unit/test_schemas.py; preserve the eight product schema names, every existing product validation and their fixtures. Update only matching release-schema paths/index/tests/documentation. This is an additive inventory amendment, not permission to change core schema semantics or numerical oracles. Independent review must verify both the original eight and the three release schemas remain covered. No other lane edits this inventory concurrently.

## V1-017 — Prepare hero sources while approved font is unavailable

Task11 may prepare its isolated hero generator, focused deterministic tests and minimal hero-only inventory registration after accepted Task10. Task12's inventory edits are complete and frozen during this work. No pinned authoring download or actual local preview is authorized by this scheduling choice. Unit outline doubles cannot establish appearance/readability or count as delivered assets. Missing approved font bytes must fail loudly; no substituted font, generated stand-in, fake acceptance or weakening of the renderer gate is permitted. Keep Task11 PARTIAL until authentic pinned inputs, generated light/dark/mobile outputs and rendered review are available. Codex will integrate the two disjoint asset-inventory entries after review, preserving each asset's declarations.

## V1-018 — Prepare independent reference documentation before final media

Task08 may prepare concepts, CLI/Python reference, FAQ, quickstart, provider/support documentation and narrowly corresponding documentation checks from accepted Task02 interfaces. README composition, final application-example claims, release notes and full Task08 acceptance retain their original dependencies on accepted Task07 and static P1 assets. Claude08 owns only general documentation and docs tests, not the normative stability/versioning/migration/schema documents, release helper/workflows, visuals, product APIs or another lane's files. SECURITY.md changes are limited to the already-approved latest1.x security-support policy and source-backed corrections within the existing threat boundary; no new exclusion, severity waiver, accepted risk or assurance is authorized. Codex's security-policy review resolves root SECURITY.md for src/actseal and preserves reportability of parser, replay, statistical and lifecycle defects. This scheduling clarification waives no review, CI, visual or publication gate.

## V1-019 — Cover implemented hero prerequisites in shared CLI tests

Hero source preparation at09e96e532cb75319bacffddbf9850d0067b9cb9e makes three old bootstrap CLI expectations stale: the hero is now implemented but its required font is absent. Claude11 temporarily owns only tests/visual/test_render_cli.py alongside its original paths, to require explicit missing-font failure/no output, use a still-unimplemented asset for planned-asset behavior, and preserve fontTools-free import/help and font-independent checks. No skipped test, fake hero output, prerequisite suppression or actual preview is authorized. Task12's separate reviewed workflow tests remain frozen on their own branch; final visual integration must preserve both sets of meaningful assertions. Correct the report's35-minute estimate to the measured783233ms CLI duration (about13m03s), clearly labelled as tool-reported elapsed time. FullTask11 remains PARTIAL until authentic inputs and rendered acceptance.

## V1-020 — Fail the application example on unsupported active archives

Review of Task07 atb7a0b54e0b661440fdf1ae134655294a0c2fa75f found its custom compatibility-free validator incomplete. Simplify: every active recorded run must pass core replay under an exact or explicitly approved producer, return non-ERROR, and equal its archived verdict. Unknown/unsupported or damaged active archives fail the check and prevent any queue operation; preserve their bytes. Remove the copied lock validator and custom benign-unapproved path. Retain only example-specific agreement among sidecar/bundle locks, producer metadata, frozen contract, fixture identity, actual input hashes and fresh results. Task19 must approve original reviewed a5fe0902… and final producer compatibility explicitly before acceptance; no silent archival exclusion or resealing. This tightens an example helper, not a stable product API. Add corruption/unsupported-set regressions and preserve request-binding/partial-effect tests.

Task07R's directory creation was automatically denied; subsequent default-temp execution departed from the requested scoped procedure. Retain those observations as executor claims, not independent acceptance. An additional scoped human approval is pending. No further example/test execution or temporary-directory preparation is authorized by this amendment; source repair and existing owned lint/type checks may continue. The old report's anticipated independent rerun is still pending.

## V1-021 — Prepare optional Jev offline code behind unchanged acceptance gates

A read-only dependency review confirmed that Task05's mocked transport/conformance preparation is independent of Task03's pending native receipt. Allow an isolated child branch from212a1d6fae154dff0ea5b3b284174a53ac7f43e0 (scoped source ACCEPT and eight green hosted jobs), retaining all original gates for full acceptance, merge and live collection. This supersedes only the supplement's dispatch timing and V1-015's remaining preparation restriction. No key access, live call, model-quality claim, dependency addition, registry approval or shipped-Jev claim is authorized. Reassess if native validation changes the shared contract; retain the14:00 optional cut.

In addition to V1-011, Claude05 owns the exact PROVIDERS set assertion in tests/unit/test_stability.py and corresponding docs/stability.md constant row: admitted serialized providers include experimental Jev; stable CLI choices remain fixture/Laya. Preserve an exact set assertion and every other stability oracle. Extend only the shared provider-support/conformance adapter cases with mocked Jev, retaining all existing negative controls. Do not touch native tests/Task03 receipts. Preserve Task09's release-schema index additions during later integration; its shared-file writes have ended. Task08 prepares general provider docs against current fixture/Laya and must not claim this optional adapter ships before its inclusion gate.

## V1-022 — Retrospective disposition of four Task05 scope deviations

Claude05 committed three additional unsupported-provider fixture substitutions at7af39829e15e68883dd13275c3647714fed81577 outside V1-011's enumerated test ownership: tests/unit/test_locking.py, test_replay.py and test_serialization.py. Each changes only the now-admitted literal `jev` to `unsupported`; all assertions and expected failures stay unchanged. It also changed only the unsupported-provider diagnostic string in runner.verify_run atf7439f51143cea39c9cbb17e8b24fac8a7ec83a2, beyond the assigned open_model guard. This was a process deviation, not prior authorization; preserve it in REPORT05.

Separate read-only review of those exact commits found the fixture edits necessary to retain their original negative meaning and the diagnostic change nonsemantic. Codex accepts these four bounded deltas retrospectively. No other shared-file or test-semantic change is authorized. Core and native/final acceptance gates remain unchanged; schemas, transport, replay and conformance must still complete and receive independent review. No live call or secret access follows from this disposition.

## V1-023 — Prepare the mandatory recording procedure before publication

Task14 explicitly includes preparation before its post-publication capture. Claude14 may now author only docs/assets/src/recording.md, a small docs/assets/src/demo_session.py command runner, tests/visual/test_demo_session.py and plan/v1/reports/14-preparation.md in an isolated branch. The runner is exercised only through injected process/clock doubles. It must not be invoked against uvx, a provider, a real recorder or renderer during preparation. Preserve the exact three approved quickstart command shapes and actual exit-code checks; do not fabricate output, a cast, package provenance or a release receipt. Keep the demo asset unimplemented until the genuine capture exists. No generic toolchain, inventory, dependency, credential or permission changes are authorized. Official tool/font downloads and actual local preview remain separately blocked; no substitute downloader, font or renderer may evade those denials. Task20, Decision2 and the original final recording/regeneration gates remain mandatory.

## V1-024 — Prepare the benchmark offline from reviewed Jev source

Task05 repaired source5849c68, unchanged at report headc2e27d2, received independent scoped ACCEPT and parent3,001 core tests plus separate six outline tests, lint/types/hooks. Permit Task06 offline implementation and concrete preregistration preparation from that exact source before full Task05/native acceptance. This supersedes only the dispatch timing in Task06 and its supplement. It does not authorize live calls, key access, a registry entry, final inclusion or a merge. All original full-task, native, permission and live-phase gates remain.

The preregistration may truthfully bind a reviewed prerelease commit, its actual package version/fingerprint and all benchmark script hashes. Final publication/version is not a prerequisite for preparing or validating it. Any later bound-source/script/input change invalidates execution under that preregistration; preserved evidence can replay in the final release only after Task19 explicitly approves its original producer compatibility, without resealing. `--check-preregistration` checks internal and current-input/source consistency without keys; a passing result alone never authorizes collection. Codex's recorded preregistration review and a separate live-phase dispatch remain the orchestration gate; do not implement a speculative approval service.

Freeze calibration order as case-sensitive sorted selected labels, then original training-record order within each label; verification remains original test order. Freeze959 schedule entries before inference. Journal entries exist only when attempts start or captures arrive. Reuse the already hash-verified public dataset cache with separate CC-BY-4.0 attribution; no download is required. Claude owns only bench/jev_audit, tests/bench/test_jev_audit.py and its REPORT. No product interface or runtime dependency changes are authorized.

## V1-025 — Prepare the mandatory social composition without rendering

Read-only dependency review of Task15 and reviewed hero5f3fee5 confirms that source/test preparation can proceed independently of the missing authentic font and pending rendered acceptance. Claude15 may use a child branch from that exact hero head to author docs/assets/src/actseal_assets/social.py, tests/visual/test_social.py, only the social renderer registration in inventory.py, and its preparation REPORT. Keep hero helpers, generic toolchain, pins, lockfile, CI and other inventory entries unchanged. Serialize shared inventory integration later.

The existing renderer contract is `render(context: RenderContext) -> Mapping[str, bytes]`, returning exactly social.png,1280×640. Compose the approved wordmark, tagline, motif and evidence-boundary caption using existing hero helpers and the same palette. Reuse existing verified resvg command and bounded execution helpers; no new dependency or downloader. Unit tests use explicit outline/transport doubles only. No actual font/tool setup, resvg invocation, PNG generation, placeholder deliverable or visual acceptance is authorized by this amendment. Original Task11 acceptance, authentic licensed inputs, repeatable PNG byte comparison, Task15 done command and readable rendered review remain mandatory. This is required social work, not P2; no upload is claimed or performed.

## V1-026 — Record remaining approved decisions before integration

Task08's documentation lane may add only ADR0017 experimental-provider boundary, ADR0018 finite-benchmark interpretation, ADR0019 platform support and ADR0020 visual-toolchain decisions, plus its own REPORT08-ADR. These are the decisions already approved in PLAN sectionsC–G, not new product policy. Reserve those four identifiers globally; preserve existing0015 and Task09-owned0016. No product, schema, existing normative document, workflow, README, test or asset edit is authorized by this supplement. State implementation/validation status honestly: optional Jev inclusion and its audit are pending, native/visual gates remain blocked, and no v1 release has occurred. Reference current source/receipt evidence without making full-task acceptance or legal guarantees. This independent documentation work does not waive Task08's remaining example/P1/release-note dependencies.

## V1-027 — Cover the social renderer's missing prerequisites in shared CLI tests

Task15 source at efcea002a248f530ce8446690a452e3f2f56937b implements the social renderer without delivering its required font or resvg. Parent verification passed245 visual tests and exposed three stale bootstrap assertions: social is no longer unimplemented, and its missing prerequisites add explicit errors. Temporarily extend Claude15 ownership to tests/visual/test_render_cli.py only. Require both implemented assets to report their actual missing prerequisites, remain unchecked and write no files; keep genuinely planned assets informational. Preserve fontTools-free import/help and all existing meaningful negative assertions. Add explicit social-only prerequisite coverage if needed. Bind shared tests and their subprocesses to an empty task-local ACTSEAL_ASSET_TOOLS fixture so they never inspect the operator cache. No suppression, skip, fake output, product-code change, actual font/tool execution or download is authorized. Final visual integration must preserve the independently reviewed workflow lane's shared CLI assertions too.

## V1-028 — Prepare architecture sources before final provider inclusion

Independent read-only dependency review permits Task13 source/unit preparation on an isolated child of reviewed Task12 head f712daef51ee005c1b34c9744dbe1d99cf499c33. Own only docs/assets/src/actseal_assets/architecture.py, tests/visual/test_architecture.py and plan/v1/reports/13-preparation.md. Reuse the reviewed font-free palette, typography and SVG helpers without refactoring them. Preserve the renderer signature and prepare four light/dark desktop/mobile byte outputs; defer inventory registration and committed SVG outputs until final provider inclusion is decided.

The draft depicts only real fixture/Laya components in seven groups: CLI/typed API, contracts/locks, providers, normalization/policy, assessment/statistics/faults, evidence and replay. Trace every group to actual modules. Live inference is solely within Laya execution; fixture inputs and synthetic faults require no model call. Replay visibly recomputes through deterministic validation/assessment without any provider arrow. No Jev inclusion or final shipping claim is implied.

Unit tests may construct and inspect SVG bytes in memory for determinism, terminology, grouping, module correspondence, font-size floors, accessibility and prohibited content. No provider call, font/binary/setup/download, external cache, pixel renderer, browser or preview operation is authorized. A denied action/resource must stop without retry through another tool, script or location. Keep REPORT13 PARTIAL. Final provider reconciliation, rendered arrow/readability review, inventory/output integration, regeneration, README integration and the original done-when remain mandatory; this scheduling clarification waives no gate.

## V1-029 — Five scoped approvals and resumed execution

Observed 2026-10-07T03:28:18.080680+00:00. Human: “Approve all five scoped requests”. Authorizes pinned official font/tooldownloads; cached native/mutation checks and actualvisualpreviews; exampletests/tempfiles; placeholder-only.env.exampleaccess; read-onlypublicBanking77cache. Normalpermissions/hooks remain, actual.env/credentials excluded, no unreviewedliveinference/merge/publication. Priorfailures/denials remainhistorical. Cachednative03, fullmutation04 and example07 nowindependently pass; seecompletionreviews. Newrm-stylecleanupdenial preservedwithoutretry.

Officialresvg0.48.1 API and independentbytes verify naming-only macassetrepair: resvg-macos-arm64.zip→resvg-macos-aarch64.zip, unchanged06440eb5aa14a28cbfc7e40ae39e1ffa71adc051b89fbaa913b4f1d9b905d09f. Claudeowns manifest/testkeyrepair. Linuxfilename/hashunchanged. No dependencyversion/license change.

## V1-030 — Integrate accepted hero and workflow registrations before social completion

Read-only review confirmed that the original Task15 branch at 7bb32f4ca78194d5316e0615528420a521cdf78a already contains the exact accepted hero/font/receipt bytes also isolated at 736d912. Do not cherry-pick those duplicate hero commits. Claude15 may merge reviewed main containing Task12 at 227c7da88f3e9366fd1f8af9569fb591693701fd into its original branch, resolving only the two anticipated product/test conflicts: docs/assets/src/actseal_assets/inventory.py and tests/visual/test_render_cli.py. Claude owns these resolutions and a new integration REPORT. Stop and report any other semantic conflict for a bounded amendment.

Register hero, how-it-works and social together: four hero SVGs, four workflow SVGs and exactly social.png. Preserve accepted hero/font/receipt bytes from 7bb32f4 and workflow source/SVG bytes from f712dae. Keep architecture, demo and P2 entries planned until their separate acceptance. No renderer redesign, new dependency, altered visual claim or provider work is authorized.

Preserve the empty task-local tool cache and subprocess propagation. Missing hero/social prerequisites must remain explicit failures and cannot count as checked/written assets. Preserve workflow-only write/check success, including without fontTools. In the isolated empty-cache fixture, fresh global check expects one checked asset, five planned assets and nine errors; global write produces exactly four workflow files, one checked asset, five planned and five prerequisite errors; subsequent check matches the four workflow outputs and still reports five prerequisite errors. Preserve hero-only/social-only/planned failures, lazy imports and argument validation. Never select an entire conflict side or weaken checks to resolve the overlap.

Complete the previously approved resvg naming-only repair and real social PNG on this combined branch. Run the focused and full visual suites, hooks, strict asset typing and separate hero/workflow/social regeneration checks. Codex must independently review the resulting diff, actual social pixels and exact-head hosted CI before merging. The combined PR may supersede isolated hero PR25 only after those gates pass; no accepted asset is silently dropped. The final README blind test remains mandatory.

## V1-031 — Pin the official Linux recording renderer before its CI use

Independent read-only verification downloaded the official asciinema/agg v1.9.0 Linux x86_64 asset433215010: agg-x86_64-unknown-linux-gnu, 15,904,064 bytes, SHA256 f111e315cd71056b116302342553dd765b7297579ed511f111d0cedb442aeda6, matching the official API digest. Release331678489 resolves to source26ca84c02523973198fca28533369edcfc7ed929 under GPL-3.0-or-later. The binary was not executed or installed. Private receipt: /tmp/actseal-agg-linux-review.796ihg8d/receipt.json.

Claude15 may add exactly one linux-x86_64 agg artifact entry to docs/assets/src/tools.toml and the corresponding exact approved-pin test entry in tests/visual/test_tools.py while repairing the same manifest for resvg. URL: https://github.com/asciinema/agg/releases/download/v1.9.0/agg-x86_64-unknown-linux-gnu . Use the filename and hash above with no member field: this is a standalone ELF, already supported by the existing bounded installer. Preserve every existing platform/version/hash, full-byte verification before executable installation and rehash-before-execution. No extractor refactor, execution on macOS, new downloader, runtime dependency or claim of Linux compatibility is authorized by this pinning amendment.

Static inspection requires the x86-64 loader, libgcc_s.so.1, libm.so.6 and glibc symbols through GLIBC_2.38. Actual hosted execution, font-explicit rendering and deterministic GIF regeneration remain Task14/09 acceptance requirements. A matching download hash is not an execution receipt; missing prerequisites must fail. Record the narrow pin addition in the integration REPORT, separately from actual social generation and later recording validation.

## V1-032 — Prepare the integration candidate before final media and registry approval

At 10:30 IST on7October the approved Fable allowance reset and the preserved Task15/06 sessions resumed successfully with the same model, account and billing route. Task06 remains offline and no actual credential access or live dispatch is authorized. To keep the release critical path parallel, Task19 may start a PARTIAL integration candidate from reviewed main20b996917c25111bc9b043f22db000be0ff8fcdc while those separate lanes finish. This changes dependency timing only; all original full-task, native, visual, exact-head hosted CI and publication gates remain.

Use a separate worktree and integrate exact reviewed snapshots05 c2e27d2235eb98be0f97c9ec6d38b0c8ff235dfa,08 eb21e8738d1f529d0e06223203e4266f1c495218 and the independently accepted Task09 snapshot named in the dispatch. Preserve authorship and reports; do not consume active Task06/15 working changes. Claude owns any semantic conflict. In docs/schemas/README.md preserve the Jev profile and all three release-receipt sections. Unexpected conflicts require review; no blanket ours/theirs resolution.

For this phase Claude19 owns src/actseal/cli.py and runner.py; tests/unit/test_cli.py, test_runner.py, test_stability.py and narrow new CLI integration tests; docs/cli.md, providers.md, python-api.md, faq.md, stability.md and schemas/README.md plus their tests/docs assertions. Preserve05's records, normalization, transport, faults and schema changes without redesign. Codex retains version/classifier/lock and packaging glue. Task15 owns all visual registrations/rendering. Task07 archive and final compatibility integration remain a later phase; do not import or exclude its known-red tests to manufacture a green candidate.

Freeze CLI behavior: lock/verify accept Jev only with --provider jev --experimental-provider. Missing opt-in returns versioned ERROR/3 before provider construction, environment access or requests. The experimental flag with fixture/Laya is usage ERROR/3; replay/demo reject it. Jev rejects --responses. Jev --offline fails with ProviderSetupError/ERROR3 before environment access or requests. Keep open_model(provider, *, responses, offline) unchanged: explicit Python selection of jev is its opt-in. Add only a lazy experimental import, retaining all import-free replay/CLI behavior, bounded diagnostics, receipts and exit codes. No fallback, retry, key access or live inference in this phase.

Replace obsolete tests that required every Jev request to fail with explicit opt-in routing and negative controls; retain unsupported-provider rejection before factories and never-fall-through-to-Laya checks. Update help, provider/stability inventories and matching docs assertions atomically. Truthfully classify Jev as PROVISIONAL and mocked behavior as mocked. Preserve stable signatures and statistical/evidence rules.

Final source/version freeze, exact producer registry approval, unchanged Task07 archive replay, any Task06 producer approval, final provider inclusion and full Task19 ACCEPT remain outstanding. A reviewed prerelease producer may later be approved only by a separate exact-hash compatibility review; no registration or released-producer claim is authorized here. No main merge follows from an early green candidate.

## V1-033 — Preserve prerequisite negative tests after the Linux agg pin

Task15 integration b11d92d8cdefc304c283ece27856dd12277e9bd4 delivers the actual social PNG and passes regeneration, but three assertions still assume agg has no Linux artifact. Independent source review confirms that V1-031 intentionally invalidated those expectations, not their negative-test purpose. Extend Claude15 ownership only to these assertions in tests/visual/test_tools.py and tests/visual/test_pipeline.py and their directly stale explanatory text.

In test_verified_binary_requires_cache_and_matching_hash, retain the Linux no-pin rejection using asciinema (still unpinned there), additionally assert agg Linux's exact not-cached error, and preserve all mac missing/tampered/valid-cache controls. In test_manifest_validation_rejects_bad_entries, require the additional agg unknown-platform error before resvg after the fixture rewrites both Linux entries. In test_planned_asset_requirements_are_informational, update Linux agg to the exact not-cached path while retaining report.ok, no errors, two informational diagnostics and zero checked assets. No product/tool implementation, pin, fixture architecture or failure suppression changes. Rerun focused/full visual and ordinary suites, hooks/types and regeneration; retain the earlier failures in history. Final source/pixel/hosted review remains required.

## V1-034 — Prepare the README and publishing guide while final architecture completes

Permit Claude08 to finish bounded documentation preparation before final Task13/07 integration. Use the exact committed integration snapshot containing accepted05/08/09, named in the dispatch; no active working changes. After Task15 source ACCEPT, consume its exact committed hero/workflow/social outputs in the isolated docs branch. This changes dispatch timing only: Task08 remains PARTIAL until every referenced image exists, final provider/example facts are integrated, all original checks pass, actual rendering is reviewed and the blind ten-second test passes. No missing-image bypass or provisional full-task ACCEPT.

Exclusive Claude08 paths: README.md, CHANGELOG.md, docs/publishing.md, necessary docs/quickstart.md and docs/concepts.md edits; new tests/docs/test_readme.py and test_publishing.py; draft plan/v1/RELEASE_NOTES.md and its own REPORT. Update only stale status paragraphs in docs/decisions/0017 and0020 (use their actual filenames), preserving each accepted decision and honestly distinguishing reviewed inputs from pending inclusion/release. Do not touch Task19-owned CLI/provider/Python/FAQ/stability/schema docs, their existing tests, tests/docs/conftest.py, other lanes, product code, workflows, packaging or docs/assets. Preserve accepted SECURITY/CONTRIBUTING/AGENTS unless a concrete finding is reported first.

Follow PLAN sectionD's exact opening order/copy and three PyPI command shapes; use absolute README documentation/image links and descriptive accessible picture sources. The four architecture filenames are frozen but their outputs are still pending. No demo GIF reference may appear before the genuine post-PyPI Task14 capture; Task21 adds it. Prepare the actual publication guide for branch workflow_dispatch rehearsal with no inputs, tag-triggered exact-artifact publication, human pypi approval and partial-publication recovery. Remove obsolete publish=true instructions without changing the workflow. Candidate checks cannot be labelled public PyPI receipts. Release-note hashes, attestation claims, final totals and live Jev results remain unclaimed until supported by actual receipts; record explicit pending gates in the draft.

Task19 supplies final experimental-provider inclusion facts; Task07 archive claims wait for final compatibility approval. No shadow edits or automatic merger of active work. Report missing prerequisites and existing assertion conflicts rather than changing another lane's tests. Codex reviews the scoped diff and exact-head CI; the release gates and deadline are unchanged.

## V1-035 — Repair audit journal validation and preserve the first preregistration candidate

Independent and parent offline probes of Task06 at5184aab reproduced invalid COMPLETE receipts for missing/forged timing, a wrong nested calibration request hash and unsupported run metadata. REVIEW06-offline-preparation requires bounded fixes within the already owned bench/jev_audit and tests/bench/test_jev_audit.py paths. No core provider/policy/statistical/schema or other-lane changes. No key access or live call is authorized.

Freeze strict run/journal record validation: exact field sets/types and supported schema; valid canonical UTC metadata; frozen5400-second budget before attempts; finite nonnegative chronological monotonic values; nested capture hash equals the scheduled request for both cohorts; coherent stop/late/budget flags derived and cross-checked against recorded timing and schedule. A request cannot start at/after the cutoff; an already-started late capture is retained and causes ERROR. Empty/interrupted journals produce explicit incomplete accounting; complete evidence cannot omit a valid budget. Reject contradictions, unknown versions and malformed interior records.

For one malformed, unterminated final journal fragment, preserve the raw file unchanged and report a torn-tail finding while accounting only for validated complete prefix entries. Never invent a terminal capture, retry or turn that run COMPLETE. Malformed complete/interior records still fail strictly. Add independent-style negative tests for all reproduced defects, byte-preservation checks, honest partial accounting, empty license and portable alternate-interpreter assertions. Keep evidence limits: recorded clocks do not prove real elapsed time or inference.

Keep the first candidate's data directory and all committed bytes at e466d9e unchanged as historical preparation. If bound scripts change, prepare the revised preregistration in a new data-revision2 directory, update the active DATA_DIR explicitly, retain attribution and original input/contract/lock bytes where unchanged, and record both candidate hashes. No observations exist and no threshold, question, sample, order or identity may change. Neither candidate is approved for live work until a new independent review. Never delete/reseal a completed run.

The benchmark checker is experimental, outside the stable core CLI. Full historical audit-receipt checking uses its recorded exact checker/producer snapshot; current-source drift must stay explicit. Final v1 may replay an unchanged ordinary evidence bundle only after Task19 approves exact producer compatibility. Do not add a broad drift allowance or claim that generic bundle replay validates the entire benchmark journal. This bounded compatibility policy keeps the optional audit inside the sprint.

## V1-036 — Complete the architecture against the reviewed experimental-provider integration

Candidate inclusion decision: retain the optional Jev adapter as PROVISIONAL, explicit opt-in only, alongside stable fixture and Laya. Reviewed Task19 source2596204/0d85fc7 and head1fd9d08 independently pass3,824 tests including native and assets, hooks, plus359 separate focused tests. Live Jev capability remains unverified; no key or live audit is authorized. Exact-head hosted green and the14:00 inclusion gate remain mandatory. The live audit is a separate optional receipt; no image or text may imply that it ran. If provider integration fails the cut, remove Jev through an explicitly reviewed amendment and regenerate the architecture.

Claude13 may merge exact main7820dba and reviewed integration1fd9d08 into its existing source branch, preserving every accepted hero/workflow/social byte and all source histories. Own architecture.py, its tests, architecture-only inventory registration, the package export if needed, four generated architecture SVGs, necessary architecture integration assertions in test_render_cli.py, the architecture section of docs/assets/src/README.md, and its new REPORT. Do not edit other renderers, product code, root README, tool pins, dependency/workflow files or other lanes. Resolve only an anticipated shared visual registration/assertion overlap by preserving all accepted behavior; unexpected semantic conflicts require review.

Depict seven real groups with the pluggable providers boundary: fixture outside live inference, Laya and optional experimental Jev inside the live-call boundary. Every node maps to actual modules at the integrated source; the Jev module is experimental.providers.jev, not an invented stable adapter. No live-verification, response-authenticity or surrounding-application enforcement claim. Replay never reaches a provider. Preserve the four frozen architecture filenames, light/dark/mobile readability, deterministic SVG structure and all original quality gates.

Register and generate the actual four outputs now using the approved existing toolchain. Run the original done command, full visual tests, asset strict typing, hooks and ordinary tests. Approved pinned resvg may render temporary review pixels; no browser workaround. Keep all missing-prerequisite negative assertions meaningful while updating only counts changed by a second font-free implemented renderer. Report actual pixels separately from structural tests. Codex independently reviews pixels, source, regeneration and hosted CI before ACCEPT. Final README/blind review remains required.

## V1-037 — Approve the exact retained example and final-candidate replay mappings

Codex packaging commit0b57933710437c6f48f5689a8b73c83db4bca6fd sets only package/source/lock self-version1.0.0 and Production/Stable metadata after reviewed Task19 product integration. Independent review confirms final candidate fingerprint8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3. Independent and parent controlled probes against the unchanged Task07 archive reproduce the entire stored PASS verdict and all negative controls; receipts are recorded in reviews/19-final-compatibility-probe.md.

Approve exactly two registry entries for actseal-choice-v1: final candidate8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3 and original example producera5fe090202f75b07510407937a86ae35a7653a75eab3f4daa2d0ace2e7641642 from reviewed source76758d7084e396c8960718d28c1cad5fb70bac03. The latter is an explicitly UNRELEASED prerelease source tree with a0.1.0 version string; it is not the releasedv0.1.0 implementation or schema1 evidence. Narrowly amend versioning/compatibility documentation to allow this named reviewed prerelease source with its retained schema2 archive. Do not claim a release occurred or approve other prerelease producers, ranges, wildcards or Task06. Final source Python edits invalidate this approval and require a new fingerprint and review.

Claude19 may integrate exact accepted Task07 source277d8e23f0de161e72a8617c74d3b05e6d75069a and Task08 preparatione90c4e6372723b01efab106f10a1ef7260a00a40 on its isolated candidate branch; this is not a main merge. Preserve original archive bytes and reports. Own the two-entry registry JSON, existing compatibility/cross-release tests and example/packaging acceptance tests needed for actual archived replay, a narrow version-output assertion update, and compatibility/versioning/migration/stability documentation describing these exact entries. Keep current-source collection strict before factory/decide. Retain empty/one-sided/wrong-engine negatives in explicit temporary registries. The packaged registry must be byte-identical to reviewed JSON in wheel and sdist, and supplied-wheel replay must run outside the checkout with transport imports and network forbidden.

Codex owns adding exactly examples/action_gate and plan/v1/RELEASE_NOTES.md to the sdist inventory and packaging glue tests. The latter is now a required input of Task08 documentation checks; it must be packaged and its pre-tag state finalized before build. Post-publication receipt/media edits cannot modify the already-published copy. Claude08 must correct any current publishing-guide assertion that this release-note file is absent from distributions after the packaging change. Preserve failed checks as history. No test exclusion, weakened gate, archive resealing or registry-dependent fingerprint monkeypatch is permitted. New unexpected semantic merge conflicts stop for a bounded review.

Task13's denied local merge is a separate blocked outcome, awaiting the user's scoped answer; this amendment does not authorize any replacement route to that denied architecture integration. Final asset/blind/rendered/hosted/publication gates remain.

## V1-038 — Close the audit validator's two remaining offline edge cases

Independent review of Task06 repaire2ab596 confirms all prior false-COMPLETE and torn-tail defects fixed,86 tests and source-verified candidate2 pass. Two bounded issues remain: float conversion ofmonotonic_s=10**400 and deadline addition at9999-12-31T23:59:59Z raise uncaughtOverflowError instead of structuredJournalError; one expected_identity(3.13.0) assertion missed the alternate-interpreter helper. These fail closed but must be corrected before preregistration approval.

Claude06 owns only the exact validator guards, narrow CLI regressions and missed test assertion, candidate-binding bookkeeping and its newREPORT. Convert only those validation arithmetic failures toJournalError; no broad exception swallowing, schema/policy/model/sample/budget change. Because bound scripts change, preserve data/ and data-revision2/ byte-for-byte, create data-revision3/ with identical six non-preregistration files and only updatedscript hashes/selfseal, update DATA_DIR and document all candidate states. No observation exists; no live/key/.envaccess is authorized. Verify both historicalcandidates remainbyte-identical, current959-case preregistrationbindings and sourcepins, fullbench tests/hooks, and actualCLI structuredfailure. Finalindependentapprovalstillrequired.

## V1-039 — Complete the registry review and record a version-test ownership deviation

Independent review of Task19 at ce38760 requires four bounded corrections: registry documentation must describe producer/engine approval, not a nonexistent per-archive allowlist; the missing-registry negative/control must use a genuinely absent fresh path; the retained-archive inventory must include PRODUCER.json and assert all nine filenames; and the action-gate example must describe the completed compatibility approval instead of a future Task19. Preserve source fingerprint8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3, both approved mappings and every original archive byte. No runtime, statistical, schema or provider change.

Claude19 owns these narrow fixes in docs/versioning.md, tests/unit/test_compatibility.py, examples/action_gate/README.md and comment/docstring/refusal-message wording in examples/action_gate/run.py, plus necessary corresponding wording assertions within tests/examples and its REPORT. The example's control flow and failure semantics must stay identical. Missing-registry tests must assert path absence; archive preservation must include PRODUCER.json SHA25663d49ba57cfbfb2ba7762bb483feebb136e772de5d95c2a695a653eadf6b580d.

Claude19 committed77b8356 before requesting the required ownership amendment for tests/acceptance/test_acceptance_wheel_receipts.py and tests/unit/test_serialization.py. Codex interrupted the session. The changes replace stale0.1.0 literals with exact1.0.0 assertions after the approved metadata bump; they do not weaken isolation/import checks. Preserve the commit and explicitly report this process deviation. Parent28 version/isolation/supplied-wheel and147 compatibility/example/wheel checks passed, but prior scoped authorization is not inferred retroactively. These two existing assertions are now included for review and future corrections only; no other acceptance-test changes are authorized.

Codex Task09 packaging commit dd1bafe adds only examples/action_gate and plan/v1/RELEASE_NOTES.md to the explicit sdist inventory, with real-artifact byte checks. Parent25 tests/hooks and independent2 real-sdist checks pass. Claude08 owns the consequent narrow publishing-guide correction and its existing tests: pre-tag release notes are packaged; later receipt/media additions do not alter published bytes. No other release facts become complete by this change. No denied Task13 action or actual key access is authorized here.

## V1-040 — Exercise the already approved Linux recording renderer in CI

Task09 may provision the existing approved agg1.9.0 linux-x86_64 pin before asset regeneration in both ordinary and publication workflows, then run an unconditional fail-closed version probe. No new pin, dependency, renderer or runtime change. A matching hash proves only consistency; actual hosted execution must be recorded before claiming Linux usability. This probe does not establish GIF rendering or Task14 completion.

Claude09 owns only .github/workflows/ci.yml, publish-pypi.yml, tools/check_release.py, focused tests/release regressions and its REPORT. Add an internal agg-version release-helper command using existing manifest/platform helpers, requiring actual linux-x86_64, verifying the binary hash immediately before run_tool([binary, --version], timeout=10), and requiring exact strippedstdout agg1.9.0 with the CLI's actual space (agg 1.9.0). Print observed version/platform and approved manifest artifact hash; fail explicitly on missing tools, wrong platform/version, nonzero status or timeout. No network in tests.

The workflow checker and tests must require locked install, exact pinned provisioning, real version probe and regeneration in order, once each, with no conditional/ignored-failure escape. Offline tests must show tamper rejection before execution and all error paths. Preserve existing failure diagnostics and mutations. This is CI/packaging glue delegated to the existing approved Claude09 executor, not a product-interface change. No local architecture-branch merge, credentials, release/tag or publication is authorized by this amendment.

## V1-041 — Human approval to resume Task13 and standing approval within the sprint

On 7 October at approximately 12:27 IST the human replied: "`approve Task13 merges` and all future Approvals." This explicitly clears the previously denied Task13 local merges of reviewed main7820dba49f68f347f42fbdc06044de256c06efa2 and reviewed integration1fd9d080996e216b9edc386597487a78067f25b5 into the isolated architecture branch. Resume the same Fable5.1/high session; preserve the prior denial/report and all reviewed histories. The V1-036 file ownership, claims, tests and independent acceptance requirements are unchanged.

The standing approval applies to necessary actions within the already approved Actseal release plan, including narrowly loading JEV_API_KEY for the reviewed, one-attempt Task06 audit. It does not authorize printing credentials, reading unrelated secrets, changing accounts/models/billing, weakening acceptance, disabling hooks or overriding a new tool denial. Codex must first recheck the exact accepted preregistration/source/interpreter and separately dispatch that live phase. Only the named key may enter the audit subprocess; do not shell-source the .env or expose its contents. No new source edits, resealing, retries, sample replacement or threshold changes are authorized. The manual pypi deployment gate and exact-head green-CI/main-merge requirements remain.

## V1-042 — Finalize accepted documentation facts while harness gates remain blocked

Claude13's fresh-approved merge was denied again as Auto-Mode Bypass and remains unperformed. Its report8c089ce is preserved; suggestions in that report to have Codex perform the same denied outcome are not authorized. Claude06's separately dispatched live audit was stopped by a Real-World Transactions denial on its .env existence preflight, before key access or any --execute call. No alternate route or credential source is authorized after that denial. Standing human approval did not change the Claude harness permission rules; those require an actual user-side grant. Do not retry either blocked outcome.

Independent documentation review found stale implementation-status claims in the otherwise accepted candidate. Codex fast-forwarded only the separate Task08 docs branch from710ae55 to reviewed integrationb05aed85; this is not the denied architecture-branch action and creates no architecture output. Claude08 may now update README, CHANGELOG, plan/v1/RELEASE_NOTES.md, docs/architecture.md, dependencies.md, providers.md, versioning.md, status/history paragraphs in ADR0004/0015/0017/0018/0019/0020, corresponding wording assertions in tests/docs, and its own new report. No normative signature/schema/statistical/registry change, product code, generated assets or old reports. Preserve source fingerprint8f316f67 and every archived byte.

Describe the included candidate experimental Jev transport/explicit flag accurately, with no accepted live evidence. Correct the historical core-contract pointer, Laya-only worker semantics, two-entry producer registry, accepted native/conformance checks, actual Linuxagg execution, accepted social pixels, and completed blind README preflight. Preserve dated earlier ADR milestones and final gates separately. Narrowly transfer only the stale prerequisite/status paragraph near the end of docs/assets/src/recording.md to Claude08; no capture procedure, helper, pin or asset edit.

Keep draft/unpublished release status until the mandatory pre-tag gates pass. Final implementation facts can be stated now; named future receipt placeholders remain for exact release artifacts/CI/publication/recording. Architecture, final visual acceptance, final candidate CI and rehearsal remain visibly pending. No wording test may pretend missing architecture exists or turn pending gates into passes. Run full Task08 done commands and report the known missing-image failures honestly; passing focused checks do not constitute full Task08 acceptance.

## V1-043 — Human confirms actual harness permission changes

The human answered the scoped permission-system request with "Claude permissions updated for both tasks", then reiterated "I approve everything." This is first-hand confirmation that the permission mechanism named by the Task13/Task06 denials was changed, not merely a relayed prompt assertion. Resume the exact previously approved operations in the same two sessions using normal permissions, after rechecking no merge/live run started. Preserve both failed resumptions and their reports. A new denial still stops that outcome; no bypass flags, alternate executor/credential route or disabled hooks. Task06 retains the same preregistration, 959 scheduled entries, one attempt per case, fixed policy and deadline. All source/release gates remain.

## V1-044 — Repair final-facts contradictions and prepare the missing demo renderer

Claude08 owns only the three documentation/test repairs in reviews/08-final-facts.md and its additive report. Its previous module-level ssl preload was a bounded ownership deviation; independent technical review accepts it because the offline socket guard remains intact. No other test/runtime ownership expansion follows. Prior denial reports stay immutable, and no denied action is retried.

Read-only Task14 review confirms accepted preparation11a31fc has no final GIF renderer: inventory still declares a planned demo.gif with renderer=None. Prepare the missing rendering code before publication without creating a cast or product GIF. Codex may fast-forward only the separate recording preparation branch to reviewed integrationb05aed85. Claude14 owns new docs/assets/src/actseal_assets/demo.py, tests/visual/test_demo_render.py, and its new report; no inventory, existing renderer/helper, recording procedure, product, dependencies, pins, README, source fixtures or Task13 work.

Freeze demo-light.gif and demo-dark.gif as the eventual two outputs. Reuse existing pinned-tool/font verification, run_tool and agg_command with its reviewed speed1, ceil(duration)+1 idle limit, theme and last-frame arguments. Validate the real input under the existing procedure: v3, approved geometry,20–40seconds, output events plus exactly one final x with payload0, no input/resize/marker events, and required ordered commands/exit markers. Never execute a cast header command. Validate actual GIF frame delays, complete bounded structure, at least one frame,20–40seconds and each file strictly below3,000,000bytes; do not treat header dimensions or configured flags as measured duration.

Offline unit fixtures/doubles must exercise malformed/missing casts, invalid events, tampered/missing prerequisites, renderer failure, stale/missing outputs, malformed/oversized/short/long GIFs and deterministic repeated rendering. Temporary synthetic test data is labelled as such and never committed under docs/assets as a product demonstration. Leave inventory unimplemented and create no actual docs/assets/src/demo.cast or GIF; actual post-PyPI capture, provenance binding, repeated real rendering, pixels and activation remain Task14's later acceptance gate. This preparation creates no new public surface or packaged Python fingerprint change.

## V1-045 — Actual Task13 rule additions and fourth denied resumption

The human added the two exact Bash merge allow rules for main7820dba and
integration1fd9d08. A single missing comma made the edited user settings invalid;
Codex repaired only that punctuation byte, validated JSON and confirmed both
exact entries. No permission entry, deny rule or mode was changed by Codex.
The same Task13 Fable5.1/high session resumed under normal permissions and
received a fourth Auto-Mode Bypass denial, preserved in report6ba49ae.

The issued command included an output pipe instead of the bare approved
command. The report incorrectly describes a cd prefix absent from the raw
stream; preserve that report and record this correction. That is a possible rule-matching cause, not an independently
established diagnosis. The new denial stops the outcome; do not retry a bare
command, split the operation, change executor or infer a further grant. Source,
outputs and main remain unchanged. Task06 has no new effective grant and no
key read, execution, journal, request or spend. Keep both blocked outcomes
separate from continuing documentation and standalone-renderer preparation.

Task08 correction2ccdac6 is scoped ACCEPT after parent and independent review;
full Task08 remains PARTIAL for its existing mandatory gates. No policy,
schema, statistical rule, registry or accepted asset changes are authorized.

## V1-046 — Correct demonstrated demo-validator defects before acceptance

Task14 preparation c788dad is REVISE despite56 passing focused tests. Parent
and independent probes demonstrate counted delays with no corresponding
image, an uncaught truncated-header IndexError and accepted empty image data.
The bounded fixes are specified in reviews/14-renderer-preparation.md.

Claude14 retains ownership of demo.py, test_demo_render.py and a new additive
report only. Additionally authorize the step7 inline GIF walker in
docs/assets/src/recording.md to be replaced by the corrected shared demo
validator, plus the stale step1 sentence claiming official downloads are
permission-blocked. Do not edit its final Pending section, which belongs to
accepted Task08 corrections, or any other recording procedure. No actual
capture, tool execution/download, product asset, inventory registration,
dependency, packaged source or policy change. Temporary synthetic test
fixtures remain clearly labelled and outside product assets.

Require one graphic control per following image, complete bounded structural
validation, early byte caps, strict string output payloads and exact TERM/LANG
header env keys, and hash verification immediately before each variant tool
execution. Keep provenance/real-pixel validation separate from structural
consistency. Preserve all earlier reports and correct stale statements only
in the additive report. Run original preparation commands with known
architecture failures reported honestly; final media remains post-publication.

## V1-047 — Prepare the existing 14:00 optional-provider cut without activating it early

At approximately13:41IST, complete candidate5e7931a has ten failed hosted jobs
across runs37590464434/37590468512. Independent full-log review finds only the
four missing architecture images. This does not satisfy PLAN/V1-036's explicit
requirement that the optional provider be integrated and exact-head green by
14:00. Component success cannot waive the approved time gate.

Prepare tasks19-jev-cut.md and19-jev-cut-docs.md now; do not dispatch before
14:00. Codex must refresh actual time and candidate/CI state at the gate. If
the complete candidate is still not green, activate the coherent adapter plus
unstarted live-audit deferral to1.1 and record that observation. If it is green,
leave these specs undispatched. Do not invent a run receipt for Task06: no key,
request, journal or credit use occurred.

On activation, Claude A owns only the explicit product/profile/CLI/schema and
associated test cut enumerated in19C; Claude D owns only current public docs,
their assertions and dated ADR addenda enumerated in19D. Preserve all accepted
source branches/history, benchmark candidates, old reports, stable fixture/Laya
semantics and the original nine-file action-gate archive. No mechanical revert,
test weakening, new dependency or statistical/policy change is authorized.

Any packaged Python change invalidates current producer8f316f67 approval.
Freeze the new source, independently recompute its exact fingerprint and repeat
the original archive's full-verdict/negative-control compatibility probe. Only
after a separate recorded exact-hash approval may a follow-up task update the
registry and current-hash assertions/docs. Keep exactly original producera5fe
and newly approved current producer; no automatic carry-forward of superseded
or benchmark producers. The cut tasks do not approve that future mapping.

Task13's actual denial remains separate. Neither this amendment nor the cut
authorizes retrying/rerouting its merge. Eventual architecture must depict only
the final admitted providers; mandatory images, original checks, ACCEPT and
exact-head green hosted CI remain required. Prepare a one-time same-thread
14:00 wakeup so the already approved cut is not missed while waiting for the
human's pending manual-merge response.
