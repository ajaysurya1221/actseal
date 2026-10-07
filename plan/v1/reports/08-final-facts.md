# REPORT 08-final-facts

Status: PARTIAL (accepted implementation facts finalized under amendment
V1-042; full Task 08 stays PARTIAL until the four architecture outputs
exist, final visual acceptance passes, the exact-head candidate CI is green
and the release rehearsal and blind final acceptance complete). Candidate
for Codex review; DONE is not ACCEPT. No v1 tag, publication, live Jev
result or final visual acceptance is claimed.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session,
run directly (no nested agents, product code, credential access, model
calls, merge, push or release). Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, branch
`claude/v1-08-readme-completion`, which Codex fast-forwarded from `710ae55`
to reviewed integration `b05aed85ccba6efee204a79c4662643ce952c6d2` before
this work; inspected first (clean tree, two approved registry entries
installed, `jev` admitted and registered behind `--experimental-provider`,
`examples/action_gate` present, nine committed figures, no architecture
outputs). Source fingerprint before and after:
`8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3`;
`git diff --stat` against `src/`, `examples/` and every committed SVG/PNG is
empty. The separately denied Task 13 merge and Task 06 live outcome were not
retried. Evidence was read, not edited, from root
`plan/v1/reviews/09-linux-agg.md`, `19-hosted-candidate-b05aed8.md`,
`reports/readme-ten-second-preflight.md`, `readme-viewport-observation.md`
and the merged tree's `plan/v1/STATE.md` and `CHANGE_LOG.md`.

## Commits (owned paths only)

| Commit | Files | Summary |
|---|---|---|
| `257b8bf` | `README.md`, `CHANGELOG.md`, `plan/v1/RELEASE_NOTES.md` | README provider row and scope paragraph name the PROVISIONAL Jev adapter behind `--provider jev --experimental-provider` (bring your own key, mocked tests only, no accepted live receipt). CHANGELOG: conformance covers fixture, mocked Laya and mocked Jev with the Task 03/19 cached-native checks completed; the example's producer and the 1.0.0 source are the two approved registry entries (V1-037); Jev is described as shipped PROVISIONAL with mocked-only evidence; the pending list is reduced to architecture, final visual acceptance and candidate CI/rehearsal. Release notes: "Conditional items" became "Decided implementation facts" (Jev included as PROVISIONAL; audit not run, live attempt stopped by a harness denial before any key read or `--execute`; example archive approved); the figures row names the committed/accepted assets and the single architecture failure at `b05aed8`; the blind-test row records the completed preflight with final public-state acceptance still `PENDING`; all publication-receipt rows stay `PENDING`. Draft/unpublished status kept. |
| `8b14653` | `docs/architecture.md`, `docs/dependencies.md`, `docs/providers.md` | Architecture: the stability manifest, versioning, migration and schemas are normative and CONTRACTS is the historical v0.1 record; the adapters row and provider paragraph include `experimental.providers.jev` as PROVISIONAL; resident-worker termination/invalidation is stated as Laya-specific, with fixture in-process and Jev as one in-process stdlib HTTPS attempt whose deadline is a socket timeout; the ADR 0009 rule is scoped to the native worker. Dependencies: Jev is a stdlib PROVISIONAL adapter with no dependency, not a "v2 adapter". Providers: dated statement that as of 7 October 2026 no live Jev request has been accepted as evidence (attempt stopped before any key read), and the stability manifest named as the normative boundary. |
| `3628a4d` | ADR 0004, 0015, 0017, 0018, 0019, 0020; `docs/assets/src/recording.md` | Status/history only; decision text unchanged. 0004 and 0015 gain dated status sections (PROVISIONAL Jev present, fallback execution still outside v1; the two approved producer/engine mappings, empty-until-integration wording made historical). 0017: retain-as-PROVISIONAL decision (V1-036), integrated opt-in scoped-accepted at Task 19 `b0031f5`, mocked and cached-native checks, no accepted live evidence, Jev producer not registered. 0018: offline ACCEPT `d3edbab`, candidate 3 approved, live attempt stopped by the harness before any key read, no journal or result. 0019: Task 03 (`212a1d6`, 177 + 5 cached native) and Task 19 (six cached native) native checks completed; Linux agg executed in hosted CI at `0e32c6c` (runs 37581140052/37581142565); candidate CI at `b05aed8` red only for architecture, final gate separate. 0020: accepted social pixels (Task 15 `fcdcfe4`, merged `7820dba`), Linux agg execution, blind first-screen preflight completed at `710ae55` with the viewport observation, architecture/final visual/recording pending. `recording.md`: only the bottom prerequisite paragraph updated (tools fetched, Linux agg executed; publication, capture and review pending). |
| `6132ade` | `tests/docs/test_policy_and_metadata.py`, `tests/docs/test_readme.py` | Dated Jev phrase assertion; README must name the PROVISIONAL opt-in and "no accepted live"; `ssl` imported at module load (see deviation 1). No assertion skipped or weakened; the architecture image test is untouched. |
| this commit | `plan/v1/reports/08-final-facts.md` | This report. |

## Task 08 done commands (final tree, before the report commit)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs` | **1 failed, 105 passed** in 1.12 s. The failure is `tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset`: README references uncommitted figure files `architecture-dark.svg`, `architecture-light.svg`, `architecture-mobile-dark.svg`, `architecture-mobile-light.svg`. Known, expected, not skipped. | 1 |
| `uv run --frozen python tools/check_release.py docs` | `docs gate has 1 unmet requirement(s): README.md links to missing file docs/assets/architecture-mobile-dark.svg` (first of the same four) | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |

Focused checks for the changed wording, run separately:

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs/test_policy_and_metadata.py -q -p no:cacheprovider` (isolated module) | 10 passed | 0 |
| `uv run --frozen ruff check tests/docs` | All checks passed | 0 |
| `uv run --frozen ruff format --check .` | 410 files already formatted | 0 |
| `uv run --frozen mypy --strict src tests` | Success: no issues found in 103 source files | 0 |
| `git diff --check` | no output | 0 |

The previously second known failure (the inherited provider assertion) no
longer exists at this head; Task 19 repaired it before the fast-forward.

## Deviations

1. **Import-order fix in a tests/docs module.** The first `pytest tests/docs`
   run at this head failed `test_providers_doc_distinguishes_stable_providers_from_provisional_jev`
   with `TypeError: function() argument 'code' must be code, not str`,
   raised from `ssl.py` while the test imported the Jev module. Cause: the
   autouse offline fixture in `tests/conftest.py` replaces `socket.socket`
   with a function; when `ssl` is first imported inside a test (via
   `http.client`), `class SSLSocket(socket)` subclasses that function. The
   full suite does not show it because `ssl` is already loaded by earlier
   modules, which is why the hosted candidate review saw no provider-test
   failure. The fix imports `ssl` at module load with an explanatory
   comment; no assertion changed. This is an import line, not a wording
   assertion, so it is reported here as a bounded deviation from the
   "corresponding wording assertions" ownership.
2. No other deviation. No capture procedure, helper, pin, asset, product
   code, normative signature/schema/statistical/registry content or earlier
   report was edited.

## Remaining gates (unchanged, visibly pending)

The four architecture outputs (Task 13; separately denied merge awaiting
the human's scoped answer); final visual acceptance and the blind final
public-state acceptance on the tagged README; the exact-head candidate CI
and release rehearsal; the pre-tag finalization gate; publication and its
receipts (Tasks 20/21); the genuine post-publication recording (Task 14).
No v1 tag or PyPI publication exists; no live Jev result exists.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
