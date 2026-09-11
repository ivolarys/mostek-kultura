"""CLI entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .build import build


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mostek-kultura")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="fetch sources and render site/")
    b.add_argument("--offline", action="store_true", help="use tests/fixtures instead of HTTP")
    b.add_argument("--no-llm", action="store_true", help="skip Claude classification")
    b.add_argument("--source", action="append", help="only these source names (repeatable)")
    b.add_argument("--record", action="store_true", help="save live responses as fixtures")
    b.add_argument("--persist", action="store_true",
                   help="write cache/last_good even outside CI (CI does it automatically)")
    b.add_argument("--out", default="site", help="output directory (default: site)")
    b.add_argument("--root", default=".", help="project root with config.yaml")
    b.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    root = Path(a.root).resolve()
    n = build(root, Path(a.out), offline=a.offline, use_llm=not a.no_llm,
              only=set(a.source) if a.source else None, record=a.record,
              persist=True if a.persist else None)
    print(f"OK: {n} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
