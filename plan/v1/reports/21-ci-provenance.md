# REPORT 21 (CI provenance correction)

Status: DONE for the owned scope. One file changed, `plan/v1/FINAL_REPORT.md`,
2 insertions and 2 deletions, attribution only. No runtime, algorithm,
receipt, hash or other document changed. No ACCEPT is claimed; no hosted
CI is claimed for this documentation commit; nothing was pushed or
published; STATE and earlier reports are untouched.

Executor: Claude Code, model `claude-fable-5-1`, effort high, normal
permissions, no subagent or model change. Branch
`claude/v1-21-release-receipts`, continued from
`0e019d33d192dfd07ab600148268fc980c2f70fb`. No tool operation was denied.

## Commit

| Commit | Content |
| --- | --- |
| `a5094f79b310a1d4b61299ebaeeeeb0b95369655` | `plan/v1/FINAL_REPORT.md` |
| (this report) | `plan/v1/reports/21-ci-provenance.md` only |

## Change

The independent reviewer found that the final report's "Hosted CI" row
and its "Checks actually completed" table called `0a0a228` the head tested
by runs 37607862358 and 37607886554. Both runs report `headSha`
`f26af8ff43302020be5dbc8eeb6c497d089fdbc2`, the reviewed PR 48 head. The two
references now read: reviewed PR 48 head `f26af8ff…` passed ten source and
assets jobs in those two runs, then merged as
`0a0a2288bed813e9fcbf7116ef97294912ca04b1`. The checkpoint paragraph's
statement that the media merged as `0a0a228` after that acceptance and
those jobs, and every other merge or source reference, are truthful as
written and were not changed.

## Commands and exit codes

Separate, unwrapped commands from this worktree on the edited file before
the commit; the committed bytes are the checked bytes (`git diff --stat`
showed only this file, and the tree was clean after the commit).

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen python tools/check_release.py receipts` | no output | 0 |
| `uv run --frozen python tools/check_release.py docs` | no output | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | no output | 0 |

## Deviations

None.

## Remaining gates

Codex's independent review, exact-head hosted CI on the integrated
documentation, Task 22 publication of the GitHub release, and the bounded
follow-up that closes the FINAL_REPORT checkpoint. None is predicted here.

## Spend

Unknown; not measured. No paid API, download or provider call.
