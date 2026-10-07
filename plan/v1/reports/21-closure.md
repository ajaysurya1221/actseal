# REPORT 21 (closure after the actual GitHub publication)

Status: DONE for the owned scope. Three documents updated to the actual
completed release; all four required checks exit 0 from this worktree. No
ACCEPT is claimed for this closing update; its independent review and
exact-head hosted CI are Codex's and are not predicted here. No push,
publication, receipt edit, STATE edit or credential operation occurred.

Executor: Claude Code, model `claude-fable-5-1`, effort high, normal
permissions, existing account and billing, no subagent or model
substitution. Branch `claude/v1-21-release-receipts` in worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, continued
from the parent merge `28a7bb487913e74496663fe53df491fa7c35600e`, which
carried `plan/v1/receipts/github-publication.json`, `claude-usage-final.json`
and `plan/v1/reviews/22.md`. Those were read as evidence; the attached
event receipt in the dispatch equals the committed file. No tool operation
was denied.

## Commit

| Commit | Content |
| --- | --- |
| `ada5fca29bea432e779c520c12f0b5c22bc3570e` | `plan/v1/FINAL_REPORT.md`, `plan/v1/LAUNCH.md`, `docs/publishing.md` (+68/-50) |
| (this report) | `plan/v1/reports/21-closure.md` only |

Not changed: `plan/v1/RELEASE_NOTES.md` (published verbatim, SHA-256
`9cc94039…`), README, tests, assets, schemas, registry, package, lock, tag,
receipts, STATE, reviews and every earlier report.

## Changes

**`plan/v1/FINAL_REPORT.md`.**

- Title line now states the release is live on PyPI and as the public
  GitHub release `v1.0.0`, with the canonical URL.
- The dated checkpoint replaces the former "still a draft / Task 22 open"
  language with the completed facts, keeping the reviewed CI head and the
  merge SHA distinct: PR 48 head `f26af8ff…` (runs 37607862358,
  37607886554) merged as `0a0a228…`; PR 49 head `814059a7…` (runs
  37609789928, 37609797286, all ten source and assets jobs SUCCESS) merged
  as `3c3a339…` at 10:54:59Z; release 405628842 published at
  2026-10-07T10:55:05Z, `draft` false, `prerelease` false, Latest, title
  "Actseal 1.0.0", notes byte-equal to `RELEASE_NOTES.md`; receipt
  `github-publication.json`; verification REVIEW 22. It states that this
  closing update's own review and CI are not claimed and that no second
  container run was made.
- "GitHub release" row lists the four uploaded assets with ids, sizes and
  abbreviated digests (wheel 618308471, sdist 618308469, release receipt
  618308475, `SHA256SUMS` 618308468), notes GitHub's automatic source
  archives, and records the public rendering observation (how-it-works
  1600×400 loaded in the notes; README recording 979×918 loaded).
- "Independent download comparison" row now says the release assets were
  downloaded while the release was then still a draft (history).
- "Hosted CI" row adds the PR 49 head and merge; "Receipts" row adds
  `github-publication.json` and `claude-usage-final.json`.
- Task 22 row: ACCEPT for the public release scope (REVIEW 22), with the
  integration of this closing update as the remaining review step; social
  upload optional, non-blocking, unclaimed.
- Known limits: the draft-release sentence is removed; the social preview
  is delivered with an optional, non-blocking, unclaimed upload; the launch
  post remains a draft and unsent.
- Spend: the dated 10:38:02 UTC observation and all its qualifications are
  retained; a sentence links `claude-usage-final.json` as a later terminal
  metadata snapshot that records its own cutoff, method and exclusions, is
  not an invoice, whose total this report does not restate, with Codex
  refreshing the final ledger before final review. Actual billed cost and
  credit change remain UNKNOWN; zero observed sprint Jev requests.
- "Next three steps after v1.0.0": exactly three post-release steps, the
  gated preregistered Jev audit (frozen inputs, effective permission,
  compatibility review), an independently reproduced application
  integration with held-out data, and the deferred P2 figures. The former
  Task 22 closure step is removed because the publication is complete.
- All failure and denial history, scope cuts and evidence limitations are
  retained unchanged.

**`docs/publishing.md`** (status only). The status note's last sentence
now records that the draft the run created was published on 7 October 2026
after the post-publication documentation was accepted, with the same four
assets and the accepted notes, citing `github-publication.json`. The
strings its tests forbid are absent.

**`plan/v1/LAUNCH.md`** (stays DRAFT, not posted). The header says the
release is public and the post is sent only on explicit request; the link
line adds the canonical release URL; the "not to be added" list drops the
no-release-link rule and notes the README recording is an illustrative
receipt.

## Commands and exit codes

Separate, unwrapped commands from this worktree on the edited files before
the commit; the committed bytes are the checked bytes (`git diff --stat`
showed only the three files, and the tree was clean after the commit).

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen python tools/check_release.py receipts` | no output | 0 |
| `uv run --frozen python tools/check_release.py docs` | no output | 0 |
| `uv run --frozen pytest tests/docs` | 111 passed in 1.15 s | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | no output | 0 |

A residual-wording scan over the three files found no "still a draft",
"Open:" or "awaiting" present-state phrase except the historical "(then
still a draft)" in the download-comparison row.

## Deviations

None from the dispatch.

## Remaining gates and limitations

- Codex's independent review and exact-head hosted CI for this closing
  update, then its merge; REVIEW 22 and STATE are Codex's.
- Codex's final ledger refresh before final review.
- Deferred to 1.1: the live Jev audit and the P2 figures. Social preview
  upload optional and unclaimed. Launch post unsent.

## Spend

Unknown; not measured by the executor. No paid API, network, provider or
model call, download or credential operation in this closure. The
committed usage observations predate this work and exclude it; actual
billed cost and Jev credit change remain UNKNOWN.
