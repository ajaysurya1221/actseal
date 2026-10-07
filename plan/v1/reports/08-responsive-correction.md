# REPORT 08R2 (Task 08R2: correct responsive-change evidence wording)

Status: DONE for the owned scope. Prose corrections only; the README and
test source at `8d03ba3010b7fd36eacdd003631269fbb60c8012` are scoped ACCEPT
and were not touched. REPORT 08R (`plan/v1/reports/08-responsive.md`) is
preserved unchanged; this report is additive and corrects it where stated.
Codex independently reviews before integration. No new test count, green
gate, live-audit or publication claim is made.

Executor: the same Claude Code session as REPORT 08R, model
`claude-fable-5-1`, effort high, normal permissions, existing account and
billing, no subagent. Branch `claude/v1-08-responsive` in worktree
`/Users/ajay/.codex/worktrees/actseal-v1-docs/not-yet-named`, continued
from `e9dc3777bae19824dd329eaf849d6fd0a5230bdc`. No merge, push, network,
key, product or test edit; no tool operation was denied.

## Finding 1: ADR measurement range

`docs/decisions/0020-reproducible-visual-assets.md`, addendum paragraph
"Measurement", previously said "800 to 1200 px windows received desktop
canvases scaled to 638 to 758 px". The review 13 table establishes
repository-view image widths of 638 to 758 px only for 1000, 1100 and
1200 px viewports. The 800 px observation (702 px image, desktop variant)
was taken on the wider file-preview page, a different surface that must not
substitute for the repository view. The sentence now reads "1000 to 1200 px
windows" and adds one sentence stating that the 800 px observation came
from the file-preview surface and is not evidence for the repository view.
No other ADR text changed.

## Finding 2: REPORT 08R command wording

REPORT 08R wrote that the four required commands were "run as separate
literal commands". The commands were run separately, but each check was
wrapped in a pipeline, not invoked bare. The actual invocations were:

```bash
uv run --frozen pytest tests/docs/test_readme.py 2>&1 | tail -4; echo "exit=${pipestatus[1]}"
uv run --frozen python tools/check_release.py docs 2>&1 | tail -4; echo "exit=${pipestatus[1]}"
uv run --frozen pre-commit run --all-files 2>&1 | tail -5; echo "exit=${pipestatus[1]}"
git diff --check; echo "exit=$?"
```

`${pipestatus[1]}` (zsh) reports the first pipeline element's status, so the
exit codes 1, 1, 0 and 0 in REPORT 08R are the checks' own exit codes, not
`tail`'s. One exception: the very first baseline run on the clean base,
before any edit, was `uv run --frozen pytest tests/docs/test_readme.py -q
2>&1 | tail -15; echo "exit=$?"`, where `$?` is `tail`'s status; it printed
`exit=0` while the visible output showed `1 failed, 9 passed`. That printed
0 was the pipe's status, not pytest's, and was never reported as a pass; the
later pipestatus-based reruns on the same state gave exit 1. Also, the
earlier pre-commit run that failed `ruff format --check` and the
`uv run --frozen ruff check tests/docs/test_readme.py` run were likewise
piped through `tail` or `head` with `pipestatus[1]`.

The parent's independent checks, run unwrapped, are the authoritative
receipts: README suite 13 passed and 1 missing-architecture failure, docs
gate exit 1, hooks exit 0. They agree with the executor's wrapped runs.

## Finding 3: `tests/visual/visual_support.py` is not Task 13R scope

REPORT 08R listed `tests/visual/visual_support.py` (default
`display_width=880`) among files carrying the 880/360 px assumption whose
"correction is Task 13R scope". Correction: that default parameterizes
synthetic probe fixtures in the visual test helpers; those 880 px probes
stay unchanged and are not Task 13R scope. The remaining items in that
list (`docs/assets/src/README.md`, `hero.py`, `how_it_works.py`,
`inventory.py`) are unchanged by this task and remain for the V1-051
visual lane as previously stated.

## Finding 4: spend wording

REPORT 08R's "About 20 minutes" is the packet's estimate, not a measured
runtime or API spend. Actual wall-clock and token spend for Task 08R were
not measured by the executor and are unknown. The same applies to this
task: the 10-minute figure is the packet estimate; actual spend unknown.

## Commands and results

```bash
git status --short --branch
git diff --check
```

- `git status --short --branch`: on `claude/v1-08-responsive`, only the
  two owned files changed before commit.
- `git diff --check`: no output, exit 0 (run bare, no pipe).

No tests were run; the task requires none for a prose correction and the
source at `8d03ba3` is unchanged.

## Deviations

None.

## Open gates (unchanged)

- The four architecture SVGs are still absent on this branch, so the README
  suite and the docs gate remain exit 1 until Task 13R outputs integrate.
- Regenerated real pixels at 838/254 px, a fresh public repository
  first-screen test on the integrated head and exact-head hosted CI remain
  outstanding. No release, tag or publication has occurred.

## Spend

Unknown; not measured. The packet estimate was 10 minutes.
