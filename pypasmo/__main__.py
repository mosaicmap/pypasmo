# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""python -m pypasmo [options] input.asm output.bin [symbols.txt [publics.txt]]"""
from .cli import cli

cli()
