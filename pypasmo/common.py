# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""Definitions used by all parts: errors, Z80 opcode tables, reserved words, disk images."""
import re


TRUE = 0xFFFF
# main option names of tape formats; the internal names (also options) are those of
# Pasmo and of the 0.5.5.paged fork
OPTION_NAMES = {"tap": "tap-48k", "tapbas": "tap-wloader-48k", "tzx": "tzx-48k",
                "tzxbas": "tzx-wloader-48k", "tap128": "tap-128k", "tapbas128": "tap-wloader-128k",
                "cdtbas": "cdt-wloader"}


def option(fmt):
    """The main option of an output format, for messages: "tap" -> "--tap-48k"."""
    return "--" + OPTION_NAMES.get(fmt, fmt)


FALSE = 0

R8 = {"B": 0, "C": 1, "D": 2, "E": 3, "H": 4, "L": 5, "(HL)": 6, "A": 7}
RP = {"BC": 0, "DE": 1, "HL": 2, "SP": 3}
RP_PUSH = {"BC": 0, "DE": 1, "HL": 2, "AF": 3}
CC = {"NZ": 0, "Z": 1, "NC": 2, "C": 3, "PO": 4, "PE": 5, "P": 6, "M": 7}
ALU = {"ADD": 0, "ADC": 1, "SUB": 2, "SBC": 3, "AND": 4, "XOR": 5, "OR": 6, "CP": 7}
ROT = {"RLC": 0, "RRC": 1, "RL": 2, "RR": 3, "SLA": 4, "SRA": 5, "SLL": 6, "SRL": 7}
BITOP = {"BIT": 0x40, "RES": 0x80, "SET": 0xC0}
NOARG = {
    "NOP": [0x00], "HALT": [0x76], "DI": [0xF3], "EI": [0xFB], "EXX": [0xD9],
    "SCF": [0x37], "CCF": [0x3F], "CPL": [0x2F], "DAA": [0x27],
    "RLCA": [0x07], "RRCA": [0x0F], "RLA": [0x17], "RRA": [0x1F], "RET": [0xC9],
    "NEG": [0xED, 0x44], "RETN": [0xED, 0x45], "RETI": [0xED, 0x4D],
    "RRD": [0xED, 0x67], "RLD": [0xED, 0x6F],
    "LDI": [0xED, 0xA0], "CPI": [0xED, 0xA1], "INI": [0xED, 0xA2], "OUTI": [0xED, 0xA3],
    "LDD": [0xED, 0xA8], "CPD": [0xED, 0xA9], "IND": [0xED, 0xAA], "OUTD": [0xED, 0xAB],
    "LDIR": [0xED, 0xB0], "CPIR": [0xED, 0xB1], "INIR": [0xED, 0xB2], "OTIR": [0xED, 0xB3],
    "LDDR": [0xED, 0xB8], "CPDR": [0xED, 0xB9], "INDR": [0xED, 0xBA], "OTDR": [0xED, 0xBB],
}
MNEMONICS = set(NOARG) | set(ALU) | set(ROT) | set(BITOP) | {
    "LD", "INC", "DEC", "JP", "JR", "DJNZ", "CALL", "RST", "IM", "PUSH", "POP",
    "EX", "IN", "OUT"}
DIRECTIVES = {
    "ORG", "EQU", "DEFL", "DB", "DEFB", "DEFM", "DW", "DEFW", "DS", "DEFS",
    "INCLUDE", "INCBIN", "IF", "IFDEF", "IFNDEF", "ELSE", "ENDIF", "END",
    "PROC", "ENDP", "LOCAL", "MACRO", "ENDM", "EXITM", ".SHIFT", "REPT", "IRP",
    ".ERROR", ".WARNING", "PUBLIC", ".Z80", ".8080",
    # from the Pasmo 0.5.5.paged fork (Jouni Korhonen)
    "DG", "DUP", "EDUP", "STRUCT", "ENDS", "BANK"}
REGISTERS = {"A", "B", "C", "D", "E", "H", "L", "I", "R", "AF", "AF'", "BC", "DE", "HL",
             "SP", "IX", "IY", "IXH", "IXL", "IYH", "IYL"}
WORD_OPS = {"MOD", "SHL", "SHR", "EQ", "NE", "LT", "LE", "GT", "GE", "NOT", "AND",
            "OR", "XOR", "HIGH", "LOW", "NUL", "DEFINED"}
RESERVED = MNEMONICS | DIRECTIVES | REGISTERS | set(CC) | WORD_OPS
# reserved like in the fork; with --pasmo-syntax-055 normal names, as in Pasmo 0.5.5
FORK_DIRECTIVES = {"DG", "DUP", "EDUP", "STRUCT", "ENDS", "BANK"}
# pypasmo extensions (off with --pasmo-syntax-055, like the .name local labels); not
# reserved, so sources for Pasmo may use these names for labels and macros
EXT_DIRECTIVES = {"PHASE", "DEPHASE", ".PHASE", ".DEPHASE", "ALIGN", "ASSERT", "DZ", "DC",
                  "TAPE_BLOCK", "TAPE_BLOCK_SCREEN", "TAP_INCLUDE", "IFB", "IFNB", "DISPLAY",
                  "D_ZX81", "D_ZX81I", "DC_ZX81", "ELSEIF"}
# the ZX81 character set: codes 0-63 (+ 128 = inverse); 1-10 are block graphics and 12 is
# the pound sign (written as numbers), 64-127 and 192-255 are not characters
ZX81_CHARS = " " + "\0" * 10 + '"\0$:?()><=+-*/;,.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ZX81_CODES = {c: i for i, c in enumerate(ZX81_CHARS) if c != "\0"}
BLOCK_START = {"MACRO", "REPT", "IRP", "DUP"}
BLOCK_END = {"ENDM", "EDUP"}           # DUP / EDUP = REPT / ENDM (0.5.5.paged fork)
# One-byte opcodes that exist on the Z80 but not on the 8080 (all CB/DD/ED/FD prefixed
# instructions are Z80 only as well): EX AF,AF', DJNZ, JR, JR cc, EXX.
Z80_ONLY_OPCODES = {0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0xD9}


class AsmError(Exception):
    pass



def readable(text):
    """Source text (read as latin-1, one character per byte) for messages: UTF-8 text
    is shown decoded, other text as it is."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text


def image(mem):
    """(lowest address, bytes from the lowest to the highest used address, gaps = 0)."""
    if not mem:
        return 0, b""
    lo, hi = min(mem), max(mem)
    return lo, bytes(mem.get(a, 0) for a in range(lo, hi + 1))


def split_tap(data, name):
    """Blocks of a .tap file: [flag + data + checksum, ...]; checks lengths and checksums."""
    blocks, pos = [], 0
    while pos < len(data):
        size = int.from_bytes(data[pos:pos + 2], "little")
        body = data[pos + 2:pos + 2 + size]
        if size < 2 or len(body) < size:
            raise AsmError(f"{name}: not a .tap file (bad block length at offset {pos})")
        check = 0
        for b in body:
            check ^= b
        if check:
            raise AsmError(f"{name}: wrong checksum of the block at offset {pos}")
        blocks.append(body)
        pos += 2 + size
    if not blocks:
        raise AsmError(f"{name}: empty .tap file")
    return blocks

# --- disk images: Extended DSK with the CP/M file system (Amsdos DATA format, +3DOS) ---
DSK_TRACKS, DSK_SECTORS, DSK_SECTOR = 40, 9, 512     # 1 side; 1 KB blocks, 2 directory blocks
# the disk specification of the PCW / +3 format (format 0: 1 side, DSK_TRACKS tracks, 9
# sectors of 512 bytes, 1 reserved track, 1 KB blocks, 2 directory blocks, gaps 2Ah, 52h),
# at the start of the first sector
PCW_DISK_SPEC = bytes([0, 0, DSK_TRACKS, 9, 2, 1, 3, 2, 0x2A, 0x52]) + bytes(6)


def cpm_name(name):
    """The CP/M name of the file on a disk image: the output file name without the
    directory, up to the first character that is not a letter or a digit, upper case, 8
    characters at most (out/hello.dsk -> HELLO)."""
    base = re.match(r"[A-Za-z0-9]*", re.split(r"[\\/]", name)[-1]).group(0).upper()[:8]
    if not base:
        raise AsmError(f"the disk image needs a file name with letters or digits (--name), not {name!r}")
    return base


def cpm_dsk(files, first_id, reserved=0, boot=b""):
    """Extended DSK image (the format of CPC and +3 emulators) of a single sided disk with
    DSK_TRACKS tracks of DSK_SECTORS sectors, sector numbers from first_id, and the files
    [(name, ext, data)] in its CP/M file system: reserved tracks first (boot: the start of
    their first sector), then the directory (blocks 0 and 1, 64 entries), the files from
    block 2; a directory entry (extent) for each 16 KB of a file. Empty space is E5h."""
    disk = bytearray(b"\xE5" * (DSK_TRACKS * DSK_SECTORS * DSK_SECTOR))
    disk[:len(boot)] = boot
    start = reserved * DSK_SECTORS * DSK_SECTOR                  # block 0
    blocks = (len(disk) - start) // 1024
    directory, block = bytearray(), 2
    for name, ext, data in files:
        for ex in range(max(1, -(-len(data) // 16384))):
            part = data[ex * 16384:(ex + 1) * 16384]
            used = list(range(block, block + -(-len(part) // 1024)))
            block += len(used)
            if block > blocks:
                raise AsmError(f"the files do not fit on the disk ({blocks - 2} KB)")
            for i, b in enumerate(used):
                chunk = part[i * 1024:(i + 1) * 1024]
                disk[start + b * 1024:start + b * 1024 + len(chunk)] = chunk
            directory += (bytes([0]) + name.ljust(8).encode() + ext.ljust(3).encode()
                          + bytes([ex & 0x1F, 0, ex >> 5, -(-len(part) // 128)]) + bytes(used).ljust(16, b"\0"))
    disk[start:start + len(directory)] = directory
    head = (b"EXTENDED CPC DSK File\r\nDisk-Info\r\n" + b"pypasmo".ljust(14) + bytes([DSK_TRACKS, 1, 0, 0])
            + bytes([(256 + DSK_SECTORS * DSK_SECTOR) >> 8]) * DSK_TRACKS)
    out = [head.ljust(256, b"\0")]
    for t in range(DSK_TRACKS):
        info = b"Track-Info\r\n" + bytes(4) + bytes([t, 0, 0, 0, 2, DSK_SECTORS, 0x4E, 0xE5])
        info += b"".join(bytes([t, 0, first_id + s, 2, 0, 0]) + DSK_SECTOR.to_bytes(2, "little")
                         for s in range(DSK_SECTORS))
        out.append(info.ljust(256, b"\0"))
        out.append(bytes(disk[t * DSK_SECTORS * DSK_SECTOR:(t + 1) * DSK_SECTORS * DSK_SECTOR]))
    return b"".join(out)
