# REPORT 14 (renderer final correction)

Repair of REVIEW 14 (bounded renderer correction, REVISE at `d8b10a36df6ec62dc501057e88c26545ae124cc3`) under the existing amendment V1-046. Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, same direct session on `claude/v1-14-recording-preparation`. No subagent, nested executor, other model, billing or credential change, personal memory write, permission change, network, download, capture, rendering, media, keys, or invocation of `uvx`, `asciinema`, `agg`, `resvg` or `setup_tools.py`. All earlier Task 14 reports are preserved unchanged; this report is additive. The five earlier repairs are preserved and still covered by their tests.

Status: **PARTIAL**. Offline authoring-code correction only. No cast, product GIF, provenance receipt, inventory registration or Task 14 acceptance exists; genuine post-publication rendering, provenance binding and pixel review remain the later gate.

## Corrections by finding

Owned edits: `docs/assets/src/actseal_assets/demo.py`, `tests/visual/test_demo_render.py`, the single step 7 proof phrase in `docs/assets/src/recording.md`, and this report. Nothing else changed.

1. **Supported extension subset only.** The generic "skip any other extension" branch is gone. `_extension` handles exactly three labels: graphic control (`0xF9`, at most one pending, unchanged association with the following image), comment (`0xFE`, bounded sub-blocks) and application (`0xFF`), for which new `_application` requires the 11-byte header block (`malformed application extension at byte N: header block size S` otherwise) followed by bounded sub-blocks through the terminator. Plain-text (`0x01`) and every other label raise `unsupported extension label 0xNN at byte N`. A pending graphic control survives only a comment or a well-formed application extension and must still be followed by an image, so the dangling and duplicate rules apply across them. No pixel decoding or general decoder was added; the `measure_gif` docstring names the subset.
2. **Step 7 wording.** The sentence "that proof is the step 3/5 binding" is replaced: the structural checks "cannot authenticate the output or establish that the commands ran or that the package came from PyPI. The separately recorded step 3/5 binding and its receipt provide supporting evidence for those claims; no structural check proves them." No other line of the procedure changed (see the three-line diff below).

## Review probes (inserted after a 2000 cs control, before the image)

| Insert | Before (`d8b10a3`) | Now |
|---|---|---|
| `21ff00` | accepted, 20.00 s | `DemoError: malformed application extension at byte 27: header block size 0` |
| `210100` | accepted, 20.00 s | `DemoError: unsupported extension label 0x01 at byte 27` |
| `210000` | accepted, 20.00 s | `DemoError: unsupported extension label 0x00 at byte 27` |
| `21ff0b NETSCAPE2.0 03 01 00 00 00` (correctly shaped) | accepted | accepted: 1 frame, 2000 cs |

## Tests added (file now 42 functions, 103 cases, all offline synthetic fixtures)

- `test_unsupported_or_malformed_extensions_are_rejected`: the three review inserts, a 10-byte application header, labels `0xF0` and `0xF1`, each checked with a preceding control (offset 27) and without (offset 19); every case carries the complete image and trailer so only the extension rule can reject it.
- `test_truncated_supported_extensions_are_demo_errors`: eight application and comment extensions cut at the introducer, inside the header, at the sub-block length, inside a sub-block and before the terminator, with and without a pending control.
- `test_well_formed_application_extension_keeps_the_pending_control`: Netscape extension before the control, between control and image, dangling across it, duplicate across it, and the synthetic padding fixture (an 11-byte application header) still measuring 2500 cs.
- Existing comment truncation expectation updated to the new message wording (`comment extension sub-block`). All earlier negatives, the four prior review inputs, cap, payload, env and agg reverification tests remain.

## Commands and results (separate literal commands)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets pytest tests/visual/test_demo_render.py` | 103 passed in 0.25s | 0 |
| `uv run --frozen --group assets pytest tests/visual` | 425 passed, 1 failed: `test_how_it_works.py::test_committed_assets_match_regeneration_in_this_checkout` (README references four `architecture*.svg` files Task 13 has not produced; pre-existing, not skipped) | 1 |
| `uv run --frozen mypy --strict docs/assets/src tests/visual/test_demo_render.py` | Success: no issues found in 17 source files | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict all Passed | 0 |
| `git diff --check` | clean | 0 |
| `uv run --frozen ruff format --check .` (extra) | 414 files already formatted | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` (extra) | `demo: not implemented (planned in Task 14)`; `demo: source docs/assets/src/demo.cast is not present`; 4 errors, all the pre-existing README architecture references | 1 |

Intermediate test-only mistakes were corrected before commit: my first probe test hard-coded a byte offset that differs with and without a preceding control, and appended an image to truncation inputs so they were not truncated; the probes were split into a complete-shape test asserting both offsets and a truncation test whose inputs end at the cut. The validator itself rejected all three review inserts on the first run.

## Honest limits

- Structural validation only: no LZW decoding or pixel comparison; real-pixel review of genuine GIFs is Codex's post-publication step.
- Cast marker, header and GIF checks establish consistency with the procedure. They do not authenticate output or prove execution or PyPI provenance; the step 3/5 binding receipt is supporting evidence recorded separately.
- Inventory still declares `demo.gif` with `renderer=None`; no `demo.cast`, GIF or receipt exists.
- `demo.py` SHA-256 after this correction: `b39db41fa4770b506e25ecfc2a7a5e6e59ed7138159881d86c8614fdd064f4b1`.

## Spend

No paid API calls, model inference, downloads or Jev requests. Claude subscription session only. Actual CLI elapsed time: unknown (no tool metadata exposed); no figure is invented.
