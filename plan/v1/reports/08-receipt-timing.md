# REPORT 08-receipt-timing

Status: PARTIAL (one precise correction of REVIEW 08 at
`6de96a8` under V1-039; full Task 08 stays PARTIAL until the architecture
outputs land, Task 19's final provider facts are integrated, the rendered
README is reviewed and the blind ten-second test passes). Candidate for
Codex review; DONE is not ACCEPT. No publication or final-acceptance claim.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session,
worktree and branch `claude/v1-08-readme-completion`, run directly (no other
edits, merge, key, network or publication). Only `docs/publishing.md`,
`tests/docs/test_publishing.py` and this report changed. Historical reports
and reviews are unchanged.

## Change

The pre-tag finalization paragraph said the release notes may carry
placeholders for "receipts that cannot exist before the upload" and then
listed the distribution hashes and sizes and the workflow run and artifact
ids, which in fact exist once the tagged `build` job has run, before any
upload. The sentence now reads: placeholders for "the final release
receipts populated as the tagged release pipeline completes", split into
build-time values that exist after the tagged `build` job but before any
upload (distribution hashes and sizes, workflow run and artifact ids) and
post-publication values that exist only after the upload (attestation
inspection, PyPI install and smoke results, the genuine demo recording).
The pre-tag final-facts requirement, the "no other marker" rule and the
immutable-bytes distinction are unchanged; nothing else was rewritten.

`tests/docs/test_publishing.py::test_guide_requires_pre_tag_documentation_finalization`
asserts the new phrase, the absence of the retracted one, and each receipt
in its correct timing group, preserving the earlier meaning.

## Commands and results (final tree before commit)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs/test_publishing.py` | 6 passed | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `uv run --frozen ruff format --check docs/publishing.md tests/docs/test_publishing.py` | 2 files already formatted | 0 |
| `git diff --check` | no output | 0 |

The full `tests/docs` suite and `check_release.py docs` were not rerun for
this focused wording change; their last results stand with the same two
known dependency failures (architecture variants, Task 13; Jev provider
assertion, Task 19).

## Deviations

None.

## Remaining gates

Unchanged from REPORT 08-finalization-clarity. No v1 tag or publication
exists.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
