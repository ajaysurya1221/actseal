# REPORT 15 — integration and completion candidate (V1-029, V1-030, V1-031)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, dispatched by Codex under the human's 7 October approval and amendments V1-029, V1-030 and V1-031. Worktree `actseal-v1-hero`, branch `claude/v1-15-social-preparation`, continuing from `7bb32f4ca78194d5316e0615528420a521cdf78a`. No subagent, nested executor, model or billing substitution, personal-memory write, secret or `.env` read, push, merge or publication. One network download was performed, expressly approved: `setup_tools.py --tool resvg`. No Linux binary was downloaded or executed. No denial occurred. No browser, data URL, local server or raw CDP was used in this session; the pixel review below reads the committed PNG produced by the pinned resvg.

Status: **Task 15 done-when passes; `docs/assets/social.png` is delivered at exactly 1280×640.** Reviewed main `20b996917c25111bc9b043f22db000be0ff8fcdc` is merged into this branch with only the two authorized conflict resolutions. All accepted hero, font, receipt and workflow bytes are unchanged. **Three unowned test assertions are stale by consequence of the authorized Linux agg pin and were not edited; the full visual suite therefore reports 3 failed / 280 passed until Codex authorizes their bounded correction (Gate 1 below).** Everything else is green. No upload was performed or is claimed. Codex ACCEPT, actual pixel review by Codex, exact-head hosted CI and the final blind README test remain required.

## Commits on this branch after `7bb32f4`

| Commit | Content |
|---|---|
| `58535ee4b80b19877ac015878e4b4285ec240840` | Merge reviewed main `20b9969` (accepted Task 12, V1-030/V1-031). Conflicts resolved: `docs/assets/src/actseal_assets/inventory.py`, `tests/visual/test_render_cli.py`. |
| `151c7c278864a584f052983050ecdcd3cf156db0` | fix(assets): resvg macOS asset renamed to its official `aarch64` name; one Linux agg pin added; `APPROVED_PINS` updated; resvg receipt recorded. |
| `59840500d820180b9de43a9f5edb8e2a223efe3c` | feat(assets): `docs/assets/social.png` generated. |
| (this commit) | docs(v1): this report. |

Not cherry-picked: `736d912` (duplicate hero isolation), as instructed. No other lane's file was written.

## Merge resolution (`58535ee`)

- **`docs/assets/src/actseal_assets/inventory.py`.** Conflict was the import line only; resolved to `from . import hero, how_it_works, social`. The auto-merged body registers all three renderers: hero with four outlined SVGs (two 1600×400, two 720×561 at 360 CSS px), how-it-works with four SVGs through main's `_svg`/`_mobile_svg` helpers and `how_it_works.render`, social with exactly `social.png` 1280×640 and `social.render`. Architecture, demo, where, matrix and boundary remain planned (`renderer=None`). `validate_inventory()` returns no problems. Neither side was taken whole.
- **`tests/visual/test_render_cli.py`.** Rewritten to carry both lanes' intent (hash `aea3d7f3e70423752c7db21e4e3ce712f478a694f260a5e86e527df489bdf489`, 19 tests):
  - `IMPLEMENTED = ("hero", "how-it-works", "social")`, `PLANNED` = the five others; the partition is asserted against the inventory.
  - Empty task-local tool cache via an autouse fixture, propagated to every subprocess through an explicit `env`; the resvg diagnostic is computed for the running platform and asserted to point under the test cache.
  - Fresh global `--check`: five planned `[info]` lines with no `[error]`; hero font + skipped; social resvg + font + skipped; four `how-it-works … is not committed` errors; exactly 9 `[error]` lines; summary `1 asset(s) checked; 5 planned/not implemented; 9 error(s)`; nothing under `docs/assets`.
  - Global `--write` then `--check`: write exits 1 with exactly the four workflow files written, 5 `[error]` lines and `1 asset(s) checked; 5 planned/not implemented; 5 error(s); 4 file(s) written`; the subsequent check reports four `matches regeneration` lines, the same 5 prerequisite errors and `1 asset(s) checked; 5 planned/not implemented; 5 error(s)`.
  - Workflow-only write then check exits 0 with no `[error]`, in process and in a fontTools-blocked subprocess.
  - Hero-only (2 errors), social-only in both modes (3 errors, nothing written), planned-asset request (`architecture`), usage exit 2, repository root, `--help`, no eager fontTools import, runtime isolation: all preserved. The fontTools-blocked subprocess helper prints `exit=N` so a non-zero status is asserted without hiding output; stderr must be empty.

## Manifest repair and pin addition (`151c7c2`)

- **resvg (V1-029, naming only).** `docs/assets/src/tools.toml` darwin-arm64 artifact: `resvg-macos-arm64.zip` → `resvg-macos-aarch64.zip` in both `url` and `filename`. Platform `darwin-arm64`, version `0.48.1`, SHA-256 `06440eb5aa14a28cbfc7e40ae39e1ffa71adc051b89fbaa913b4f1d9b905d09f`, `member = "resvg"`, source commit and the Linux entry are unchanged. `APPROVED_PINS` key renamed to match. Synthetic nested-archive fixtures in `test_tools.py` untouched.
- **agg Linux (V1-031, pin only).** One new `[[agg.artifacts]]`: platform `linux-x86_64`, URL `https://github.com/asciinema/agg/releases/download/v1.9.0/agg-x86_64-unknown-linux-gnu`, filename `agg-x86_64-unknown-linux-gnu`, SHA-256 `f111e315cd71056b116302342553dd765b7297579ed511f111d0cedb442aeda6`, no `member`. `APPROVED_PINS` gains the matching entry. The binary was not downloaded, installed or executed on this Mac; a matching hash is not an execution receipt, and hosted execution, font-explicit rendering and deterministic GIF regeneration stay Task 14/09 acceptance requirements.
- **resvg setup (approved download).** `uv run --frozen python docs/assets/src/setup_tools.py --tool resvg` → `resvg 0.48.1: installed ~/.cache/actseal-assets/resvg-0.48.1/resvg; receipt docs/assets/src/receipts/resvg-darwin-arm64.json`, exit 0. Receipt: archive `resvg-macos-aarch64.zip` SHA-256 `06440eb5…d09f` (matches the pin), retained beside the member; extracted executable SHA-256 `50e57a945189f74ee89766a2d5b8e1a8e5254416880f9e57b36d1307e71e94ce` (re-hashed locally, identical). `tools.verified_binary` re-hashes the archive, re-extracts and compares bytes before every execution.

## Social asset (`5984050`)

**Delivered file: `docs/assets/social.png`**, 1280×640, 44319 bytes, SHA-256 `90f82ac2617ddfa8f49c7bd5f80f66b7a83635a63b9d2c5e512ad255c1cdc5ce`. Produced by `render.py --write --only social` from the pinned JetBrains Mono files and the verified resvg with `--skip-system-fonts` and the pinned font directory only. Upload through GitHub Settings → General → Social preview is the user's manual step; it has not been done.

Pixel review (this executor, reading the committed PNG): wordmark "Actseal", tagline on two lines, one freeze → run → replay loop with the return route, caption "Replay cannot authenticate responses, prove inference occurred, or establish label truth." on two lines, light palette, nothing else drawn. No clipping or overlap; margins even; smallest text (caption and labels, 36 units = 36 px at 1:1, 18 px at half scale) clearly legible. Codex's independent pixel review is still required.

## Commands and results at `5984050`

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen python docs/assets/src/setup_tools.py --tool resvg` (approved) | installed and verified; receipt written | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --write --only social` | `wrote docs/assets/social.png (44319 bytes)`; `1 asset(s) checked; 0 planned/not implemented; 0 error(s); 1 file(s) written` | 0 |
| **`uv run --frozen --group assets python docs/assets/src/render.py --check --only social`** (Task 15 done-when) | **`docs/assets/social.png matches regeneration (44319 bytes)`; `1 asset(s) checked; 0 planned/not implemented; 0 error(s)`** | **0** |
| `uv run --frozen --group assets python docs/assets/src/render.py --check --only hero` | four `matches regeneration`; 1 checked; 0 errors | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check --only how-it-works` | four `matches regeneration`; 1 checked; 0 errors | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` (full inventory) | hero 4 ok, how-it-works 4 ok, social ok; five planned `[info]`; `3 asset(s) checked; 5 planned/not implemented; 0 error(s)` | 0 |
| `UV_OFFLINE=1 uv run --frozen --group assets pytest tests/visual/test_render_cli.py tests/visual/test_hero.py tests/visual/test_how_it_works.py tests/visual/test_social.py tests/visual/test_tools.py` | **2 failed, 103 passed** (both in `test_tools.py`, Gate 1) | 1 |
| `UV_OFFLINE=1 uv run --frozen --group assets pytest tests/visual` | **3 failed, 280 passed** (Gate 1) | 1 |
| `uv run --frozen python -c "… sys.modules['fontTools'] = None … pytest.main(['tests/visual'])"` | same 3 failed, 264 passed, 11 skipped (`test_outline.py` and the 10 fontTools unit-double hero tests) | 1 |
| `uv run --frozen pytest tests -q -m "not integration and not packaging"` (default suite) | **3 failed, 2955 passed**, 20 deselected in 64.23 s; the same three Gate 1 tests | 1 |
| `uv run --frozen mypy --strict docs/assets/src` | Success: no issues found in 14 source files | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check Passed; ruff format --check Passed; mypy --strict Passed | 0 |
| `uv run --frozen ruff format --check .` / `ruff check .` | 304 files already formatted / All checks passed | 0 |
| `git diff --cached --check` before each commit; `git status --short` after | clean | 0 |

### Unchanged accepted bytes

`git diff --stat` is empty for the following, so every accepted asset is carried byte for byte:

| Comparison | Paths |
|---|---|
| `7bb32f4..HEAD` | `hero-light.svg`, `hero-dark.svg`, `hero-mobile-light.svg`, `hero-mobile-dark.svg`, `docs/assets/src/fonts/*`, receipts `jetbrains-mono-any.json`, `agg-darwin-arm64.json`, `asciinema-darwin-arm64.json`, `hero.py`, `social.py`, `test_hero.py`, `test_social.py` |
| `f712dae..HEAD` and `20b9969..HEAD` | `how-it-works-light.svg`, `how-it-works-dark.svg`, `how-it-works-mobile-light.svg`, `how-it-works-mobile-dark.svg`, `how_it_works.py`, `test_how_it_works.py` |

| Committed asset | SHA-256 |
|---|---|
| `hero-light.svg` | `19a8f20f4987d69481622d372d6eb5de2262896a1b8f2db62d0f2ce7989b3fe6` |
| `hero-dark.svg` | `77bb337db71e1224df3d83f43cf73754e84201d93cabf61c62f63d3492b3d324` |
| `hero-mobile-light.svg` | `0de55733d1a247328da52c793445b9d195d97caafa6aac0f0c8ab269efa990f3` |
| `hero-mobile-dark.svg` | `eeeac139209f95ae6f99cab7ea5770978a28156074eb0ada6585fd731a84d27e` |
| `how-it-works-light.svg` | `6a9df7e85e1813b6f15dc0013572938582db58e31037312457d06b681e6d3702` |
| `how-it-works-dark.svg` | `603656501635b9ba8881bf151c3b4187da58a5cf0562947f342d8637e82f1d91` |
| `how-it-works-mobile-light.svg` | `159a068383295e5471cd08a82f674346f8be987fd9ebc8b50a73c6585938b0ee` |
| `how-it-works-mobile-dark.svg` | `70152ab11af906706b6b923319f64ed637144858fafb4e01a06bea2f6f77b82b` |
| `social.png` | `90f82ac2617ddfa8f49c7bd5f80f66b7a83635a63b9d2c5e512ad255c1cdc5ce` |

Changed-file hashes: `tools.toml` `509b3b211678b219699f806447f419f4e8eb85c90e879e2f4ecdb012448fae57`; `test_tools.py` `27f6630945c20beaf2fdce7c1747f33c7b2c6d75cd29f367c15d0c64481e9995`; `inventory.py` `70a37f961f455f094f2ee0e42d295babc48a23c7981022d2ce15c7aed05b9232`; `receipts/resvg-darwin-arm64.json` `ac385f84501465a1e5a1b7b9e004905d61f937567197cf092e2fbd2acfcbfa90`.

## Gate 1 — three stale assertions caused by the authorized Linux agg pin (not edited; bounded amendment requested)

All three assumed that agg has no `linux-x86_64` artifact, which V1-031 changes by design. They sit outside this lane's ownership (`test_pipeline.py` is unowned; in `test_tools.py` only the `APPROVED_PINS` entries were authorized), so they were left as they are and the suites above report them. Each keeps a meaningful intent that can be preserved without weakening:

1. `tests/visual/test_tools.py::test_verified_binary_requires_cache_and_matching_hash` (line 152): expects `no pinned artifact for platform linux-x86_64` for agg; actual is now `agg 1.9.0 is not cached at <cache>/agg-1.9.0/agg-x86_64-unknown-linux-gnu; run setup_tools.py`. Intent (a platform without a pin is refused) is preservable by asserting it on `asciinema`, which still has only a darwin-arm64 artifact, and additionally asserting the agg Linux "not cached" message.
2. `tests/visual/test_tools.py::test_manifest_validation_rejects_bad_entries`: the fixture rewrites every `platform = "linux-x86_64"` to `windows-arm64`; with two Linux artifacts the expected list needs the extra line `agg/agg-x86_64-unknown-linux-gnu: unknown platform 'windows-arm64'` before the resvg line (manifest order). No check is weakened; one more rejection is asserted.
3. `tests/visual/test_pipeline.py::test_planned_asset_requirements_are_informational[linux-x86_64-…]`: the Linux parametrization expects `agg 1.9.0: no pinned artifact for platform linux-x86_64`; actual is `agg 1.9.0 is not cached at {cache}/agg-1.9.0/agg-x86_64-unknown-linux-gnu; run setup_tools.py`. Intent (an unavailable prerequisite of a planned asset is informational on every platform) is preservable by updating the Linux expectation to the not-cached form, or by parametrizing the "no pinned artifact" case on `asciinema`.

No product code change is needed; `tools.py` and `pipeline.py` behave as designed. Full-suite green is blocked only on this amendment.

## Other gates and notes

- Codex independent review of the combined diff (`20b9969..5984050`: 24 files, 2601 insertions, 31 deletions, of which the branch's own non-asset changes are `inventory.py`, `test_render_cli.py`, `tools.toml`, `test_tools.py`), the actual social pixels and exact-head hosted CI, before the combined PR supersedes isolated hero PR 25. No accepted asset is dropped.
- Final blind README ten-second test (Task 08) remains mandatory; not claimed.
- Linux agg: pin only. No execution, compatibility claim or GIF validation.
- Previous reports and receipts preserved; REPORT 11 completion's Chrome preview stands as an earlier historical observation and was not repeated.
- Implementation and review done directly by Fable 5.1 (dispatch forbids nested executors).

## Spend

Claude subscription session only. One approved pinned download (resvg archive, 1756629 bytes). No paid API calls, no live providers. Commits carry git timestamps.
