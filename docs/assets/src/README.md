# Asset sources and renderer

One renderer produces every committed file under `docs/assets/` from the
sources in this directory. Regeneration is deterministic: the same sources,
pins and fonts yield byte-identical outputs, which is what `--check` verifies.

```text
render.py --write [--only ASSET]
render.py --check [--only ASSET]
```

Asset names: `hero`, `how-it-works`, `architecture`, `demo`, `social`,
`where`, `matrix`, `boundary`. The declared outputs, dimensions and sources
live in `actseal_assets/inventory.py`; an asset without a renderer is reported
as `not implemented` and is never counted as passed.

## Commands

```bash
uv sync --frozen --group dev --group assets
uv run --frozen --group assets python docs/assets/src/render.py --check
uv run --frozen --group assets python docs/assets/src/render.py --write --only hero
uv run --frozen pytest tests/visual
```

`--check` regenerates each implemented asset twice into temporary storage,
rejects nondeterministic renderers, validates the bytes and compares them with
the committed files. It also validates the tool manifest against `uv.lock`,
font attribution, every image reference in `README.md` and `docs/*.md`, and
reports files under `docs/assets/` that no asset declares. Exit status is 0
only when no error was reported.

Prerequisite errors abort the run before any renderer or tool is called and
before anything is written: invalid declarations (an output or source that is
not a plain file name, a `docs/assets` directory that resolves outside the
repository), manifest or `uv.lock` pin problems, and wrong or unlicensed font
bytes. Fonts and binaries that are simply not fetched yet stay informational
until an implemented asset needs them. Reference and orphan errors are
reported but do not block, so a figure the README already cites can be
written for the first time. Every write destination is re-resolved
immediately before writing; symlinks and anything resolving outside
`docs/assets` are refused.

Image references are parsed with the standard library HTML parser (quoted
`>` characters, single quotes, unquoted values and multi-line tags) and a
Markdown scanner that resolves inline and reference-style images
(`![alt][label]`, `![alt][]`, `![alt]`). `<img src>`, `<img srcset>` and
`<source srcset>` are all inspected; an `<img>` without `src`, an unresolved
reference label, or `<object>`, `<embed>`, `<iframe>` and `<video>` are
errors, never skips. Relative paths and absolute URLs for this repository
(`raw.githubusercontent.com/ajaysurya1221/actseal/...` or
`github.com/ajaysurya1221/actseal/blob|raw/...`) must point at an existing,
declared output of an *implemented* asset. Badges from `img.shields.io`, this
repository's workflow badges and `results.pre-commit.ci` are exempt from the
file check only. Any other absolute URL is an error. Markdown images and
`<img>` tags, badges included, need non-empty alt text; `<source srcset>`
entries do not. Nothing is fetched during validation.

## Validation rules applied to SVG outputs

- Explicit `width`, `height` and matching `viewBox`; `role="img"` with a
  non-empty `<title id="title">` and `<desc id="desc">` as the first children.
- Element allowlist only: no `<script>`, `<style>`, `<image>`,
  `<foreignObject>`, gradients, filters, patterns or animation; no event
  handler or `style` attributes; `href` must be a local fragment. The raw
  text is scanned for `<!DOCTYPE`, `<!ENTITY`, `<?xml-stylesheet`, `url(`
  and friends; decoded attribute values are scanned again (with whitespace
  removed) so character references cannot hide `url(`, `javascript:` or a
  scheme, and decoded element text is scanned for CSS/script syntax. A
  backslash anywhere in an attribute value is rejected outright, so CSS
  escapes such as `\75rl(` cannot bypass the token scan.
- Text uses a font stack ending in a generic family and a finite, positive
  `font-size` that renders at 14 px or more at the asset's declared display
  width after `transform` scaling on the element and its ancestors.
  `translate` and `rotate` preserve size; `scale` contributes its smaller
  axis and `matrix` its minimum singular value (the exact lower bound, so a
  singular or near-singular matrix fails); skews or unparsable transforms are
  errors. Outlined assets (the hero banner) may not contain `<text>` at all.
- LF line ends, UTF-8 and a final newline.

PNG and GIF outputs are checked by header for exact dimensions and size
limits. The raw demo recording (`demo.cast`, asciicast v2 or v3) is checked
for finite, non-negative, non-decreasing (v2) or finitely accumulating (v3)
event times, duration bounds and credential-looking output; GIF rendering
uses speed 1 and an idle limit longer than the whole recording.

## Pinned authoring tools

Pins, licenses, source commits and SHA-256 digests are in `tools.toml` and
summarized in `NOTICES.md`. Nothing executable is committed.

```bash
uv run --frozen python docs/assets/src/setup_tools.py --tool jetbrains-mono
uv run --frozen python docs/assets/src/setup_tools.py --tool resvg
```

Setup is explicit and network-bound; unit tests never download. Fonts and the
upstream `OFL.txt` are installed to `fonts/`; binaries go to
`$ACTSEAL_ASSET_TOOLS` (default `~/.cache/actseal-assets`). Each download is
hashed against the pin before it is installed, and a receipt with the verified
hashes and source URLs is written to `receipts/`. Receipts are records only.
Before executing a tool, `render.py` re-hashes the cached binary against the
pin; for archived tools (resvg) the pinned archive is retained in the cache,
re-hashed, its member re-extracted and compared byte for byte with the cached
executable.

## How-it-works figure (Task 12)

`actseal_assets/how_it_works.py` renders four outputs from one content table:
`how-it-works-light.svg` and `how-it-works-dark.svg` (1600×400, five
horizontal stages Freeze → Run → Verify → Seal → Replay plus a command
bracket row) and `how-it-works-mobile-light.svg` /
`how-it-works-mobile-dark.svg` (720 wide, stages stacked vertically, the
command written under each stage heading; height derived from the wrapped
content). Each stage states its inputs and, after an arrow, its output:
policy + labelled inputs → lock; provider answers → ACT · ABSTAIN · ESCALATE
· DENY; bounds and fault rules → verdict with exit code; lock, answers,
decisions and verdict → bounded evidence bundle; replay recomputes the
verdict offline with no model call. Module names, file inventories and hashes
are deliberately absent from this overview (they belong to the architecture
figure). Light and dark differ only in colour. Desktop labels are 26 units
(14.3 px at the 880 px README column) with 34-unit headings; mobile labels
are 30 units (15 px at 360 px) with 44-unit headings.

Text uses `Helvetica, Arial, Liberation Sans, sans-serif`, three
metric-compatible faces that resolve on macOS, Windows and Linux before the
generic fallback. Every line is measured against Helvetica advance widths
with an 8 % safety factor (10 % more for bold); a phrase that would not fit
its column, or a canvas that would overflow 400 units, makes the renderer
raise instead of shrinking anything. Decision and verdict runs wrap greedily
on ` · ` separators, so the same phrases pack differently per canvas.

## Adding a figure

1. Implement `render(context) -> {output path: bytes}` for the asset, building
   SVG with `actseal_assets.svg` (sorted attributes, canonical numbers) and
   outlining banner text with `actseal_assets.outline`.
2. Attach it as the asset's `renderer` in `inventory.py` and finalize the
   provisional dimensions.
3. Run `render.py --write --only NAME`, review the result, then confirm
   `render.py --check --only NAME` passes before committing.
