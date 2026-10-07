# REPORT 08-packaged-release-notes

Status: PARTIAL (bounded wording correction under amendment V1-039 at root
commit `3ad6cc6`; full Task 08 stays PARTIAL until the architecture outputs
land, Task 19's final provider facts are integrated, the rendered README is
reviewed and the blind ten-second test passes). Candidate for Codex review;
DONE is not ACCEPT. No publication, hosted-CI or final-acceptance claim.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session,
worktree and branch `claude/v1-08-readme-completion`, from
`e90c4e6372723b01efab106f10a1ef7260a00a40`, run directly (no nested
executors, network, keys, merges or publication). Only `docs/publishing.md`,
`tests/docs/test_publishing.py` and this report changed. The Codex packaging
commit `dd1bafe7553e551f43dba7824921d350b313a82c` was read with
`git show dd1bafe:pyproject.toml` and not merged.

## Change

`docs/publishing.md` previously said the release notes, final report and
later documentation commit "are not part of the published distribution".
That was wrong for the source distribution: at `dd1bafe` the sdist
`only-include` list packages `plan/v1/RELEASE_NOTES.md`, `plan/v1/reports`,
`plan/v1/reviews` and `docs` (it does not package `plan/v1/FINAL_REPORT.md`
or `plan/v1/LAUNCH.md`).

The pre-tag finalization paragraph now distinguishes the two states: the
sdist packages the **pre-tag copies** of `plan/v1/RELEASE_NOTES.md`,
`plan/v1/reports/` and `plan/v1/reviews/` as listed in `pyproject.toml`, so
the draft inside the sdist is whatever that file says at the tag, with its
pending markers; the publication receipts are added afterwards in a later
documentation commit to the repository's release notes, the final report and
the GitHub release, and those additions cannot alter the already-tagged
commit or the already-uploaded wheel and sdist. No guarantee was broadened
and no publication is implied.

`tests/docs/test_publishing.py::test_guide_requires_pre_tag_documentation_finalization`
now asserts the retracted sentence is absent and the pre-tag-copy and
cannot-alter wording is present; the rest of the test is unchanged.

## Commands and results (final tree before commit)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs/test_publishing.py` | 6 passed | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `uv run --frozen ruff format --check docs/publishing.md tests/docs/test_publishing.py` | 2 files already formatted | 0 |
| `git diff --check` | no output | 0 |

The full `tests/docs` suite and `check_release.py docs` were not rerun for
this focused wording change; their last results (`96f4928`/`e90c4e6`) stand:
2 failed, 103 passed, and 1 unmet docs-gate requirement, both from the known
dependencies below. Nothing in this change touches those paths.

## Deviations

None. The sdist inventory was verified from the referenced commit rather
than from a build; no distribution was built here.

## Remaining gates

Unchanged: the four absent architecture variants (Task 13) and the inherited
Jev provider assertion (Task 19) keep `tests/docs` and the docs gate red;
Task 07 example integration; pre-tag documentation finalization;
`check_release.py docs` green on the integrated tree; exact-head hosted CI;
rendered README review; the blind ten-second test; publication receipts
(Tasks 20/21) and the genuine recording (Task 14). No v1 tag or publication
exists.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
