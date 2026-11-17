# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
r"""pypasmo - Z80 assembler in pure Python, compatible with Pasmo 0.5.5.

Usage (the same as pasmo):
    python -m pypasmo [options] input.asm output.bin [symbols.txt [publics.txt]]
    python run_pypasmo.py ...     (in the pypasmo folder, without installing)
    pypasmo ...                   (after pip install pypasmo)

Output format (default --bin):
    --bin            raw binary from the lowest to the highest used address
    --hex            Intel HEX
ZX Spectrum output (other names in brackets: those of Pasmo and the 0.5.5.paged fork):
    --tap-48k        .tap tape image with a CODE block (--tap)
    --tap-wloader-48k  .tap with a Basic loader: CLEAR, LOAD "" CODE, RANDOMIZE USR
                     (--tapbas)
    --tzx-48k        .tzx tape image with a CODE block (--tzx)
    --tzx-wloader-48k  .tzx with a Basic loader (--tzxbas)
    --pzx-48k        .pzx tape image with a CODE block (pypasmo extension, early version)
    --pzx-wloader-48k  .pzx with a Basic loader (pypasmo extension, early version)
    --tap-128k       .tap for the Spectrum 128K: a CODE block for each BANK (--tap128;
                     early version)
    --tap-wloader-128k  the same with a Basic loader that pages the banks in
                     (--tapbas128; early version)
    --tzx-128k       .tzx with the blocks of --tap-128k (pypasmo extension, IN DEVELOPMENT)
    --tzx-wloader-128k  .tzx with the blocks of --tap-wloader-128k (pypasmo extension,
                     IN DEVELOPMENT)
    --pzx-128k       .pzx with the blocks of --tap-128k (pypasmo extension, IN DEVELOPMENT)
    --pzx-wloader-128k  .pzx with the blocks of --tap-wloader-128k (pypasmo extension,
                     IN DEVELOPMENT)
    --sna-48k        48K .sna snapshot, runs at once in an emulator (pypasmo extension,
                     early version)
    --z80-48k        the same as a 48K .z80 snapshot (version 3, compressed; pypasmo
                     extension, early version)
    --sna-128k       128K .sna snapshot with the banks of BANK (pypasmo extension,
                     early version)
    --z80-128k       the same as a 128K .z80 snapshot (version 3, compressed; pypasmo
                     extension, early version)
    --plus3dos       +3DOS disk file (Spectrum +3; early version)
    --dsk-plus3      Spectrum +3 .dsk disk image: NAME.BIN and the Basic loader DISK,
                     run by "Loader" in the +3 menu (pypasmo extension, early version)
Amstrad CPC output:
    --amsdos         disk file with an Amsdos header (LOAD "file",addr / RUN "file")
    --dsk-cpc        .dsk disk image (DATA format) with the Amsdos file NAME.BIN:
                     RUN "name" (pypasmo extension, early version)
    --sna-cpc6128    CPC 6128 .sna snapshot in Basic, runs at once, RET goes back to
                     Basic (pypasmo extension, early version)
    --sna-cpc464     the same for the CPC 464 (pypasmo extension, early version)
    --cdt            .cdt tape image (RUN ""; early version)
    --cdt-wloader    .cdt with a Locomotive Basic loader (MEMORY, LOAD "!", CALL;
                     --cdtbas; early version)
MSX output:
    --msx            BLOAD file (BLOAD "file",R)
    --rom-msx        cartridge ROM: the source writes the header "AB" + INIT at 4000h
                     or 8000h, padded to 8/16/32 KB (pypasmo extension, early version)
    --cas-msx        .cas tape: a binary file for BLOAD "CAS:",R (pypasmo extension)
    --dsk-msx        720 KB .dsk disk image: NAME.BIN and AUTOEXEC.BAS that runs it
                     (BLOAD ,R), code in 8800h-DE3Fh (pypasmo extension, early version)
Other output:
    --tap-ace        Jupiter Ace .tap: a loader and the code, 0 0 BLOAD NAME loads and
                     runs it, the code returns with JP (IY) (pypasmo extension,
                     IN DEVELOPMENT)
    --kcc-kc85       Robotron KC 85/2-4 .kcc file with autostart (pypasmo extension,
                     early version)
    --z80-z1013      Robotron Z 1013 .z80 file (headersave; pypasmo extension,
                     early version)
    --rom-sms        Sega Master System cartridge ROM .sms, 32 KB from 0000h, the header
                     with the checksum at 7FF0h (pypasmo extension, early version)
    --rom-gg         the same for the Sega Game Gear, .gg (pypasmo extension,
                     early version)
    --p-zx81         ZX81 .p file (as in emulators): the code in 1 REM (ORG 16514),
                     runs at once (RAND USR), 16K RAM (pypasmo extension, early version)
    --prl            relocatable .prl / .rsx file for CP/M Plus, source without ORG
                     (early version; a plain CP/M .COM program is --bin with ORG 100h)
    --trs            TRS-80 /CMD file: load records + the entry from END (Model I/III/4;
                     early version)
    --cas-trs        TRS-80 Model I tape .cas (500 baud): SYSTEM, the name, then / runs
                     it (Model III: L at Cass?; pypasmo extension, IN DEVELOPMENT)
    --mzf            Sharp MZ-700/800 .mzf tape file: 128 byte header (name, load and
                     start address) + code (pypasmo extension, early version)
    --dsk-pcw        Amstrad PCW .dsk disk image with the CP/M program NAME.COM (ORG 100h),
                     run it by its name under CP/M Plus (pypasmo extension, IN DEVELOPMENT)
    --rom-coleco     ColecoVision cartridge ROM .col from 8000h, the source writes the header
                     AAh 55h / 55h AAh (pypasmo extension, IN DEVELOPMENT)
Options:
    --name NAME      name in the file header (default: the output file name):
                     .tap/.tzx (10 characters), .cdt (16), Amsdos (8+3), .mzf (16),
                     .cas (6), --tap-ace (10, 0 0 BLOAD name), .kcc (8), Z 1013 (16),
                     --cas-trs (6), the file NAME.BIN on --dsk-cpc / --dsk-plus3 /
                     --dsk-msx and NAME.COM on --dsk-pcw (8)
    --nocase         identifiers are case insensitive
    -I DIR           add a directory for INCLUDE and INCBIN
    -E, --equ X[=V]  predefine symbol X (default value FFFFh)
    -B, --bracket    bracket only mode: only [ ] means indirection, ( ) only groups
    --alocal         autolocal mode: labels starting with _ are local
    -8, --w8080      warn about instructions that the 8080 does not have
    --werror         treat warnings as errors
    --pasmo-syntax-055  only the source syntax of Pasmo 0.5.5, to assemble old sources
                     whose labels collide with newer directives: no PHASE, DEPHASE,
                     ALIGN, ASSERT, DZ, DC, TAPE_BLOCK, TAPE_BLOCK_SCREEN, TAP_INCLUDE,
                     DISPLAY, D_ZX81, D_ZX81I, DC_ZX81, ELSEIF, IFB, IFNB, BANK_OF,
                     macro parameter defaults, INCBIN offset, .name local labels
                     (pypasmo) and no DG,
                     DUP, EDUP, STRUCT, ENDS, BANK (0.5.5.paged fork);
                     these are normal names then
    --err            assembly errors go to standard output instead of standard error
    --public         symbol file contains only PUBLIC symbols
    -d               print the listing to standard output
    --lst FILE.lst   write the listing to FILE.lst (pypasmo extension, with T-states)
    --dbgsym-list FILE.list
                     list file for the DeZog debugger (VS Code), debugging in the
                     list file (revEng format: labels, EQU, code; pypasmo extension, 48K)
    --dbgsym-sld FILE.sld
                     SLD file (Source Level Debugging, as sjasmplus --sld) for
                     DeZog: stepping in the .asm source (pypasmo extension, 48K/128K)
    --memmap         print the used memory pages and Spectrum 128K banks
    --version        print the version
    -h, --help       print this help

Documentation: doc/index.md, original Pasmo documentation: https://pasmo.speccy.org/pasmodoc.html

From Python:
    import pypasmo
    asm = pypasmo.assemble_text(" org 8000h\n ld a,1\n")
    lo, data = pypasmo.image(asm.mem)
"""
# (this docstring is the text of --help)
import os
import re
import sys
from pathlib import Path

from . import PASMO_VERSION, __version__
from .assembler import Assembler
from .common import OPTION_NAMES, TRUE, AsmError, cpm_name, image, option, readable
from .lexer import comment_of, lex
from .out_other import (ace_tap, amsdos, cdt_basic, cdt_code, coleco_rom, cpc_basic_loader, dsk_cpc, dsk_msx, dsk_pcw,
                        intel_hex, kcc, msx, msx_cas,
                        msx_rom, mzf, prl, sms_rom, sna_cpc464, sna_cpc6128, trs, trs_cas, z1013, zx81_p)
from .out_spectrum import (TZX_HEAD, basic_loader, dsk_plus3, memmap_text, plus3dos, plus3_loader, sna, sna128, tap128, tap_basic,
                           pzx, tap_code, tap_listed_blocks, tape_warnings, tzx, z80)

VERSION_TEXT = f"pypasmo {__version__} (based on Pasmo {PASMO_VERSION})"


FORMATS = ("bin", "hex", "prl", "tap", "tapbas", "tzx", "tzxbas", "plus3dos", "sna-48k",
           "z80-48k", "sna-128k",
           "z80-128k", "tap128", "tapbas128", "amsdos", "cdt", "cdtbas", "msx",
           "rom-msx", "cas-msx", "mzf", "p-zx81", "tap-ace", "kcc-kc85", "z80-z1013", "rom-sms",
           "rom-gg", "dsk-cpc", "dsk-plus3", "trs", "cas-trs", "sna-cpc6128", "sna-cpc464", "dsk-msx",
           "pzx-48k", "pzx-wloader-48k", "dsk-pcw", "rom-coleco",
           "tzx-128k", "tzx-wloader-128k", "pzx-128k", "pzx-wloader-128k")
TAPE_CODE = ("tap", "tzx", "pzx-48k")                       # a CODE block
TAPE_LOADER = ("tapbas", "tzxbas", "pzx-wloader-48k")       # a Basic loader + a CODE block
TAPE_128 = ("tap128", "tzx-128k", "pzx-128k")               # a CODE block for each BANK
TAPE_128_LOADER = ("tapbas128", "tzx-wloader-128k", "pzx-wloader-128k")   # + the 128K loader
# the main names of the Spectrum tape formats (with the machine in the name)
FORMAT_ALIASES = {name: fmt for fmt, name in OPTION_NAMES.items()}


def tape(fmt, tap):
    """The tap blocks in the file format of fmt: .tap, .tzx or .pzx."""
    if fmt.startswith("tzx"):
        return tzx(tap)
    if fmt.startswith("pzx"):
        return pzx(tap)
    return tap


def output_bytes(asm, fmt, name):
    """Content of the output file in one of FORMATS."""
    if asm.banks and fmt not in TAPE_128 + TAPE_128_LOADER + ("sna-128k", "z80-128k"):
        raise AsmError(f"BANK {min(asm.banks)} with code at C000h-FFFFh needs a 128K format"
                       " (--tap-128k, --tap-wloader-128k, --tzx-128k, --tzx-wloader-128k, --pzx-128k,"
                       " --pzx-wloader-128k, --sna-128k, --z80-128k)")
    lo, data = image(asm.mem)
    if len(data) > 0xFFFF and fmt not in ("bin", "hex"):
        # the headers have a 16 bit length (Pasmo writes a broken file with length 0)
        raise AsmError(f"the code fills the whole 64 KB, too big for {option(fmt)}")
    if asm.tape_blocks and fmt in TAPE_128 + TAPE_128_LOADER:
        raise AsmError(f"TAPE_BLOCK is not supported with {option(fmt)} (use --tap-48k, "
                       "--tap-wloader-48k, --tzx-48k, --tzx-wloader-48k, --pzx-48k or --pzx-wloader-48k)")
    if fmt in TAPE_128 + TAPE_128_LOADER:
        return tape(fmt, tap128(asm, name, fmt in TAPE_128_LOADER, fmt))
    if asm.tape_blocks and fmt in TAPE_CODE + TAPE_LOADER:
        return tape(fmt, tap_listed_blocks(asm, fmt in TAPE_LOADER, fmt))
    if fmt == "hex":
        return intel_hex(asm.mem, asm.entry).encode("ascii")
    if fmt == "plus3dos":
        return plus3dos(lo, data)
    if fmt == "sna-48k":
        return sna(asm)
    if fmt == "z80-48k":
        return z80(asm)
    if fmt == "sna-128k":
        return sna128(asm)
    if fmt == "z80-128k":
        return z80(asm, k128=True)
    if fmt == "prl":
        return prl(asm)
    if fmt in TAPE_CODE:
        tape_warnings(asm, fmt, [lo] if data else [])
        return tape(fmt, tap_code(lo, data, name))
    if fmt in TAPE_LOADER:
        basic = basic_loader(lo, asm.entry)
        tape_warnings(asm, fmt, [lo] if data else [], basic, lo - 1 if data else None)   # no code: no CLEAR
        return tape(fmt, tap_basic(basic) + tap_code(lo, data, name))
    if fmt == "amsdos":
        return amsdos(lo, data, asm.entry, name)
    if fmt == "cdt":
        return TZX_HEAD + cdt_code(lo, data, asm.entry, name)
    if fmt == "cdtbas":
        return TZX_HEAD + cdt_basic(cpc_basic_loader(lo, asm.entry)) + cdt_code(lo, data, asm.entry, name)
    if fmt == "msx":
        return msx(lo, data, asm.entry)
    if fmt == "rom-msx":
        return msx_rom(lo, data)
    if fmt == "cas-msx":
        return msx_cas(lo, data, asm.entry, name)
    if fmt == "trs":
        return trs(lo, data, asm.entry)
    if fmt == "cas-trs":
        return trs_cas(lo, data, asm.entry, name)
    if fmt == "mzf":
        return mzf(lo, data, asm.entry, name)
    if fmt == "tap-ace":
        return ace_tap(lo, data, asm.entry, name)
    if fmt == "kcc-kc85":
        return kcc(lo, data, asm.entry, name)
    if fmt == "z80-z1013":
        return z1013(lo, data, asm.entry, name)
    if fmt in ("rom-sms", "rom-gg"):
        return sms_rom(asm.mem, 4 if fmt == "rom-sms" else 7)
    if fmt == "sna-cpc6128":
        return sna_cpc6128(asm)
    if fmt == "sna-cpc464":
        return sna_cpc464(asm)
    if fmt == "dsk-cpc":
        return dsk_cpc(lo, data, asm.entry, name)
    if fmt == "dsk-msx":
        return dsk_msx(lo, data, asm.entry, name)
    if fmt == "dsk-pcw":
        return dsk_pcw(lo, data, asm.entry, name)
    if fmt == "rom-coleco":
        return coleco_rom(lo, data)
    if fmt == "dsk-plus3":
        tape_warnings(asm, fmt, [lo] if data else [], plus3_loader(lo, asm.entry, cpm_name(name) + ".BIN"),
                      lo - 1 if data else None)
        return dsk_plus3(lo, data, asm.entry, name)
    if fmt == "p-zx81":
        return zx81_p(lo, data, asm.entry, asm.warnings)
    return data



def listing_text(asm):
    out = []
    for i, (addr, data, t, text, depth) in enumerate(asm.listing):
        a = "    " if addr is None else f"{addr:04X}"
        cells = [x if isinstance(x, str) else f"{x:02X}" for x in data]
        rows = [cells[k:k + 6] for k in range(0, len(cells), 6)] or [[]]
        mark = "+" * depth               # + marks lines from macros, REPT and IRP
        # T-states of an instruction as a comment at the end of the line: ;17T
        out.append(f"{a}  {' '.join(rows[0]):<18}{mark:<2}{text.rstrip()}" + (f"  ;{t}T" if t else ""))
        for k, row in enumerate(rows[1:], 1):
            out.append(f"{(addr + 6 * k) & 0xFFFF:04X}  {' '.join(row)}")
        if i in asm.routine_totals:          # a simple routine (pypasmo extension)
            name, total = asm.routine_totals[i]
            out.append(f"      ; {name}: {total}T from the label to RET")
    out.append("")
    out.append("Symbols:")
    for k, v in sorted(asm.symbols.items(), key=lambda kv: (kv[1], kv[0])):
        if asm.symkind.get(k) != "defl":
            out.append(f"  {k:<16} {v:04X}")
    return "\n".join(out) + "\n"


def symbol_text(asm, only=None):
    """Symbol table in Pasmo format (can be INCLUDEd in another source).
    only: list of names to include (the PUBLIC symbols), None = all."""
    names = sorted(asm.symbols) if only is None else sorted({asm.norm(n) for n in only})
    out = []
    for k in names:
        if k not in asm.symbols or asm.symkind.get(k) == "defl" or k in asm.predefined:
            continue
        pad = "\t\t" if len(k) < 8 else "\t" if len(k) < 16 else " "
        out.append(f"{k}{pad}EQU 0{asm.symbols[k]:04X}H")
    return "\n".join(out) + ("\n" if out else "")


def list_dbgsym_text(asm):
    """--dbgsym-list (pypasmo extension): a list file for the DeZog debugger (VS Code) in
    its "revEng" format: 'ADDR BYTES  label: ; source line' for the code, 'name: EQU value'
    for constants, the other lines are comments. Labels and EQU; DEFL, -E symbols and
    LOCAL / autolocal symbols (internal names 00000000 ...) are left out. The addresses
    are $ (with PHASE: where the code runs). Only 48K: no bank numbers yet."""
    if asm.banks:
        raise AsmError("--dbgsym-list: BANK is not supported (no bank numbers in the file yet)")

    def wanted(k, kind):
        return asm.symkind.get(k) == kind and k not in asm.predefined and not re.fullmatch(r"[0-9A-F]{8}", k)
    labels = {}
    for k, v in sorted(asm.symbols.items()):
        if wanted(k, "label"):
            labels.setdefault(v, []).append(k)
    out = ["; DeZog list file (revEng format) made by pypasmo"]
    out += [f"{k}: EQU {v}" for k, v in sorted(asm.symbols.items()) if wanted(k, "equ")]
    for addr, data, t, text, depth in asm.listing:
        src = readable(text.strip()).replace("/*", "/ *")      # /* starts a comment in DeZog
        if addr is None or not any(isinstance(x, int) for x in data):
            out.append(f"; {src}".rstrip())
            continue
        names = labels.pop(addr, [])
        out += [f"{addr:04X} {name}:" for name in names[:-1]]
        for k in range(0, len(data), 6):
            hexes = " ".join(f"{x:02X}" for x in data[k:k + 6] if isinstance(x, int))
            label = f"{names[-1]}: " if names and k == 0 else ""
            out.append(f"{(addr + k) & 0xFFFF:04X} {hexes}  {label};" + (f" {src}" if k == 0 else ""))
    out += [f"{a:04X} {name}:" for a, names in sorted(labels.items()) for name in names]
    return "\n".join(out) + "\n"


SLD_ZX48K = "pages.size:16384,pages.count:4,slots.count:4,slots.adr:0,16384,32768,49152"
SLD_ZX128K = "pages.size:16384,pages.count:8,slots.count:4,slots.adr:0,16384,32768,49152"
SLD_KEYWORDS = re.compile(r"\b(WPMEM|LOGPOINT|ASSERTION)([\s,]|$)")     # as DeZog finds them


def sld_text(asm):
    """--dbgsym-sld (pypasmo extension): Source Level Debugging data of sjasmplus (SLD
    version 1) for DeZog, stepping and breakpoints in the .asm source. The ZX Spectrum
    48K, or the 128K with BANK (the 'Z' line that DeZog takes as ZX48K / ZX128K). The
    page of an address: 48K its slot (DeZog does not use it), 128K its RAM bank (BANK at
    C000h-FFFFh, 5 at 4000h, 2 at 8000h; 9 = DeZog's ROM1, the 48 BASIC ROM, below).
    T lines: each instruction with its file and line (for a macro the line of the call);
    L lines: labels and EQU; K lines: comments with WPMEM, LOGPOINT or ASSERTION (DeZog
    commands) with the address ($) of the line. Checked against the SLD parser of DeZog
    (src/labels/sjasmplussldlabelparser.ts)."""
    k128 = bool(asm.banks)

    def page(addr, bank):
        if not k128:
            return addr >> 14
        return bank if addr >= 0xC000 else 2 if addr >= 0x8000 else 5 if addr >= 0x4000 else 9

    def where(loc):
        name, _, line = loc.rpartition(":")
        path = asm.src_files.get(name, name)
        try:
            path = os.path.relpath(path)             # DeZog looks for it in its srcDirs
        except ValueError:                           # another drive (Windows)
            pass
        # the paths in UTF-8 (DeZog reads UTF-8), the file is written byte for byte (latin-1)
        return path.replace("\\", "/").encode("utf-8").decode("latin-1"), line
    main_file = where(f"{asm.path.name}:1")[0]
    out = ["|SLD.data.version|1", "||K|KEYWORDS|WPMEM,LOGPOINT,ASSERTION",
           f"{main_file}|1||0|-1|-1|Z|{SLD_ZX128K if k128 else SLD_ZX48K}"]
    for k, v in sorted(asm.symbols.items()):
        kind = asm.symkind.get(k)
        if k not in asm.label_loc or kind not in ("label", "equ") or re.fullmatch(r"[0-9A-F]{8}", k):
            continue
        loc, bank = asm.label_loc[k]
        f, line = where(loc)
        pg, traits = (page(v, bank), "") if kind == "label" else (-1, ",+equ")
        out.append(f"{f}|{line}||0|{pg}|{v}|L|,{k},{traits}")
    for i, (addr, data, t, text, depth) in enumerate(asm.listing):
        if i not in asm.listing_src:
            continue
        loc, bank, pc = asm.listing_src[i]
        f, line = where(loc)
        comment = comment_of(text)                                 # DeZog: the text after ';'
        if SLD_KEYWORDS.search(comment):
            pc = addr if addr is not None else pc                  # $ after the line's bytes
            out.append(f"{f}|{line}||0|{page(pc, bank)}|{pc}|K|{readable(comment.replace('|', ' ')).rstrip()}")
        if addr is not None and t:                                 # instructions
            out.append(f"{f}|{line}||0|{page(addr, bank)}|{addr}|T|")
    return "\n".join(out) + "\n"


def main(argv):
    opts = {"nocase": False, "fmt": "bin", "inc": [], "equ": {}, "lst": None, "d": False,
            "name": None, "bracket": False, "alocal": False, "w8080": False, "werror": False,
            "public": False, "err": False, "memmap": False, "pasmo_syntax": False,
            "dbgsym_list": None, "dbgsym_sld": None}
    try:
        files = parse_args(argv, opts)
    except StopIteration:
        print(f"Option {argv[-1]} needs an argument.", file=sys.stderr)
        return 2
    except (AsmError, ValueError) as e:
        print(f"Invalid option: {e}", file=sys.stderr)
        return 2
    if files in ("help", "version"):
        print(VERSION_TEXT)
        if files == "help":
            print(__doc__)
        return 0
    if files is None:
        return 2
    if len(files) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    if len(files) > 4:                               # Pasmo: "WARNING: Extra arguments ignored"
        print(f"warning: extra arguments ignored: {' '.join(files[4:])}", file=sys.stderr)
    asm = Assembler(opts["nocase"], opts["inc"], opts["equ"], bracket=opts["bracket"],
                    alocal=opts["alocal"], w8080=opts["w8080"], werror=opts["werror"],
                    pasmo_syntax=opts["pasmo_syntax"])
    try:
        mem = asm.assemble(files[0])
    except (AsmError, OSError) as e:
        for msg in getattr(asm, "displays", []):
            print(msg)
        # --err: like Pasmo, assembly errors (not warnings) go to standard output
        for msg in getattr(e, "errors", None) or [e]:
            print(f"ERROR: {msg}", file=sys.stdout if opts["err"] else sys.stderr)
        return 1
    for msg in asm.displays:
        print(msg)
    try:
        return write_outputs(asm, mem, files, opts)
    except (AsmError, OSError) as e:      # --prl assembles again, files may not be writable
        print(f"ERROR: {e}", file=sys.stdout if opts["err"] else sys.stderr)
        return 1


def parse_args(argv, opts):
    """Parse options into opts and return the list of files
    (None = invalid option, "help" / "version" for those options)."""
    files = []
    it = iter(argv)
    for a in it:
        if a.startswith("--") and a[2:] in FORMATS:
            opts["fmt"] = a[2:]
        elif a.startswith("--") and a[2:] in FORMAT_ALIASES:
            opts["fmt"] = FORMAT_ALIASES[a[2:]]
        elif a == "--name":
            opts["name"] = next(it)
        elif a == "--nocase":
            opts["nocase"] = True
        elif a == "-I":
            opts["inc"].append(next(it))
        elif a in ("-E", "--equ"):
            # like Pasmo: NAME or NAME=number (a number only, no expression)
            name, eq, val = next(it).partition("=")
            ntoks, vtoks = lex(name), lex(val)
            if len(ntoks) != 1 or ntoks[0].kind != "id" or (eq and (len(vtoks) != 1 or vtoks[0].kind != "num")):
                raise AsmError(f"--equ {name}{eq}{val}: expected NAME or NAME=number")
            opts["equ"][ntoks[0].val] = vtoks[0].val if eq else TRUE
        elif a in ("-B", "--bracket"):
            opts["bracket"] = True
        elif a == "--alocal":
            opts["alocal"] = True
        elif a in ("-8", "--w8080"):
            opts["w8080"] = True
        elif a == "--werror":
            opts["werror"] = True
        elif a == "--pasmo-syntax-055":
            opts["pasmo_syntax"] = True
        elif a == "--public":
            opts["public"] = True
        elif a == "--lst":
            opts["lst"] = next(it)
        elif a == "--dbgsym-list":
            opts["dbgsym_list"] = next(it)
        elif a == "--dbgsym-sld":
            opts["dbgsym_sld"] = next(it)
        elif a == "--memmap":
            opts["memmap"] = True
        elif a == "-d":
            opts["d"] = True
        elif a in ("-h", "--help"):
            return "help"
        elif a == "--version":
            return "version"
        elif a == "--err":
            opts["err"] = True
        elif a in ("-v", "-1"):
            pass
        elif a == "--":
            files += list(it)
        elif a.startswith("-") and len(a) > 1:
            print(f"Option {a} is not supported by pypasmo.", file=sys.stderr)
            return None
        else:
            files.append(a)
    return files


def write_outputs(asm, mem, files, opts):
    try:
        # Name in the .tap header: like Pasmo, the output file name as given (max. 10 chars).
        out = output_bytes(asm, opts["fmt"], opts["name"] or files[1])    # may add warnings
    finally:
        for w in asm.warnings:
            print(w, file=sys.stderr)
    if opts["werror"] and asm.warnings:
        raise AsmError("warnings treated as errors (--werror)")
    lo, data = image(mem)
    if opts["public"] and not asm.publics:
        print("warning: no public symbols", file=sys.stderr)
    # all texts first: an error in one of them (BANK with --dbgsym-list ...) leaves no files
    texts = []                                       # (file name, text); "-" = standard output
    symfiles = [(files[2] if len(files) > 2 else "", asm.publics if opts["public"] else None),
                ("" if opts["public"] or len(files) < 4 else files[3], asm.publics)]
    texts += [(fname, symbol_text(asm, only)) for fname, only in symfiles if fname]
    if opts["dbgsym_list"]:
        texts.append((opts["dbgsym_list"], list_dbgsym_text(asm)))
    if opts["dbgsym_sld"]:
        texts.append((opts["dbgsym_sld"], sld_text(asm)))
    memmap = memmap_text(asm) if opts["memmap"] else ""
    lst = listing_text(asm) if opts["lst"] or opts["d"] else ""
    if opts["lst"]:
        texts.append((opts["lst"], lst))
    Path(files[1]).write_bytes(out)
    for fname, text in texts:
        if fname == "-":
            sys.stdout.write(text)
        else:
            Path(fname).write_text(text, encoding="latin-1")
    sys.stdout.write(memmap)
    if opts["d"]:
        sys.stdout.write(readable(lst))
    banks = "".join(f", bank {n}: {len(image(m)[1])} bytes from {min(m):04X}h"
                    for n, m in sorted(asm.banks.items()))
    print(f"{files[0]} -> {files[1]}: {len(data)} bytes from {lo:04X}h{banks}", file=sys.stderr)
    return 0


def cli():
    """Entry point of the 'pypasmo' command installed by pip (see pyproject.toml)."""
    sys.exit(main(sys.argv[1:]))
