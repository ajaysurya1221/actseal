# REPORT 08-publication-state

Status: PARTIAL (bounded test correction of REVIEW `96f49288ac8bc0bac9318f441171d3e1183ea02a`;
full Task 08 stays PARTIAL until the architecture outputs land, Task 19's
final provider facts are integrated, the rendered README is reviewed and the
blind ten-second test passes). Candidate for Codex review; DONE is not
ACCEPT. No final rendered, blind-test, hosted-CI or publication claim.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session,
worktree and branch `claude/v1-08-readme-completion`, run directly (no nested
executors, credentials, model calls, push or main merge). Only
`tests/docs/test_readme.py`, `tests/docs/test_publishing.py` and this report
changed; no document, asset, product, Task 19 or packaging file was edited.
Earlier reports are preserved unchanged.

## Finding and correction

Two of my new tests enforced temporary draft wording on mutable publication
documents, so a truthful pre-tag finalization would have broken permanent
tests:

- `test_readme.py` required the navigation label "release notes (draft until
  published)" and the word `DRAFT` inside `plan/v1/RELEASE_NOTES.md`.
  Renamed to `test_navigation_links_the_release_notes_absolutely_and_labels_their_state`:
  it still requires an absolute `blob/main/plan/v1/RELEASE_NOTES.md` link
  whose target exists and whose label starts with "release notes", and now
  requires the label's draft wording to equal the notes' actual state (the
  `DRAFT` status marker present or absent). Neither state is forced on the
  notes; both the current draft and a finalized release pass.
- `test_publishing.py::test_guide_requires_pre_tag_documentation_finalization`
  required the CHANGELOG's temporary pending paragraph to stay forever. That
  assertion is removed with an explanatory docstring; the test keeps the
  normative pre-tag gate in `docs/publishing.md` and the permanent
  `source_commit` receipt field name in the release notes.

The current documents are unchanged and accurately remain drafts. No skip,
blanket exclusion or removal of a required link or existence check.

## Commands and results (final tree before commit)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs` | **2 failed, 103 passed** (the two known dependency failures below; no new failure) | 1 |
| `uv run --frozen python tools/check_release.py docs` | 1 unmet: `README.md links to missing file docs/assets/architecture-mobile-dark.svg` | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `uv run --frozen ruff check tests/docs` | All checks passed | 0 |
| `uv run --frozen ruff format --check .` | 362 files already formatted | 0 |
| `uv run --frozen mypy --strict src tests` | Success: no issues found in 94 source files | 0 |
| `git diff --check` | no output | 0 |

## Known dependency failures (unchanged, unaccepted, not edited)

1. `tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset` and the docs gate: the four frozen architecture variants are absent and unregistered until Task 13 lands.
2. `tests/docs/test_policy_and_metadata.py::test_providers_doc_describes_jev_as_unshipped_and_experimental`: the inherited provider assertion conflicts with accepted Task 05's admitted `jev` identity; Task 19 repairs it atomically with the provider docs.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
