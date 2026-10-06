# Recording the public PyPI demo (Task 14 procedure)

Status: **procedure only**. No cast, GIF, version or hash receipt exists yet.
The `demo` asset stays `not implemented` in `actseal_assets/inventory.py`
until a genuine capture of the public PyPI `actseal` 1.0.0 release exists and
Codex has reviewed it. Nothing below may be run against a local wheel, a
prerelease or 0.1.0 and labelled v1.0.0.

What the capture must show, unedited: the three approved quickstart commands,
their real output and their real exit codes 0, 0, 1, inside 20 to 40 seconds
at speed 1, rendered to a GIF below 3,000,000 bytes that reproduces
byte-for-byte from the committed cast.

## 0. Inputs supplied by Task 20 (do not retype from memory)

Task 20's publication receipt supplies, after v1.0.0 is on PyPI:

- the published version string, which must read `1.0.0`;
- the SHA-256 digests of the published wheel and sdist that Task 20 downloaded
  from PyPI and compared with the GitHub release assets;
- the accepted source fingerprint (`implementation_sha256`) of the released
  code, which the demo's `lock.json` files will repeat;
- the public project URL on PyPI.

Copy those values from that receipt into the shell variables in step 4. They
are inputs to a comparison, not evidence; the evidence is the comparison's
outcome recorded in step 7. If any value is missing from the receipt, stop.

## 1. Tools, pins and provenance (outside the timed demo)

The recorder and renderer are the pinned binaries in `tools.toml`:
asciinema 3.2.1 (commit `70c4af0505fe1dbc7a2170392559d258bd4af92c`) and agg
1.9.0 (commit `26ca84c02523973198fca28533369edcfc7ed929`), plus JetBrains
Mono 2.304 for GIF rendering. They are fetched only by
`setup_tools.py` in a session where the official downloads are permitted;
as of this writing those downloads are permission-blocked and no substitute
downloader may be used. Before any capture, `actseal_assets.tools.verified_binary`
must re-hash both binaries against the pins (it does so on every call), and
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
`$PYTHON` is the interpreter that will run the helper (step 3); `$CHECKOUT`
is the repository checkout whose `demo_session.py` is recorded. The helper
needs only the standard library of Python 3.12 or newer and never imports
`actseal` or the asset toolchain.

Upstream flags relied on (confirmed read-only at the pinned commits):
`rec`, `--output-format` (default `asciicast-v3`), `--command`,
`--window-size COLSxROWS`, `--return`; agg `--speed`, `--idle-time-limit`,
`--font-dir`, `--font-family`, `--last-frame-duration`, `--theme`.
asciinema 3.2.1 has no `--capture-input`, `--append` or `--overwrite`.
`--return` is required: without it the recorder exits 0 regardless of the
helper's exit. `--capture-env` must not be relied on to sanitize anything;
the environment is controlled in step 2 instead, and the cast header's
`env` object is inspected afterwards (step 6).

## 2. Fresh working directory and controlled environment

Everything runs outside the checkout, in directories created by this
procedure. `mkdir` without `-p` fails if a directory already exists; that is
the overwrite refusal, never bypass it.

```bash
SESSION="$(mktemp -d /tmp/actseal-recording.XXXXXX)"
mkdir "$SESSION/warmup"
mkdir "$SESSION/attempt-1"
mkdir "$SESSION/attempt-1/work"
```

Every command from step 3 on runs under this exact environment prefix, with
no user shell startup files and no inherited variables:

```bash
env -i PATH="$PATH" HOME="$HOME" TERM="$TERM" LANG="$LANG" SHELL=/bin/sh \
```

`env -i` starts from an empty environment and sets only the five names
written above; it reads nothing else, so no credential is read, printed or
redacted. `SHELL=/bin/sh` makes any shell the recorder spawns for
`--command` a non-interactive POSIX shell that reads no rc file. `PATH` must
contain `uvx`. If `uv` needs a non-default cache location, add
`UV_CACHE_DIR="$UV_CACHE_DIR"` to the prefix and to the receipt; the helper
forwards the same allowlisted names to each child (`demo_session.ENV_ALLOWLIST`)
and closes the child's stdin, so no typed input can be captured.

## 3. Warm-up and version/hash binding, before capture

Installation and first-run work happen here, outside the timed demo and in
`warmup`, which never contains `actseal-demo`. The requirement spelling
`actseal` with no version pin is deliberately the same as the demo command,
so the environment uvx resolves here is the one the capture uses.

```bash
cd "$SESSION/warmup"
env -i PATH="$PATH" HOME="$HOME" TERM="$TERM" LANG="$LANG" SHELL=/bin/sh \
  uvx --python 3.12 actseal --version
```

Required output: `actseal 1.0.0`. Anything else (a 0.1.0 line, a
prerelease, an error) stops the procedure; record the output and do not
capture.

Then bind the resolved environment to the Task 20 artifact:

```bash
env -i PATH="$PATH" HOME="$HOME" uv cache dir
find "<uv cache dir>" -type d -name 'actseal-*.dist-info'
```

Every directory listed must be named `actseal-1.0.0.dist-info`. For each,
hash its `METADATA` file and compare with the SHA-256 of
`actseal-1.0.0.dist-info/METADATA` extracted from the wheel whose digest
Task 20 verified (re-hash that wheel against the receipt digest first; the
installer rewrites `RECORD`, so `METADATA` is the file that stays
byte-identical). Record both digests. A mismatch, or no directory at all,
stops the procedure. `$PYTHON` for the next step is the interpreter printed
by `uv python find 3.12` under the same prefix; record its path and version.

## 4. Capture

Receipt variables, filled from the Task 20 receipt and the commands above:

```bash
TASK20_VERSION=        # must be 1.0.0
TASK20_WHEEL_SHA256=   # from the Task 20 receipt
TASK20_SDIST_SHA256=   # from the Task 20 receipt
TASK20_IMPLEMENTATION_SHA256=   # accepted source fingerprint from Task 20
HELPER="$CHECKOUT/docs/assets/src/demo_session.py"
```

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
env -i PATH="$PATH" HOME="$HOME" TERM="$TERM" LANG="$LANG" SHELL=/bin/sh \
  "$ASCIINEMA" rec \
    --output-format asciicast-v3 \
    --window-size 100x40 \
    --return \
    --command "$PYTHON $HELPER" \
    "$SESSION/attempt-1/demo.cast"
echo "asciinema exit: $?"
```

`$PYTHON` and `$HELPER` are absolute paths without spaces, so the command
string needs no quoting beyond the above. `100x40` is the initial geometry
choice: 100 columns keep every approved command on one line and 40 rows keep
the first command visible while the demo output scrolls; decide geometry
before the attempt and record it, never adjust it afterwards in rendering.
Run in a real terminal; `--headless` is only for a noninteractive driver.

Record the printed `asciinema exit`. With `--return` it equals the helper's
exit: 0 means all three commands exited 0, 0, 1; 1 means a mismatch or a
command that could not start; 2 means `./actseal-demo` already existed,
which cannot happen in a fresh `work` directory. A non-zero exit, or a cast
outside the duration window, is a failed attempt: leave `attempt-1`
untouched, write `attempt-1/FAILED.md` with the exit code and reason, and
start `attempt-2` from step 2's `mkdir` lines. Never delete, rename or
re-record into an existing attempt directory.

## 5. Post-capture binding (outside the cast)

Immediately after the capture, in `warmup` again:

```bash
cd "$SESSION/warmup"
env -i PATH="$PATH" HOME="$HOME" TERM="$TERM" LANG="$LANG" SHELL=/bin/sh \
  uvx --offline --python 3.12 actseal --version
```

Must again print `actseal 1.0.0`. Repeat the `find` and `METADATA` digest
comparison from step 3; the digests must equal the pre-capture values. Then
read the fingerprint the demo itself wrote during the capture:

```bash
grep -h '"implementation_sha256"' \
  "$SESSION/attempt-1/work/actseal-demo/bad/lock.json" \
  "$SESSION/attempt-1/work/actseal-demo/fixed/lock.json"
```

Both lines must carry `$TASK20_IMPLEMENTATION_SHA256`. Any difference between
pre- and post-capture versions or digests, or a fingerprint that is not the
accepted one, invalidates the attempt even if the cast looks right.

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

`check_cast` also rejects credential-looking output. Inspect the v3 header
by eye as well: `command` must be the helper invocation, `term.cols`/`rows`
must be `100`/`40`, and any `env` object may contain only names from step 2.
Record the parsed duration; the final GIF duration in step 7 adds the
last-frame hold on top of it.

## 7. Render the GIF, then verify reproducibility

Build the agg command with the accepted helper, never by hand:
`actseal_assets.tools.agg_command(agg, cast, gif, duration_seconds=<parsed
duration>, font_dir=<checkout>/docs/assets/src/fonts, extra=("--last-frame-duration",
"3", "--theme", "<chosen theme>"))`. That yields `--speed 1`, an idle limit
of `ceil(duration) + 1` seconds (longer than the whole cast, so agg's
default 5 s idle limit never trims a pause), the pinned font directory and
`--font-family "JetBrains Mono"`. `--select` is forbidden; no geometry
override, trimming or speed change of any kind. Choose the theme once and
record it.

Account for the hold explicitly: GIF duration = cast duration + 3 s
last-frame hold, and that sum must stay within 20 to 40 s. If it does not,
the attempt failed; re-record with different pauses rather than shortening
the hold below a readable value.

Render twice into separate temporary files and require identical SHA-256
digests and a size below 3,000,000 bytes:

```bash
shasum -a 256 "$SESSION/attempt-1/render-a/demo.gif" "$SESSION/attempt-1/render-b/demo.gif"
wc -c "$SESSION/attempt-1/render-a/demo.gif"
```

If the size cap fails, stop and report; do not improvise agg flags.

## 8. Receipt, then integration (separate, reviewed step)

The capture receipt pins everything above: Task 20 version and digests as
supplied; pre- and post-capture `--version` output; `METADATA` digests;
both `implementation_sha256` values; cast SHA-256, parsed duration, geometry
and event count; GIF SHA-256, byte size and the two-render identity; the
exact agg command; `uv`, asciinema, agg and `$PYTHON` versions and paths;
the pinned binary digests re-verified by `verified_binary`; the checkout
commit and the helper's blob hash; the `env -i` prefix used; the attempt
number and every failed attempt directory kept. The receipt is a record; the
bytes it describes are the evidence.

Only after Codex reviews the raw capture does the asset get integrated:
`demo.cast` copied unchanged to `docs/assets/src/demo.cast`, `demo.gif` to
`docs/assets/demo.gif`, a `demo` renderer attached in `inventory.py` that
re-renders from the committed cast with the same `agg_command`, and
`uv run --frozen --group assets python docs/assets/src/render.py --check --only demo`
passing. None of that is part of this preparation.

## Pending (explicitly not done)

- Official asciinema/agg/font downloads: permission-blocked; `setup_tools.py`
  has not been run.
- Task 20 publication and its receipt (version, wheel/sdist digests, source
  fingerprint): pending; Decision 2 exception governs the post-publication
  capture.
- Actual warm-up, version/hash receipts, cast, GIF, two-render identity,
  duration and size measurements: none exist.
- Codex review of the raw capture and full Task 14 acceptance.
