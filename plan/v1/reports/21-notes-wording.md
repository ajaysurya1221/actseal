# REPORT 21 (release-notes wording)

Status: DONE for the owned scope. One file changed: `plan/v1/RELEASE_NOTES.md`,
7 insertions and 5 deletions, present-state wording only. No receipt fact,
hash, link or other document changed. No ACCEPT is claimed; no external
publication occurred; the GitHub release is not asserted to be public.

Executor: Claude Code, model `claude-fable-5-1`, effort high, normal
permissions, no subagent or model change. Branch
`claude/v1-21-release-receipts`, continued from
`5cebd9165c0a7658699d8f1e5442b73952345f85`. No product, test, asset, STATE,
review or earlier-report edit; no network, credential, merge, push or
publication command. No tool operation was denied.

## Commit

| Commit | Content |
| --- | --- |
| `e3690bb746be5018fa0298e34f71fe303ef558a7` | `plan/v1/RELEASE_NOTES.md` |
| (this report) | `plan/v1/reports/21-notes-wording.md` only |

## Change

The read-only review of `230462c` found that the release notes, which are
published verbatim after accepted CI, still described GitHub release
405628842 as a current draft in two places. Both are now
publication-neutral:

- **"Independent download comparison" row.** Now states that Codex
  downloaded the official PyPI wheel and sdist and the assets of release
  405628842 (the wheel, sdist, `SHA256SUMS` and release receipt the mirror
  job uploaded) while that release was still a draft, that both pairs are
  byte-identical and equal the tagged build checksums, and that publication
  of the release was gated on accepted post-publication documentation and
  media and green hosted CI (Task 22). The review citation and the
  independent receipt reviewer ACCEPT are unchanged.
- **Closing paragraph.** Now states that the release was created as a draft
  by the tagged run, that its publication was gated on the same conditions,
  and that its status at and after that event is recorded in the dated
  checkpoint of `plan/v1/FINAL_REPORT.md`. The launch-draft and social
  preview sentences are unchanged.

The remaining uses of "draft" in the notes are the launch posts (which
remain drafts by design) and the historical "created as a draft by the
tagged run". The FINAL_REPORT's dated checkpoint retains the actual pending
publication and is closed after the event by the bounded follow-up.

## Commands and exit codes

Separate, unwrapped commands from this worktree, run on the edited notes
before the commit above; the commit contains exactly that content.

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen python tools/check_release.py receipts` | no output | 0 |
| `uv run --frozen python tools/check_release.py docs` | no output | 0 |
| `uv run --frozen pytest tests/docs` | 111 passed in 1.05 s | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | no output | 0 |

These checks were not rerun after the commit itself; the committed bytes
are the checked bytes (`git diff --stat` showed only the one file before
staging, and the tree was clean after the commit).

## Deviations

None.

## Remaining gates

Codex's independent review, exact-head hosted CI, Task 22 publication of
the GitHub release, and the bounded follow-up that closes the FINAL_REPORT
checkpoint. None of those outcomes is predicted here.

## Spend

Unknown; not measured. No paid API, download or provider call.
