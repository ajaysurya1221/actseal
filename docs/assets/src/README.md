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

Invalid declarations (an output or source that is not a plain file name, a
`docs/assets` directory that resolves outside the repository) abort the run
before any renderer is called. Every write destination is re-resolved
immediately before writing; symlinks and anything resolving outside
`docs/assets` are refused.

Image references are classified. Relative paths and absolute URLs for this
repository (`raw.githubusercontent.com/ajaysurya1221/actseal/...` or
`github.com/ajaysurya1221/actseal/blob|raw/...`) must point at an existing,
declared output of an *implemented* asset. Badges from `img.shields.io`, this
repository's workflow badges and `results.pre-commit.ci` are exempt. Any other
absolute URL is an error. Markdown images and `<img>` tags need non-empty alt
text; `<source srcset>` entries do not. Nothing is fetched during validation.

## Validation rules applied to SVG outputs

- Explicit `width`, `height` and matching `viewBox`; `role="img"` with a
  non-empty `<title id="title">` and `<desc id="desc">` as the first children.
- Element allowlist only: no `<script>`, `<style>`, `<image>`,
  `<foreignObject>`, gradients, filters, patterns or animation; no event
  handler or `style` attributes; `href` must be a local fragment. The raw
  text is scanned for `<!DOCTYPE`, `<!ENTITY`, `<?xml-stylesheet`, `url(`
  and friends; decoded attribute values are scanned again (with whitespace
  removed) so character references cannot hide `url(`, `javascript:` or a
  scheme, and decoded element text is scanned for CSS/script syntax.
- Text uses a font stack ending in a generic family and a finite, positive
  `font-size` that renders at 14 px or more at the asset's declared display
  width after `transform` scaling on the element and its ancestors.
  `translate`, `rotate`, `scale` and `matrix` are understood; skews or
  unparsable transforms are errors. Outlined assets (the hero banner) may not
  contain `<text>` at all.
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

## Adding a figure

1. Implement `render(context) -> {output path: bytes}` for the asset, building
   SVG with `actseal_assets.svg` (sorted attributes, canonical numbers) and
   outlining banner text with `actseal_assets.outline`.
2. Attach it as the asset's `renderer` in `inventory.py` and finalize the
   provisional dimensions.
3. Run `render.py --write --only NAME`, review the result, then confirm
   `render.py --check --only NAME` passes before committing.
