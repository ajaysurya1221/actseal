# REPORT 14 (activation)

Second bounded phase under CHANGE_LOG V1-053 after Codex's raw-capture ACCEPT (`plan/v1/reviews/14-capture.md`). Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, same session `241e6a45-571b-4ca9-ad83-243d7c53b003`, branch `claude/v1-14-published-recording` continuing from `f55fd5b` (REPORT 14 capture). Normal permissions; no subagent, model or billing substitution, permission change, network, download, re-capture, GitHub push, tag, release or user-data upload. The private attempt and its receipt are unchanged; REPORT 14 (capture) is preserved as raw-pending history.

Status: **ACTIVATED.** `uv run --frozen --group assets python docs/assets/src/render.py --check --only demo` exits 0. Hosted exact-head Linux regeneration and Task 21 README/final-receipt integration remain.

## Files in this commit (owned paths only)

| File | Change | SHA-256 |
|---|---|---|
| `docs/assets/src/demo.cast` | new, byte-identical copy of `/tmp/actseal-recording.zCynsQ/attempt-1/demo.cast` (`cmp` exit 0) | `cdce70c61100d9b38c247db272517ca3f28b7c01c84d38c5518b59feb54963e6` |
| `docs/assets/demo-light.gif` | new, copy of render-light-a; `cmp` against render-light-b exit 0 | `653f6bb6f83724d34afab53fa4f707dcc6dda8e6e427f5f0a04943d211cfc4af` |
| `docs/assets/demo-dark.gif` | new, copy of render-dark-a; `cmp` against render-dark-b exit 0 | `5af6a3cec2f3dea292664c86e7d56d9dd9b9788af5dd61eb0984cd3bfa42968b` |
| `docs/assets/src/receipts/demo-capture.json` | new public receipt: `provenance` (private receipt path, its SHA-256 `b78f44c3…`, its status at capture), `integration` (ACCEPT reference, activation date, committed file hashes, accepted deviations, limits) and `original`, the private receipt verbatim | `6e45db4b4564d55c0f94b1040cdc1e81c5468c16b8e5e0c123011af7a8e6a240` |
| `docs/assets/src/actseal_assets/inventory.py` | import `demo`; the `demo` asset now declares outputs from `demo.THEMES` (`demo-light.gif`, `demo-dark.gif`, kind gif, undeclared pixel size, `max_bytes` 3,000,000), source `demo.CAST_SOURCE` with the 20 to 40 s bounds, needs unchanged, `renderer=demo.render` | |
| `tests/visual/test_render_cli.py` | `IMPLEMENTED` gains `demo`, `PLANNED` is `where`/`matrix`/`boundary`; new `_demo_agg_error`/`_assert_demo_blocked` require the four demo prerequisite errors (agg not cached in the empty test cache, fonts not fetched, cast not present, skipped) in the bootstrap fresh-check, write-then-check and fontTools-free tests; `PREREQUISITE_ERRORS` 5 to 9; summaries `3 planned`; the `--only social` test asserts no demo line | |
| `tests/visual/test_demo_render.py` | docstring updated; `test_inventory_still_declares_the_demo_as_planned` replaced by `test_inventory_registers_the_demo_renderer_with_both_variants` and `test_committed_recording_is_the_accepted_capture_unchanged` (committed cast and GIF SHA-256s, `validate_cast`, `check_cast`, `validate_gif`: 8 frames, 2451 cs, 979x918, under the cap); all synthetic-fixture tests unchanged | |
| `docs/assets/src/recording.md` | status header now "captured and activated" with the committed hashes and review reference; step 3 describes both accepted launcher forms (Python shebang, or uv 0.12.5's `#!/bin/sh` relocatable launcher whose exec target is the sibling `bin/python`, with `ls -li`, `realpath` and `pyvenv.cfg` agreement required) with the payload diffs mandatory in both; step 4 notes `--headless` was used by the accepted noninteractive capture; final status section lists Task 20 publication, the accepted capture facts and deviations, and the remaining hosted-regeneration/Task 21 items | |
| `plan/v1/reports/14-activation.md` | this report | |

Not changed: `demo.py`, `demo_session.py`, `checks.py`, `tools.py`, `pipeline.py`, `references.py`, `__init__.py`, `tools.toml`, fonts, dependencies, every other asset's bytes, product source, registry, original example, root README, earlier reports and the private receipt.

## Verification (separate commands, literal exits)

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen --group assets python docs/assets/src/render.py --check --only demo` | `[ok] demo: source docs/assets/src/demo.cast validated`; `demo-light.gif matches regeneration (571102 bytes)`; `demo-dark.gif matches regeneration (569379 bytes)`; `1 asset(s) checked; 0 planned/not implemented; 0 error(s)` | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` | all 17 committed outputs of hero, how-it-works, architecture, demo and social match regeneration; 16 image references ok; `5 asset(s) checked; 3 planned/not implemented; 0 error(s)` | 0 |
| `uv run --frozen --group assets pytest tests/visual/test_demo_render.py` | 104 passed in 0.39s | 0 |
| `uv run --frozen --group assets pytest tests/visual` | 481 passed in 1.73s; the earlier known architecture failure is gone because this branch carries the architecture assets | 0 |
| `uv run --frozen mypy --strict docs/assets/src tests/visual` | Success: no issues found in 33 source files | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict all Passed | 0 |
| `git diff --check` | clean | 0 |
| `uv run --frozen ruff format --check .` | 457 files already formatted | 0 |

The regeneration check ran the pinned agg (hash re-verified by `tools.verified_binary` before each of its two renders per variant) against the committed cast and reproduced both GIFs byte for byte, so rendering reproduces from the original capture on this macOS arm64 host.

One intermediate test mistake was corrected before commit: a blanket insertion placed the demo-blocked assertion into the `--only social` test, which prints no demo lines; it now asserts the demo is absent there.

## Review-sensitive notes

1. **Receipt layering.** The public receipt never restates captured facts in edited form; it wraps the private receipt verbatim under `original`, records the private file's SHA-256, and adds only `provenance` and `integration` objects. The private file's hash `b78f44c3…` is unchanged after activation.
2. **Procedure wording.** Both launcher forms require the same payload diffs and identity checks; the literal Python-shebang criterion is not claimed to have passed for the accepted capture.
3. **GIF geometry.** The GIF outputs keep undeclared width/height because pixel size follows the recorded terminal and the pinned renderer; the `max_bytes` cap and the measured-duration rule are enforced by the renderer and by `check_output`.
4. **Hosted rendering.** Only the macOS arm64 agg has rendered these GIFs; the pinned Linux agg's exact-head regeneration in hosted CI is a remaining gate, as the review states.
5. **Nature of the evidence.** The recording and GIFs are illustrative receipts of the public 1.0.0 package bound to the verified wheel; they are not authenticated model evidence, and no independent cryptographic attestation verification is claimed.

## Spend

No paid API calls, model inference, downloads or Jev requests. Four local agg renders during the regeneration checks, under a second each. Claude subscription session only. Actual CLI elapsed time: unknown (no tool metadata exposed); no figure is invented.
