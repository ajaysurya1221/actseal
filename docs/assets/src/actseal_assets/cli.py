"""Command-line entry for ``render.py``.

    render.py --write [--only ASSET]
    render.py --check [--only ASSET]

Exit status 0 when every check passed, 1 when any error was reported and 2 for
usage errors. Output is one line per finding followed by a summary.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .inventory import ASSET_NAMES
from .pipeline import run

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def repository_root() -> Path:
    """``docs/assets/src/actseal_assets/cli.py`` is four levels below the root."""
    return Path(__file__).resolve().parents[4]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render.py",
        description="Regenerate or verify Actseal documentation assets deterministically.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="render and write validated outputs")
    mode.add_argument(
        "--check",
        action="store_true",
        help="render into temporary storage and compare with committed outputs",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="ASSET",
        choices=ASSET_NAMES,
        help="restrict to one asset; may be repeated (%(choices)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, root: Path | str | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE
    mode = "write" if args.write else "check"
    target = Path(root) if root is not None else repository_root()
    report = run(target, mode=mode, only=tuple(args.only))
    sys.stdout.write("\n".join(report.lines()) + "\n")
    return EXIT_OK if report.ok else EXIT_FAILED
