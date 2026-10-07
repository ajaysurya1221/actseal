# REPORT 08-final-facts-correction

Status: PARTIAL (bounded correction of REVIEW 08 "final implementation
facts" at `9519324762633375cf4ba644d2f9fd179b37c1c4`; full Task 08 stays
PARTIAL until the four architecture outputs exist, final visual acceptance
passes, the exact-head candidate CI is green and the release rehearsal and
blind final acceptance complete). Candidate for Codex review; DONE is not
ACCEPT. No v1 tag, publication, live Jev result or final visual acceptance
is claimed. REPORT 08-final-facts is preserved unchanged as a dated snapshot.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session,
worktree `/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`,
branch `claude/v1-08-readme-completion`, run directly (no nested agents,
product code, credentials, provider calls, merge, push or release). Source
fingerprint unchanged (`8f316f67…98ed3`); `git diff --stat` against `src/`,
`examples/` and every committed SVG/PNG is empty. Root state, reviews and
other lanes' assets were not edited.

## Corrections

1. **Stale earlier status clauses marked historical.** ADR 0017's
   Consequences bullet no longer says Task 19 has yet to integrate the flag
   or that documentation describes conditional preparation; it states the
   integrated opt-in and labels the earlier wording "Historical status,
   superseded", pointing to the dated evidence section. ADR 0019's
   Consequences bullet keeps the rule that native paths need their own
   cached-native receipt but labels the "currently pending" clause historical
   and points to the completed Task 03/19 checks, with the final candidate
   gate kept separate. Decisions and dated evidence are unchanged.
2. **Transient permission history removed from public docs.** ADR 0017,
   ADR 0018 (status line and evidence), ADR 0004's status note,
   `docs/providers.md` and `plan/v1/RELEASE_NOTES.md` no longer narrate a
   single dispatched attempt or its `.env` preflight denial. Each now carries
   a concise dated statement (as of 7 October 2026): live collection has not
   begun, no key read, no `--execute` call, no journal or result, and no live
   Jev result is accepted as evidence, with the chronology delegated to the
   Task 06 operational receipts under `plan/v1/`. ADR 0020 now says the
   architecture merge is blocked by an effective harness permission gate
   that standing human approval does not change, not that a user answer is
   awaited. Architecture, final visual acceptance and full release gates stay
   visibly pending.
3. **Date-pinned absence assertions removed from tests.**
   `tests/docs/test_policy_and_metadata.py` now requires a labelled, dated
   `Verification status (as of ` statement in `docs/providers.md` rather than
   the fixed "no live … accepted" sentence; the experimental opt-in,
   `JEV_API_KEY`, mocked-transport, `replay` never imports, `--offline`,
   `--responses`, may-change wording, stale-phrase rejections and stability/
   CLI checks are unchanged. `tests/docs/test_readme.py` requires the README
   to name the PROVISIONAL opt-in and state the live-evidence status (the
   word "live") instead of the phrase "no accepted live". A future honest
   live receipt no longer fails the suite; no trust-boundary check was
   loosened.

The module-level `ssl` preload in `test_policy_and_metadata.py` (commit
`6132ade`) is retained as reviewed and accepted; it is the only test import
inside this scope, and the deviation recorded in REPORT 08-final-facts
stands.

## Task 08 done commands (final tree, before the report commit)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs` | **1 failed, 105 passed** in 1.07 s; the failure is the known `test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset` (four uncommitted architecture variants). Not skipped. | 1 |
| `uv run --frozen python tools/check_release.py docs` | `docs gate has 1 unmet requirement(s): README.md links to missing file docs/assets/architecture-mobile-dark.svg` | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |

Focused checks for the changed files:

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs/test_policy_and_metadata.py tests/docs/test_readme.py -q -p no:cacheprovider` | 1 failed (the same architecture test), 19 passed | 1 |
| `uv run --frozen ruff format --check .` | 411 files already formatted | 0 |
| `git diff --check` | no output | 0 |

## Commits

| Commit | Files |
|---|---|
| docs correction | `docs/decisions/0004`, `0017`, `0018`, `0019`, `0020`, `docs/providers.md`, `plan/v1/RELEASE_NOTES.md` |
| test correction | `tests/docs/test_policy_and_metadata.py`, `tests/docs/test_readme.py` |
| report | `plan/v1/reports/08-final-facts-correction.md` |

Exact hashes are in `git log`; REPORT 08-final-facts and all earlier
reports are untouched.

## Deviations

None beyond the already reviewed `ssl` preload.

## Remaining gates

Unchanged: architecture outputs (effective harness gate), final visual
acceptance and blind final acceptance on the tagged README, exact-head
candidate CI and release rehearsal, the pre-tag finalization gate,
publication receipts (Tasks 20/21), the genuine recording (Task 14). No v1
tag or publication exists; no live Jev result exists.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
