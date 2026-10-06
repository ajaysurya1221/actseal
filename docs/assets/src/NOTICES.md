# Asset authoring notices

The Actseal runtime has no dependencies. The tools below are used only to
author the files under `docs/assets/`; none of them is linked into, vendored
in or required by the published package. Exact pins, source commits, download
URLs and SHA-256 digests are in [`tools.toml`](tools.toml). `setup_tools.py`
verifies each download against that digest before installing it, and
`render.py` re-verifies a cached binary before every execution (for archived
tools by re-hashing the retained archive and re-extracting the member).

| Tool | Version | License | Use | Distribution in this repository |
|---|---|---|---|---|
| fontTools | 4.66.1 | MIT | Outline the pinned banner glyphs into SVG paths | Not committed; installed through the uv `assets` dependency group and pinned in `uv.lock` |
| JetBrains Mono | 2.304 | SIL OFL-1.1 | Source font for the outlined banner and terminal rendering | Font files and the upstream `OFL.txt` are placed under `fonts/` by setup, unmodified |
| asciinema | 3.2.1 | GPL-3.0-or-later | Record the real published demo | Not committed; executed from the local cache |
| agg | 1.9.0 | GPL-3.0-or-later | Render the raw recording to GIF | Not committed; executed from the local cache |
| resvg | 0.48.1 | Apache-2.0 OR MIT | Rasterize the social preview PNG | Not committed; executed from the local cache |

## JetBrains Mono (SIL Open Font License 1.1)

Copyright 2020 The JetBrains Mono Project Authors
(<https://github.com/JetBrains/JetBrainsMono>), with Reserved Font Name
"JetBrains Mono". The font is used as supplied at the pinned commit; it is not
modified, renamed or sold. The committed banner SVGs contain outlines derived
from the font, and the social PNG and demo GIF are rasterizations. The
upstream `OFL.txt` is fetched verbatim and must stay beside the font files;
`render.py --check` fails when it is missing.

## asciinema and agg (GPL-3.0-or-later)

Both programs are run as separate executables to produce media files. Their
output (the `.cast` recording and the rendered GIF) is Actseal documentation
and is not a derivative work of either program. No GPL code is copied into
this repository.

## fontTools (MIT) and resvg (Apache-2.0 OR MIT)

Used as installed tools. License texts are available at the `license_url`
recorded for each entry in `tools.toml`.
