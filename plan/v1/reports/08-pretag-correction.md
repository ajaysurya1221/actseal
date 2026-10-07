# REPORT 08F2 (Task 08F2: correct pre-tag documentation review findings)

Status: DONE for the owned scope. All four done-when commands exit 0 when
run unwrapped. REPORT 08F (`plan/v1/reports/08-pretag.md`) is preserved
unchanged; this report is additive. No full release ACCEPT, tag, artifact,
attestation, PyPI receipt, recording or live Jev evidence is claimed.

Executor: the same Claude Code documentation session, model
`claude-fable-5-1`, effort high, normal permissions, existing account and
billing, no subagent. Branch `claude/v1-08-pretag` in worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, continued
from `88a5b30084f2ce0ed118466b648fe5289c6e2181`. No merge, push, tag,
network, key or provider access; no source, test, asset, schema, helper,
lock or packaging edit; `tools/check_release.py` and its schemas were read
only. No tool operation was denied.

## Commits

| Commit | Content |
| --- | --- |
| `6e5103e702db471a6fed74dfabb9ac461e852aa6` | ADR 0016, ADR 0019, ADR 0020, `docs/threat-model.md`, `plan/v1/RELEASE_NOTES.md` (+74/-31) |
| (this report) | `plan/v1/reports/08-pretag-correction.md` only |

## Review findings and corrections (REVIEW 08F, `08-pretag-initial.md`)

**1 (P1). Full implementation SHA-256 in the release notes.** The receipts
gate (`_check_release_notes`, lines 2286–2289) rejects any 64-hex hash in
the notes that is absent from the actual release and post-publication
receipts, and the implementation fingerprint is not part of those schemas.
Both occurrences (intro and the "Implementation source" row) now read
`8f316f67…98ed3` with an absolute link to `docs/versioning.md`, whose
registry table carries the exact value. `grep -c` for a 64-hex pattern in
the notes now returns 0. The checker and schemas are unchanged.

**2 (P2). Mislabelled CI runs and overstated historical pass.** ADR 0016
now states that runs 37581140052 and 37581142565 at PR 18 head `0e32c6c`
were the ordinary push and pull-request `ci.yml` workflow, exercising the
release helper's tests and the asset pipeline, not a `publish-pypi.yml`
rehearsal. ADR 0019's historical bullet now says the red runs at `b05aed8`
and `5e7931a` failed on the four absent architecture figures with lint and
type steps passing, and that the downstream build, packaging, reproduction
and hook steps were skipped after the failure and not run, so those runs
establish nothing about them. The failed history is retained.

**3 (P2). Threat-model key claim.** The sentence "the key never enters
locks, captures, diagnostics or evidence" is replaced: the adapter excludes
the key and authorization headers from the metadata and diagnostics it
generates (identity, captured outcomes, locks and error records), with the
reviewed guard that detects the literal key and a limited set of JSON
escapings in that material; this does not redact arbitrary caller-supplied
inputs or raw provider bodies, which are preserved as data and must be
reviewed before sharing. That matches ADR 0017's existing boundary; no new
security claim is made and the earlier raw-data warning stays.

**4 (P2). ADR 0020 resize wording and future gates.** The status and
architecture bullets now say Task 13R re-validated the three SVG groups at
the measured widths, regenerating ten variants (hero mobile, how-it-works,
architecture) while the desktop hero SVGs and `social.png` stayed
byte-identical. The recording and the tagged publication are listed as
future gates with no receipt claimed. The final first-screen review is now
cited from the actual receipt below; the `710ae55` preflight is retained as
history.

## New receipts recorded (supplied by Codex after the 08F dispatch)

Recorded in the release notes' pre-publication table and in ADRs 0016,
0019 and 0020, distinguished from the still-`PENDING` tagged-pipeline rows:

- PR 46 merged `277d729c192a7e41ffc4432e5943e74cd4a87c35` after
  independent integration ACCEPT at the exact reviewed head `ff0f66c`
  (`plan/v1/reviews/19-combined-static.md`); all ten hosted source and
  assets jobs succeeded there (push run 37599734305, PR run 37599764080).
  Product source unchanged from `5e7931a`.
- Parent combined checks at `ff0f66c`: 4,163 ordinary tests passed, 1
  explicit obsolete-manifest observation skip, 31 deselected; 25 packaging
  passed; 6 cached-native passed with no skips; all 4,195 collected cases
  accounted for; 590 docs/visual checks, hooks, full static regeneration
  and 16 README references passed.
- Non-publishing `publish-pypi.yml` rehearsal run 37599844342 at `ff0f66c`
  completed SUCCESS: build once, assets, all four exact-artifact platform
  verify jobs passed; publish, post-publish and mirror intentionally
  skipped. Recorded as pre-tag evidence only, not a tag, artifact or PyPI
  receipt.
- Final GitHub README first-screen screenshot at `main` `277d729`,
  1366×900, device pixel ratio 1, 838 px image width, captured 7 October
  09:33 UTC (`plan/v1/reports/readme-first-screen-277d729-final.jpg`, present
  in root at dispatch). The fresh context-free reviewer's two sentences are
  quoted verbatim in the release notes. Codex accepted the semantic
  ten-second gate; the receipt `plan/v1/reports/readme-ten-second-final.md`
  is cited as the receipt Codex stated it will persist in root before
  integration, and it was not present in root when this task ran. The notes
  state this is one reviewer's reading of one screenshot, not a timed human
  study, and that the badge shows the then-current 0.1.0 PyPI release.

## Commands and exit codes

Run as separate, unwrapped commands on the corrected content before the
commit (no pipes, `tail`, `head` or `echo`).

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen pytest tests/docs` | 110 passed in 1.08 s | 0 |
| `uv run --frozen python tools/check_release.py docs` | no output | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | no output | 0 |

The `receipts` gate was not run: it requires the tagged release receipts
that do not exist yet. The hash finding was verified against its source
(the 64-hex allowlist) and by the zero-count grep above, not by running it.

## Deviations

None. One note for review: the `readme-ten-second-final.md` receipt is cited
by the path Codex supplied although it was not yet in root; if Codex
persists it under a different name, the three citations (release notes,
ADR 0020, this report) need a one-line follow-up.

## Remaining release gates (unchanged in kind)

- Codex's independent review of `6e5103e` and this report, then
  integration of the pre-tag documentation.
- Final candidate gate and exact-head hosted checks on the final clean
  tree that carries these documentation commits.
- Tag, human `pypi` environment approval, publication, post-publication
  receipts (Task 20/21) and the genuine post-PyPI demo recording
  (Decision 2A).
- The P2 figures remain unimplemented and the live Jev audit remains not
  run; both stay outside the planned 1.0 delivery. The unchanged adapter is
  retained.

## Spend

Unknown; not measured. The packet estimate was 20 minutes.
