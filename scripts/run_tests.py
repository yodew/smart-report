"""Discover the whole suite and fail on unexpected skips, including missing extras."""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# Run: .venv/bin/python scripts/run_tests.py full  (or base, without PDFium)

from __future__ import annotations

import sys
import unittest
from importlib.util import find_spec
from pathlib import Path


def main() -> int:
    match sys.argv[1:]:
        case ["full"]:
            allow_gaussian_skip = False
        case ["base"]:
            allow_gaussian_skip = True
        case _:
            print("Usage: python scripts/run_tests.py {base|full}", file=sys.stderr)
            return 2

    if allow_gaussian_skip and find_spec("pypdfium2") is not None:
        print("Base checks require an environment without pypdfium2", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unexpected = [
        test.id()
        for test, _reason in result.skipped
        if not (allow_gaussian_skip and test.id().rsplit(".", 1)[-1] in {
            "test_gaussian_shadow", "test_report_visuals",
        })
    ]
    if unexpected:
        print(f"Unexpected skipped tests: {', '.join(unexpected)}", file=sys.stderr)
    return int(not result.wasSuccessful() or bool(unexpected) or result.testsRun == 0)


if __name__ == "__main__":
    raise SystemExit(main())
