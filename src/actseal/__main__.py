"""``python -m actseal`` entry point; delegates to :func:`actseal.cli.main`."""

from __future__ import annotations

from actseal.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
