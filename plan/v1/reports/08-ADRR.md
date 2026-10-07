# REPORT 08-ADRR

Status: PARTIAL (wording repair of ADRs 0017 to 0020 under V1-026; full
Task 08 still depends on accepted Task 07, accepted static P1 assets, the
final README and release notes). Candidate for Codex review; DONE is not
ACCEPT. No release, media or live-audit claim is made.

Executor: Claude Code, model `claude-fable-5-1`, effort high, same direct
session and ownership as REPORT 08-ADR. Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, branch
`claude/v1-08-reference-preparation`, reviewed commit
`4a235d6d6de9dba8ab7bbd15450a75325e2fe81d` (independent plus parent review:
REVISE, wording only). Nothing pushed, merged, tagged or released. No
product, test, README or other doc edit; no nested executor, external path
read, key, network, tool, render, preview or package operation. REPORT
08-ADR is preserved unchanged.

## Corrections applied

| # | ADR | Finding | Repair |
|---|---|---|---|
| 1 | 0017 | Consequence claimed `records.PROVIDERS` stays `fixture`/`laya` until Task 19, which is wrong for the reviewed Jev branch. | Now states that on the reviewed candidate branch `jev` is already admitted in serialized records and published schemas (V1-011, V1-021), that stable default CLI choices and runner registration remain `fixture`/`laya` until Task 19 integrates the experimental flag, and that accepted main carries neither change. No claim that Task 19 still needs an enum change or that Jev already ships. |
| 2 | 0018 | Interrupted and complete-but-late runs were conflated as "incomplete/ERROR". | Completeness and timeliness are now separate: an interrupted run is incomplete/ERROR with no ordinary bundle; a complete-but-late run makes the overall audit receipt ERROR with `budget_exceeded` while its complete verification bundle is still published and retains its independently computed verdict. A complete late bundle is never called incomplete and its verdict is never changed to the overall ERROR. |
| 3 | 0020 | Single-renderer provenance was claimed for every committed file; rationale claimed to keep GPL/font licences out of the distributed package; how-it-works status was stale. | Provenance restricted to generated visual outputs (SVG variants, social PNG, demo GIF); sources are authored, fonts upstream at pinned hashes, raw `.cast` genuinely recorded and only validated/converted. Rationale now states zero runtime dependency and that the sdist includes `docs/` and may carry notices and font material under their own licences; no categorical licence exclusion. How-it-works: earlier REVISE followed by source/semantic ACCEPT at `f712dae`, actual rendered review still pending, not finally accepted. |
| 4 | 0019 | Native receipts were attributed to "Task 03". | Now attributed to the historical v0.1 milestones recorded in `docs/providers.md` (T30 provider/normalizer milestone with macOS cached-native tests and the Linux native workflow run, plus the native CLI receipt). Notes the v1 Task 01 baseline passed independently before the later cached-native denial, and that the v1 Task 03 native rerun is still pending. No new counts or current acceptance invented. |
| 5 | 0017 | "One attempt with the fixed collection deadline" implied a universal hard wall-clock bound; key-exclusion wording implied sanitizing arbitrary encoded secrets. | Now: one attempt with a validated per-request timeout, callers keep the fixed schedule/deadline, transport timeout behaviour bounded as specified but not a universal wall-clock bound on OS/network operations. Key and header exclusion is scoped to captures, evidence, logs, diagnostics and locks the adapter owns; the reviewed guard detects the literal key and a limited set of JSON escapings, not every possible encoding in a malicious provider body, so raw bodies remain data to review. Rationale kept compact. |

## Checks

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen ruff format --check .` | 269 files already formatted (Markdown fences included) | 0 |
| `git diff --check` | no output | 0 |
| `git status --short` before staging | exactly the four ADR files modified | 0 |
| relative link targets in the four ADRs | same nine targets as REPORT 08-ADR plus 0017 itself; all exist | 0 |

Not run, as allowed for prose-only corrections: docs test suite, product
tests, native tests, mutations, renderer, previews, package installation,
network. No test mirroring the prose was added. `tools/check_release.py
docs` remains absent on this branch and is still reported as not run.

## Deviations

None.

## Open issues

Unchanged from REPORT 08-ADR: ADRs 0017/0018 are revisited at the Jev
inclusion decision; 0020's pending list closes only with accepted assets and
the post-publication recording; full Task 08 dependencies and the
out-of-ownership README/CHANGELOG/metadata items remain.

## Spend

- API/credits (live provider usage): none.
- Claude subscription: this resumed CLI process; elapsed time unknown until
  Codex's stream result is available. Not estimated.
