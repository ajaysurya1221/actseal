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
