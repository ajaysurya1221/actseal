# REPORT 08-finalization-clarity

Status: PARTIAL (bounded clarification of REVIEW 08 "Packaged release notes"
at `89e7879b30ffc25867c1ac33d0fef8389e975d2e`, source `3523ad2`, under
V1-039; full Task 08 stays PARTIAL until the architecture outputs land,
Task 19's final provider facts are integrated, the rendered README is
reviewed and the blind ten-second test passes). Candidate for Codex review;
DONE is not ACCEPT. No final Task 08 ACCEPT, hosted-CI or publication claim.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session,
worktree and branch `claude/v1-08-readme-completion`, run directly (no
merges, other files, product, visuals, credentials, publication or bypass).
Only `docs/publishing.md`, `tests/docs/test_publishing.py` and this report
changed. Historical reports and reviews are unchanged.

## Change

The pre-tag finalization paragraph in `docs/publishing.md` previously let the
packaged release-notes draft carry "whatever that file says at the tag, with
its pending markers". It now:

- names `plan/v1/RELEASE_NOTES.md` explicitly, alongside `CHANGELOG.md`,
  `README.md` and `docs/`, as an input that must be resolved to the shipped
  facts before the tag;
- requires the release notes at the tag to state the final implementation,
  scope and inclusion facts (Jev, example, benchmark, figures);
- permits **only** named placeholders for publication receipts that cannot
  exist before the upload: distribution hashes and sizes, workflow run and
  artifact ids, the attestation inspection, the post-publication install and
  smoke results, and the genuine demo recording; no other draft, candidate
  or pending marker may remain;
- states that historical reports and reviews under `plan/v1/` keep their
  original content;
- preserves the distinction that post-publication additions go to the
  repository's release notes, the final report and the GitHub release and
  cannot alter the already-tagged commit or the uploaded wheel and sdist.

`tests/docs/test_publishing.py::test_guide_requires_pre_tag_documentation_finalization`
now asserts the release-notes finalization requirement, the absence of the
broad "with its pending markers" permission, the narrow named-placeholder
allowance (each receipt category named) and the "no other marker" sentence.
It does not force published-state language onto the current draft, which
accurately remains a draft until the pre-tag finalization step; the
state-tracking README link test from `cf614ed` is unchanged.

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

Unchanged from REPORT 08-packaged-release-notes: architecture outputs,
Task 19 provider facts, Task 07 example integration, the pre-tag
finalization itself, a green docs gate on the integrated tree, exact-head
hosted CI, rendered README review, the blind ten-second test, publication
receipts (Tasks 20/21) and the genuine recording (Task 14). No v1 tag or
publication exists.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
