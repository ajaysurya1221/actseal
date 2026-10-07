# REPORT 13R — label floor at the measured GitHub README widths

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, the existing Task 13 session on `claude/v1-13-architecture-preparation`. Source commit at dispatch: `c84d515de1c4b76529178496e4673ceef68afaf7` (REVIEW 13 real README sizing, REVISE). No merge command was run. No subagent, other model or nested Claude. No personal-memory writes, downloads, secrets, provider or model call, push, main merge or publication. Every earlier report (`13-preparation.md`, `13-blocked*.md`, `13-manual-unblock-completion.md`) is unchanged. No product, registry, pin, font, validator, root README, ADR or planning file was touched; `git diff --stat 7820dba HEAD` over `src/` shows only the human-merged Task 19 integration.

Status: **DONE** for the Task 13R scope. All six done-when commands pass with exit 0. Temporary pixels at 838, 294 and 254 px were rendered with the pinned resvg and inspected by the executor. Codex's independent review, the Task 08R README responsive change (mobile below 1280 px), the fresh repository first-screen test and exact-head hosted CI remain.

## What changed and why

The validator computes a label's rendered size as font size × (display width ÷ SVG width) and requires 14 px. With the measured widths (838 px desktop at 1280/1366 px viewports; 254 px mobile at a 320 px viewport, 294 px at 360), the previous sizes gave:

| Figure, variant | Before | Rendered before | After | Rendered after |
|---|---|---|---|---|
| how-it-works desktop (1600 wide) | 26 units | 13.62 px | **27 units** | 14.14 px |
| how-it-works mobile (720 wide) | 30 units | 10.58 px (at 254), 12.25 px (at 294) | **40 units** | 14.11 px (at 254), 16.33 px (at 294) |
| architecture desktop | 26 units | 13.62 px | **27 units** | 14.14 px |
| architecture mobile | 30 units | 10.58 px | **40 units** | 14.11 px |
| hero mobile caption and step labels | 30 units | 10.58 px | **40 units** | 14.11 px |
| hero desktop caption and labels | 28 units | 14.67 px | 28 units (unchanged) | 14.67 px |

The floor, the validator and the width model are unchanged. Text was never shrunk; columns were widened by trimming margins, gaps and padding, notes and arrow labels now wrap on word boundaries, and the stacked canvases grew where the taller type needed it.

### Dimensions

| Output | Before | After |
|---|---|---|
| `hero-light.svg`, `hero-dark.svg` | 1600×400 | 1600×400, **bytes unchanged** |
| `hero-mobile-light.svg`, `hero-mobile-dark.svg` | 720×561 | 720×658 |
| `how-it-works-light.svg`, `how-it-works-dark.svg` | 1600×400 | 1600×400 (same canvas; columns 294.4 wide instead of 288, inner 270.4) |
| `how-it-works-mobile-light.svg`, `how-it-works-mobile-dark.svg` | 720×1790 | 720×2152 |
| `architecture-light.svg`, `architecture-dark.svg` | 1600×980 | 1600×980 (same canvas; columns 371 wide instead of 358, inner 347) |
| `architecture-mobile-light.svg`, `architecture-mobile-dark.svg` | 720×2166 | 720×3148 |
| `social.png` | 1280×640 | unchanged |

### Per-file changes

- `inventory.py`: `README_DISPLAY_WIDTH` 880→**838**, `MOBILE_DISPLAY_WIDTH` 360→**254**, with the measurement source in the comment. Nothing else.
- `hero.py`: the two display-width constants match inventory; mobile `tagline` 40→42, `caption` 30→40, `label` 30→40, `caption_step` 40→50, `caption_baseline` 452→476, `motif_top` 262→264, `pill_height` 68→76; `MOBILE_CAPTION_LINES` re-broken into four lines ("Replay cannot authenticate" / "responses, prove inference" / "occurred, or establish" / "label truth.") that rejoin to the approved caption exactly (`validate_copy` enforces this). Desktop `Canvas` untouched. Measured with the real JetBrains Mono advances at render time.
- `how_it_works.py`: desktop `label`/`body` 26→27, `pad` 14→12, `DESKTOP_MARGIN` 20→16, `DESKTOP_GAP` 30→24; mobile `heading` 44→48, `label`/`body` 30→40, `line` 38→50. Content table, commands, palette, arrows unchanged.
- `architecture.py`: desktop `body` 26→27, `pad` 16→12, `DESKTOP_MARGIN` 20→16, `DESKTOP_COLUMN_GAP` 36→28; mobile `heading` 36→44, `heading_line` 42→50, `body` 30→40, `line` 40→52, `MOBILE_GAP` 60→130; `layout()` wraps each note on spaces; `_label()` wraps an arrow label on spaces and centres the lines on the original baseline. Groups, modules, edges, palette unchanged.
- Tests (three figure files): inventory widths asserted as 838/254; new `test_every_label_clears_the_floor_at_the_measured_readme_widths` in the how-it-works and architecture files computes every label's effective size from its font size and the asset's declared display width, requires ≥14 px, and shows the earlier 26/30-unit sizes fail there; hero tests assert the new rendered sizes (14.665 and 14.111 px), that 30 mobile units would fail at 254 px, the four-line caption and `mobile_height() == 658`; architecture tests accept wrapped headings/notes/labels by rejoining them per element group, use an unbreakable word for the overflow test, and update the pure wrap-model expectations to the new sizes. Every module, edge, geometry, no-overlap, light/dark parity, forbidden-language and missing-font/missing-resvg negative check is retained.
- `docs/assets/src/README.md`: the how-it-works and architecture size paragraphs updated; a new "Measured display widths" section records the measurements, the validation rule and that these are one page's measurements, not a GitHub guarantee.
- `tests/visual/test_pipeline.py` and `test_render_cli.py`: no change needed; neither asserts a display width.

Not touched, as required: `checks.py` (floor and algorithm), `svg.py`, `pipeline.py`, `social.py`, `tools.toml`, fonts, `hero-light.svg`, `hero-dark.svg`, `social.png`, product code, root README, ADRs, planning files.

## Commits (after `c84d515`)

| Commit | Subject |
|---|---|
| `af907860817ad6f1b3ca3d8eb063b09cc61861c9` | fix(assets): validate figures at the measured 838/254 px README image widths |
| `153e45450be5117cee35bf1a93ccee0300d8c95a` | fix(assets): raise hero mobile type to 40 units for the 254 px column |
| `c08790e02876a154e212b6607264fbaed9621911` | fix(assets): raise how-it-works labels to 27 desktop and 40 mobile units |
| `f2986e00c581227181c924bc57b425e14527e0aa` | fix(assets): raise architecture labels to 27 desktop and 40 mobile units |
| `d710c34dfc32d8ff32f402d5ff2ad009fd1db593` | test(assets): pin the measured display widths and effective label sizes |
| `4f67761969a89e8c15323afa06b5bfb339440626` | assets: regenerate the ten variants affected by the measured widths |
| `7b866926f77d87550f8d814346a15fbe9c7282a7` | docs(assets): record the measured display widths and new label sizes |
| (this report) | docs(v1): REPORT 13R |

Owned-file blobs at HEAD: `inventory.py` `6e47cbbe6f5eb8f17b7f3b4b0ae9dc7ac41a29b8`; `hero.py` `1b5324e2d306c9b46b9f260024d6128ab9cf411f`; `how_it_works.py` `e701ea2dae493686fcfc6a663f0cf7688e5dce85`; `architecture.py` `afae23d523036d3b27de2f5ff9f7f372c78321fb`; `test_hero.py` `620900d83d8584275fbd43e66bd152929a6724b4`; `test_how_it_works.py` `00551e7dca50a487ad494b5bb89264896abd9622`; `test_architecture.py` `03b3787016700536580a2696b6c618e2313b7cc5`; `docs/assets/src/README.md` `457dad7ab2a58f0c533661ba638d0ad307da867a`.

### Generated outputs (SHA-256; `render.py --check` confirms byte-identical regeneration)

| Output | Bytes | SHA-256 |
|---|---|---|
| `hero-light.svg` (unchanged) | 64,768 | `19a8f20f4987d69481622d372d6eb5de2262896a1b8f2db62d0f2ce7989b3fe6` |
| `hero-dark.svg` (unchanged) | 64,768 | `77bb337db71e1224df3d83f43cf73754e84201d93cabf61c62f63d3492b3d324` |
| `hero-mobile-light.svg` | 58,228 | `01c44de097ca4bd038a3a561517a86a4900a2c466e4eb21b7c344c785c1ee99d` |
| `hero-mobile-dark.svg` | 58,228 | `e610e7728da731442072daf384f7af6b5452b437b52e44dceb4e05157c500db2` |
| `how-it-works-light.svg` | 6,426 | `269434512d23a6aadf7a8ac1865d2f0ccfadfa34e3f058b8393efd0ce7ad8d68` |
| `how-it-works-dark.svg` | 6,426 | `c64274d9e6e77575dae38890c9f64fb513bd37085a615e239c424c285e4a9b95` |
| `how-it-works-mobile-light.svg` | 5,944 | `86625844b6574153e0400b2e33b88901e7a35d3a7a516f144e3ba5befac42c88` |
| `how-it-works-mobile-dark.svg` | 5,944 | `9b89832fd09830d91dc38d7e2373a957e0260c78b99829cbb94bc76b5879faad` |
| `architecture-light.svg` | 9,788 | `70da3481ee78b9c88a99352b0c65b33348761b713ec99ab4c49150215b752281` |
| `architecture-dark.svg` | 9,788 | `24a803c3083ff880298288d6a92db6f933a4315ea4635e4d613952574397efe5` |
| `architecture-mobile-light.svg` | 9,864 | `8ec07e248a49ce166eeeb0207978443d8c42886584c011875c30e78b9c4f9ea8` |
| `architecture-mobile-dark.svg` | 9,864 | `63009d178e9f832e2f53ce1b9190bf2ca6d576e956eb90986f47ca15cbb1a149` |

## Done-when commands (each run separately, after the last code change)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets python docs/assets/src/render.py --check` | 12 SVG variants and `social.png` match regeneration; `check: 4 asset(s) checked; 4 planned/not implemented; 0 error(s)` | 0 |
| `uv run --frozen --group assets pytest tests/visual` | 337 passed | 0 |
| `uv run --frozen mypy --strict docs/assets/src tests/visual` | Success: no issues found in 29 source files | 0 |
| `uv run --frozen pytest -m "not integration and not packaging"` | 3898 passed, 27 deselected in 74.94 s | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict: Passed | 0 |
| `git diff --check` | clean | 0 |

Supporting runs: `render.py --write --only hero`, `--only how-it-works`, `--only architecture` (4 files each, 0 errors); the three figure test files alone (103 passed); `ruff check` on the seven owned Python files (clean after two line-length/literal fixes). Integration and packaging markers were not run (unchanged by this task). Hosted CI has not run on this branch.

## Actual pixels (temporary; not committed, not deliverables)

Rendered by the cached pinned resvg 0.48.1 (`/Users/ajay/.cache/actseal-assets/resvg-0.48.1/resvg`, re-verified against `tools.toml` in the previous dispatch; the same binary and archive are still in place) as `resvg --width N docs/assets/<file>.svg /tmp/actseal-arch-review/<name>.png`, system fonts allowed so the generic sans-serif stack resolves. resvg reported "Fallback from Helvetica to Arial Unicode MS" for the how-it-works renders; that is the arrow and middle-dot glyphs, which Helvetica lacks on this machine, and does not affect label sizes.

| Path | SHA-256 |
|---|---|
| `/tmp/actseal-arch-review/hero-light-838.png` | `6741691c5fbd50576ba7ed3d3c063872f7695b379ccd657642ea608d19dbe0c0` |
| `/tmp/actseal-arch-review/hero-dark-838.png` | `cf88e31c576d91586b88961527a543a79922d0a7cae2952b5e019590e996fe05` |
| `/tmp/actseal-arch-review/hero-mobile-light-294.png` | `e609c9fa3777294a80af8a1a7bbf14c01534edee79a249b96f6789574a9e5927` |
| `/tmp/actseal-arch-review/hero-mobile-light-254.png` | `e0c5dc0ce3b124266dd3da302e9264159286a1e546d5e0d64bd7735a10962e8f` |
| `/tmp/actseal-arch-review/hero-mobile-dark-294.png` | `482985920c10af980ea15aeecf57222bfb22bec7ea8204fc087a41364b0d662c` |
| `/tmp/actseal-arch-review/hero-mobile-dark-254.png` | `77b7c0df1b65bc34c3311265de0ee87881a02972630a226b03487777bb18dc17` |
| `/tmp/actseal-arch-review/how-it-works-light-838.png` | `5cc2d25eda3cfbfaa7a1e9be04688e7207cfa95c41e3a15f941ac5e0d431c408` |
| `/tmp/actseal-arch-review/how-it-works-dark-838.png` | `d303ab2a5b97bc6369b914e91dbb42ee811303545d3296c6d1e2308efdedffa6` |
| `/tmp/actseal-arch-review/how-it-works-mobile-light-294.png` | `fc82446a409677812e248b20ab13bd4463a847988f8aaef548385593c516a3f3` |
| `/tmp/actseal-arch-review/how-it-works-mobile-light-254.png` | `5b4e1982464c8b6eb0afbea9a20e62bcf6f8e13b5be8e80e41208fa1f4d4041b` |
| `/tmp/actseal-arch-review/how-it-works-mobile-dark-294.png` | `a82cf55d3a8cda56cd7a0ca707e7654c538c2067e009910e2620d07c51a6e384` |
| `/tmp/actseal-arch-review/how-it-works-mobile-dark-254.png` | `af5ebd4901027e45f5a8a4bea1b981dab8ea77faa0dae09baf1b788797ff2772` |
| `/tmp/actseal-arch-review/architecture-light-838.png` | `0e327a54128e9b084e22b2dfaa5a5302779f5f22d8df3a076d180c45a18ed2f8` |
| `/tmp/actseal-arch-review/architecture-dark-838.png` | `cd1dd16979c36e5dd5ac6b513e7019a8b64c72d512f15a1a831b9dd173eaa98d` |
| `/tmp/actseal-arch-review/architecture-mobile-light-294.png` | `5581d25cf74c09cdee77b41513d5fa9d0dace7c3291eaa491db945e7ef717b30` |
| `/tmp/actseal-arch-review/architecture-mobile-light-254.png` | `5aad7938873b578bcbb452ec6088fc6b69efc377c16834fc0213cfaca5a168a2` |
| `/tmp/actseal-arch-review/architecture-mobile-dark-294.png` | `a04b92495574eba9c333fb8f7dd631d6f80d56844eaf6df6a7128f32eec7576a` |
| `/tmp/actseal-arch-review/architecture-mobile-dark-254.png` | `5e4f16dd0b4eadcd9ebbf3aa170c4a1c82be4fa801e3a5cd51c9034583e9705c` |

Executor's reading of nine of those images (hero, how-it-works and architecture: light at 838, light at 254, dark at 294), distinct from the structural tests: every label legible, no clipping, no overlap; hero mobile caption on four lines above the margin; how-it-works mobile decision and verdict runs wrap to two lines inside their boxes; architecture mobile wraps the "Assessment / statistics / faults" heading, the long assessment note and the "verdict, records, faults" label, each staying clear of arrows and dividers. The standalone PNGs show the SVG at the measured widths; they are not browser evidence of the repository page.

## Deviations and judgement calls

1. **Mobile canvases are taller**: hero 561→658, how-it-works 1790→2152, architecture 2166→3148 units. At 254 px these display at roughly 232, 759 and 1111 px tall. Taller type at the same column width leaves no alternative that does not shrink or remove content.
2. **Hero mobile caption is four lines, not three**, and the tagline is 42 units: at 40-unit JetBrains Mono (600/1000 em) a 680-unit column holds 28 characters, so the approved caption cannot stay on three lines; the rejoined text is byte-identical to the approved copy.
3. **Desktop how-it-works and architecture keep their canvases** by trimming margins, gaps and padding (4 to 8 units each); the width model's 8 % safety factor still applies to every line.
4. **Floor margin is thin by design**: 27 and 40 units give 14.14 and 14.11 px at 838 and 254, the smallest whole-unit sizes that clear 14 px. Any further reduction of the measured widths (for example a narrower GitHub layout) would fail the validator rather than silently undersize.
5. **Architecture mobile return arrows** still run in left channels 12 units apart (about 4 px at 254); noted previously, unchanged, visibly distinct in the 254 px render.
6. `visual_support.make_output` keeps its probe default of 880 px; it is a test helper outside this task's ownership and its 28-unit probe still clears the floor at 838.

## Open issues

- Task 08R must switch the README to mobile variants below 1280 px and desktop at 1280 px and above; until then intermediate viewports receive the desktop variant at less than 838 px and the 27-unit labels fall below 14 px there (for example 13.0 px at a 1000 px viewport's 638 px image). That is the README's selection, outside this task.
- Codex's independent pixel review at measured widths, the fresh repository first-screen test and exact-head hosted CI remain.

## Spend

Claude subscription session only; cost not measured. No paid API calls, no model inference, no Jev credit, no downloads. Eighteen resvg invocations ran the already-cached pinned binary. Commits are timestamped 7 October 2026 (IST); this report follows immediately after.
