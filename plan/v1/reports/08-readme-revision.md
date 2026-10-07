# REPORT 08-readme-revision

Status: PARTIAL (repair of REVIEW 08 at `8d818a696c37ee357f8c61977ae6bbfb4f18c80e`;
full Task 08 stays PARTIAL until the architecture outputs land, Task 19's
final provider facts are integrated, the actual rendered README is reviewed
and the blind ten-second test passes). Candidate for Codex review; DONE is
not ACCEPT. No publication, live or final-acceptance claim.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same docs
worktree and branch `claude/v1-08-readme-completion`, run directly (no nested
agents, account/billing switch, key or `.env` access, push, main merge or
publication). Task 19-owned files, inherited assertions and all assets are
unchanged; image bytes untouched.

## Repairs (owned paths only)

| # | Finding | Repair |
|---|---|---|
| 1 | `docs/publishing.md` said "No token or secret is involved". | Replaced with the precise mechanism: no PyPI API token is stored in the repository or its secrets; the `publish` job requests a short-lived GitHub OIDC token for its own run, PyPI Trusted Publishing exchanges that identity for a temporary upload credential scoped to the project, and the credential expires with the job; the pinned PyPA action performs the exchange. |
| 2 | Candidate/pending CHANGELOG wording was left for Task 21, which cannot change tagged bytes. | `docs/publishing.md` step 1 gains a **Pre-tag documentation finalization** gate: before the tag, every unreleased/candidate/pending/conditional statement in `CHANGELOG.md`, `README.md` and `docs/`, and the ADR status paragraphs, must be resolved to the shipped facts; only publication receipts are added afterwards, to `plan/v1/RELEASE_NOTES.md`, the final report and a later documentation commit, which are not part of the published distribution. `CHANGELOG.md`'s pending paragraph now states the same rule; `plan/v1/RELEASE_NOTES.md`'s status paragraph states that its conditional sections are resolved before the tag and only receipts follow publication. The "unreleased candidate" heading itself is preserved until the final facts arrive, as instructed. |
| 3 | README navigation lacked the release-notes link; hero alt text omitted the drawn evidence-limit caption. | Navigation row now links `https://github.com/ajaysurya1221/actseal/blob/main/plan/v1/RELEASE_NOTES.md` as "release notes (draft until published)". The hero `<img alt>` now ends with the caption already present in the SVG's `<desc>`: "Caption: Replay cannot authenticate responses, prove inference occurred, or establish label truth." No image byte changed. |
| 4 | Release-notes draft named the receipt field `source.commit`. | Corrected to `source_commit`, matching `tools/check_release.py`'s build and release receipts. |
| 5 | ADR 0017 did not separate completed native checks from pending revalidation. | Evidence/status now records that the five cached-native tests passed independently at `c2e27d2` with the 390 focused offline tests (STATE, Task 05 row), that this covers the reviewed Task 05 source only, and that Task 19's integration changes source and needs its own native revalidation before acceptance. Decision text unchanged. |

New regression tests, all passing: `test_readme.py::test_navigation_links_the_draft_release_notes_absolutely` (absolute link present, target file exists and is marked DRAFT) and `::test_hero_alt_text_states_the_three_evidence_limits` (the three limits and the exact SVG caption appear in the hero alt text); `test_publishing.py::test_guide_describes_oidc_exchange_not_token_absence` (old sentence absent, OIDC/temporary-credential wording present) and `::test_guide_requires_pre_tag_documentation_finalization` (gate text in the guide, the CHANGELOG rule, `source_commit` in and `source.commit` out of the release notes).

## Commands and results (final tree before commit)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs` | **2 failed, 103 passed** (the two known dependency failures below; no new failure) | 1 |
| `uv run --frozen python tools/check_release.py docs` | 1 unmet: `README.md links to missing file docs/assets/architecture-mobile-dark.svg` (first of the four absent architecture outputs) | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `uv run --frozen ruff check tests/docs` | All checks passed | 0 |
| `uv run --frozen ruff format --check .` | 360 files already formatted | 0 |
| `uv run --frozen mypy --strict src tests` | Success: no issues found in 94 source files | 0 |
| `git diff --check` | no output | 0 |

Intermediate, fixed before commit without weakening: one Ruff E501 wrap in
the new hero-alt test, and one new assertion that compared against wrapped
prose (now whitespace-collapsed), which briefly failed as a third test.

## Known dependency failures (unchanged, not edited)

1. `tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset` and the docs gate: the four frozen architecture variants are absent and unregistered until Task 13 lands.
2. `tests/docs/test_policy_and_metadata.py::test_providers_doc_describes_jev_as_unshipped_and_experimental`: the inherited provider assertion conflicts with accepted Task 05's admitted `jev` identity; Task 19 repairs it atomically with the provider docs.

## Gates still pending for full Task 08

Accepted architecture outputs; Task 19 final provider facts and the
resulting README/provider wording; Task 07 example integration; the pre-tag
documentation finalization above; `check_release.py docs` green on the
integrated tree; exact-head hosted CI; actual rendered README review; the
blind ten-second test with saved prompt, screenshot hash and answer;
publication receipts (Tasks 20/21) and the genuine recording (Task 14).

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
