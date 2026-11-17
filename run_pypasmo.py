#!/usr/bin/env python3
"""Run pypasmo from this folder without installing it:

    python run_pypasmo.py [options] input.asm output.bin [symbols.txt [publics.txt]]

The same as python -m pypasmo (or the pypasmo command after pip install).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))      # the folder with pypasmo/

from pypasmo.cli import cli  # noqa: E402

cli()
