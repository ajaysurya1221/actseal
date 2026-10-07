# REPORT 15 — Linux agg assertion repair (amendment recorded at `9fa66fa`)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, dispatched by Codex under the amendment recorded at `9fa66fa` ("Preserve prerequisite negative tests after the Linux agg pin"). Worktree `actseal-v1-hero`, branch `claude/v1-15-social-preparation`, continuing from `b11d92d8cdefc304c283ece27856dd12277e9bd4`. No subagent, nested executor, model, account or billing substitution, personal-memory write, key or `.env` access, download, installation, push, merge or publication. No denial occurred.

Status: **the three stale assertions reported as Gate 1 in REPORT 15 integration are corrected with their negative meaning intact, and every suite is green.** Codex's independent pixel review of `docs/assets/social.png` has passed; final source review and exact-head hosted CI remain required before any merge. The Task 15 deliverable is unchanged: `docs/assets/social.png`, 1280×640, SHA-256 `90f82ac2617ddfa8f49c7bd5f80f66b7a83635a63b9d2c5e512ad255c1cdc5ce`. Upload is still the user's manual step and is not claimed.

## Commit

| Commit | Content |
|---|---|
| `7b849ddfc44bbcd8d3aa475e078ab024d9ea20ef` | test(assets): keep the prerequisite negative tests exact after the Linux agg pin |
| (this commit) | docs(v1): this report |

Diff `b11d92d..7b849dd`: `tests/visual/test_tools.py` (+10/−1) and `tests/visual/test_pipeline.py` (+10/−4) only. `git diff --stat b11d92d HEAD -- docs/assets docs/assets/src/actseal_assets docs/assets/src/tools.toml docs/assets/src/fonts docs/assets/src/receipts` is empty: every hero, workflow, font, receipt, manifest and social byte is unchanged.

| File at `7b849dd` | SHA-256 |
|---|---|
| `tests/visual/test_tools.py` | `c522675d6deab3a2ebd036a57a851d19d59dcc48e610f9515bd04b3bfa649db6` |
| `tests/visual/test_pipeline.py` | `ff6c4db7f909b80aed631f201e157f9a7d27e97fa50dc2ba5ed4a96af5998ea2` |

## The three corrections

1. **`test_tools.py::test_verified_binary_requires_cache_and_matching_hash`.** The macOS controls are untouched: not cached → `not cached`; tampered bytes → `does not match pinned`; correct bytes → returns the cached path. After them, two Linux assertions replace the single stale one. agg, now pinned for Linux, must fail with the exact message `agg 1.9.0 is not cached at <cache>/agg-1.9.0/agg-x86_64-unknown-linux-gnu; run setup_tools.py` (the path is also asserted to be the cached-binary path for the Linux artifact). asciinema, still pinned for darwin-arm64 only, must still be refused with `no pinned artifact for platform linux-x86_64`. The no-pin rejection is therefore kept, on a tool where it is still true.
2. **`test_tools.py::test_manifest_validation_rejects_bad_entries`.** The fixture rewrites every `platform = "linux-x86_64"` to `windows-arm64`; since the manifest now has two Linux artifacts, the expected error list gains `agg/agg-x86_64-unknown-linux-gnu: unknown platform 'windows-arm64'` between the agg sha256 error and the resvg line, in manifest order. One more rejection is required; none removed.
3. **`test_pipeline.py::test_planned_asset_requirements_are_informational[linux-x86_64]`.** The Linux parametrization expects `requires agg 1.9.0: agg 1.9.0 is not cached at {cache}/agg-1.9.0/agg-x86_64-unknown-linux-gnu; run setup_tools.py`; the test still requires `report.ok`, no errors, exactly the two informational diagnostics (`info`, `info`), `planned == ["probe"]` and `checked == []`. The docstring's "no pinned artifact in the audit" sentence, now false, is replaced by "both pinned since V1-031, neither cached".

No product or tool implementation, pin, fixture architecture or failure suppression changed. No test was skipped, marked xfail or loosened to a prefix where it was exact before.

## Commands and results at `7b849dd`

| Command | Result | Exit |
|---|---|---|
| `UV_OFFLINE=1 uv run --frozen --group assets pytest tests/visual/test_tools.py tests/visual/test_pipeline.py` | 62 passed | 0 |
| **`UV_OFFLINE=1 uv run --frozen --group assets pytest tests/visual`** | **283 passed** in 1.32 s (was 3 failed / 280 passed at `b11d92d`) | 0 |
| **`uv run --frozen pytest -m "not integration and not packaging"`** | **2958 passed**, 20 deselected in 63.94 s (was 3 failed / 2955 passed) | 0 |
| `uv run --frozen python -c "… sys.modules['fontTools'] = None … pytest.main(['tests/visual'])"` | 267 passed, 11 skipped (`test_outline.py`, 10 fontTools unit-double hero tests) | 0 |
| **`uv run --frozen mypy --strict docs/assets/src`** | Success: no issues found in 14 source files | 0 |
| `uv run --frozen mypy --strict tests/visual/test_tools.py tests/visual/test_pipeline.py` | Success: no issues found in 2 source files | 0 |
| **`uv run --frozen pre-commit run --all-files`** | ruff check Passed; ruff format --check Passed; mypy --strict Passed | 0 |
| `uv run --frozen ruff format` / `ruff check` on the two files | 2 files left unchanged / All checks passed | 0 |
| **`uv run --frozen --group assets python docs/assets/src/render.py --check`** | hero 4 ok, how-it-works 4 ok, social ok, five planned `[info]`; `check: 3 asset(s) checked; 5 planned/not implemented; 0 error(s)` | 0 |
| `git diff --check` before commit; `git status --short` after | clean | 0 |

History retained: the 3 failed / 280 passed and 3 failed / 2955 passed receipts at `b11d92d` stand in REPORT 15 integration and are not rewritten.

## Remaining gates

1. Codex final source review of the combined branch diff against main `20b9969` (now including `7b849dd`).
2. Exact-head hosted CI on the reviewed commit.
3. Codex ACCEPT; the combined PR may then supersede isolated hero PR 25 with no accepted asset dropped.
4. Final blind README ten-second test (Task 08) remains mandatory.
5. Manual upload of `docs/assets/social.png` by the user; not performed, not claimed.
6. Linux agg stays a pin only: no execution, compatibility claim or GIF validation until Task 14/09.

## Spend

Claude subscription session only. No downloads, no paid API calls, no live providers. Commits carry git timestamps.
