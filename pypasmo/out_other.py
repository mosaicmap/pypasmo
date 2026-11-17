# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""Other output formats: Intel HEX, CP/M Plus .prl, Amstrad CPC (Amsdos, .cdt), MSX, Sharp MZ,
ZX81, Jupiter Ace, Robotron KC 85 / Z 1013, Sega Master System."""
import re

from .assembler import Assembler
from .common import PCW_DISK_SPEC, ZX81_CODES, AsmError, cpm_dsk, cpm_name, image
from .cpc_state import CPC_STATE


def intel_hex(mem, entry=None):
    """Intel HEX like Pasmo 0.5.5: CRLF lines, entry point (END x, else 0) in the end record."""
    lo, data = image(mem)
    out = []

    def record(addr, rtype, payload):
        rec = [len(payload), addr >> 8, addr & 0xFF, rtype] + list(payload)
        out.append(":" + "".join(f"{b:02X}" for b in rec) + f"{(-sum(rec)) & 0xFF:02X}")
    for off in range(0, len(data), 16):
        record(lo + off, 0, data[off:off + 16])
    record(entry or 0, 1, b"")
    return "\r\n".join(out) + "\r\n"


# --- Amstrad CPC: Amsdos disk header, .cdt tape image (cpc.cxx in Pasmo) ---
def cpc_crc(data):
    """CRC-16 (polynomial 1021h, start FFFFh, result inverted) of a 256 byte tape
    chunk; a shorter chunk is padded with zeros."""
    crc = 0xFFFF
    for b in bytes(data[:256]).ljust(256, b"\0"):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc ^ 0xFFFF


def amsdos(lo, data, entry, name):
    """Amsdos file: 128 byte header (binary file) + code. The name is split at the
    first dot into 8 + 3 characters like in Pasmo."""
    base, _, ext = name.partition(".")
    head = bytearray(128)
    head[1:12] = ((base + " " * 8)[:8] + (ext + " " * 3)[:3]).encode("latin-1", "replace")
    head[0x12] = 2                                         # file type: binary
    head[0x15:0x17] = lo.to_bytes(2, "little")             # load address
    head[0x18:0x1A] = (len(data) & 0xFFFF).to_bytes(2, "little")
    head[0x1A:0x1C] = (entry or 0).to_bytes(2, "little")
    head[0x40:0x43] = len(data).to_bytes(3, "little")      # real length of the file
    head[0x43:0x45] = (sum(head[:0x43]) & 0xFFFF).to_bytes(2, "little")
    return bytes(head) + data


def dsk_cpc(lo, data, entry, name):
    """Amstrad CPC disk image .dsk (--dsk-cpc, pypasmo extension): DATA format (sectors
    C1h-C9h, no reserved track) with the Amsdos file NAME.BIN (RUN "name")."""
    file = cpm_name(name)
    return cpm_dsk([(file, "BIN", amsdos(lo, data, entry, file + ".BIN"))], 0xC1)


def cdt_turbo(length):
    """TZX turbo speed data block (ID 11h) with the CPC timing used by Pasmo."""
    timing = (0x0380, 0x01C0, 0x01C0, 0x01C0, 0x0380, 0x1000)
    return (b"\x11" + b"".join(t.to_bytes(2, "little") for t in timing) + b"\x08"
            + (0x0970).to_bytes(2, "little") + length.to_bytes(3, "little"))


def cdt_record(sync, data):
    """A CPC tape record: sync byte, 256 byte chunks each followed by its CRC
    (big endian), 4 trailer bytes FFh."""
    body = b"".join(bytes(data[k:k + 256]).ljust(256, b"\0") + cpc_crc(data[k:k + 256]).to_bytes(2, "big")
                    for k in range(0, len(data), 256))
    return cdt_turbo(len(body) + 5) + bytes([sync]) + body + b"\xFF" * 4


def cdt_header(name, ftype, block, first, last, block_len, length, load=0, entry=0):
    """64 byte CPC tape header record of one block (ftype 0 = Basic, 2 = binary)."""
    head = bytearray(64)
    raw = name.encode("latin-1", "replace")[:16]
    head[:len(raw)] = raw
    head[0x10] = block
    head[0x11] = 0xFF if last else 0
    head[0x12] = ftype
    head[0x13:0x15] = block_len.to_bytes(2, "little")
    head[0x15:0x17] = load.to_bytes(2, "little")
    head[0x17] = 0xFF if first else 0
    head[0x18:0x1A] = (length & 0xFFFF).to_bytes(2, "little")
    head[0x1A:0x1C] = entry.to_bytes(2, "little")
    return cdt_record(0x2C, head)


def cdt_code(lo, data, entry, name):
    """The code as CPC tape blocks of max. 2 KB, each a header + data record. Like
    Pasmo, every header has the load address of the whole file."""
    out = b""
    for num, pos in enumerate(range(0, len(data), 2048), 1):
        chunk = data[pos:pos + 2048]
        out += cdt_header(name, 2, num & 0xFF, num == 1, pos + 2048 >= len(data),
                          len(chunk), len(data), lo, entry or 0)
        out += cdt_record(0x16, chunk)
    return out


def cpc_basic_loader(lo, entry):
    """Locomotive Basic: 10 MEMORY lo-1 / 20 LOAD "!",lo / [30 CALL entry]"""
    MEMORY, LOAD, CALL, HEXNUM = b"\xAA", b"\xA8", b"\x83", b"\x1C"

    def line(num, body):
        return (len(body) + 5).to_bytes(2, "little") + num.to_bytes(2, "little") + body + b"\0"

    def hexnum(n):
        return HEXNUM + (n & 0xFFFF).to_bytes(2, "little")
    basic = line(10, MEMORY + hexnum(lo - 1)) + line(20, LOAD + b'"!",' + hexnum(lo))
    if entry is not None:
        basic += line(30, CALL + hexnum(entry))
    return basic + b"\0\0"


def cdt_basic(basic):
    """Basic program "LOADER" as a one-block CPC tape file."""
    return (cdt_header("LOADER", 0, 1, True, True, len(basic), len(basic))
            + cdt_record(0x16, basic))


def cpc_return(head):
    """The end of the --sna-cpc6128/--sna-cpc464 routine: DI, the registers of the template (AF', BC',
    DE', HL', the ROM state of the Gate Array again with OUT (C),C of BC', I, IM, AF, BC, DE,
    IX, IY, HL), EI if the interrupts were on, JP to its PC."""
    w = lambda at: head[at:at + 2]                       # noqa: E731 (a word of the header)
    ld_af = lambda at: b"\x21" + w(at) + b"\xE5\xF1"      # noqa: E731 LD HL,nn: PUSH HL: POP AF
    out = (b"\xF3\x08" + ld_af(0x26) + b"\x08\xD9" + b"\x01" + w(0x28) + b"\x11" + w(0x2A)
           + b"\x21" + w(0x2C) + b"\xED\x49\xD9" + b"\x3E" + head[0x1A:0x1B] + b"\xED\x47"
           + (b"\xED\x46", b"\xED\x56", b"\xED\x5E")[head[0x25] % 3] + ld_af(0x11)
           + b"\x01" + w(0x13) + b"\x11" + w(0x15) + b"\xDD\x21" + w(0x1D) + b"\xFD\x21" + w(0x1F)
           + b"\x21" + w(0x17))
    return out + (b"\xFB" if head[0x1B] else b"") + b"\xC3" + w(0x23)


CPC_L_ROM_DISABLE = 0xB909   # firmware KL L ROM DISABLE (the same on the 464, 664, 6128)


def sna_cpc(asm, cpc):
    """Amstrad CPC snapshot .sna, version 2 (--sna-cpc6128: cpc 2, --sna-cpc464: cpc 0,
    pypasmo extension, early version): the state of the CPC in Basic (Ready, cpc_state.py,
    saved by an emulator) with the code. PC is a routine just below HIMEM: KL L ROM DISABLE
    (the template is in the lower ROM; the code runs in the RAM, also below 4000h, as after
    CALL from Basic), CALL to the code (END, else its first byte), then the registers of the
    state and JP to where the firmware was, so a RET of the code goes back to Basic."""
    option = "--sna-cpc" + ("464", "664", "6128")[cpc]
    header, state, himem = CPC_STATE[cpc]
    if not asm.mem:
        raise AsmError(f"{option}: no code")
    lo = min(asm.mem)
    entry = lo if asm.entry is None else asm.entry
    ret = cpc_return(header)
    stub = himem - 6 - len(ret)
    for a in asm.mem:
        if a < 0x40 or stub <= a < 0xC000:
            raise AsmError(f"{option}: code at {a:04X}h: 0000h-003Fh (restart vectors), {stub:04X}h-"
                           f"{himem - 1:04X}h (the routine that calls the code) and "
                           f"{himem:04X}h-BFFFh (firmware, stack) are used")
    ram = bytearray(0x10000)
    for a, b in state:
        ram[a:a + len(b)] = b
    for a, b in asm.mem.items():
        ram[a] = b
    ram[stub:himem] = b"\xCD" + CPC_L_ROM_DISABLE.to_bytes(2, "little") + b"\xCD" + entry.to_bytes(2, "little") + ret
    head = bytearray(256)
    head[:len(header)] = header
    head[0x10] = 2                                       # version 2: the CPC type is used
    head[0x23:0x25] = stub.to_bytes(2, "little")
    head[0x6B:0x6E] = b"\x40\x00" + bytes([cpc])        # 64 KB of RAM, the CPC type
    return bytes(head) + bytes(ram)


def sna_cpc6128(asm):
    """CPC 6128 snapshot (--sna-cpc6128), see sna_cpc."""
    return sna_cpc(asm, 2)


def sna_cpc464(asm):
    """CPC 464 snapshot (--sna-cpc464), see sna_cpc."""
    return sna_cpc(asm, 0)


# --- MSX (asm.cxx in Pasmo) ---
def msx(lo, data, entry):
    """MSX BLOAD file: FEh, start, end, execution address, code."""
    words = (lo, (lo + len(data) - 1) & 0xFFFF, entry or 0)
    return b"\xFE" + b"".join(w.to_bytes(2, "little") for w in words) + data


# MSX disk 720 KB (2DD): 80 tracks, 2 sides, 9 sectors of 512 bytes, FAT12 of MSX-DOS (media F9h)
MSX_BPB = bytes.fromhex("0002020100027000A005F90300090002000000")   # boot sector 0Bh-1Dh
MSX_ROOT = 7             # the root directory: sectors 7-13 (112 entries)
MSX_DATA = 14            # cluster 2 = sectors 14, 15
MSX_DISK_CODE = (0x8800, 0xDE3F)   # above Basic (program, stack, strings), below the disk ROM


def fat12_msx(files):
    """720 KB MSX disk image (raw sectors) with the files [(name, ext, bytes)] in the root
    directory, each in consecutive clusters from cluster 2; the boot sector is bootable
    (EBh FEh 90h) and its code a RET, so Disk BASIC starts (and runs AUTOEXEC.BAS)."""
    disk = bytearray(80 * 2 * 9 * 512)
    disk[:3] = b"\xEB\xFE\x90"
    disk[3:11] = b"PYPASMO "
    disk[0x0B:0x1E] = MSX_BPB
    disk[0x1E] = 0xC9
    fat = [0xFF9, 0xFFF]
    for i, (name, ext, data) in enumerate(files):
        first, count = len(fat), max(1, -(-len(data) // 1024))
        fat += [first + k + 1 for k in range(count - 1)] + [0xFFF]
        at = (MSX_DATA + (first - 2) * 2) * 512
        disk[at:at + len(data)] = data
        entry = (name.ljust(8) + ext.ljust(3)).encode("ascii") + b"\x20" + bytes(10)
        entry += b"\x00\x00\x21\x00" + first.to_bytes(2, "little") + len(data).to_bytes(4, "little")
        disk[MSX_ROOT * 512 + 32 * i:MSX_ROOT * 512 + 32 * (i + 1)] = entry   # time 0, 1 Jan 1980
    fat += [0] * (len(fat) % 2)
    packed = b"".join(bytes([a & 0xFF, a >> 8 | (b & 15) << 4, b >> 4]) for a, b in zip(fat[::2], fat[1::2]))
    for n in (1, 4):
        disk[n * 512:n * 512 + len(packed)] = packed
    return bytes(disk)


def dsk_msx(lo, data, entry, name):
    """MSX disk image .dsk (--dsk-msx, pypasmo extension, early version): 720 KB, FAT12,
    NAME.BIN (the BLOAD file) and AUTOEXEC.BAS (ASCII) with CLEAR 200,&H(start - 1) (so
    Basic keeps its strings and stack below the code) and BLOAD "NAME.BIN",R; the code runs
    at END, else at its first byte."""
    if not data:
        raise AsmError("--dsk-msx: no code")
    end = lo + len(data) - 1
    if lo < MSX_DISK_CODE[0] or end > MSX_DISK_CODE[1]:
        raise AsmError(f"--dsk-msx: the code ({lo:04X}h-{end:04X}h) must be in {MSX_DISK_CODE[0]:04X}h-"
                       f"{MSX_DISK_CODE[1]:04X}h (Basic below, the work area of the disk ROM above)")
    file = cpm_name(name)
    basic = f'10 CLEAR 200,&H{lo - 1:X}:BLOAD"{file}.BIN",R\r\n'.encode("ascii") + b"\x1A"
    return fat12_msx([("AUTOEXEC", "BAS", basic), (file, "BIN", msx(lo, data, lo if entry is None else entry))])


# --- TRS-80 (asm.cxx in Pasmo) ---
def trs(lo, data, entry):
    """TRS-80 /CMD file (--trs, as Pasmo 0.5.5): load records 01, length (data + 2, the low
    byte: 256 bytes = 02), address, up to 256 bytes; then the transfer record 02 02 entry
    (END, else 0)."""
    out = bytearray()
    for at in range(0, len(data), 256):
        part = data[at:at + 256]
        out += bytes([1, (len(part) + 2) & 0xFF]) + ((lo + at) & 0xFFFF).to_bytes(2, "little") + part
    return bytes(out) + b"\x02\x02" + (entry or 0).to_bytes(2, "little")


def trs_cas(lo, data, entry, name):
    """TRS-80 Model I SYSTEM tape .cas, 500 baud (--cas-trs, pypasmo extension, IN
    DEVELOPMENT): 256 zeros, A5h, 55h, the name (6 characters, upper case, spaces), blocks 3Ch,
    length (256 = 0), address, data, checksum (the sum of the address bytes and the data),
    then 78h and the entry (END, else the load address). SYSTEM loads it, / runs it."""
    if data and lo < 0x4000:
        raise AsmError(f"--cas-trs: code at {lo:04X}h is in the ROM (0000h-3FFFh)")
    base = re.match(r"[A-Za-z0-9]*", file_name(name)).group(0).upper()[:6]
    if not base:
        raise AsmError(f"--cas-trs needs a name with letters or digits (--name), not {name!r}")
    out = bytearray(256) + b"\xA5\x55" + base.ljust(6).encode("ascii")
    for at in range(0, len(data), 256):
        part, addr = data[at:at + 256], lo + at
        out += bytes([0x3C, len(part) & 0xFF, addr & 0xFF, addr >> 8]) + part
        out.append((addr & 0xFF) + (addr >> 8) + sum(part) & 0xFF)
    return bytes(out) + b"\x78" + (lo if entry is None else entry).to_bytes(2, "little")


def mzf(lo, data, entry, name):
    """Sharp MZ-700/800 tape file .mzf (--mzf, pypasmo extension, early version): 128 byte
    header (attribute 01h = machine code, name up to 16 characters upper case ended and
    filled with 0Dh, size, load address, start address = END or load address, 104 bytes
    of comment) + code."""
    head = bytearray(128)
    head[0] = 1
    head[1:18] = (file_name(name).upper().encode("latin-1", "replace")[:16] + b"\x0D").ljust(17, b"\x0D")
    for at, word in ((18, len(data)), (20, lo), (22, lo if entry is None else entry)):
        head[at:at + 2] = word.to_bytes(2, "little")
    return bytes(head) + data


ZX81_PROG = 0x407D       # the Basic program after the system variables (from 4009h)
ZX81_REM_CODE = 16514    # the code in 1 REM: after the line number, length and REM


ZX81_STACK = 256         # warning with less space for the stacks of the ROM under 8000h


def zx81_p(lo, data, entry, warnings=None):
    """ZX81 .p file (--p-zx81, pypasmo extension, early version): the memory from 4009h
    (system variables) to the variables, as SAVE writes it on the tape: 1 REM with the
    code (ORG 16514), 2 RAND USR VAL "start" (END or 16514), the full display file
    (16K RAM), runs at once after LOAD (NXTLIN = line 1). The system variables are those
    of z88dk (appmake), as the ROM leaves them after the program is typed in. A warning
    (to warnings) when less than ZX81_STACK bytes stay free under 8000h (16K RAM): the
    calculator stack of the ROM grows up from STKEND, the machine stack down from RAMTOP."""
    if lo != ZX81_REM_CODE or not data:
        raise AsmError(f"--p-zx81: the code must start at {ZX81_REM_CODE} (ORG 16514, the REM line)")
    start = lo if entry is None else entry
    digits = bytes(ZX81_CODES[c] for c in str(start))
    rem = bytes([0, 1]) + (len(data) + 2).to_bytes(2, "little") + b"\xEA" + data + b"\x76"
    usr = b"\xF9\xD4\xC5\x0B" + digits + b"\x0B\x76"             # RAND USR VAL "..."
    prog = rem + bytes([0, 2]) + len(usr).to_bytes(2, "little") + usr
    d_file = ZX81_PROG + len(prog)
    display = b"\x76" + (bytes(32) + b"\x76") * 24
    vars_ = d_file + len(display)
    e_line = vars_ + 1
    if e_line + 5 > 0x8000:
        raise AsmError(f"--p-zx81: the program with the display file ends at {e_line:04X}h,"
                       " past 32K (7FFFh)")
    free = 0x8000 - (e_line + 5)
    msg = (f"warning: --p-zx81: only {free} bytes stay free under 8000h (16K RAM) for the stacks"
           f" of the ROM and the program (less than {ZX81_STACK})")
    if free < ZX81_STACK and warnings is not None and msg not in warnings:
        warnings.append(msg)

    def w(*words):
        return b"".join(x.to_bytes(2, "little") for x in words)
    sysvars = (b"\x00" + w(1, d_file, d_file + 1, vars_, 0, e_line, e_line + 4, 0, e_line + 5, e_line + 5)
               + b"\x00" + w(0x405D) + b"\x00\x02" + w(0) + b"\xBF\xFD\xFF\x37" + w(ZX81_PROG, 0)
               + b"\x00" + w(0, 0x0C8D, 0, 63000, 0) + b"\xBC\x21\x18\x40" + bytes(32) + b"\x76"
               + bytes(10) + b"\x84\x20" + bytes(20))
    assert len(sysvars) == ZX81_PROG - 0x4009
    return sysvars + prog + display + b"\x80"


def ace_tap(lo, data, entry, name):
    """Jupiter Ace .tap (--tap-ace, pypasmo extension, early version; as z88dk appmake):
    two "bytes" files, each a header block (type 32, name of 10 characters, length, load
    address, 10 spaces) and a data block; each block has its length (with the check byte)
    before it and the XOR of its bytes after it. The first file (named NAME, 32 bytes for
    22E0h, the input line on the screen) is the command "0 0 BLOAD code <start> CALL", so
    after 0 0 BLOAD NAME the Forth runs it: loads the code (file "code") and calls it
    (start = END or the load address). The code returns to Forth with JP (IY)."""
    if lo < 0x2000:
        raise AsmError(f"--tap-ace: code at {lo:04X}h is in the ROM (0000h-1FFFh)")

    def block(b):
        x = 0
        for v in b:
            x ^= v
        return (len(b) + 1).to_bytes(2, "little") + b + bytes([x])

    def head(file_name, length, load):
        return (bytes([32]) + file_name + length.to_bytes(2, "little") + load.to_bytes(2, "little")
                + b" " * 10)
    start = lo if entry is None else entry
    own = file_name(name).split(".")[0].encode("latin-1", "replace")[:10].ljust(10)
    cmd = b"0 0 BLOAD " + ACE_CODE + b" " + str(start).encode().ljust(5) + b" CALL"
    return (block(head(own, 32, 0x22E0)) + block(b"\x00" + cmd)
            + block(head(ACE_CODE, len(data), lo)) + block(data))


ACE_CODE = b"code      "     # the name of the code file on the Jupiter Ace tape


def kcc(lo, data, entry, name):
    """Robotron KC 85/2-4 .kcc file (--kcc-kc85, pypasmo extension, early version; as z88dk
    appmake): 128 byte header (name of 8 characters, upper case, up to the first character
    that is not a letter or a digit, filled with zeros; "KCC"; 5 zeros; 3 addresses =
    autostart: load, end + 1, start = END or load; 105 zeros) + the code padded with zeros
    to a multiple of 128 bytes."""
    base = re.match(r"[A-Za-z0-9]*", file_name(name)).group(0).upper()[:8]
    start = lo if entry is None else entry
    head = (base.encode("ascii").ljust(8, b"\x00") + b"KCC" + bytes(5) + bytes([3])
            + b"".join((x & 0xFFFF).to_bytes(2, "little") for x in (lo, lo + len(data), start)) + bytes(105))
    return head + data + bytes(-len(data) % 128)


def z1013(lo, data, entry, name):
    """Robotron Z 1013 .z80 file ("headersave", --z80-z1013, pypasmo extension, early version;
    as z88dk appmake; not the .z80 snapshot of the ZX Spectrum): 32 byte header (load,
    end = the last byte, start = END or load, 6 zeros, type "C" = executable, D3 D3 D3,
    name of 16 characters up to the first dot, filled with spaces) + the code."""
    start = lo if entry is None else entry
    words = b"".join(x.to_bytes(2, "little") for x in (lo, (lo + len(data) - 1) & 0xFFFF, start))
    own = file_name(name).split(".")[0].encode("latin-1", "replace")[:16].ljust(16)
    return words + bytes(6) + b"C\xD3\xD3\xD3" + own + data


SMS_HEADER = 0x7FF0      # the header of a Sega Master System ROM (16 bytes)


def sms_rom(mem, region=4):
    """Sega Master System cartridge ROM .sms (--rom-sms, pypasmo extension, early version):
    32 KB from 0000h (where the Z80 starts), padded with FFh, without a mapper. The header
    at 7FF0h: "TMR SEGA", 2 spaces, checksum, product code 0, version 0, region 4 (export
    SMS) and ROM size C (32 KB), as z88dk appmake writes it. A source may write its own
    header there (it must start with "TMR SEGA", size C). The checksum is the 16 bit sum of
    0000h-7FEFh, low byte first; the export BIOS checks it (SMS Power, ROM header, BIOS).
    --rom-gg (Game Gear): the same with region 7 (Game Gear international)."""
    option = "--rom-gg" if region in (5, 6, 7) else "--rom-sms"
    if any(a >= 0x8000 for a in mem):
        raise AsmError(f"{option}: code at 8000h-FFFFh: only 32 KB ROMs (0000h-7FFFh, no mapper)")
    if 0 not in mem:
        raise AsmError(f"{option}: no code at 0000h, where the Z80 starts")
    rom = bytearray(b"\xFF" * 0x8000)
    for a, b in mem.items():
        if b is not None:
            rom[a] = b
    if any(a >= SMS_HEADER for a in mem):
        if rom[SMS_HEADER:SMS_HEADER + 8] != b"TMR SEGA":
            raise AsmError(f'{option}: code at 7FF0h-7FFFh: the header there must start with "TMR SEGA"')
        if rom[0x7FFF] & 0x0F != 0x0C:
            raise AsmError(f"{option}: the ROM size in the header (7FFFh) must be C (32 KB)")
    else:
        rom[SMS_HEADER:] = b"TMR SEGA  " + bytes(2) + bytes([0, 0, 0, region << 4 | 0x0C])
    rom[0x7FFA:0x7FFC] = (sum(rom[:SMS_HEADER]) & 0xFFFF).to_bytes(2, "little")
    return bytes(rom)


CAS_SYNC = bytes.fromhex("1FA6DEBACC137D74")   # starts every block of a .cas file


def file_name(name):
    """The name for a header without the directory (dir/hello.cas -> hello.cas)."""
    return re.split(r"[\\/]", name)[-1]


def msx_cas(lo, data, entry, name):
    """MSX tape .cas (--cas-msx, pypasmo extension) with a binary file for
    BLOAD "CAS:",R: header block (sync header, 10 x D0h, name of 6 characters: up to the
    first dot) + data block (sync header, start, end, start address = END or start, code).
    Zeros after each block, so that every sync header is at a multiple of 8."""
    def pad(b):
        return b + bytes(-len(b) % 8)
    head = CAS_SYNC + b"\xD0" * 10 + file_name(name).split(".")[0].encode("latin-1", "replace")[:6].ljust(6, b" ")
    words = (lo, (lo + len(data) - 1) & 0xFFFF, lo if entry is None else entry)
    return pad(head) + pad(CAS_SYNC + b"".join(w.to_bytes(2, "little") for w in words) + data)


MSX_ROM_HEAD = ('    org 4000h\n    db "AB"         ; ID\n    dw init         ; INIT (start address)\n'
                '    dw 0, 0, 0      ; STATEMENT, DEVICE, TEXT\n    ds 6            ; reserved')


def msx_rom(lo, data):
    """MSX cartridge ROM (--rom-msx, pypasmo extension, early version): the code starts with
    the 16 byte header "AB" + INIT ... (written in the source, see MSX_ROM_HEAD) at 4000h
    or 8000h; padded with FFh to 8, 16 or 32 KB (32 KB = 4000h-BFFFh)."""
    if lo not in (0x4000, 0x8000):
        raise AsmError(f"--rom-msx: the ROM must start at 4000h or 8000h, not {lo:04X}h")
    if data[:2] != b"AB":
        raise AsmError("--rom-msx: the ROM must start with the header \"AB\", e.g.:\n" + MSX_ROM_HEAD)
    size = next((s for s in (0x2000, 0x4000, 0x8000) if len(data) <= s and lo + s <= 0xC000), None)
    if size is None:
        raise AsmError(f"--rom-msx: {len(data)} bytes from {lo:04X}h, at most 4000h-BFFFh (32 KB)")
    return data + b"\xFF" * (size - len(data))


# --- ColecoVision (pypasmo extension) ---
COLECO_ROM_HEAD = ('    org 8000h\n    db 0AAh, 55h    ; AAh 55h: the title screen of the BIOS first, 55h AAh: no\n'
                   '    dw 0, 0, 0, 0   ; BIOS tables (sprites, buffer, controllers)\n'
                   '    dw start        ; 800Ah: the start of the program')


def coleco_rom(lo, data):
    """ColecoVision cartridge ROM .col (--rom-coleco, pypasmo extension, IN DEVELOPMENT):
    the code from 8000h, which starts with the header written in the source (AAh 55h or
    55h AAh, the BIOS tables, the start at 800Ah, the RST / NMI jumps from 800Ch, the title
    text at 8024h; see COLECO_ROM_HEAD); padded with FFh to 8, 16, 24 or 32 KB (8 KB chips
    at 8000h, A000h, C000h, E000h)."""
    if not data:
        raise AsmError("--rom-coleco: no code")
    if lo != 0x8000:
        raise AsmError(f"--rom-coleco: the ROM must start at 8000h, not {lo:04X}h")
    if data[:2] not in (b"\xAA\x55", b"\x55\xAA"):
        raise AsmError("--rom-coleco: the ROM must start with the header AAh 55h or 55h AAh, e.g.:\n"
                       + COLECO_ROM_HEAD)
    return data + b"\xFF" * (-len(data) % 0x2000)


# --- Amstrad PCW (pypasmo extension) ---
def dsk_pcw(lo, data, entry, name):
    """Amstrad PCW disk image .dsk (--dsk-pcw, pypasmo extension, IN DEVELOPMENT): the CP/M
    program NAME.COM (the code from 100h, no header) on a disk in the PCW / +3 format
    (PCW_DISK_SPEC, as --dsk-plus3). The disk does not start by itself (no CP/M on it):
    start CP/M Plus, then the program with its name."""
    if not data:
        raise AsmError("--dsk-pcw: no code")
    if lo != 0x100:
        raise AsmError(f"--dsk-pcw: a CP/M program starts at 0100h (ORG 100h), not at {lo:04X}h")
    if entry not in (None, 0x100):
        raise AsmError(f"--dsk-pcw: CP/M starts the program at 0100h, not at {entry:04X}h (END)")
    return cpm_dsk([(cpm_name(name), "COM", data)], 1, reserved=1, boot=PCW_DISK_SPEC)


# --- CP/M Plus .prl / .rsx (emitprl in Pasmo asm.cxx) ---
def prl(asm):
    """PRL file: the source is assembled again starting at 100h instead of 0; the bytes
    that differ by 1 are high bytes of addresses and get a bit in the relocation bitmap.
    256 byte header (code length at offset 1), code for 100h, bitmap (1 bit per byte,
    the highest bit first)."""
    off = Assembler(**asm.options, base=0x100)
    off.assemble(asm.path, text=asm.text)
    if not asm.mem or not off.mem:
        lo = hi = lo2 = hi2 = 0
    else:
        lo, hi, lo2, hi2 = min(asm.mem), max(asm.mem), min(off.mem), max(off.mem)
    shift = off.start_pc - asm.start_pc
    if lo2 - lo != shift or hi2 - hi != shift:
        raise AsmError("PRL generation failed: out of sync (do not use an absolute ORG)")
    _, code0 = image(asm.mem)
    _, code1 = image(off.mem)
    reloc = bytearray((len(code0) + 7) // 8)
    for pos, (b0, b1) in enumerate(zip(code0, code1)):
        if b0 != b1:
            if b1 - b0 != shift // 256:
                raise AsmError(f"PRL generation failed: out of sync at {lo + pos:04X}h")
            reloc[pos // 8] |= 0x80 >> (pos % 8)
    head = bytearray(256)
    head[1:3] = (len(code0) & 0xFFFF).to_bytes(2, "little")
    return bytes(head) + code1 + bytes(reloc)
