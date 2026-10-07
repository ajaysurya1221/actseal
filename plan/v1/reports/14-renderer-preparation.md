# REPORT 14 (renderer preparation)

Amendment V1-044, Task 14 paragraphs only. Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, same direct session on `claude/v1-14-recording-preparation`, which Codex fast-forwarded from `11a31fc` to reviewed integration `b05aed85ccba6efee204a79c4662643ce952c6d2` before this work. No subagent, nested executor, other model, billing or credential change, personal memory write, permission change, download, network call, capture, preview, package execution, or invocation of `uvx`, `asciinema`, `agg`, `resvg` or `setup_tools.py`. REPORT 14, 14R and 14R2 are preserved unchanged.

Status: **PARTIAL**. The missing GIF renderer and its offline tests exist; no cast, product GIF, provenance receipt, inventory registration or Task 14 acceptance exists. The genuine post-PyPI capture, provenance binding, repeated real rendering, pixel review and activation remain the original later gate.

## Changes (owned new files only)

- `docs/assets/src/actseal_assets/demo.py` (new). Frozen outputs `demo-light.gif` and `demo-dark.gif` with agg themes `github-light`/`github-dark` (names confirmed by the parent in pinned `lib.rs` 84-90), one untouched source `demo.cast`, approved geometry 100x40, 20 to 40 s and 3,000,000-byte bounds repeated from the inventory constants (the inventory will import this module, so it cannot import the inventory at load; `RenderContext` is a `TYPE_CHECKING` import and `tools` is imported lazily, as in `social.py`). `require_fonts` demands the hash-pinned JetBrains Mono files from the manifest (presence; hashes stay with the global check), `require_agg` goes through `tools.verified_binary`, `cast_path` refuses a missing or symlinked source. `validate_cast` applies the accepted `checks.check_cast` (parse, duration window, credential scan) and then the procedure's stricter rules: v3 only, 100x40, every event `o` except exactly one final `x` whose payload is the string `"0"`, no `i`/`r`/`m`/unknown codes, and the seven approved command and exit markers from `demo_session.py` in order. The header `command` is read as JSON data only; the module imports no process facility. `measure_gif` walks every block to the trailer (global/local colour tables, extensions, image descriptors, sub-blocks), sums Graphic Control Extension delays in centiseconds, counts frames and rejects truncation, trailing bytes, unknown blocks and malformed extensions; `validate_gif` requires at least one frame, a measured 20 to 40 s and strictly fewer than 3,000,000 bytes, never using header dimensions or flags as duration. `render_variant` writes only into `RenderContext.work`, unlinks any stale target first, builds the command with the reviewed `tools.agg_command` (speed 1, `ceil(duration)+1` idle limit, pinned font dir and family) plus explicit `--last-frame-duration 3` and one `--theme`, runs it through `tools.run_tool`, and fails if the tool exited 0 without writing a regular file. `render` returns both variants from the one cast. Exported functions are internal authoring helpers, not product APIs; no packaged Python or public surface changes.
- `tests/visual/test_demo_render.py` (new, 56 tests, all offline). Synthetic cast and synthetic GIF builders are labelled fixtures under `tmp_path`, never written under the repository's `docs/assets`; doubles replace `tools.verified_binary` and `tools.run_tool`, zero-byte stand-ins satisfy font presence, and the tool cache points at an empty temporary directory. Covered: frozen outputs/themes/bounds and marker equality with `demo_session.STEPS`; inventory still planned with no cast or GIF in the checkout; lazy imports; valid synthetic cast facts; malformed casts (empty, non-UTF-8, bad header, v2, wrong columns/rows, too short, too long); input/resize/marker/unknown events; missing, non-final, non-zero and integer-payload exit events; out-of-order or missing command/exit/summary markers; credential-looking output; header command never executed (marker file plus source scan for process facilities); GIF measurement independent of canvas size with local tables and padding; malformed GIFs (not a GIF, PNG, no trailer, trailing byte, truncation, bad GCE, unknown block); frame/duration/size bounds including both window edges and a near-cap file; prerequisites failing before any tool runs (missing fonts, missing agg against the real pin and empty cache, tampered cached agg refused by the real verifier, unpinned tool names, missing/symlinked/invalid cast); both variants rendered with the exact `agg_command` shape and no `--select`/geometry flags; deterministic repeated rendering and the pipeline's own twice-render check; tool failure propagation; tool writing nothing despite a stale file or stale symlink; per-variant wrong outputs; pipeline write-then-check round trip, missing and stale committed outputs, cast and GIF failures without writing, and the bootstrap repository blocking all prerequisites. The pipeline tests use a temporary asset declaration built in the test, not the real inventory.
- `plan/v1/reports/14-renderer-preparation.md` (this report).

No edits to `inventory.py`, `tools.py`, `checks.py`, `pipeline.py`, `__init__.py`, `recording.md`, `demo_session.py`, pins, dependencies, README, fixtures or any other lane's files. `kit.demo` is bound in the tests by importing the submodule, since the package init does not import it until registration.

## Commands and results

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets pytest tests/visual/test_demo_render.py` | 56 passed in 0.17s | 0 |
| `uv run --frozen --group assets pytest tests/visual` | 378 passed, 1 failed: `test_how_it_works.py::test_committed_assets_match_regeneration_in_this_checkout` (README references four `architecture*.svg` files Task 13 has not produced; same failure on `b05aed8` before this work) | 1 |
| `uv run --frozen mypy --strict docs/assets/src tests/visual/test_demo_render.py` | Success: no issues found in 17 source files | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict all Passed | 0 |
| `git diff --check` | clean | 0 |
| `uv run --frozen ruff format --check .` | 412 files already formatted | 0 |
| `uv run --frozen ruff check docs/assets/src tests/visual` | All checks passed | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` | `demo: not implemented (planned in Task 14)`; `demo: source docs/assets/src/demo.cast is not present`; 3 checked, 5 planned, 4 errors, all four the pre-existing README architecture references | 1 |

The full-visual failure and the four `--check` errors are the known missing architecture assertion, reported and not skipped; nothing in this work touches them. Intermediate failures during development (font presence including the receipt-verified `OFL.txt`, four fixture mistakes in the tests, one unresolved static import under the pre-commit mypy path, one scripted edit that damaged the test file and was rewritten from scratch) were all repaired before this commit.

## Deviations and review-sensitive choices

1. Font presence checks the two hash-pinned TTFs only, as the hero does; the pipeline's `_check_needs` additionally lists `OFL.txt`, so an unfetched notice is still reported there and the global font check enforces its markers once fonts exist.
2. The cast event rule is implemented in `demo.py` rather than `checks.py` (not owned); `check_cast` continues to accept the `x` event and is applied first.
3. `validate_cast` rejects a cast where any non-`o` event precedes the final `x`, including an early `x`, and reports the offending line number.
4. `measure_gif` treats trailing bytes after the trailer as an error rather than ignoring them, so a padded or concatenated file cannot pass.
5. The temporary asset used by pipeline tests mirrors the eventual inventory entry (two GIF outputs, one cast source, `agg` and `jetbrains-mono` needs) but lives only in the test module; the real inventory is unchanged.

## Pending

- Task 20 publication, the genuine post-PyPI capture under `recording.md`, provenance binding, cast receipt, actual agg rendering twice, measured durations/sizes, pixel review by Codex.
- Inventory registration (`renderer=demo.render`, outputs `demo-light.gif`/`demo-dark.gif`), committed `demo.cast` and GIFs, and `render.py --check --only demo` passing, all after the capture is accepted.
- Official tool/font downloads remain permission-blocked; `verified_binary` cannot succeed yet.
- Task 13 architecture assets for the known full-visual failure (other lane).

## Spend

No paid API calls, model inference, downloads or Jev requests. Claude subscription session only. Actual CLI elapsed time: unknown (no tool metadata exposed); no figure is invented.
