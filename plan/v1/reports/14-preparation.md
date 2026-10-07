# REPORT 14 (preparation)

Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, isolated worktree branch `claude/v1-14-recording-preparation` from `d58018a7c2b6b680f2550b48ed30dd7592d35a15`. Work applied directly; no subagent, nested executor, other model, billing or credential change, personal memory write, permission change, download, network call, or invocation of `uvx`, `asciinema`, `agg`, `resvg`, `setup_tools.py` or the real demo. Scope follows V1-023 and Decision 2.

Status: **PARTIAL**. Preparation deliverables only. No cast, GIF, version/hash receipt or Task 14 acceptance exists; the `demo` asset remains `not implemented` in the inventory, by design.

## Changes (owned paths only)

- `docs/assets/src/demo_session.py` (new, stdlib only, never imports `actseal` or `actseal_assets`). The recorded command. Frozen `STEPS` hold the three approved commands as argument arrays with expected exits `(0, 0, 1)`; each printed label is `shlex.join` of the same array. `run_session` refuses an existing `./actseal-demo` (directory, file or dangling symlink) before anything runs (exit 2), prints `$ <command>` before each child, streams child stdout/stderr unchanged by inheriting the terminal, prints `exit N (expected M)` after each child, stops with exit 1 at the first mismatch or process-start failure, and returns 0 only after all three expected exits. `run_inherited` spawns with an argument list, `stdin=DEVNULL` and an allowlisted environment (`ENV_ALLOWLIST`: PATH, HOME, TERM, COLORTERM, LANG, LC_ALL, LC_CTYPE, TMPDIR, XDG_CACHE_HOME, XDG_DATA_HOME, UV_CACHE_DIR, UV_PYTHON_INSTALL_DIR, UV_TOOL_DIR) built by looking up only those names, never iterating the parent environment. No `shell=True`, `eval`, `os.system` or output capture/filtering anywhere. Real pauses (`Pauses`: 4 s before each command, 3 s after each printed exit, flags `--pause`/`--hold`, bounded 0 to 30 s, finite) occur only between printed lines, never while a child runs. Exit 0 ok, 1 failed, 2 refused/usage.
- `docs/assets/src/recording.md` (new). Copy-ready procedure: Task 20 inputs described (version `1.0.0`, wheel/sdist SHA-256, accepted `implementation_sha256`, PyPI URL) without inventing their path or schema; pinned tool provenance and `verified_binary` re-hash; fresh `mktemp`/`mkdir` directories outside the checkout with `mkdir` as the overwrite refusal; `env -i` five-name prefix with `SHELL=/bin/sh`, no rc files, no credential read; warm-up `uvx --python 3.12 actseal --version` must print `actseal 1.0.0` before capture and `--offline` after; binding of the resolved uv environment to the Task 20 wheel through `actseal-1.0.0.dist-info/METADATA` digests pre and post capture; `implementation_sha256` in both demo `lock.json` files must equal Task 20's accepted fingerprint; `asciinema rec --output-format asciicast-v3 --window-size 100x40 --return --command "$PYTHON $HELPER"`; failed attempts preserved in numbered directories with `FAILED.md`, never deleted or overwritten; `check_cast` with the six required texts and 20 to 40 s; agg via accepted `agg_command` (speed 1, idle limit beyond the cast, pinned font) with `--last-frame-duration 3` and a fixed theme, no `--select`/geometry/trim; GIF duration counted as cast plus hold inside 20 to 40 s; two renders byte-identical and below 3,000,000 bytes; receipt fields; integration listed as a separate reviewed step; explicit pending list.
- `tests/visual/test_demo_session.py` (new, 38 tests). Exact three command strings and arrays; label derivation from arrays (quoting shown); shared fresh output directory and `--offline` placement; source contains no shell/eval/popen; success path emits every exit and summary; pause boundaries (interleaved sleep/emit/run log, zero pauses never call the clock, defaults leave room under the 40 s bound); seven exit-mismatch cases including the bad replay exiting 0 or 2, each stopping immediately with exit 1 and no further run or hold; process-start failure path and real missing executable; reused directory/file/dangling symlink refused before any run or sleep, via `run_session`, `main` and the script as a process; spawner double proves list args, `stdin=DEVNULL`, allowlisted env only, and no `shell`/`stdout`/`stderr`/`capture_output`/`input` kwargs; allowlist excludes secret-looking names and never copies unlisted present variables; real `sys.executable` children under `capfd` prove unchanged stdout/stderr (including an ANSI sequence), empty stdin, real exit 3, and in-order interleaving of helper lines with child output; CLI defaults/flags, seven invalid options exit 2 without running, `--help` exits 0; script imports only the standard library.
- `plan/v1/reports/14-preparation.md` (this report).

No edits to `tools.py`, `checks.py`, `inventory.py`, `tools.toml`, `pyproject.toml`, `uv.lock`, workflows, README, product code or any other lane's files.

## Commands and results

| Command | Result | Exit |
|---|---|---|
| `uv run --frozen ruff format docs/assets/src/demo_session.py tests/visual/test_demo_session.py` | 2 files reformatted (owned files only) | 0 |
| `uv run --frozen ruff check docs/assets/src/demo_session.py tests/visual/test_demo_session.py` | All checks passed | 0 |
| `uv run --frozen ruff format --check docs/assets/src/demo_session.py tests/visual/test_demo_session.py` | 2 files already formatted | 0 |
| `uv run --frozen mypy --strict docs/assets/src` | Success: no issues found in 12 source files | 0 |
| `uv run --frozen mypy --strict src/actseal tests` | Success: no issues found in 61 source files | 0 |
| `uv run --frozen pytest tests/visual/test_demo_session.py -q -p no:cacheprovider` | 38 passed in 0.14s | 0 |
| `uv run --frozen pytest tests/visual -q -p no:cacheprovider -rs` | 242 passed in 0.95s, no skips | 0 |
| `uv run --frozen pre-commit run --all-files` | ruff check, ruff format --check, mypy --strict all Passed | 0 |
| `uv run --frozen --group assets python docs/assets/src/render.py --check` | `check: 0 asset(s) checked; 8 planned/not implemented; 0 error(s)`; `demo: not implemented (planned in Task 14)`; no `[error]` | 0 |

One earlier run of the new test file failed on a self-inflicted assertion (a hold pause is legitimately adjacent to the next command's pause); the assertion was corrected to check that no sleep touches a child run, and the first lint run flagged one 101-character line, which was rewrapped. Both fixes are in the committed files.

Exclusions: the full default suite (`pytest -m "not integration"`), packaging and integration markers were not run; no product file changed and the visual suite plus the repository hooks cover every changed file. Hosted CI has not run on this branch. Nothing was pushed or merged.

## Deviations and review-sensitive choices

1. Default pauses total 21 s (3 x 4 s before, 3 x 3 s after). With the measured 0.1.0 demo and replay times (roughly 1.5 s and under 1 s each after warm-up) the first attempt should land near 24 to 27 s of cast plus a 3 s GIF hold. This is an estimate, not a timing receipt; the parent reviews real timing after capture and adjusts only through the flags before a new attempt.
2. Mismatch handling is fail-fast: the session stops at the first unexpected exit and does not run later commands or the final hold. A continued run after a failed step would still be failed evidence, so stopping keeps the capture honest and short.
3. The output-directory check is the helper's own precondition in the current working directory; `actseal demo` additionally refuses an existing `--out`, so both layers agree.
4. Geometry `100x40` and `--last-frame-duration 3` are proposals in the procedure, to be fixed before the attempt and recorded; the inventory's GIF has no declared dimensions, so no inventory edit was needed or made.
5. The procedure binds the uvx environment to the Task 20 wheel through the `METADATA` file digest rather than `RECORD`, because installers rewrite `RECORD`. The exact uv cache layout is not asserted; the `find` step accepts any number of `actseal-1.0.0.dist-info` directories and requires each to match.
6. `env -i` and `SHELL=/bin/sh` are specified for the human-run capture. How asciinema 3.2.1 spawns `--command` was not verified beyond the parent's read of `cli.rs`; the procedure therefore also requires inspecting the cast header's `env` object after capture rather than trusting `--capture-env`.
7. Implementation was done directly by Fable 5.1 per the dispatch's no-nested-executor rule, instead of the general worker-routing preference.

## Pending

- Official asciinema/agg/font downloads (permission-blocked); `setup_tools.py` not run; `verified_binary` cannot yet succeed.
- Task 20 publication and receipt; Decision 2 post-publication capture window.
- Warm-up, version/hash receipts, raw cast, GIF, two-render identity, duration and size measurements, cast header inspection.
- `demo` renderer attachment in `inventory.py`, committed `demo.cast`/`demo.gif`, `render.py --check --only demo`, Codex review of the raw capture, full Task 14 acceptance.

## Spend

No paid API calls, model inference, downloads or Jev requests. Claude subscription session only. Actual CLI elapsed time: unknown (no tool metadata exposed to the executor); no figure is invented.
