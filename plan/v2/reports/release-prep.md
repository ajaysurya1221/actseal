# v2 release preparation REPORT — 13 November 2026

Status: implementation complete on `claude/v2-foundations`. The requested
local completion gate is met with its explicitly permitted seven `/bin/ps`
sandbox exceptions. All other tests and the required type/lint/format checks
pass. Process-cleanup verification and the cross-lane workflow issue below
remain unresolved.
This is an executor report, not an independent ACCEPT or publication approval.

## Scope and evidence

Read `AGENTS.md`, `CLAUDE.md`, the active v2 state, plan and change log,
`plan/CONTRACTS.md`, stability/statistical guidance, and the M4, M5, M6 and
assets reports before editing. `plan/v2/reports/M2.md` and `M3.md` do not exist
in this checkout; their absence is recorded, not treated as verification.
V2-003 supersedes the original proposal's engine/schema changes and V2-002
defers the model comparison.

The working tree already contained reviewed, uncommitted work. The task permits
only the four excluded top-level Python files, documentation, README, tests,
packaging metadata and `action.yml`. No hashed kernel file, packaged registry,
`tests/unit/test_compatibility.py` or `APPROVED_REGISTRY` constant is owned here.
The orchestrator is registering the final fingerprint separately.

## Work ledger

1. Report presentation: complete; stored-value headline, badge and numeric
   formatting, with 32 passing focused regressions.
2. Version and release documentation: complete; 2.0.0 remains unreleased.
3. README and executable examples: complete; synthetic/recorded scope and
   historical audit provenance retained; 35 focused tests pass.
4. Whole-tree verification: complete with the seven named sandbox exceptions
   below. Scope comparison and internal review found no unresolved in-scope issue.

## Changed files for this task

- Presentation: `src/actseal/report.py`, `tests/unit/test_report_render.py`,
  `tests/unit/test_report_cli.py`.
- README: `README.md`, `tests/docs/test_readme.py`.
- Version metadata: `pyproject.toml`, `src/actseal/__init__.py`, `CITATION.cff`,
  `uv.lock`, `action.yml`.
- Documentation: `CHANGELOG.md`, `SECURITY.md`,
  `docs/{migration,stability,versioning,github-action,quickstart,faq,python-api,cli}.md`,
  `docs/schemas/README.md`.
- Version/metadata tests: `tests/docs/test_policy_and_metadata.py`,
  `tests/unit/{test_github_action,test_cli,test_serialization}.py`,
  `tests/acceptance/test_acceptance_wheel_receipts.py`; this REPORT.

These are this task's changes, not the complete working-tree diff. Earlier v2
work in all other dirty/untracked files is preserved. A before/after source-byte
snapshot shows only top-level `__init__.py` and `report.py` changed among all
packaged Python files. Every hashed kernel file, the packaged registry and
`tests/unit/test_compatibility.py` match the entry snapshot exactly. No packaged
Python file was added or deleted. The running fingerprint at the time of this
report was the then-registered 2.0.0 candidate value, later superseded by
`1c579ef18c4aada29bc7b0fc2d9b319e13cb30c973ec50484bfa025ccd233b42` after a
review finding moved report-command integrity logic into the fingerprinted
`actseal.qualification` module.
`tests/examples/test_run.py` and its `APPROVED_REGISTRY` were not edited.

## Implementation details

The renderer reads the stored verdict's coverage lower bound and the locked
contract's risk limit, alpha and threshold. It does not compute bounds or
evaluate a decision. Only PASS gets an automation headline and expanded badge;
BLOCK, INCONCLUSIVE and ERROR say the risk limit was not shown to be met and
keep a status-only badge. Percentages show one decimal. The table-formatting
instruction is interpreted as at most four decimal places with trailing zeros
removed; evidence bytes and the headline's exact threshold value are retained.

Version 2.0.0 is synchronized across package metadata, the top-level version,
the lockfile's own-package entry, citation metadata and the Action default.
The citation's old release date is removed because 2.0.0 is unreleased.
Dependency records are not re-resolved. The changelog separates new features,
compatibility and known limits; historical entries and receipts stay historical.
Current migration, stability, support and replay wording are aligned with v2.

The README starts with the requested sentence, synthetic qualification,
recorded predictions, planning and the Action. It keeps the engineering strip,
badges, license, historical Jev evidence and lower references. The recorded
JSONL example is explicitly three illustrative rows, not a sufficient sample.
Executable docs tests extract all ten shell commands, the inline application
command and the Action arguments, substituting only the local interpreter for
the environment launcher. Complete synthetic splits contain all three literal
example rows. These tests verify CLI flags and behavior, not installation or
hosted execution. The audit check compares counts and both intervals to stored
evidence and rejects the obsolete archived-producer requirement.

Internal read-only review identified stale compatibility sentences in the
versioning/stability/API/schema/CLI documentation; they now distinguish
exact-source collection from exact-or-dual-registered replay. This review is
not independent third-party acceptance. It also corrected “without reading
verification responses” to “without running verification”: the recorded adapter
parses the combined predictions file, but selection never uses verification
outcomes.

## Focused checks

- Report renderer/CLI tests: exit **0**, **32 passed**. The new headline tests
  failed before implementation and cover stored lower bounds versus observed
  counts, contract limits, all statuses, placement and deterministic bytes.
- Version/metadata/CLI/serialization/stability/Action tests: exit **0**,
  **641 passed**; subsequent docs/API/stability/Action tests: exit **0**,
  **217 passed**. A mistyped test filename caused one exit **4** with no tests
  collected; the corrected test selection passed.
- `.venv/bin/python -m pytest tests/unit/test_compatibility.py
  tests/unit/test_jev_audit_replay.py tests/examples/test_recorded.py
  tests/examples/test_run.py -q`: exit **0**, **109 passed**. No temporary
  registry augmentation was used.
- `.venv/bin/python -m actseal replay
  docs/results/jev-audit-2026-10-08/evidence --json`: expected exit **2**,
  INCONCLUSIVE; 580/639 ACT, 24 errors; risk
  `[0.02498087158203282, 0.06393316057415596]`, coverage
  `[0.8787825228681747, 0.9316794056630708]`. Direct packaged-registry replay
  is verified against the existing audit bytes.
- A fresh `demo --qualify` and `report` both exited **0** under
  `/private/tmp/actseal-release-prep.5X5f0n/`. The synthetic run selected 0.95,
  returned PASS with 100/100 ACT and zero errors, and rendered the stored lower
  bound as 95.7% at risk limit 20.0% and confidence 95.0%.

## Command environment

`uv run --frozen pytest -m 'not integration and not packaging' -q` exited **2**
before pytest started: opening `/Users/ajay/.cache/uv/sdists-v9/.git` was denied.
The task explicitly permits `.venv/bin/python -m ...`; subsequent checks use
that existing environment. No denied cache retry, permission override,
dependency re-resolution or substitute process inspection is authorized.

## Final whole-tree checks and failure split

All commands below ran against the final implementation, after the three edit
lanes settled. Only this REPORT was edited afterward.

| Command | Exit / result |
| --- | --- |
| `.venv/bin/python -m pytest -m 'not integration and not packaging' -q` | **1**: **4,612 passed, 7 failed, 1 skipped, 31 deselected**, 108.75 seconds. |
| `.venv/bin/python -m mypy --strict src tests` | **0**: 126 source files. |
| `.venv/bin/python -m ruff check .` | **0**: all checks passed. |
| `.venv/bin/python -m ruff format --check .` | **0**: 521 files already formatted. |
| `.venv/bin/python tools/check_release.py docs` | **0**. |
| `git diff --check` | **0**. |
| `.venv/bin/python -m actseal --version` | **0**: `actseal 2.0.0`. |

The full pytest output is retained at
`/private/tmp/actseal-release-prep.5X5f0n/pytest.log`.

**Unregistered-fingerprint failures: 0. Other product/docs/visual failures: 0.**

**Sandbox process-inspection failures: 7**, all in
`tests/unit/test_providers.py`. Every traceback ends in
`PermissionError: [Errno 1] Operation not permitted: '/bin/ps'` while checking
for remaining child processes. The exhaustive names, grouped by test class:

| Test | Failing parameter values |
| --- | --- |
| `test_startup_failures_raise_and_leave_no_child` | `hang-on-start`, `exit-on-start`, `setup-error`, `garbage-on-start`, `deep-on-start` |
| `test_substituted_identity_is_a_setup_error` | `wrong-identity`, `bad-identity` |

No test was skipped, weakened or marked expected-failure to hide these denials.
The existing one skip and marker deselections are reported above. Child-process
cleanup remains unverified in this environment; no alternative inspection or
permission override was attempted.

## Cross-lane work and limits

`.github/workflows/action-selftest.yml` lines 45 and 87 assert that a PASS badge
message equals exactly `PASS`. The requested richer PASS badge makes those
assertions stale. The workflow is outside the explicit file allowlist and stays
untouched; its owner must update both assertions before hosted execution. This
is a concrete remaining workflow issue, not evidence of hosted success.

No branch switch, commit, push, tag, stash, revert, publish or public post is
performed. No live provider/server, hosted runner, integration or packaging
execution is claimed. Actual agent billed spend is **UNKNOWN**: no spend
receipts are available.

The browser preview attempt for the generated HTML returned “The browser
access host is unavailable.” Desktop/mobile pixel rendering is unverified;
HTML/Markdown structure, escaping and deterministic bytes have executable
coverage. No alternate browser-control mechanism was used.
