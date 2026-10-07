# Recording the public PyPI demo (Task 14 procedure)

Status: **procedure only**. No cast, GIF, version or hash receipt exists yet.
The `demo` asset stays `not implemented` in `actseal_assets/inventory.py`
until a genuine capture of the public PyPI `actseal` 1.0.0 release exists and
Codex has reviewed it. Nothing below may be run against a local wheel, a
prerelease or 0.1.0 and labelled v1.0.0. No snippet in this file has been
run against a package during preparation.

What the capture must show, unedited: the three approved quickstart commands,
their real output and their real exit codes 0, 0, 1, in a raw cast of 20 to
40 seconds at speed 1, rendered to light and dark GIFs that each play for a
measured 20 to 40 seconds, stay below 3,000,000 bytes and reproduce
byte-for-byte from the committed cast.

## 0. Inputs supplied by Task 20 (do not retype from memory)

Task 20's publication receipt supplies, after v1.0.0 is on PyPI:

- the published version string, which must read `1.0.0`;
- the SHA-256 digests of the published wheel and sdist that Task 20 downloaded
  from PyPI and compared with the GitHub release assets, and the wheel file
  those bytes were hashed from (called `$VERIFIED_WHEEL` below; re-hash it
  before every use);
- the accepted source fingerprint (`implementation_sha256`) of the released
  code, which the demo's `lock.json` files repeat;
- the public project URL on PyPI.

Copy those values from that receipt into these shell variables before step 3.
They are inputs to comparisons, not evidence; the evidence is each
comparison's recorded outcome. If any value is missing from the receipt, stop.

```bash
TASK20_VERSION=        # must be 1.0.0
TASK20_WHEEL_SHA256=   # from the Task 20 receipt
TASK20_SDIST_SHA256=   # from the Task 20 receipt
TASK20_IMPLEMENTATION_SHA256=   # accepted source fingerprint from Task 20
VERIFIED_WHEEL=        # the wheel file the Task 20 receipt hashed
```

## 1. Tools, pins, flags and configuration (outside the timed demo)

The recorder and renderer are the pinned binaries in `tools.toml`:
asciinema 3.2.1 (commit `70c4af0505fe1dbc7a2170392559d258bd4af92c`) and agg
1.9.0 (commit `26ca84c02523973198fca28533369edcfc7ed929`), plus JetBrains
Mono 2.304 for GIF rendering. They are fetched only by `setup_tools.py`
(the accepted provisioning path; no substitute downloader may be used), and
provisioning history is separate from this task's own unrun genuine
rendering. Before any capture, `actseal_assets.tools.verified_binary` must
re-hash both binaries against the pins (it does so on every call), and
`check_fonts` must accept the font files and `OFL.txt`.

Record for the receipt, each from its own command, before capture:

```bash
uv --version
"$ASCIINEMA" --version
"$AGG" --version
"$PYTHON" --version
git -C "$CHECKOUT" rev-parse HEAD
git -C "$CHECKOUT" rev-parse HEAD:docs/assets/src/demo_session.py
```

`$ASCIINEMA` and `$AGG` are the paths returned by `verified_binary`;
`$PYTHON` is the interpreter that runs the helper (step 3); `$CHECKOUT` is
the repository checkout whose `demo_session.py` is recorded. The helper needs
only the standard library of Python 3.12 or newer and never imports `actseal`
or the asset toolchain.

### asciinema 3.2.1 flags (corrected)

The first version of this procedure stated, from the dispatch's premise, that
asciinema 3.2.1 has no `--capture-input`, `--append` or `--overwrite`. That
premise was wrong; the parent's read of the pinned `src/cli.rs` corrected it.
The recorder **does** have `--capture-input` (`-I`, `--stdin`), `--append`
(`-a`) and `--overwrite`. All three are **forbidden** for this capture: no
keystroke may be recorded, nothing may be appended to an existing cast and
no cast may be overwritten. Flags used: `rec`, `--output-format asciicast-v3`
(the default, written explicitly), `--window-size COLSxROWS`, `--return`,
`--command`, `--capture-env TERM,LANG`. `--return` is required: without it
the recorder exits 0 regardless of the helper's exit. The capture is local
only: an explicit `--command`, no upload, stream or server operation.

### asciinema configuration roots

At the pinned commit `src/config.rs` loads `/etc/asciinema/config.toml`
first, then `defaults.toml` and `config.toml` from the directory selected by
`ASCIINEMA_CONFIG_HOME`; `ASCIINEMA_STATE_HOME` selects state storage. This
procedure does not claim the `/etc` file is unread; it sets task-owned
config and state roots whose later, explicit values govern every sensitive
recording setting, and passes `--capture-env` on the command line as well.
`HOME` is left unchanged and is not repurposed.

Create exactly this file as `$SESSION/asciinema-config/config.toml` (the
`[session]` keys are a boolean, a string, a float and three strings; the
`[notifications]` key is a boolean, per the pinned struct descriptions):

```toml
[session]
capture_input = false
capture_env = "TERM,LANG"
idle_time_limit = 60.0
prefix_key = ""
pause_key = ""
add_marker_key = ""

[notifications]
enabled = false
```

`idle_time_limit = 60.0` is above the helper's maximum pause (30 s per flag)
so it never shortens a recorded pause; empty key bindings make the session
non-interactive for the recorder. `defaults.toml` is deliberately absent.

## 2. Fresh working directories and controlled environment

Everything runs outside the checkout, in directories created by this
procedure. `mkdir` without `-p` fails if a directory already exists; that is
the overwrite refusal, never bypass it. The uv cache and tool directories are
task-owned and start empty, so unrelated caches (for example 0.1.0 tool
environments under the user's default cache) can neither be used nor cause a
refusal.

```bash
SESSION="$(mktemp -d /tmp/actseal-recording.XXXXXX)"
mkdir "$SESSION/uv-cache" "$SESSION/uv-tools" "$SESSION/uv-credentials"
mkdir "$SESSION/asciinema-config" "$SESSION/asciinema-state"
mkdir "$SESSION/warmup" "$SESSION/wheel"
mkdir "$SESSION/attempt-1" "$SESSION/attempt-1/work"
touch "$SESSION/netrc"
ls -la "$SESSION/netrc" "$SESSION/uv-credentials"
```

`$SESSION/netrc` must be an **existing, empty** file and
`$SESSION/uv-credentials` an **existing, empty** directory, as the `ls`
line shows (size 0; only `.` and `..`). Pinned uv 0.12.5 falls back to
`$HOME/.netrc` when the `NETRC` path does not exist
(`crates/uv-netrc/src/lib.rs` 85-98), so an existing empty file is what
disables personal netrc reads; `UV_CREDENTIALS_DIR`
(`crates/uv-static/src/env_vars.rs` 63-65) points the credential store at
the empty task directory. Neither the personal `~/.netrc` nor any personal
credential store is read, listed or copied to prepare these.

Every command from step 3 on runs under this exact prefix (a bash/zsh
array), with no user shell startup files and no inherited variables:

```bash
PREFIX=( env -i
  PATH="$PATH" HOME="$HOME" TERM="$TERM" LANG="$LANG" SHELL=/bin/sh
  UV_CACHE_DIR="$SESSION/uv-cache" UV_TOOL_DIR="$SESSION/uv-tools"
  UV_NO_CONFIG=1 UV_NO_ENV_FILE=1
  UV_DEFAULT_INDEX=https://pypi.org/simple UV_KEYRING_PROVIDER=disabled
  NETRC="$SESSION/netrc" UV_CREDENTIALS_DIR="$SESSION/uv-credentials"
  ASCIINEMA_CONFIG_HOME="$SESSION/asciinema-config"
  ASCIINEMA_STATE_HOME="$SESSION/asciinema-state"
)
```

`env -i` starts from an empty environment and sets only the names written
above; it reads nothing else, so no credential is read, printed or redacted.
The uv names (confirmed in the pinned local uv 0.12.5 help and source) mean:
task-owned cache and tool directories; no `uv.toml`/`pyproject`
configuration and no `.env` file; the official index as the only default
index; no keyring lookups; an empty netrc file and an empty credential
store. Any other index, extra-index, find-links, proxy, TLS or token
override is absent because `env -i` never carries it, and the helper's own
allowlist (`demo_session.ENV_ALLOWLIST`) forwards to each `uvx` child only
`PATH`, `HOME`, `TERM`, `LANG`, these uv names, `NETRC` and
`UV_CREDENTIALS_DIR`, with the child's stdin closed. Every probe of the
package or its executable in this procedure, including the direct
`"$ENV_BIN"` call, runs under the same prefix. `SHELL=/bin/sh` makes any shell the recorder spawns for
`--command` a non-interactive POSIX shell; with `ENV` unset it reads no
startup file. `PATH` must contain `uvx`. Confirm the roots took effect:

```bash
"${PREFIX[@]}" uv cache dir
```

Required output: `$SESSION/uv-cache`. Anything else stops the procedure.

## 3. Warm-up, environment identity and payload binding, before capture

Installation and first-run work happen here, outside the timed demo and in
`warmup`, which never contains `actseal-demo`. The requirement spelling
`actseal` with no version pin is deliberately the same as the demo command,
so the environment uvx resolves here is the one the capture uses.

```bash
cd "$SESSION/warmup"
"${PREFIX[@]}" uvx --python 3.12 actseal --version
```

Required output: `actseal 1.0.0`. Anything else (a 0.1.0 line, a
prerelease, an error) stops the procedure; record the output and do not
capture.

### Identify the environment the fixed invocation actually uses

The cache was empty, so every file in it was created by that one invocation.

```bash
find "$SESSION/uv-cache" -type f -path '*/bin/actseal'
```

Exactly one path must be listed; call it `$ENV_BIN` and its environment
`ENV_DIR="$(dirname "$(dirname "$ENV_BIN")")"`. Zero or several paths mean
the invoked executable cannot be identified: fail the capture. Then record
the identity and show the wrapper points into that environment:

```bash
ls -li "$ENV_BIN"
head -n 1 "$ENV_BIN"
cat "$ENV_DIR/pyvenv.cfg"
"${PREFIX[@]}" "$ENV_BIN" --version
"${PREFIX[@]}" uvx --offline --python 3.12 actseal --version
find "$SESSION/uv-cache" -type f -path '*/bin/actseal'
```

The shebang must name a Python inside `$ENV_DIR`; both version lines must
read `actseal 1.0.0`; the second `find` must list the same single path with
the same inode as the `ls -li` line. A second environment appearing after
the offline run means the offline invocation did not reuse the identified
one: fail the capture. This same `find`/`ls -li` pair is repeated after the
capture (step 5); the identity holds only if the single path and inode are
unchanged throughout.

### Verify all installed code and data against the Task 20 wheel

```bash
shasum -a 256 "$VERIFIED_WHEEL"
unzip -l "$VERIFIED_WHEEL"
unzip -q "$VERIFIED_WHEEL" -d "$SESSION/wheel"
ls "$SESSION/wheel"
SITE="$ENV_DIR/lib/python3.12/site-packages"
ls "$SITE"
diff -r -x __pycache__ "$SESSION/wheel/actseal" "$SITE/actseal"
diff -r -x RECORD -x INSTALLER -x REQUESTED -x 'uv_*' \
  "$SESSION/wheel/actseal-1.0.0.dist-info" "$SITE/actseal-1.0.0.dist-info"
```

Required: the digest equals `$TASK20_WHEEL_SHA256`; the wheel listing's
top-level entries are exactly `actseal/` and `actseal-1.0.0.dist-info/` (if
the wheel carries any other top-level entry, add a `diff -r` line for it; no
payload directory may go uncompared); `$SITE` contains exactly one
`actseal-*.dist-info`, named `actseal-1.0.0.dist-info`; both `diff -r`
commands print nothing and exit 0. The dist-info exclusions are only the
files the installer writes itself; `METADATA`, `WHEEL`, `entry_points.txt`
and `licenses/` are compared. `METADATA` alone is not accepted as a binding,
and the lock's self-reported fingerprint (step 5) is an additional check,
never the sole one.

Select the helper's interpreter and enforce space-free paths before the
command string is formed:

```bash
PYTHON="$("${PREFIX[@]}" uv python find 3.12)"
HELPER="$CHECKOUT/docs/assets/src/demo_session.py"
case "$PYTHON$HELPER" in (*[[:space:]]*) echo "refusing: whitespace in PYTHON or HELPER";; esac
"$PYTHON" --version
```

If the `case` line prints `refusing`, stop: `--command` is passed as one
string and this procedure does not quote inside it.

## 4. Capture

The recorded command is the helper itself. It prints each approved command
from its argument array, streams the child output unchanged, prints
`exit N (expected M)` after each command, and exits 0 only after exits
0, 0, 1. Default real pauses: 4 s before each command and 3 s after each
printed exit code (the last one holds the final exit on screen), 21 s in
total plus the commands' own time. Pauses are changed only through
`--pause SECONDS` and `--hold SECONDS` before a new attempt; timestamps are
never edited, output is never trimmed and nothing is sped up.

```bash
cd "$SESSION/attempt-1/work"
"${PREFIX[@]}" "$ASCIINEMA" rec \
    --output-format asciicast-v3 \
    --window-size 100x40 \
    --capture-env TERM,LANG \
    --return \
    --command "$PYTHON $HELPER" \
    "$SESSION/attempt-1/demo.cast"
echo "asciinema exit: $?"
```

No `--capture-input`/`-I`/`--stdin`, `--append`/`-a` or `--overwrite`
appears, and the output path is inside a directory this attempt created.
`100x40` is the initial geometry choice: 100 columns keep every approved
command on one line and 40 rows keep the first command visible while the
demo output scrolls; decide geometry before the attempt and record it, never
adjust it afterwards in rendering. Run in a real terminal; `--headless` is
only for a noninteractive driver.

Record the printed `asciinema exit`. With `--return` it equals the helper's
exit: 0 means all three commands exited 0, 0, 1; 1 means a mismatch or a
command that could not start; 2 means `./actseal-demo` already existed,
which cannot happen in a fresh `work` directory. A non-zero exit, or a cast
outside the duration window, is a failed attempt: leave `attempt-1`
untouched, write `attempt-1/FAILED.md` with the exit code and reason, and
start `attempt-2` from step 2's `mkdir "$SESSION/attempt-2" ...` lines under
the same `$SESSION` and the same uv cache. Never delete, rename or re-record
into an existing attempt directory.

## 5. Post-capture binding (outside the cast)

Immediately after the capture, in `warmup` again, under the same prefix:

```bash
cd "$SESSION/warmup"
"${PREFIX[@]}" uvx --offline --python 3.12 actseal --version
find "$SESSION/uv-cache" -type f -path '*/bin/actseal'
ls -li "$ENV_BIN"
diff -r -x __pycache__ "$SESSION/wheel/actseal" "$SITE/actseal"
diff -r -x RECORD -x INSTALLER -x REQUESTED -x 'uv_*' \
  "$SESSION/wheel/actseal-1.0.0.dist-info" "$SITE/actseal-1.0.0.dist-info"
grep -h '"implementation_sha256"' \
  "$SESSION/attempt-1/work/actseal-demo/bad/lock.json" \
  "$SESSION/attempt-1/work/actseal-demo/fixed/lock.json"
```

Required: `actseal 1.0.0`; the single `bin/actseal` path and inode unchanged
from step 3; both `diff -r` commands silent with exit 0; both `grep` lines
carry `$TASK20_IMPLEMENTATION_SHA256`. Any difference invalidates the
attempt even if the cast looks right.

## 6. Validate the raw cast

```bash
shasum -a 256 "$SESSION/attempt-1/demo.cast"
```

Then, from the checkout, parse the untouched bytes with the accepted
validator (`actseal_assets.checks.check_cast`, `min_seconds=20`,
`max_seconds=40`) and require these exact texts in the recorded output:

```text
$ uvx --python 3.12 actseal demo --out ./actseal-demo
$ uvx --offline --python 3.12 actseal replay ./actseal-demo/fixed/evidence
$ uvx --offline --python 3.12 actseal replay ./actseal-demo/bad/evidence
exit 0 (expected 0)
exit 1 (expected 1)
demo-session: all 3 commands exited as expected (0, 0, 1)
```

`check_cast` also rejects credential-looking output. Independently inspect
the header and count event codes with this stdlib snippet (saved beside the
attempt, not in the repository):

```python
import json
import sys

lines = [l for l in open(sys.argv[1], encoding="utf-8").read().split("\n") if l.strip()]
header = json.loads(lines[0])
events = [json.loads(line) for line in lines[1:]]
codes: dict[str, int] = {}
for _, code, _ in events:
    codes[code] = codes.get(code, 0) + 1
print("term:", header.get("term"))
print("command:", header.get("command"))
print("env:", header.get("env"))
print("codes:", codes)
print("last:", events[-1][1], repr(events[-1][2]))
```

Required: `term` cols/rows `100`/`40`; `command` equal to `"$PYTHON $HELPER"`;
`env` with exactly the keys `TERM` and `LANG` and no other name; `codes`
with exactly two keys, `"o"` (output) and `"x"` with count 1, and
**zero** `"i"` (input) events; `last` must be `x '0'`, that is the single
exit event is the final event and its payload is the string `"0"`. The
pinned recorder (`src/session.rs`, `src/asciicast/v3.rs` at
`70c4af05…`) always writes that terminal `x` event carrying the recorded
command's exit status, so its absence, a payload other than `"0"`, or any
`"m"` marker, `"r"` resize or unknown code means an interactive action, a
window change or an unexpected recorder path: treat it as a failed attempt.
The accepted `check_cast` collects only `"o"` payloads and accepts the `x`
event without conflict; it does not enforce the event-code rule, which is
why this inspection is separate. Record the parsed duration from
`check_cast`.

## 7. Render light and dark GIFs, measure them, verify reproducibility

Both variants derive from the same untouched cast. Build each agg command
with the accepted helper, never by hand:
`actseal_assets.tools.agg_command(agg, cast, gif, duration_seconds=<parsed
cast duration>, font_dir=<checkout>/docs/assets/src/fonts,
extra=("--last-frame-duration", "3", "--theme", THEME))` with `THEME`
`github-light` for the light variant and `github-dark` for the dark one
(confirm both names against the pinned agg's `--help`; if either is absent,
stop and report rather than improvising). That yields `--speed 1`, an idle
limit of `ceil(duration) + 1` seconds (longer than the whole cast, so agg's
default 5 s idle limit never trims a pause), the pinned font directory and
`--font-family "JetBrains Mono"`. `--select` is forbidden; no geometry
override, trimming or speed change of any kind. `--last-frame-duration 3`
is explicit and recorded, but **no formula** converts it and the cast
duration into a GIF duration: pinned agg 1.9 keeps output events only,
deduplicates frames, shifts the first timestamp and caps the frame rate
before encoding, so the GIF's duration is measured, never derived.

Render each variant twice into separate directories
(`render-light-a`, `render-light-b`, `render-dark-a`, `render-dark-b`) and
measure every file from the checkout with the shared validator, which is the
same code the renderer will apply to the committed files:

```bash
uv run --frozen --group assets python -c 'import sys; sys.path.insert(0, "docs/assets/src"); from pathlib import Path; from actseal_assets import demo; p = Path(sys.argv[1]); print(p.name, demo.validate_gif(demo.read_bounded(p), p.name))' "$SESSION/attempt-1/render-light-a/demo-light.gif"
```

Run it once per file (the four paths differ only in their directory and
variant name). `read_bounded` reads at most the cap plus one byte and
refuses an oversized file unread; `validate_gif` rejects a file at or above
3,000,000 bytes before parsing, then walks every block with bounded reads
(signature, logical screen descriptor, colour tables, extensions, image
descriptors, code sizes, non-empty image data, terminators, trailer) and
sums only the delays of graphic control extensions that are each followed
by exactly one image. Duplicate or dangling controls, images without data,
unknown blocks, truncation and trailing bytes are errors, not estimates.
The printed `GifFacts` carry `size`, `frames` and `delay_centiseconds`.
This is structural validation; it does not decode pixels. The rendered
images are reviewed by eye separately, and the recorded text markers
checked in step 6 are consistency checks, not proof that the commands ran
or that the package came from PyPI; that proof is the step 3/5 binding.

Required for each GIF: `validate_gif` returns facts (no `DemoError`) with
`delay_centiseconds` between 2000 and 4000 (20 to 40 s), at least one frame
and `size` below 3,000,000; for each variant the two renders have identical
SHA-256 digests:

```bash
shasum -a 256 "$SESSION/attempt-1"/render-*/demo*.gif
```

If a duration or size bound fails, the attempt failed: re-record with
different pauses or stop and report; do not improvise agg flags.

## 8. Receipt, then integration (separate, reviewed step)

The capture receipt pins everything above: Task 20 version and digests as
supplied; `uv cache dir` output; pre- and post-capture `--version` output;
the single `bin/actseal` path, inode, shebang and `pyvenv.cfg`; the wheel
digest, listing and both `diff -r` outcomes before and after; both
`implementation_sha256` values; cast SHA-256, parsed duration, geometry,
header `env` keys and event-code counts; each GIF's SHA-256, byte size,
frame count, measured delay sum and two-render identity; the exact agg
commands and theme names; `uv`, asciinema, agg and `$PYTHON` versions and
paths; the pinned binary digests re-verified by `verified_binary`; the
checkout commit and the helper's blob hash; the `PREFIX` array, the `ls -la`
line proving the empty netrc file and credential directory, and the
asciinema `config.toml` used; the cast header `env` keys, event-code counts
and final `x` payload; the attempt number and every failed attempt
directory kept. The receipt is a record; the bytes it describes are the
evidence.

Only after Codex reviews the raw capture does the asset get integrated:
`demo.cast` copied unchanged to `docs/assets/src/demo.cast`, the two GIFs
under `docs/assets/`, a `demo` renderer attached in `inventory.py` (with the
light/dark outputs declared there) that re-renders from the committed cast
with the same `agg_command` calls, and
`uv run --frozen --group assets python docs/assets/src/render.py --check --only demo`
passing. None of that is part of this preparation.

## Pending (explicitly not done)

- Official asciinema/agg/font downloads: permission-blocked; `setup_tools.py`
  has not been run.
- Task 20 publication and its receipt (version, wheel/sdist digests, verified
  wheel file, source fingerprint): pending; Decision 2 governs the
  post-publication capture.
- Actual warm-up, environment identity, payload comparison, version/hash
  receipts, cast, GIFs, measured durations, sizes, two-render identity: none
  exist. The parent verifies the actual binding after publication.
- Codex review of the raw capture and full Task 14 acceptance.
