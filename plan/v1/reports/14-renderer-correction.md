# REPORT 14 (renderer correction)

Repair of REVIEW 14 (standalone renderer preparation, REVISE at `c788dad19fd49368ed882aa97a3a3105b25f816d`, reviewed `demo.py` SHA-256 `a5d8cc05…`) under amendment V1-046. Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, same direct session on `claude/v1-14-recording-preparation`. No subagent, nested executor, other model, billing or credential change, personal memory write, permission change, network, download, capture, preview, package execution, or invocation of `uvx`, `asciinema`, `agg`, `resvg` or `setup_tools.py`. All earlier Task 14 reports are preserved unchanged; this report is additive.

Status: **PARTIAL**. Prepublication offline authoring-code repair only. No cast, product GIF, provenance receipt, inventory registration or Task 14 acceptance exists; genuine post-publication rendering, provenance binding and pixel review remain the later gate.

## Corrections by finding

Owned edits: `docs/assets/src/actseal_assets/demo.py`, `tests/visual/test_demo_render.py`, the step 7 inline GIF walker and the stale step 1 download sentence in `docs/assets/src/recording.md`, and this report. The procedure's final Pending section, other reports, inventory, package init, tools/checks/pipeline helpers, `demo_session.py`, pins, dependencies, README and product code are untouched.

1. **One graphic control per following image.** `measure_gif` now keeps a single `pending` control. A second control before any image is `duplicate graphic control extension at byte N`; a control still pending at the trailer is `dangling graphic control extension with no following image`. An image's delay is its own pending control's delay or zero; unshown time is never counted. The fixed graphic control block is validated explicitly: block size byte must be 4, four body bytes, then a `0x00` terminator (`malformed graphic control extension at byte N: block size S` / `: no terminator`).
2. **Complete bounded structural validation.** A `_Reader` cursor performs every read with an explicit bound and raises `DemoError("GIF ends inside <what> at byte N")` on truncation; nothing indexes bytes directly. Validated in order: signature (checked first so a PNG still reads `not a GIF file`), 13-byte logical screen descriptor, global colour table, each extension introducer and label, sub-block sequences through their terminator, the 9-byte image descriptor with non-zero width and height, the local colour table, the LZW minimum code size (2 to 8), and image data that must contain at least one non-empty sub-block before its terminator (`image at byte N has no image data`). Trailing bytes after the trailer remain an error. The docstrings and the procedure state plainly that this is structural validation without LZW pixel decoding; no image decoder was added.
3. **Early byte cap.** `measure_gif` refuses `len(data) > 3_000_000` before any walk (`not parsed`); `validate_gif` rejects `len(data) >= 3_000_000` first, keeping the strict less-than rule; new `read_bounded(path)` reads at most the cap plus one byte and refuses an oversized file unread. `render_variant` uses `read_bounded` instead of `read_bytes`.
4. **Cast structural rules.** Every output event before the final exit must carry a string payload (`line N: output payload is not a string`); the shared parser's silent skip of non-string output is covered by a test that shows `check_cast` passing while the renderer rejects. The header `env` must be a JSON object whose keys are exactly `TERM` and `LANG` with string values (`header lacks an env object` / `header env keys [...]`). The module docstring, `validate_cast` docstring and the procedure now state that command and exit markers are consistency checks on recorded text, not proof of execution or PyPI provenance; the step 3/5 post-publication binding receipt remains necessary.
5. **Per-variant agg reverification.** `render_variant` no longer receives a binary path; it calls `require_agg(context)` (hence `tools.verified_binary`, which re-hashes) immediately before `tools.run_tool` for each variant. `render` still verifies once up front so a missing or tampered cache fails before the cast is parsed; a successful render performs three verifications. The procedure's step 1 sentence claiming official downloads are permission-blocked is replaced: tools are fetched only by the accepted `setup_tools.py` provisioning path, and provisioning history is separate from this task's own unrun genuine rendering. The stale "permission-blocked" statements in REPORT 14 (renderer preparation) and the procedure's final Pending section (Task 08 ownership) are corrected only here, not edited in place.

The step 7 inline walker in `recording.md` is replaced by one `uv run … python -c` invocation of `demo.read_bounded` plus `demo.validate_gif` per rendered file, so the procedure and the renderer apply the same validator; the required outcome is stated in terms of the returned facts.

## Review regression inputs (exact `bytes.fromhex` from the review)

| Input | Before (reviewed `a5d8cc05…`) | Now |
|---|---|---|
| `dangling_delay` | accepted as 20.00 s, 1 frame | `DemoError: dangling graphic control extension with no following image` |
| `duplicate_controls` | accepted as 20.00 s, 1 frame | `DemoError: duplicate graphic control extension at byte 27` |
| `ten_byte_header` | uncaught `IndexError` | `DemoError: GIF ends inside the header at byte 0` |
| `empty_lzw_image` | accepted as 1 frame, 20.00 s | `DemoError: image at byte 27 has no image data` |

Each is a parametrized test through both `measure_gif` and `validate_gif`.

## Tests added (test file now 39 functions, 88 cases, all offline synthetic fixtures)

Review regression inputs; unshown control time (a control separated from its image by a comment extension still counts once; an image with no control counts zero); seventeen truncation/malformation cases (global table, block stream, extension introducer, fixed GCE body/terminator/extra block/wrong size, comment sub-block, image descriptor, local table, code-size byte, image-data sub-block and length, code size 1 and 9, zero-size image); early cap (3,000,001 bytes refused before parsing, exactly 3,000,000 refused by `validate_gif`, `read_bounded` refusing a 4,000,006-byte synthetic file and returning a small one intact); non-string output payloads for five value kinds; seven header-env negatives (missing, string, subset, extra `SHELL`, extra `AWS_SECRET`, non-string value, empty); cached agg changed between variants (verification 3 fails, exactly one variant ran, no dark output). Existing expectations updated for the new verification count and messages.

## Commands and results (separate literal commands)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets pytest tests/visual/test_demo_render.py` | 88 passed in 0.41s | 0 |
| `uv run --frozen --group assets pytest tests/visual` | 410 passed, 1 failed: `test_how_it_works.py::test_committed_assets_match_regeneration_in_this_checkout` (README references four `architecture*.svg` files Task 13 has not produced; pre-existing, unchanged by this work) | 1 |
| `uv run --frozen mypy --strict docs/assets/src tests/visual/test_demo_render.py` | Success: no issues found in 17 source files | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict all Passed | 0 |
| `git diff --check` | clean | 0 |
| `uv run --frozen ruff format --check .` (extra) | 413 files already formatted | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` (extra) | `demo: not implemented (planned in Task 14)`; `demo: source docs/assets/src/demo.cast is not present`; 4 errors, all the pre-existing README architecture references | 1 |

The known missing-architecture failure remains visible and is not skipped. Intermediate test-expectation mismatches from the new message wording (signature-first ordering, truncated header, missing trailer now reported as a truncated block stream) were corrected before commit; one lint fix (`ruff format` on the test file) was applied.

## Honest limits

- Structural validation only: no LZW decoding, no pixel comparison. Real-pixel review of the genuine GIFs is Codex's post-publication step.
- Cast marker and header checks establish consistency with the procedure, not that the commands executed or that the package was the public PyPI 1.0.0 release; the separate binding receipt is required.
- Inventory still declares `demo.gif` with `renderer=None`; no `demo.cast`, GIF or receipt exists in the checkout.
- `demo.py` SHA-256 after this repair: `763dc2851f646a9c96417587d7d8754faa3e6379856b6c95ff609c2d9dda8875` (recomputed on commit if formatting changes nothing further; the committed blob is authoritative).

## Spend

No paid API calls, model inference, downloads or Jev requests. Claude subscription session only. Actual CLI elapsed time: unknown (no tool metadata exposed); no figure is invented.
