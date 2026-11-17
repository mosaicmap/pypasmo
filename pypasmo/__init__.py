# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
#
# Derived from Pasmo 0.5.5, (C) 2004-2022 Julian Albo "NotFound" <julian.notfound@gmail.com>,
# https://pasmo.speccy.org/ - the behaviour (syntax, operator precedence, output formats)
# follows its source code and documentation.
#
# DG, DUP/EDUP, STRUCT/ENDS, BANK, --tap128, --tapbas128, --memmap, the Spectrum 128K Basic
# loader (with its bank switching routine) and the (IX-n+m) fix follow the Pasmo
# 0.5.5.paged fork, (C) 2018-2023 Jouni Korhonen, https://github.com/jounikor/pasmo (GPL v3).
#
# SPDX-License-Identifier: GPL-3.0-only  (same as Pasmo: "GPL license v.3")
#
# This program is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details (file LICENSE).

r"""pypasmo - Z80 assembler in pure Python, compatible with Pasmo 0.5.5.

Command line: python -m pypasmo [options] input.asm output.bin (see pypasmo/cli.py).

From Python:
    import pypasmo
    asm = pypasmo.assemble_text(" org 8000h\n ld a,1\n")
    lo, data = pypasmo.image(asm.mem)
    tap = pypasmo.output_bytes(asm, "tapbas", "demo")

Parts: lexer, expr (expressions), z80 (instructions), assembler, out_spectrum and
out_other (output formats), cli (command line, listing, symbol files).
"""
__version__ = "0.7.0b1"          # the only place with the version (pyproject.toml reads it)
PASMO_VERSION = "0.5.5"         # the Pasmo version pypasmo is based on
# set before the imports below: cli.py reads them

from .assembler import Assembler, assemble_text  # noqa: E402
from .cli import FORMATS, cli, list_dbgsym_text, listing_text, main, output_bytes, sld_text, symbol_text  # noqa: E402
from .common import FALSE, TRUE, AsmError, image  # noqa: E402
from .lexer import lex  # noqa: E402
from .common import cpm_dsk  # noqa: E402
from .out_other import (ace_tap, amsdos, cdt_code, coleco_rom, cpc_crc, dsk_cpc, dsk_msx, dsk_pcw, fat12_msx, intel_hex, kcc, msx, msx_cas, msx_rom,  # noqa: E402
                        mzf, prl, sms_rom, sna_cpc, sna_cpc464, sna_cpc6128, trs, trs_cas, z1013, zx81_p)
from .out_spectrum import (basic_line, basic_loader, dsk_plus3, memmap_text, plus3_loader, plus3dos, sna, sna128, tap128,  # noqa: E402
                           pzx, tap_basic, tap_code, tzx, z80, z80_compress)
from .z80 import tstates  # noqa: E402
