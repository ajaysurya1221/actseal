# REPORT 14 (capture)

Genuine post-publication capture of the public PyPI `actseal` 1.0.0 demo under `docs/assets/src/recording.md`. Executor: Claude Code, model `claude-fable-5-1` (Claude Fable 5.1), effort high, same session `241e6a45-571b-4ca9-ad83-243d7c53b003`, branch `claude/v1-14-published-recording` at `04c10d3fec60727310cf65acf6528f13264a26d4`, normal permissions. No subagent, model or billing substitution, permission change, key, `.env`, personal netrc or credential-store read, GitHub push/tag/release, or user-data upload. The only network step was uvx resolving `actseal` from `https://pypi.org/simple` into a task-owned cache. The git tree was not modified in this phase; this report is the only committed file.

Status: **CAPTURE COMPLETE, PENDING CODEX RAW-CAPTURE REVIEW.** No inventory activation, no copied product media, no `demo.cast` or GIF in the repository. Integration (step 8 of the procedure) waits for review ACCEPT.

## Raw artifacts (private, outside the checkout)

Session root `/tmp/actseal-recording.zCynsQ`; attempt 1 succeeded on the first run, so there are no failed-attempt directories.

| Artifact | Path | SHA-256 | Size |
|---|---|---|---|
| Raw cast | `/tmp/actseal-recording.zCynsQ/attempt-1/demo.cast` | `cdce70c61100d9b38c247db272517ca3f28b7c01c84d38c5518b59feb54963e6` | 3,626 B |
| Light GIF (render a and b identical) | `/tmp/actseal-recording.zCynsQ/attempt-1/render-light-{a,b}/demo-light.gif` | `653f6bb6f83724d34afab53fa4f707dcc6dda8e6e427f5f0a04943d211cfc4af` | 571,102 B |
| Dark GIF (render a and b identical) | `/tmp/actseal-recording.zCynsQ/attempt-1/render-dark-{a,b}/demo-dark.gif` | `5af6a3cec2f3dea292664c86e7d56d9dd9b9788af5dd61eb0984cd3bfa42968b` | 569,379 B |
| Capture receipt | `/tmp/actseal-recording.zCynsQ/attempt-1/capture-receipt.json` | `b78f44c3943df4001471afce6df1f181dc527e8748436d3d115d9f72b73c476d` | 10 KB |
| Demo output tree | `/tmp/actseal-recording.zCynsQ/attempt-1/work/actseal-demo/{inputs,bad,fixed}` | bad lock `0db9130d…`, fixed lock `5d67a27d…` | |

## Task 20 inputs used (supplied, re-checked here)

Version `1.0.0`; `VERIFIED_WHEEL=/tmp/actseal-v1-orchestration/release-37603727302/pypi/actseal-1.0.0-py3-none-any.whl` re-hashed to `4497fef4878cb67f03845e13f91c8b8c4e7686361198d0ebc52a1764157ae3bf` (101,900 B, equal to the supplied digest); sdist re-hashed to `aa31ccf9f5cce30c40269dd5d9904ef61f147f9c4aaf21e3db288981b3278da6` (2,054,855 B, equal); accepted fingerprint `8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3`; the postpublish receipt reports `actseal 1.0.0`, demo exit 0, replay exits 0/1 in the clean container, attestation presence only.

## Tools and provenance

| Item | Value |
|---|---|
| uv | `uv 0.12.5 (Homebrew 2026-08-14 aarch64-apple-darwin)` |
| asciinema | `/Users/ajay/.cache/actseal-assets/asciinema-3.2.1/asciinema-aarch64-apple-darwin`, `asciinema 3.2.1`, re-hashed by `tools.verified_binary` against pin `1f0c76da…` before capture |
| agg | `/Users/ajay/.cache/actseal-assets/agg-1.9.0/agg-aarch64-apple-darwin`, `agg 1.9.0`, re-hashed by `tools.verified_binary` against pin `742b2b62…` immediately before each of the four renders; `--help` lists `github-light` and `github-dark` |
| Fonts | `check_fonts` returned `([], True)`: both pinned TTFs and `OFL.txt` present and hash-valid |
| Helper interpreter | `/Users/ajay/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12`, `Python 3.12.13`, selected by `uv python find 3.12` under the prefix from the project-free warm-up directory; importing `demo_session` under it loads no `actseal`/`fontTools` module |
| Checkout | head `04c10d3f…`; blobs `demo_session.py` `81487915…`, `demo.py` `ce563ff1…`, `recording.md` `8da37e2d…` |
| Manifest | `validate_manifest` returned no errors |

## Controlled environment

Fresh `mktemp` session with empty `uv-cache`, `uv-tools`, `uv-credentials` (listing shows only `.` and `..`), an existing zero-byte `netrc`, task-owned `asciinema-config/config.toml` exactly as the procedure specifies (`capture_input = false`, `capture_env = "TERM,LANG"`, `idle_time_limit = 60.0`, empty keys, notifications off) and `asciinema-state`. Every command from warm-up on ran under the `env -i` prefix with `PATH`, `HOME` (unchanged), `TERM`, `LANG`, `SHELL=/bin/sh`, `UV_CACHE_DIR`, `UV_TOOL_DIR`, `UV_NO_CONFIG=1`, `UV_NO_ENV_FILE=1`, `UV_DEFAULT_INDEX=https://pypi.org/simple`, `UV_KEYRING_PROVIDER=disabled`, `NETRC`, `UV_CREDENTIALS_DIR`, `ASCIINEMA_CONFIG_HOME`, `ASCIINEMA_STATE_HOME`. `uv cache dir` printed the task cache. The helper's recorded first line confirms the children received exactly `PATH HOME TERM LANG UV_CACHE_DIR UV_TOOL_DIR UV_NO_CONFIG UV_NO_ENV_FILE UV_DEFAULT_INDEX UV_KEYRING_PROVIDER UV_CREDENTIALS_DIR NETRC`.

## Environment identity and payload binding (before and after capture)

- Warm-up `uvx --python 3.12 actseal --version` from the official index: `Installed 1 package in 5ms` then `actseal 1.0.0`.
- `find` over the task cache listed exactly one `bin/actseal`: `/tmp/actseal-recording.zCynsQ/uv-cache/archive-v0/-6ljBQcdSsFak4-u/bin/actseal`, inode `137174376`, identical before the offline run, after it, and after the capture.
- The executable is uv's relocatable wrapper (`#!/bin/sh` then `'''exec' "$(dirname -- "$(realpath -- "$0")")"/'python' "$0" "$@"`), so it runs `<env>/bin/python`, a symlink to the uv-managed `cpython-3.12-macos-aarch64-none/bin/python3.12` (realpath `cpython-3.12.13-macos-aarch64-none`); `pyvenv.cfg` names that home, `version_info = 3.12.13`, `uv = 0.12.5`.
- Direct `"$ENV_BIN" --version` and `uvx --offline --python 3.12 actseal --version` both printed `actseal 1.0.0` before the capture; the offline form printed `actseal 1.0.0` again after it.
- Wheel top-level entries are exactly `actseal` and `actseal-1.0.0.dist-info`; site-packages holds exactly one dist-info, `actseal-1.0.0.dist-info`. `diff -r -x __pycache__` of the package and `diff -r -x RECORD -x INSTALLER -x REQUESTED -x 'uv_*'` of the dist-info were both silent with exit 0 before and after the capture.
- Both demo locks carry `implementation_sha256 = 8f316f679b2ed5be4ce19127da87db21511ce4de2ff1450439fcf3c549598ed3` and `replay_engine_version = actseal-choice-v1` (extracted as JSON, equal to the Task 20 value).

## Capture

```text
asciinema rec --output-format asciicast-v3 --window-size 100x40 --capture-env TERM,LANG --headless --return
  --command "<PYTHON> <CHECKOUT>/docs/assets/src/demo_session.py" /tmp/actseal-recording.zCynsQ/attempt-1/demo.cast
asciinema exit: 0        (2026-10-07T10:16:09Z to 10:16:30Z)
```

Helper defaults: 4 s pause before each command, 3 s hold after each printed exit. No `--capture-input`, `--append` or `--overwrite`.

Raw cast facts (accepted `check_cast` with the seven required markers: no errors; owned `validate_cast`: `CastFacts(duration=21.517, outputs=21)`): asciicast v3, `term` 100x40, `idle_time_limit` 60.0, header `env` exactly `{LANG, TERM}`, 22 events = 21 `o` + 1 final `x` with payload `"0"`, zero input/resize/marker events, no credential pattern. Recorded content, unedited: the demo printed `[bad] expected BLOCK, observed BLOCK, replay BLOCK (match)` and `[fixed] expected PASS, observed PASS, replay PASS (match)`, `result: success`, `exit 0 (expected 0)`; the fixed replay printed `status: PASS` and `exit 0 (expected 0)`; the bad replay printed `status: BLOCK`, `reasons: risk.exceeds_limit`, `errors/accepted: 32/128` and `exit 1 (expected 1)`; then `demo-session: all 3 commands exited as expected (0, 0, 1)`. Lock digests shown in the output: bad `1ae0f9fb…`, fixed `3089eb01…`. The demo itself reported `duration_s: 0.129`.

## Rendering

Each variant built by `demo.agg_arguments` over the accepted `tools.agg_command`: `--speed 1 --idle-time-limit 23 --font-dir <checkout>/docs/assets/src/fonts --font-family "JetBrains Mono" --last-frame-duration 3 --theme github-light|github-dark <cast> <gif>`; no `--select`, geometry or trim flags. Each rendered twice into separate directories through `tools.run_tool`.

| GIF | Measured by `validate_gif` | Two-render identity |
|---|---|---|
| `demo-light.gif` | 571,102 B, 8 frames, 2451 cs = 24.51 s, 979x918 px | identical SHA-256 |
| `demo-dark.gif` | 569,379 B, 8 frames, 2451 cs = 24.51 s, 979x918 px | identical SHA-256 |

Both are below 3,000,000 B and inside 20 to 40 s; the cast is inside 20 to 40 s at 21.517 s. Durations were measured from encoded frame delays, not derived.

## Deviations and review notes

1. **`--headless`.** This driver has no TTY (`tty` exit 1), so the capture used `--headless`, which the procedure reserves for exactly a noninteractive driver. The child still ran in a PTY at 100x40; the recorder's own status lines went to the driver, not into the cast.
2. **`TERM=dumb`.** The prefix forwards the driver's `TERM`, which is `dumb`; it is recorded literally in the cast header and the helper's environment line. Output is plain text either way, but Codex may prefer a re-capture with a conventional terminal type; that would be attempt 2 under the same session and cache, never an edit of attempt 1.
3. **Wrapper shebang.** The procedure expected a Python shebang; uv 0.12.5 writes a `#!/bin/sh` relocatable wrapper. The binding was established instead by reading the wrapper's exec line, the `bin/python` symlink target and `pyvenv.cfg`, all inside the identified environment.
4. **Interpreter selection.** `uv python find 3.12` run from the checkout cwd first returned the project `.venv` interpreter; it was re-run from the project-free warm-up directory and the uv-managed CPython 3.12.13 was used for the capture. Both outcomes are recorded.
5. **Duration margin.** The cast is 1.5 s above the lower bound because the installed demo takes 0.13 s; the GIFs sit at 24.5 s. If a longer capture is wanted, only `--pause`/`--hold` would change in a new attempt.
6. **Fingerprint extraction.** The procedure's `grep` printed whole single-line lock files; the field was extracted with `json` instead and compared exactly.

Text markers, header checks and structural GIF validation are consistency evidence; execution and provenance rest on the binding facts above together with Task 20's receipts, not on the recording alone. No independent cryptographic attestation verification is claimed.

## Commands and exits

| Step | Command (abridged) | Exit |
|---|---|---|
| Tool verification | `tools.verified_binary` for asciinema and agg, `check_fonts`, `validate_manifest` | 0 |
| Versions/identity | `uv --version`, `asciinema --version`, `agg --version`, `git rev-parse …` | 0 |
| Wheel/sdist re-hash | `shasum -a 256 …` | 0 |
| Session roots | `mktemp`, `mkdir` (no `-p`), `touch netrc`, config write | 0 |
| Cache root | `"${PREFIX[@]}" uv cache dir` | 0 |
| Warm-up | `"${PREFIX[@]}" uvx --python 3.12 actseal --version` | 0 |
| Identity pre | `find`, `ls -li`, `head`, `cat pyvenv.cfg`, direct and offline `--version`, `find` | 0 |
| Payload pre | `unzip`, `diff -r` package, `diff -r` dist-info | 0, 0 |
| Interpreter | `uv python find 3.12` (warm-up cwd), whitespace guard, stdlib-import check | 0 |
| Capture | `asciinema rec … --headless --return …` | 0 |
| Identity/payload post | offline `--version`, `find`, `ls -li`, both `diff -r` | 0, 0, 0 |
| Fingerprints | JSON extraction of both locks | 0 (both MATCH) |
| Cast validation | `check_cast`, `validate_cast`, header/event inspection | 0 |
| Renders | 4 x `agg` via `run_tool` with `verified_binary` before each; `validate_gif`, `shasum` | 0 |
| Receipt | `capture-receipt.json` written | 0 |
| Tree check | `git status --short`, `git diff --stat` | clean |

## Next (after Codex ACCEPT of the raw capture, separate owned activation)

Copy `demo.cast` unchanged to `docs/assets/src/demo.cast`, the two GIFs to `docs/assets/`, register `demo.render` with `demo-light.gif`/`demo-dark.gif` in `inventory.py`, narrow visual-test updates for planned to implemented, then `uv run --frozen --group assets python docs/assets/src/render.py --check --only demo`, full visual checks, regeneration of all assets, strict asset typing and hooks. Root README integration belongs to Task 21.

## Spend

No paid API calls, model inference or Jev requests. One PyPI download of the 101,900-byte wheel by uvx into the task cache. Claude subscription session only. Actual CLI elapsed time: unknown (no tool metadata exposed); capture wall clock 21 s, four agg renders under 0.7 s total.
