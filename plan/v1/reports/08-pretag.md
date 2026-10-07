# REPORT 08F (Task 08F: finalize immutable pre-tag documentation)

Status: DONE for the owned scope. All four done-when commands exit 0 when
run unwrapped. This is a documentation finalization only; it claims no tag,
PyPI install, attestation, recording, full combined suite, exact-head hosted
CI or final release acceptance. Codex independently reviews before
integration and closes the gates listed at the end before any tag.

Executor: the same Claude Code documentation session, model
`claude-fable-5-1`, effort high, normal permissions, existing account and
billing, no subagent. Branch `claude/v1-08-pretag` in worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, continued
from base `ff0f66cbf802309dea06e98c48a9c3abaa441cca`. No merge, push, tag,
network, download, key or provider access; no product code, test, asset,
schema, packaging, lockfile, other-report, state or review edit. No tool
operation was denied.

## Commits

| Commit | Content |
| --- | --- |
| `0363124922637b944a2af52230518425e7503e22` | README, CHANGELOG, release notes, four current-status docs, six ADRs |
| (this report) | `plan/v1/reports/08-pretag.md` only |

Thirteen files changed in `0363124` (180 insertions, 104 deletions):
`README.md`, `CHANGELOG.md`, `plan/v1/RELEASE_NOTES.md`,
`docs/architecture.md`, `docs/threat-model.md`, `docs/dependencies.md`,
`docs/versioning.md`, `docs/decisions/0004-…`, `0015-…`, `0016-…`,
`0017-…`, `0019-…`, `0020-…`. The implementation fingerprint
`8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3` is
untouched: no file under `src/`, `tests/`, `docs/assets/`, `docs/schemas/`
or packaging changed.

## Receipts cited (supplied at dispatch and in accepted reviews)

- Implementation fingerprint `8f316f67…98ed3`, unchanged from the retained
  candidate `5e7931a` through every later documentation and asset commit.
- Task 13/13R: ACCEPT for source, generated static assets and local checks
  at `77a13bd` (`plan/v1/reviews/13-readability.md`): byte-identical
  regeneration of twelve SVGs and `social.png`, 337 visual tests, 3,898
  ordinary tests, strict typing, hooks, and all twelve variants viewed as
  actual resvg pixels at 838 px desktop and 254 px mobile.
- Task 08R/08R2: ACCEPT for the responsive README at `95e17b4`
  (`plan/v1/reviews/08-responsive.md`).
- Combined locally at `c1b5481`: parent 590 docs/visual checks, docs gate,
  hooks and 16 README image references regenerating (STATE, V1 Task 08/19
  rows).
- Blind first-screen preflight at `710ae55`
  (`plan/v1/reports/readme-ten-second-preflight.md`,
  `readme-viewport-observation.md`).
- Historical, kept as dated history: hosted CI at `b05aed8` and `5e7931a`
  red solely for the then-absent architecture figures; Task 13 harness
  denials; the unrun Task 06 live audit (no key read, no request, no
  journal, no verdict); the 14:00 IST cut activation superseded by V1-049.

## What changed, per acceptance criterion

**Candidate/unreleased/missing-architecture claims resolved.**

- `CHANGELOG.md`: heading `## v1.0.0 — unreleased candidate` is now
  `## v1.0.0` (the docs gate's heading regex still matches). The opening
  paragraph states the implementation fingerprint and that tag and
  publication receipts live in the release notes. The figures bullet now
  describes the three P1 figure groups at the measured widths plus the
  social preview, names the P2 figures as not part of 1.0.0, and places the
  genuine recording after publication under Decision 2A. The Jev bullet
  records that the optional live audit was not run (no key, request, journal
  or verdict). The trailing "Pending before this entry is final" paragraph is
  removed, as `docs/publishing.md` requires before the tag.
- `plan/v1/RELEASE_NOTES.md`: title and status drop the DRAFT marker. A new
  "Pre-publication receipts (final)" table cites the implementation
  fingerprint and registry, the accepted static figures at `77a13bd`, the
  responsive README at `95e17b4` with the `c1b5481` combined checks, the
  blind preflight at `710ae55`, and the native receipts. The
  "Release-pipeline receipts" table keeps only named placeholders: source
  commit/tag, distribution hashes and sizes, workflow run and artifact id,
  verify matrix, tagged `assets` job, attestation inspection,
  clean-container install, PyPI classifier, and the post-PyPI recording.
  The audit paragraph states the 959-case preregistration is not a run
  receipt; a figures paragraph records P1 accepted and P2 not implemented.
  `source_commit` and the how-it-works figure are retained for the receipts
  gate; the PyPI link remains a named post-publication placeholder.
- `README.md`: one change, the navigation label "release notes (draft until
  published)" becomes "release notes", which `test_readme` requires once the
  notes carry no DRAFT marker. Opening order, copy, quickstart, media paths,
  source order, alt text and evidence-boundary wording are unchanged.
- `docs/architecture.md`: "the 1.0.0 candidate's receipts" becomes "the
  1.0.0 reports and reviews", with the fingerprint and a pointer that the
  README architecture figure draws the seven groups from this source.
- `docs/versioning.md`: registry row "the 1.0.0 candidate source itself"
  becomes "the 1.0.0 source itself".
- `docs/dependencies.md`: a dated 7 October status paragraph states the pins
  and lock are unchanged in the 1.0.0 source and labels the milestone
  sections as dated history; three "pending/release-candidate checks"
  sentences now point to the task reports and release notes. The T30
  milestone paragraphs still say "candidate" for their own 6 October commit;
  that is the milestone's historical wording, now labelled as history.

**Threat model.** `docs/threat-model.md` no longer says "Jev and actual
fallback execution remain outside v1". It states that the experimental Jev
adapter is included in 1.0 as a PROVISIONAL explicit opt-in with a
vendor-reported identity, mocked-transport evidence only and no key in
evidence, and that autonomous fallback execution is outside 1.0. All
evidence limits and the fallback-removes-ACT rule are retained.

**ADR status paragraphs.**

- 0004: status notes that "deferred to v2" was superseded for the adapter
  but not for fallback execution; mocked-transport evidence only; live audit
  not run; autonomous fallback outside 1.0.
- 0015: "1.0.0 candidate" wording becomes 1.0.0; "No v1 tag or publication
  has occurred" becomes a statement that the fingerprint is unchanged and
  the tag receipts are in the release notes.
- 0016: status and evidence record the complete static-asset inputs at
  `77a13bd`/`95e17b4`, the PR 18 branch-workflow rehearsal as a rehearsal,
  and that the tagged pipeline's receipts are the release notes', not the
  ADR's.
- 0017: status is "included in 1.0.0 as PROVISIONAL", retained by V1-049
  after the superseded cut trigger; the earlier red hosted CI is labelled
  historical; the live-evidence bullet records the unrun audit with no
  invented key, call, journal or verdict.
- 0019: "candidate" wording resolved; the `b05aed8`/`5e7931a` red CI is
  labelled historical with the later `77a13bd`/`95e17b4` acceptance; the
  tagged commit's matrix result is deferred to the pipeline receipts.
- 0020: status bullet lists all four P1 groups accepted at the measured
  widths, P2 not implemented, recording post-PyPI. The old "Pending"
  evidence bullet becomes a historical-blocker-then-closure bullet
  (harness denial, manual merges V1-050, acceptance at `77a13bd`, combined
  checks at `c1b5481`), plus P2, recording and final-acceptance bullets.
  The 08R addendum's status paragraph now records that Task 13R completed.

**Not claimed anywhere.** A `v1.0.0` tag, a public PyPI install,
attestation inspection, the genuine recording, a green full combined suite,
exact-head hosted CI, the release rehearsal, the final repository
first-screen review, any live Jev receipt, any P2 figure, or any numerical
performance or model-accuracy figure.

## Commands and exit codes

Run as separate, unwrapped commands (no pipes, `tail`, `head` or `echo`),
on the final content before the commit; the docs suite, docs gate and diff
check were rerun after the last ADR edit with identical results.

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen pytest tests/docs` | 110 passed in 1.07 s | 0 |
| `uv run --frozen python tools/check_release.py docs` | no output | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | no output | 0 |

The docs suite is now fully green on this branch because the base `ff0f66c`
already carries the accepted architecture SVGs; the earlier
missing-architecture failure recorded in REPORTs 08R/08R2 is history, not
an exclusion. No test was edited.

## Deviations

None from the packet. Two judgement calls to review:

- The CHANGELOG `v1.0.0` heading carries no date, unlike `v0.1.0`, because
  no release date exists; the date belongs with the tag receipt.
- `docs/dependencies.md` keeps the word "candidate" inside its dated 6
  October T30 milestone paragraphs (the milestone commit `17ed087`), now
  labelled as history by the new status paragraph, rather than rewriting
  the milestone narrative.

## Remaining release gates (for Codex to close before tagging)

- **Final repository first-screen gate:** a fresh blind ten-second review of
  the integrated README on the actual public repository view, with the
  responsive variants selected by a real browser. Explicitly open; the
  release notes cite only the `710ae55` preflight.
- Full combined test suite and exact-head hosted CI on the integrated head
  (in progress at dispatch; not claimed here).
- Release rehearsal and the candidate gate on the final clean tree.
- Codex's independent review of `0363124` and this report.
- After the tag: the named pipeline receipts in the release notes (Task
  20/21), the post-PyPI recording under Decision 2A, and the manual social
  preview upload.

## Spend

Unknown; not measured. The packet estimate was 30 minutes.
