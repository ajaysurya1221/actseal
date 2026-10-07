# REPORT 11 — PARTIAL (preparation only)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, dispatched by Codex under the standing authorization. Worktree `actseal-v1-hero`, branch `claude/v1-11-hero-preparation` from main `77bf39f`. No subagent, Agent/Task tool, other model or nested Claude produced any product, test or documentation text. No personal-memory writes, no secrets read, no network call, no font or tool fetched, no `setup_tools.py` run, no local preview rendered.

Status: **PARTIAL by design.** The hero generator, its inventory registration and the focused tests are complete and green. **No hero asset exists**, the Task 11 done-when command **fails loudly (exit 1)** because the pinned JetBrains Mono files are not fetched, and no rendered review has happened. This report does not claim Task 11 acceptance. The parent resumes `--write`, rendered review and acceptance only after the scoped font-download and preview approvals.

Revision: REVIEW 11 (REVISE at `09e96e5`) authorized amendment V1-019, under which this lane temporarily owns `tests/visual/test_render_cli.py` to replace three stale bootstrap expectations with missing-prerequisite tests, and asked for the time receipt to be corrected. Both are done below; the initial receipts are retained as history and the new results are reported separately.

## Commits (owned files only)

| Commit | Message |
|---|---|
| `f26451fb9e909405da3dafff31d64f7aa0d0d36c` | feat(assets): add the hero banner generator and register its outlined outputs |
| `d658b63fdbe94933585524fa08889bcbaf131fe1` | test(assets): cover hero copy, declarations, readability floors and fail-loud fonts |
| `09e96e532cb75319bacffddbf9850d0067b9cb9e` | docs(v1): record REPORT 11 preparation for the hero banner (reviewed: REVISE) |
| `e8cffe535eeb515d64dfa38d925916446fabd471` | test(assets): expect the implemented hero to fail on its missing pinned font (V1-019) |
| (this revision) | docs(v1): amend REPORT 11 preparation after REVIEW 11 |

SHA-256 of the owned files at `e8cffe5` (the three Task 11 files are unchanged since `d658b63`):

| File | SHA-256 |
|---|---|
| `docs/assets/src/actseal_assets/hero.py` | `11b3b2a71db8fd23cb519805aa455a78a2ff42362e343b7561cccde83aa5fe09` |
| `docs/assets/src/actseal_assets/inventory.py` | `5f09ccb2c557751fc57468a1af4395a2e9b2472a8cd39491455464dcea842ea3` |
| `tests/visual/test_hero.py` | `b264a71ba0f400f697f19859357efb769ae19e9c6a46819f9355e957923324be` |
| `tests/visual/test_render_cli.py` (V1-019 temporary ownership) | `f1ca0357799f569555dc5cda98e281cb83aeb263d21c70a0d977db3405bcfdd2` |

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

- **`tests/visual/test_render_cli.py`** (revision under amendment V1-019, commit `e8cffe5`). The three bootstrap expectations that assumed an unimplemented hero are replaced by missing-prerequisite tests with the same intent:
  - `test_bootstrap_repository_reports_planned_assets_and_missing_hero_font[--check|--write]`: the seven planned assets stay `[info] … not implemented` with no `[error]`; the hero reports exactly `requires jetbrains-mono 2.304; not fetched: JetBrainsMono-Regular.ttf, JetBrainsMono-Bold.ttf, OFL.txt` and `skipped rendering because prerequisites failed`; no `[ok] hero`; exit 1; summary `0 asset(s) checked; 7 planned/not implemented; 2 error(s)` (`; 0 file(s) written` in write mode); no `hero*` file exists under `docs/assets`.
  - `test_only_implemented_hero_without_font_exits_one`: `--check --only hero` exits 1 with the two hero errors, no `hero: not implemented`, `0 asset(s) checked`, nothing written.
  - `test_only_planned_asset_exits_one`: the explicit unimplemented request now uses `architecture` (Task 13, planned on every lane) and asserts neither `hero` nor `how-it-works` appears in the output.
  - `test_render_script_runs_without_fonttools`: the fontTools-blocked subprocess runs `--check`, exits 1 with an **empty stderr**, reports the two hero font errors and the references `[ok]` line, and leaves no hero file; a sibling `test_render_script_check_of_planned_asset_runs_without_fonttools` runs `--check --only architecture` in the same blocked process and asserts the hero is never touched.
  - Unchanged: usage errors exit 2, `repository_root()`, `--help`, no eager fontTools import, runtime package has no toolchain dependency. No test is skipped or weakened; pipeline and product semantics are untouched. Task 12's workflow-specific tests on its own branch were not copied or integrated; its `IMPLEMENTED`/`PLANNED` reshaping of the same tests will need a reconciliation that keeps both the how-it-works write-then-check assertions and the hero missing-font assertions.

No edits to `__init__.py` (the `hero` submodule is reachable as `actseal_assets.hero` through the inventory import), `pyproject.toml`, `uv.lock`, root `README.md`, `docs/assets/src/README.md`, workflows, product code, other assets, other shared tests, shared state or REVIEW records.

## Commands and results — initial receipt at `09e96e5` (history, retained)

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

## Commands and results — after REVIEW 11, at `e8cffe5` (new, reported separately)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets pytest tests/visual -q -p no:cacheprovider -rs` | **226 passed** in 1.10 s (223 before V1-019: 3 tests replaced by 2 + 1 parametrized pair, 1 sibling added) | 0 |
| `uv run --frozen python -c "import sys; sys.modules['fontTools'] = None; import pytest; sys.exit(pytest.main(['tests/visual', '-q', '-p', 'no:cacheprovider', '-rs']))"` (core environment simulation, whole visual suite) | 210 passed, 11 skipped (`test_outline.py` module skip; 10 unit-double hero tests) | 0 |
| **`uv run --frozen --group assets python docs/assets/src/render.py --check --only hero`** (Done-when, still blocked) | identical to the initial receipt: two hero errors, `check: 0 asset(s) checked; 0 planned/not implemented; 2 error(s)` | **1** |
| `uv run --frozen pre-commit run --all-files` | ruff check Passed; ruff format --check Passed; mypy --strict Passed | 0 |
| `uv run --frozen mypy --strict docs/assets/src` (extra) | Success: no issues found in 12 source files | 0 |
| `uv run --frozen ruff check docs/assets/src tests/visual` / `ruff format --check docs/assets/src tests/visual` | All checks passed / 25 files already formatted | 0 |
| `git diff --check` (working tree) and `git diff --cached --check` | clean | 0 |
| `ls docs/assets` | `src` only; **no hero asset exists** | 0 |

Still not run and not authorized: font or tool download, `setup_tools.py`, any rasterizer or preview, native or mutation harness, network or live providers, secrets. No fake hero output was produced; unit doubles exist only inside temporary test directories.

## Deviations

1. **Three shared tests failed at `09e96e5` by consequence, now corrected under V1-019.** `tests/visual/test_render_cli.py::test_check_on_bootstrap_repository_reports_planned_assets` (expected exit 0 and eight planned assets), `::test_only_planned_asset_exits_one` (expected `not implemented (planned in Task 11)`) and `::test_render_script_runs_without_fonttools` (expected `--check` exit 0 in a bootstrap repository) assumed the hero had no renderer. With the renderer registered and no pinned fonts, `--check` reports the hero's missing font as an error and exits 1, which is the fail-loud behaviour this task requires. The initial 3 failed / 220 passed receipt above is retained as history. Commit `e8cffe5` replaces the stale expectations with explicit missing-font failure, no-output and zero-checked assertions, moves the planned-asset request to `architecture`, and keeps the fontTools-free import/help/check paths (details under Changes). Task 12's branch rewrites the same tests for the how-it-works figure; integration must keep both sets of assertions.
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
5. Reconciliation of `tests/visual/test_render_cli.py` with Task 12's version at integration (Deviation 1): both the how-it-works write-then-check assertions and the hero missing-font assertions must survive.

## Spend

Claude subscription session only. No paid API calls, no model inference, no Jev credits, no downloads.

Time receipt: the initial report estimated "approximately 35 minutes" of wall-clock; that estimate was not measured and is withdrawn. The tool-reported elapsed time of the initial CLI session (through `09e96e5`) is `duration_ms = 783233` (about 13 minutes 3 seconds) with `duration_api_ms = 780872`, as recorded by the Claude CLI result. These are elapsed-time counters supplied by the harness; they do not measure active reasoning time and are not a billing figure. The V1-019 revision session's duration is not available to this executor and is not estimated here; its commits carry git timestamps.
