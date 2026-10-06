"""Single renderer for Actseal documentation assets.

    uv run --frozen --group assets python docs/assets/src/render.py --write [--only ASSET]
    uv run --frozen --group assets python docs/assets/src/render.py --check [--only ASSET]

See ``actseal_assets`` beside this file for the implementation and
``README.md`` in this directory for setup of the pinned authoring tools.
"""

from __future__ import annotations

import sys

from actseal_assets.cli import main

if __name__ == "__main__":
    sys.exit(main())
