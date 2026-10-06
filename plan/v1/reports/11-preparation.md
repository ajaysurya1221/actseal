# REPORT 11 — PARTIAL (preparation only)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, dispatched by Codex under the standing authorization. Worktree `actseal-v1-hero`, branch `claude/v1-11-hero-preparation` from main `77bf39f`. No subagent, Agent/Task tool, other model or nested Claude produced any product, test or documentation text. No personal-memory writes, no secrets read, no network call, no font or tool fetched, no `setup_tools.py` run, no local preview rendered.

Status: **PARTIAL by design.** The hero generator, its inventory registration and the focused tests are complete and green. **No hero asset exists**, the Task 11 done-when command **fails loudly (exit 1)** because the pinned JetBrains Mono files are not fetched, and no rendered review has happened. This report does not claim Task 11 acceptance. The parent resumes `--write`, rendered review and acceptance only after the scoped font-download and preview approvals.

## Commits (owned files only)

| Commit | Message |
|---|---|
| `f26451fb9e909405da3dafff31d64f7aa0d0d36c` | feat(assets): add the hero banner generator and register its outlined outputs |
| `d658b63fdbe94933585524fa08889bcbaf131fe1` | test(assets): cover hero copy, declarations, readability floors and fail-loud fonts |
| (this report) | docs(v1): record REPORT 11 preparation |

SHA-256 of the owned files at `d658b63`:

| File | SHA-256 |
|---|---|
| `docs/assets/src/actseal_assets/hero.py` | `11b3b2a71db8fd23cb519805aa455a78a2ff42362e343b7561cccde83aa5fe09` |
| `docs/assets/src/actseal_assets/inventory.py` | `5f09ccb2c557751fc57468a1af4395a2e9b2472a8cd39491455464dcea842ea3` |
| `tests/visual/test_hero.py` | `b264a71ba0f400f697f19859357efb769ae19e9c6a46819f9355e957923324be` |

Hashes were computed with Python `hashlib` through `uv run --frozen python -c ...`; `shasum` was not used.

## Changes

- **`docs/assets/src/actseal_assets/hero.py`** (new, 503 lines). One content table and two canvases:
  - Frozen copy: `WORDMARK = "Actseal"`; `TAGLINE = "Test model-chosen actions. Replay the evidence."` broken as two lines at the sentence boundary; `CAPTION = "Replay cannot authenticate responses, prove inference occurred, or establish label truth."` broken as two desktop lines (`… responses, prove` / `inference occurred, …`) and three mobile lines (`… responses,` / `prove inference occurred,` / `or establish label truth.`); `MOTIF_STEPS = ("freeze", "run", "replay")`. `validate_copy()` requires every line tuple to rejoin to the approved string and runs before any rendering.
  - Motif: one loop. Three rounded pills labelled freeze, run, replay; accent arrows freeze→run and run→replay; a return route below the pills from replay back to freeze ending in an upward arrowhead. Flat colours, no gradients, no icons, no padlock/shield/key or other security symbolism.
  - `TITLE`/`DESC`: the description names the wordmark, quotes the tagline, describes the loop and quotes the caption verbatim. No new assurance is stated.
  - Fonts: `REGULAR_FONT = "JetBrainsMono-Regular.ttf"`, `BOLD_FONT = "JetBrainsMono-Bold.ttf"` under `RenderContext.fonts` (`docs/assets/src/fonts/`). `require_fonts()` raises `OutlineError` naming every missing file and `setup_tools.py --tool jetbrains-mono`, and states that no substitute font is used. It runs before fontTools is imported and before any glyph is drawn. Hash verification against `tools.toml` remains the pipeline's job (`fonts` is a blocking scope), which is the accepted pin-checking path; `--check`/`--write` cannot reach `render()` with wrong font bytes.
  - All text is path data from `outline.outline_text`; the outputs contain no `<text>`, no `font-family`, no `transform`. Every string is measured with the real advances first; a line wider than its column raises `ValueError` ("Text is not shrunk; change the layout or the line breaks").
  - **Desktop** `hero-light.svg` / `hero-dark.svg`, 1600×400, displayed at 880 CSS px (scale 0.55): wordmark 104 units bold (57.2 px), tagline 44 (24.2 px), caption 28 (15.4 px), motif labels 28 (15.4 px). Text column x 72–872, motif x 940–1540, caption bottom 370, motif bottom 278.
  - **Mobile** `hero-mobile-light.svg` / `hero-mobile-dark.svg`, 720×561, displayed at 360 CSS px (scale 0.5): wordmark 84 (42 px), tagline 40 (20 px), caption 30 (15 px), labels 30 (15 px). Stacked: wordmark, tagline, motif row, three caption lines. Height is derived from the baselines (`mobile_height()`), not hand-set.
  - `require_readable()` enforces the 14 px floor on every type size at the declared display width (same constant as `checks.MIN_LABEL_PX`, which exempts outlined assets, so the module enforces its own floor). `_require_extents()` refuses geometry that leaves the canvas or its margin.
  - Palette identical to the Task 12 figure for consistency: light `#ffffff/#f6f8fa/#d0d7de/#1f2328/#24292f/#57606a/#0969da`, dark `#0d1117/#161b22/#30363d/#e6edf3/#c9d1d9/#8b949e/#58a6ff`. Explicit canvas rect in each variant.
- **`docs/assets/src/actseal_assets/inventory.py`** — minimal registration: `from . import hero`; the `hero` asset gains `renderer=hero.render` and two mobile outputs (`hero-mobile-light.svg`, `hero-mobile-dark.svg`, `hero.MOBILE_WIDTH × hero.mobile_height()`, `display_width=MOBILE_DISPLAY_WIDTH`, `outlined=True`) built as plain `Output(...)` so the shared `_svg()` helper and every other asset are untouched. The desktop declarations (1600×400, outlined) are unchanged. The Task 12 how-it-works registration was not touched or anticipated; its `from . import how_it_works` line will sit next to the new import at integration (trivial adjacent-line merge).
- **`tests/visual/test_hero.py`** (new, 19 tests). Font-free: exact copy and line rejoin; drifted line breaks rejected; forbidden-language scan (tamper, secure, signed, trust, guarantee, enforce, sandbox, padlock, shield, safe, proof, verified, … and `authentic`/`prove`/`truth` permitted only inside the caption); inventory declares exactly the four outlined outputs with the renderer, sizes and display widths; type sizes meet the floor (desktop caption 15.4 px, mobile 15.0 px) and a 20-unit caption is rejected; fixed geometry fits both canvases and crowded geometry is rejected; missing pinned fonts raise before outlining with both file names and the setup command; the real hero declaration in a font-less repository fails `check` and `write` with exactly `requires jetbrains-mono 2.304; not fetched: …` + `skipped rendering because prerequisites failed`, writes nothing; the in-process done-when command exits 1 with those errors and `0 asset(s) checked`. **Unit doubles** (fontTools only, skipped otherwise): rectangle-glyph TrueType files built in a temp dir under the pinned names, labelled in the module docstring and fixture as stand-ins that carry none of the pinned font's glyphs, metrics or bytes. They cover: exact output set and determinism; every output passes `checks.check_output` as outlined (no `<text>`, `font-family`, `transform`; title/desc exact); structure (groups `wordmark, tagline, motif, caption`; three `step-*` pills in order each with one rect and one glyph path; three arrowheads; one return route; 8 glyph paths desktop, 9 mobile; pills share a row); light/dark differ only in `fill`/`stroke`; a narrowed column raises instead of shrinking; a double lacking `,` raises `OutlineError`; and a pipeline `--write` then `--check --only hero` round trip passes when the copied manifest is re-pinned to the doubles' hashes (pipeline wiring only).

No edits to `__init__.py` (the `hero` submodule is reachable as `actseal_assets.hero` through the inventory import), `pyproject.toml`, `uv.lock`, root `README.md`, `docs/assets/src/README.md`, workflows, product code, other assets, shared tests, shared state or REVIEW records.

## Commands and results

| Command | Result | Exit |
|---|---|---|
| **`uv run --frozen --group assets python docs/assets/src/render.py --check --only hero`** (Done-when, expected blocked) | `[error] hero: requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, JetBrainsMono-Bold.ttf, OFL.txt`; `[error] hero: skipped rendering because prerequisites failed`; `check: 0 asset(s) checked; 0 planned/not implemented; 2 error(s)` | **1** |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` (full inventory) | same two hero errors; seven `[info] … not implemented`; `check: 0 asset(s) checked; 7 planned/not implemented; 2 error(s)` | 1 |
| `uv run --frozen --group assets pytest tests/visual/test_hero.py -q -p no:cacheprovider -rs` | 19 passed in 0.26 s | 0 |
| `uv run --frozen python -c "import sys; sys.modules['fontTools'] = None; import pytest; sys.exit(pytest.main(['tests/visual/test_hero.py', '-q', '-p', 'no:cacheprovider', '-rs']))"` (core environment simulation) | 9 passed, 10 skipped (`fontTools.fontBuilder` unavailable) | 0 |
| `uv run --frozen --group assets pytest tests/visual -q -p no:cacheprovider -rs` | **3 failed, 220 passed** in 1.09 s; all three failures in the shared `tests/visual/test_render_cli.py` (see Deviation 1) | 1 |
| `uv run --frozen pre-commit run --all-files` | ruff check Passed; ruff format --check Passed; mypy --strict Passed | 0 |
| `uv run --frozen mypy --strict docs/assets/src` (extra; pre-commit does not cover this path) | Success: no issues found in 12 source files | 0 |
| `uv run --frozen ruff check docs/assets/src tests/visual` / `ruff format --check docs/assets/src tests/visual` | All checks passed / 25 files already formatted | 0 |
| `git diff --cached --check` | clean | 0 |

Not run: `render.py --write --only hero` (would fail identically; nothing to write without fonts), `setup_tools.py` (prohibited), any rasterizer or preview (approval pending), packaging/integration markers, the full default suite (unchanged outside `tests/visual`; the three shared-test failures above would appear there too).

## Deviations

1. **Three shared tests now fail, by consequence, not by edit.** `tests/visual/test_render_cli.py::test_check_on_bootstrap_repository_reports_planned_assets` (expects exit 0 and eight planned assets), `::test_only_planned_asset_exits_one` (expects `not implemented (planned in Task 11)`) and `::test_render_script_runs_without_fonttools` (expects `--check` exit 0 in a bootstrap repository) all assumed the hero had no renderer. With the renderer registered and no pinned fonts, `--check` reports the hero's missing font as an error and exits 1, which is exactly the fail-loud behaviour this task requires. I did not edit that file: it is outside my ownership and Task 12's reviewed branch already rewrites the same tests (`IMPLEMENTED`/`PLANNED` tuples, write-then-check sibling). Codex should integrate one update covering both assets; note that the hero cannot join a bootstrap "write-then-check passes" test until the fonts exist, so the bootstrap expectation for hero is the two font errors recorded above.
2. **Four outputs instead of two.** The provisional inventory declared light/dark desktop files only; the task requires readable mobile variants, so two stacked `hero-mobile-*.svg` outputs were added. README `<picture>` wiring belongs to Task 08.
3. **Mobile canvas 720×561.** Width follows the Task 12 convention (720 units for a 360 px column); height derives from the baselines.
4. **Widths are verified only by the real font at render time.** Line breaks were planned against a 0.6 em monospace advance (JetBrains Mono's nominal advance). The unit doubles use the same advance so the fit checks are representative, but this is an assumption: if the real advance differs, `render()` raises `… units wide … Text is not shrunk` and the fix is a different line break or column width, never a smaller size. Planned slack: desktop caption 773 of 800 units, mobile caption line 1 at 666 of 680.
5. **Pin verification is not duplicated in `hero.py`.** The module checks presence and fails loudly; hash checking stays in the pipeline's blocking `fonts` scope (`tools.check_fonts`), which is the accepted pin-checking pipeline. A direct `render()` call with present-but-wrong bytes would outline with those bytes; `--write`/`--check` cannot.
6. **Palette reused from Task 12** rather than defined once in a shared module, to avoid a generic renderer change. Both lanes can consolidate later if Codex wants a single palette source.
7. Implementation was done directly by Fable 5.1 rather than delegated, following the dispatch's no-subagent instruction over the general routing preference.

## Blocked and outstanding (for the parent after approval)

1. `uv run --frozen python docs/assets/src/setup_tools.py --tool jetbrains-mono` — network-bound, pinned-hash download; requires the pending scoped approval.
2. `uv run --frozen --group assets python docs/assets/src/render.py --write --only hero` — expect `4 file(s) written`; any `does not fit` error means a line break must change (Deviation 4).
3. `uv run --frozen --group assets python docs/assets/src/render.py --check --only hero` — the actual done-when; must report four `matches regeneration` lines and `1 asset(s) checked; 0 error(s)`.
4. Rendered review per the supplement: light/dark at 1366×900 README top, 360 px mobile, labels ≥ 14 px after transforms, no clipping; blind reviewer with screenshot only; reject any response-authentication, inference-proof or label-truth inference. Expect to tune `LABEL_BASELINE_SHIFT` (vertical centring of the lowercase pill labels) and the wordmark/tagline spacing after the first real render; those are constants in `hero.py`.
5. Integration of the shared `test_render_cli.py` expectations (Deviation 1) together with Task 12.

## Spend

Claude subscription session only. No paid API calls, no model inference, no Jev credits, no downloads. Wall-clock approximately 35 minutes; commits at the timestamps recorded in git.
