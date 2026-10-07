# REPORT 08-token-expiry

Status: PARTIAL (narrow correction of REVIEW `0b46ce27dc59731cacd89ff102f08ce128329893`;
full Task 08 stays PARTIAL until the architecture outputs land, Task 19's
final provider facts are integrated, the rendered README is reviewed and the
blind ten-second test passes). Candidate for Codex review; DONE is not
ACCEPT. No publication or live claim.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same session,
worktree and branch `claude/v1-08-readme-completion`, run directly (no nested
executors, credentials, live calls, push or main merge). Only
`docs/publishing.md`, `tests/docs/test_publishing.py` and this report changed;
no asset, Task 19-owned file or other status assertion was edited.

## Correction

REPORT 08-readme-revision (repair 1) and commit `1932e05` stated that the
PyPI upload credential "expires with the job", and the regression test
enforced that sentence. That statement was wrong. The official primary
source, https://docs.pypi.org/trusted-publishers/, states that the minted
project-scoped API token is valid for 15 minutes from creation. REPORT
08-readme-revision is preserved unchanged as the historical incorrect
receipt; this report corrects it.

- `docs/publishing.md`, publish step 3, now reads: no PyPI API token is
  stored in the repository or its secrets; the job requests a short-lived
  GitHub OIDC token for its own run, and PyPI's Trusted Publishing exchanges
  that identity for a project-scoped API token that, per the linked official
  documentation, is valid for 15 minutes from creation. The job-lifetime
  claim is removed.
- `tests/docs/test_publishing.py::test_guide_describes_oidc_exchange_not_token_absence`
  now asserts the OIDC exchange, the project-scoped token, the verified
  "valid for 15 minutes from creation" lifetime and the official link, and
  asserts that the retracted "expires with the" wording is absent.

## Commands and results (final tree before commit)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen pytest tests/docs` | **2 failed, 103 passed** (the two known dependency failures below; no new failure) | 1 |
| `uv run --frozen python tools/check_release.py docs` | 1 unmet: `README.md links to missing file docs/assets/architecture-mobile-dark.svg` | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `uv run --frozen ruff check tests/docs` | All checks passed | 0 |
| `uv run --frozen ruff format --check .` | 361 files already formatted | 0 |
| `uv run --frozen mypy --strict src tests` | Success: no issues found in 94 source files | 0 |
| `git diff --check` | no output | 0 |

## Known dependency failures (unchanged, unaccepted, not edited)

1. `tests/docs/test_readme.py::test_every_image_resolves_to_a_committed_implemented_asset` and the docs gate: the four frozen architecture variants are absent and unregistered until Task 13 lands.
2. `tests/docs/test_policy_and_metadata.py::test_providers_doc_describes_jev_as_unshipped_and_experimental`: the inherited provider assertion conflicts with accepted Task 05's admitted `jev` identity; Task 19 repairs it atomically with the provider docs.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this CLI process; elapsed time unknown until Codex's
  stream result is available. Not estimated.
