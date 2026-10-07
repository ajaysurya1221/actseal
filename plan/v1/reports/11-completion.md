# REPORT 11 — completion candidate (generated and pixel-reviewed; blind README test pending)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, dispatched by Codex under the human's 7 October approval of the five scoped requests (authentic pinned font/tool downloads and actual visual previews). Approved plan hash `bb3538db868f929c1f779dcbcd105936f521acba51fbfe7c08988fedcd0fdcaa` (verified locally with Python `hashlib`). Worktree `actseal-v1-hero`, branch `claude/v1-15-social-preparation`, continuing from `64b8e03c0aed6aa6952057cf705d620a2d70e71f`. No subagent, nested executor, model or billing substitution, personal-memory write, secret read, push, merge or publication. No download was performed by this executor; the fonts and receipts below are Codex's approved `setup_tools.py` outputs found in the worktree. No denial occurred.

Status: **Task 11 done-when passes and the four hero assets are committed.** This report distinguishes three levels of evidence:

| Level | State |
|---|---|
| Generated | Done. Four outlined SVGs written from the hash-verified JetBrains Mono 2.304 files; `render.py --check --only hero` passes with four `matches regeneration` lines. |
| Pixel review (this executor) | Done. Light and dark desktop at 880 CSS px, light and dark mobile at 360 CSS px, and a 1366×900 README-top mock, all rendered in headless Google Chrome from the committed files and inspected. Findings below. |
| Blind README ten-second test | **Pending.** Requires the README integration (Task 08) and a reviewer who sees only the screenshot. Not claimed here. |

Codex ACCEPT and CI on the reviewed commit remain required; this is not self-acceptance.

## Commits (owned files only)

| Commit | Content |
|---|---|
| `461f9ee5c64137263df181b830ec7a44e222f036` | chore(assets): commit the pinned JetBrains Mono 2.304 fonts, OFL notice and setup receipts |
| `db56f368a388c1fee82a7edcfa22bacb06809fa2` | feat(assets): generate the hero banner from the pinned fonts (light, dark and mobile variants) |
| (this commit) | docs(v1): record REPORT 11 completion candidate |

No source change was needed: `hero.py`, `inventory.py`, `test_hero.py` and `test_render_cli.py` are unchanged from `64b8e03`. The real glyph advances fit every planned line break, so no layout constant moved.

### Authentic inputs committed at `461f9ee` (Codex setup outputs, hashes verified with Python `hashlib`)

| File | SHA-256 | Matches |
|---|---|---|
| `docs/assets/src/fonts/JetBrainsMono-Regular.ttf` | `a0bf60ef0f83c5ed4d7a75d45838548b1f6873372dfac88f71804491898d138f` | `tools.toml` pin |
| `docs/assets/src/fonts/JetBrainsMono-Bold.ttf` | `5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb` | `tools.toml` pin |
| `docs/assets/src/fonts/OFL.txt` | `30f0c136e3c88e422d0791acd97238870f9054a9729bc34cf2ff0d4ed8cac4ad` | receipt; carries "SIL OPEN FONT LICENSE Version 1.1" and "JetBrains Mono" |
| `docs/assets/src/receipts/jetbrains-mono-any.json` | — | source commit `cd5227bd1f61dff3bbd6c814ceaf7ffd95e947d9`, retrieved 2026-10-07 |
| `docs/assets/src/receipts/asciinema-darwin-arm64.json`, `agg-darwin-arm64.json` | — | binaries live in `~/.cache/actseal-assets` only; not needed by the hero |

### Generated assets at `db56f36`

| File | Size | SHA-256 |
|---|---|---|
| `docs/assets/hero-light.svg` (1600×400) | 64768 B | `19a8f20f4987d69481622d372d6eb5de2262896a1b8f2db62d0f2ce7989b3fe6` |
| `docs/assets/hero-dark.svg` (1600×400) | 64768 B | `77bb337db71e1224df3d83f43cf73754e84201d93cabf61c62f63d3492b3d324` |
| `docs/assets/hero-mobile-light.svg` (720×561) | 57076 B | `0de55733d1a247328da52c793445b9d195d97caafa6aac0f0c8ab269efa990f3` |
| `docs/assets/hero-mobile-dark.svg` (720×561) | 57076 B | `eeeac139209f95ae6f99cab7ea5770978a28156074eb0ada6585fd731a84d27e` |

Each file contains no `<text>`, `font-family`, `transform`, script, style or external reference; `<title>`/`<desc>` carry the approved wording and the caption verbatim.

## Commands and results

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets python docs/assets/src/render.py --check --only hero` (before `--write`) | `[ok] fonts: jetbrains-mono 2.304 present with upstream notice`; four `is not committed; run render.py --write` errors; `1 asset(s) checked` (the renderer itself succeeded deterministically) | 1 |
| `uv run --frozen --group assets python docs/assets/src/render.py --write --only hero` | four `wrote docs/assets/hero-*.svg` lines; `write: 1 asset(s) checked; 0 planned/not implemented; 0 error(s); 4 file(s) written` | 0 |
| **`uv run --frozen --group assets python docs/assets/src/render.py --check --only hero`** (Task 11 done-when) | **four `matches regeneration` lines; `check: 1 asset(s) checked; 0 planned/not implemented; 0 error(s)`** | **0** |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` (full inventory) | hero four `[ok]`; six planned `[info]`; social `[error] requires resvg 0.48.1: resvg 0.48.1 is not cached at ~/.cache/actseal-assets/resvg-0.48.1/resvg; run setup_tools.py` and `skipped rendering because prerequisites failed`; `1 asset(s) checked; 6 planned/not implemented; 2 error(s)` (expected: resvg pending, see Task 15 note) | 1 |
| `uv run --frozen --group assets pytest tests/visual -q -p no:cacheprovider -rs` | 250 passed in 1.17 s | 0 |
| `uv run --frozen pytest tests -q -p no:cacheprovider -m "not integration and not packaging"` (default suite) | 2769 passed, 20 deselected in 53.39 s | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check Passed; ruff format --check Passed; mypy --strict Passed | 0 |
| `uv run --frozen ruff format --check .` / `ruff check .` / `mypy --strict docs/assets/src` | 251 files already formatted / All checks passed / no issues in 13 source files | 0 |
| `git status --short` after commits | clean | 0 |

## Pixel review (this executor, headless Google Chrome, committed files)

Method: HTML wrappers under `/tmp/actseal-preview/` placing each committed SVG as an `<img>` at its README display width (880 CSS px desktop, 360 CSS px mobile) on the matching theme background, rendered with `Google Chrome --headless=new --screenshot` at device scale 2, plus a 1366×900 viewport mock of the README top (banner, one-sentence description, badge placeholder row) at device scale 1. Screenshots are review scratch files and are not committed. Chrome is a viewer here, not part of the pipeline; the committed SVGs are the deliverable.

Findings, all four variants:

- **Copy exact.** "Actseal"; "Test model-chosen actions." / "Replay the evidence."; "Replay cannot authenticate responses, prove inference occurred, or establish label truth." Nothing else is drawn.
- **One motif.** Three pills freeze → run → replay with forward arrows and one return route from replay back to freeze. No padlock, shield, key or other security symbol. Labels are vertically centred in the pills with the real font (the `LABEL_BASELINE_SHIFT` tuning flagged in REPORT 11 preparation was not needed).
- **No clipping, no overlap.** Desktop: text column ends well before the motif; caption sits above the bottom margin. Mobile: wordmark, tagline, motif row and three caption lines stack with clear gaps.
- **Readability.** At 880 CSS px the caption and labels render at 15.4 px, tagline 24.2 px, wordmark 57.2 px; at 360 CSS px the caption and labels render at 15 px, tagline 20 px, wordmark 42 px. All above the 14 px floor as computed; visually the 15 px caption is legible but is the smallest element and reads as deliberately secondary (muted colour).
- **Themes.** Light on `#ffffff` and dark on `#0d1117` differ only in fill/stroke; both have adequate contrast on their intended surfaces; the accent arrows are clearly visible in both.
- **README top at 1366×900.** Banner at 880 px plus the description and a badge row occupy roughly the top 340 px; purpose and the evidence-limit caption are visible without scrolling. The actual ten-second test with real badges, the how-it-works figure and a blind reviewer is Task 08's and remains pending.

No defect found that requires a source change. Review-sensitive but accepted as-is: the muted caption colour is the lowest-contrast text; the wordmark/tagline gap on desktop is slightly tighter than the tagline/caption gap.

## Task 15 note (not part of Task 11)

The social preview depends on the pinned resvg 0.48.1 binary. Codex's setup reported a 404 for the macOS archive URL and installed nothing; Codex is independently verifying the correct official asset filename and digest. This executor did not download, guess or alter the pin and did not substitute a renderer. Task 15 proceeds only after a verified resvg is cached; its done-when remains unrun. `render.py --check` without `--only hero` therefore still exits 1 on social, as shown above.

## Deviations

1. The preview viewer is Google Chrome rather than resvg, because resvg is not yet available; Chrome is used only to look at the committed SVGs and is not a pipeline dependency.
2. Scratch preview files live under `/tmp/actseal-preview/`, outside the repository; no screenshot is committed.
3. Implementation and review were done directly by Fable 5.1 rather than delegated, following the dispatch's no-nested-executor instruction.

## Outstanding

1. Codex ACCEPT of this candidate and green CI on the reviewed commit.
2. Blind README ten-second test after Task 08 wires `<picture>` light/dark/mobile sources.
3. Task 15 after the verified resvg pin repair.

## Spend

Claude subscription session only. No paid API calls, no downloads by this executor, no live providers. Commits carry git timestamps.
