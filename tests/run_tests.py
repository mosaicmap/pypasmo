#!/usr/bin/env python3
"""Run all pypasmo tests (unittest from the standard library, nothing to install).

usage: python tests/run_tests.py [-q] [unittest options] [test names]

Without test names all tests in this folder run; names are e.g. test_pypasmo.Labels or
test_pypasmo.Labels.test_equ. Works from any current folder.
"""
import sys
import unittest
from pathlib import Path

HERE = str(Path(__file__).resolve().parent)


def main():
    args = sys.argv[1:]
    if "-q" not in args and "--quiet" not in args:
        args = ["-v"] + args
    names = [a for a in args if not a.startswith("-")]
    sys.path.insert(0, HERE)
    if names:
        argv = ["run_tests.py"] + args
    else:
        argv = ["run_tests.py", "discover", "-s", HERE, "-t", HERE] + args
    unittest.main(module=None, argv=argv)


if __name__ == "__main__":
    main()
