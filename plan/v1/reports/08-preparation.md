# REPORT 08-preparation

Status: PARTIAL (independent reference portion under V1-018; full Task 08
remains PARTIAL and still depends on accepted Task 07 and accepted static P1
assets). DONE here means "candidate for Codex review", not ACCEPT.

Executor: Claude Code, model `claude-fable-5-1`, effort high, run directly
(no subagents, nested executors or model substitution). Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, branch
`claude/v1-08-reference-preparation`, base `77bf39feb542d4cbaa2b9034e1210704a6019b68`
(accepted main, Task 02 stable interfaces). Python 3.12.13, uv frozen
environment, macOS. Nothing pushed, merged, tagged or released. No model or
API calls, no network downloads, no credential or private-memory access, no
dependency, lockfile, product-code, schema, normative-doc or asset change.

## Scope limits applied

- Owned paths only: `docs/concepts.md`, `docs/cli.md`, `docs/python-api.md`,
  `docs/faq.md`, `docs/quickstart.md`, `docs/providers.md`, `SECURITY.md`,
  `CONTRIBUTING.md`, `AGENTS.md`, `tests/docs/`, this report.
- Not touched: README, CHANGELOG, release notes, `docs/publishing.md`,
  architecture/threat-model/statistical-contract docs, `docs/stability.md`,
  `docs/versioning.md`, `docs/migration.md`, `docs/schemas/`, `docs/assets/`,
  product code, `pyproject.toml`, `uv.lock`, any other lane's files.
- No README composition, no final application-example claim, no release
  notes, no PyPI timing/output receipt for 1.0.0 (gated on Tasks 20/14).

## Changes

Commits on this branch, oldest first (each ends with the Co-Authored-By
trailer):

| Commit | Files | Summary |
|---|---|---|
| `b189495` | `docs/concepts.md`, `docs/cli.md`, `docs/python-api.md`, `docs/faq.md` (new) | Concepts: frozen question/policy, selected-option probability, scheduled denominator, per-case decisions vs whole-run verdicts (no one-to-one mapping), six faults, `evidence_scope` demo vs population assumptions, one attempt and no retries-to-PASS, producer provenance vs replay engine. CLI reference: exact `--help` usage lines, option table, no abbreviations, root-only `--version`, exits 0/1/2/3, `lock` exit 0 and `demo` exit-0 semantics, schema-1 receipt field table per variant, per-command behaviour. Python guide: surface by group with module paths, a 45-row exact-signature table, six runnable examples with typed inputs, provider protocol limits (only `fixture`/`laya` identities; no wrappers promised), errors. FAQ: verdict reading, retries, INCONCLUSIVE, zero-ACT, decisions vs verdicts, replay exit 1, authenticity limits, scope, Windows, zero-dependency core, legacy and cross-release replay. |
| `e8f21fd` | `docs/quickstart.md` (rewritten), `docs/providers.md` (edited) | Quickstart: the three PLAN section D commands verbatim; explicit note that the latest PyPI release is 0.1.0 and 1.0.0 is an unpublished candidate; expected demo table; exits; lock/verify/replay individually; Laya pointer; limits; Windows unsupported. Providers: "GitHub-wheel quickstart" wording corrected to the PyPI quickstart; explicit Windows-unsupported statement; Python-boundaries section points at the stability manifest and Python guide; Jev section retitled "conditional experimental work, not shipped" and rewritten to describe only the plan's PROVISIONAL boundary (`actseal.experimental.providers.jev`, `--provider jev --experimental-provider`, deadline-cut) and state the current source ships no Jev adapter; "outside v1" chain wording generalized to 1.x. Historical native/upstream receipts preserved unchanged. |
| `5357ccf` | `SECURITY.md`, `CONTRIBUTING.md`, `AGENTS.md` | SECURITY: only the approved support update (latest 1.x minor at its latest patch, current main; latest 0.1.x until 1.0.0 is published; pinned 0.1.0 replay is a compatibility path, not a 0.1 security branch) plus a stability-manifest pointer in the closing link list. Private advisory route, required invariants, reportable defect classes (parser, replay, statistical, lifecycle) and the three authenticity limits are byte-unchanged; no exclusion, waiver, accepted risk or new assurance. CONTRIBUTING: macOS/Linux only (Windows unsupported), docs tests note, stability/versioning pointers, dependency-free core, v0.1.0 sprint statement kept as history with the v1 pointer to `plan/v1/STATE.md`. AGENTS: active pointers to `plan/v1/STATE.md`, `plan/v1/tasks/<id>.md`, `plan/v1/CHANGE_LOG.md`, `plan/v1/reviews/`, `plan/v1/reports/`, `docs/stability.md`, `plan/v1/PLAN.md`; V1-005 autonomous Claude CLI orchestration supersedes the manual-dispatch model only; executor remains Fable 5.1/high; Codex writes planning/reviews/CI and packaging glue including CI helper tests, Claude writes product code/tests/docs/visuals; normal permissions, denials stay denied, no broad or permanent overrides; v1 release rules; old product constraints and private shared-brain exclusion preserved; v0.1.0 records kept as history. |
| `e9ddf09` | `tests/docs/__init__.py`, `conftest.py`, `test_links.py`, `test_cli_reference.py`, `test_python_guide.py`, `test_quickstart.py`, `test_policy_and_metadata.py` (new) | 88 tests, all offline, collected by the default suite. See Tests. |

The SECURITY.md diff for Codex's security-policy review is exactly the two
hunks in commit `5357ccf` (support sentence block; closing link list).

### What the tests check (no source-text mirror suite)

- `test_python_guide.py`: every `python` fence of the guide is executed in
  document order, in a fresh directory where `demo_run` has produced
  `./actseal-demo`, as a subprocess of the locked interpreter; each
  documented signature row is compared with `inspect.signature` of the
  installed object; every public module function in the manifest modules must
  appear in the table; every name in the surface table must be exported by one
  of its listed modules; examples import nothing optional, experimental or
  private.
- `test_cli_reference.py`: the documented usage lines equal the token stream
  of real `--help` output for the root and all four commands; the option
  table equals the real option inventory; each truncated option is rejected
  as a usage error with exit 3; `--version` after a command is exit 3; the
  exit-code table equals `EXIT_CODES`; the receipt field table equals the key
  set of real `lock`, `verify`, `replay` (success, integrity ERROR, usage
  error, unparsed command) and `demo` receipts; a replay of the demo's bad
  evidence exits 1 with status BLOCK and no integrity reason.
- `test_quickstart.py`: the first bash fence equals the three PLAN section D
  commands and that text is present verbatim in `plan/v1/PLAN.md`; the page
  does not claim 1.0.0 is published; candidate verification runs the
  equivalent `python -m actseal demo`/`replay fixed`/`replay bad` from the
  checked-out package and requires exits 0/0/1 with statuses PASS/PASS/BLOCK,
  the expected-observation table values, the documented output layout, and
  exit 3 "destination already exists" on reuse.
- `test_links.py`: every relative link and `#anchor` in the nine owned
  documents resolves inside the checkout; owned reference docs embed no
  images (static P1 assets are not accepted); every owned doc except AGENTS
  links to a normative document.
- `test_policy_and_metadata.py`: installed metadata has macOS/Linux and no
  Windows classifier, every `Requires-Dist` is under the `laya` extra,
  `Requires-Python >=3.12`; "Windows is unsupported" appears in quickstart,
  providers, FAQ, CONTRIBUTING and AGENTS; zero-dependency wording present;
  providers describes Jev as unshipped/experimental; SECURITY keeps the
  advisory URL, the new support rule, the reportable classes and the three
  authenticity limits and contains no exclusion/accepted-risk wording; every
  AGENTS pointer names an existing path.

Test-generated files use the task-owned directory
`<checkout>/.actseal/task08-docs-tmp/<uuid>/` (`.actseal/` is already
gitignored); each fixture use is removed afterwards. A one-off scratch runner
used while drafting lived under `.actseal/task08-scratch/` and was deleted
before commit; it was never tracked.

## Tests

All commands run from the worktree root on the final committed tree
(`e9ddf09`, working tree clean).

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs` | 88 passed in 1.05 s | 0 |
| `uv run --frozen ruff check tests/docs` | All checks passed | 0 |
| `uv run --frozen ruff format --check tests/docs` | 7 files already formatted | 0 |
| `uv run --frozen mypy --strict src/actseal tests` | Success: no issues found in 67 source files | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `uv run --frozen pytest -m "not integration and not packaging" -q -p no:cacheprovider` | 2811 passed, 20 deselected in 53.59 s (2723 pre-existing + 88 new) | 0 |
| `git diff --check` | no output | 0 |
| `uv run --frozen python tools/check_release.py docs` | **Not run: `tools/` does not exist on accepted main `77bf39f`** (the helper lives on the unmerged Task 09 branch). Reported, not weakened. | n/a |

Intermediate runs before the final tree: the first `tests/docs` run had 15
failures caused by test-side parsing (escaped pipes in Markdown tables,
same-file anchors, digits in field names, `actseal.adapters` not being a root
attribute, `actseal.stats` lacking `__all__`) and by the CLI page omitting
`[-h]` from usage lines; all were fixed in the tests or the page, none by
weakening an assertion. Every Python guide example passed on its first
execution against a fresh demo.

Not run, by packet instruction: live providers, native/integration tests,
mutation harness, authoring setup/downloads, local preview, `uvx` network
commands, pushes, merges.

## Deviations

- `tools/check_release.py docs` is absent from this base, so that Done-when
  command could not be executed; the gate is reported as missing, not
  satisfied.
- The quickstart's PyPI commands were not executed (they would download from
  the network and would resolve 0.1.0). Candidate verification used
  `python -m actseal` from the locked environment and is labelled as such in
  the page and the test module docstring.
- The security-policy skill's resolver helper (`launch_codex_security_mcp
  --helper resolve-security-md`) was not executed: the packet states Codex
  already resolved root `SECURITY.md` as the only applicable policy for
  `src/actseal`, the edit is the pre-approved bounded support update, and no
  new permission ceremony was authorized. Codex reviews the exact diff.
- `tests/docs` is collected by the default suite (`testpaths = tests`), so
  the new tests also run in ordinary CI. They are offline and complete in
  about one second; the subprocess examples use the locked interpreter only.
- No personal memory was written and no memory tool was used.

## Open issues

- Full Task 08 acceptance: README composition (PLAN section D order/copy),
  CHANGELOG, draft release notes, final application-example claims and asset
  references wait for accepted Task 07 and accepted static P1 assets.
- The published PyPI package is 0.1.0; the quickstart's three commands are
  the 1.x form and currently resolve 0.1.0. The 1.0.0 timing/output receipt
  and the README demo recording are gated on Tasks 20 and 14; the quickstart's
  version note must be refreshed at Task 21.
- Installed metadata still carries `Development Status :: 3 - Alpha` and
  version 0.1.0; the Production/Stable classifier and version bump are Codex
  packaging edits at integration (Task 19/20). The metadata test deliberately
  asserts only platform classifiers and extra-scoped dependencies.
- If Jev is cut to 1.1, `docs/providers.md`'s Jev section needs only its
  deadline sentence updated; if it ships, the CLI and Python pages need a
  PROVISIONAL section.
- Factual items outside my ownership, for Codex: `README.md` still says
  "v0.1.0 supports…", "Jev is deferred", uses `--from actseal==0.1.0` and lacks
  the Windows statement; `CHANGELOG.md` has no 1.0.0 entry;
  `docs/publishing.md` describes the 0.1.0 hardcoded workflow. None were
  edited.

## Spend

- API/credits: none (no model or API calls).
- Subscription meter: one Claude Code session; wall time approximately
  40 minutes of tool activity. No separate billing was used.
