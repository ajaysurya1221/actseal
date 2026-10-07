# REPORT 08R (Task 08R: readable README variants at real GitHub widths)

Status: DONE for the owned scope. Two of the four required commands exit 1
on the same pre-existing cause, the four architecture SVGs that the clean
base does not contain; that failure is reported below as a failure, not a
pass or an exclusion. Candidate for Codex review; DONE is not ACCEPT and
full acceptance follows the independent integrated review, the regenerated
pixels at the measured widths (Task 13R) and a fresh public first-screen test
on the integrated head. No public release or live-audit claim is made.

Executor: Claude Code, model `claude-fable-5-1`, effort high, direct session,
no subagent, no model/account/billing substitution. Worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, new branch
`claude/v1-08-responsive` created from the retained candidate
`5e7931a1ec8b0197d87ddc1e01a0835e011b470f`. Nothing pushed, merged, tagged,
downloaded or fetched; no browser interaction, no provider or key access, no
merge command run. No tool operation was denied. Root planning files, other
lanes' files, assets, renderer sources, schemas, metadata, lockfile and
`.env.example` were not edited.

## Commits

| Commit | Content |
| --- | --- |
| `8d03ba3010b7fd36eacdd003631269fbb60c8012` | README breakpoint, README tests, ADR 0020 addendum |
| (this report) | `plan/v1/reports/08-responsive.md` only |

Files changed in `8d03ba3`: `README.md` (6 lines, media queries only),
`tests/docs/test_readme.py` (+163/-10), and
`docs/decisions/0020-reproducible-visual-assets.md` (+53 addendum).

## What changed

**README.** In all three `<picture>` blocks (hero, how-it-works,
architecture) the two mobile `<source>` rows now carry
`(max-width: 1279px)` instead of `(max-width: 600px)`:

```html
<source media="(prefers-color-scheme: dark) and (max-width: 1279px)" srcset="…-mobile-dark.svg">
<source media="(max-width: 1279px)" srcset="…-mobile-light.svg">
<source media="(prefers-color-scheme: dark)" srcset="…-dark.svg">
<img alt="…" src="…-light.svg" width="100%">
```

Viewports below 1280 px select the existing vertical variants; 1280 px and
above select the desktop variants. Dark rows precede light rows, so the
first matching source wins in dark mode. `git diff` confirms the opening
order, copy, three quickstart commands, alt text, absolute links, image
paths and `width="100%"` attributes are byte-identical to the base.

**Tests (`tests/docs/test_readme.py`).** The HTML parser now records each
`<picture>` block's `<source>` rows (media, target) in document order and
its `<img>` fallback, and rejects nested pictures, a second `<img>`, a
`<source>` after the `<img>`, multi-candidate `srcset` values and a
`<picture>` without `<img>`. A small evaluator understands exactly
`prefers-color-scheme`, `max-width` and `min-width` joined by `and`, and
fails loudly on anything else. New tests:

- `test_every_picture_uses_the_measured_breakpoint_with_dark_before_light`:
  exact source order and media strings per figure, light `<img>` fallback,
  and no `600px` anywhere in the README.
- `test_viewports_below_1280_select_the_vertical_variants`: 320, 360, 800,
  1000, 1200 and 1279 px select `-mobile-dark` / `-mobile-light` in dark and
  light schemes for all three figures.
- `test_viewports_at_1280_and_above_select_the_desktop_variants`: 1280, 1366
  and 1920 px select `-dark` / `-light`.
- `test_breakpoint_change_kept_every_picture_full_width_without_new_paths`:
  exactly twelve referenced asset names (four per figure) and three
  `width="100%"` attributes.

Before the README edit these three selection tests failed on the base
(`hero-dark.svg` selected at 800 px, for example); after it they pass.
`test_every_image_resolves_to_a_committed_implemented_asset` and the other
missing-asset and architecture-filename checks are unchanged and still fail
by design on the base.

**ADR 0020 addendum (dated 2026-10-07).** Records that the 880/360 px
column widths were design assumptions, now historical; reproduces the
review 13 measurement table (320→254, 360→294, 1000→638, 1100→658,
1200→758, 1280→838, 1366→838); derives from the committed 1600/720-unit
canvases that 26-unit desktop text is 13.6 px at 838 px and 30-unit mobile
text is 12.3 px at 294 px and 10.6 px at 254 px, while the hero's 28-unit
desktop labels fit at 14.7 px; states the new 1280 px README breakpoint and
the 838/254 px validation widths; and says explicitly that these figures are
arithmetic from the measurement table, not a browser test of this unmerged
README, with the renderer-side correction owned separately by Task 13R.

## Commands and exit codes

Run as separate literal commands from the worktree at `8d03ba3` content
(before the report commit; the report changes no checked file).

| Command | Result | Exit |
| --- | --- | --- |
| `uv run --frozen pytest tests/docs/test_readme.py` | 13 passed, 1 failed: `test_every_image_resolves_to_a_committed_implemented_asset`, `README references uncommitted figure files: ['architecture-dark.svg', 'architecture-light.svg', 'architecture-mobile-dark.svg', 'architecture-mobile-light.svg']` | 1 |
| `uv run --frozen python tools/check_release.py docs` | `docs gate has 1 unmet requirement(s): README.md links to missing file docs/assets/architecture-mobile-dark.svg` | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | no output | 0 |

Both exit-1 results are the known missing-architecture condition: the base
tree `5e7931a` has zero `architecture*` files under `docs/assets/` and its
README already referenced the same four names, so the failure predates and
is independent of this change. It must stay red until the Task 13R outputs
are integrated; it is not excluded, skipped or relabelled.

Additional evidence: `uv run --frozen pytest tests/docs` gave 109 passed,
the same 1 failed, exit 1. Intermediate runs: the first pre-commit pass
exited 1 on `ruff format --check` for the new test file and a later
`ruff check` found one PT018 and two E501 in the same file; all three were
fixed in the owned test file before the final pass above.

## Deviations

None from the packet. One judgement call: the breakpoint is written as
`(max-width: 1279px)` rather than a fractional `1279.98px`; integer CSS
viewport widths are the measured and tested cases, and a fractional
viewport between 1279 and 1280 px would take the desktop variant.

## Open issues and follow-ups (not owned here)

- `docs/assets/src/README.md` lines 123–124, `hero.py`, `how_it_works.py`
  and `inventory.py` still document the 880/360 px assumption and
  `tests/visual/visual_support.py` defaults `display_width=880`; the ADR
  addendum marks these historical, and their correction is Task 13R scope.
- Regenerated real pixels at 838/254 px, a fresh public repository
  first-screen test and exact-head hosted CI on the integrated README all
  remain outstanding.
- The two expected exit-1 commands above will only go green once the four
  architecture SVGs are committed.

## Spend

About 20 minutes of one Fable 5.1/high session; no network, downloads,
provider calls, key access, browser use, merges or pushes.
