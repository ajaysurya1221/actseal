# REPORT 08-ADRR2

Status: PARTIAL (final narrow wording correction to ADR 0018 under V1-026;
full Task 08 still depends on accepted Task 07, accepted static P1 assets,
the final README and release notes). Candidate for Codex review; DONE is not
ACCEPT. No release, media or live-audit claim is made.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same direct
session and ownership as REPORTs 08-ADR and 08-ADRR. Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, branch
`claude/v1-08-reference-preparation`, reviewed commit
`99d0682a7b470f45a98371faf06123db23f1c37b` (independent and parent review:
all prior areas fixed; one remaining wording item). Nothing pushed, merged,
tagged or released. No product, test or other doc edit; no network, key,
tool, preview or cache operation. REPORTs 08-ADR and 08-ADRR are preserved
unchanged.

## Finding and repair

ADR 0018 conflated overall 959-case audit completeness with the eligibility
of the 639-record verification bundle. The one affected bullet was replaced
with the supplied rule, in prose: completeness and timeliness are separate;
an incomplete audit or a collection-budget violation makes the overall audit
receipt ERROR with every scheduled case accounted for; an incomplete
verification inventory cannot produce an ordinary verification bundle; a
complete, valid verification inventory may produce its ordinary bundle and
retains its independently computed verdict even if the wider audit is
incomplete or late; never shrink or reseal the schedule, fabricate missing
captures, or replace the bundle verdict with the overall audit status; the
eligibility depends on the 639 verification records, not on all 959 cohort
captures. No other line of the ADR changed.

## Checks

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen ruff format --check .` | 270 files already formatted (Markdown fences included) | 0 |
| `git diff --check` | no output | 0 |
| `git status --short` before staging | exactly `docs/decisions/0018-finite-benchmark-audit.md` modified | 0 |

Not run, as allowed for a prose-only edit: docs test suite, product tests,
native tests, mutations, renderer, previews, package installation, network.
No test mirroring the prose was added. `tools/check_release.py docs`
remains absent on this branch and is still reported as not run.

## Deviations

None.

## Open issues

Unchanged from REPORT 08-ADRR.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this resumed CLI process; elapsed time unknown until
  Codex's stream result is available. Not estimated.
