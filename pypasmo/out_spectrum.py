# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""ZX Spectrum output: .tap, .tzx, .pzx, +3DOS, .sna, Spectrum 128K banks."""
from .common import PCW_DISK_SPEC, AsmError, cpm_dsk, cpm_name, image, option, split_tap


def plus3dos(lo, data, autostart=None):
    """+3DOS file: 128 byte header (type CODE) + code, padded with zeros to a multiple
    of 128 bytes (like spectrum.cxx in Pasmo; the size in the header excludes the padding).
    With autostart (a line number): a Basic program (type 0) for --dsk-plus3."""
    head = bytearray(128)
    head[0:11] = b"PLUS3DOS\x1A\x01\x00"
    head[11:15] = (len(data) + 128).to_bytes(4, "little")
    head[15] = 3 if autostart is None else 0
    head[16:18] = len(data).to_bytes(2, "little")
    if autostart is None:
        head[18:20] = lo.to_bytes(2, "little")
        head[20:22] = b"\x80\x80"
    else:
        head[18:20] = autostart.to_bytes(2, "little")
        head[20:22] = len(data).to_bytes(2, "little")       # the variables after the program
    head[127] = sum(head[:127]) & 0xFF
    return bytes(head) + data + bytes(-len(data) % 128)


# --- ZX Spectrum .tap (the same as tap.cxx and spectrum.cxx in Pasmo) ---
def tap_block(flag, data):
    body = bytes([flag]) + bytes(data)
    check = 0
    for b in body:
        check ^= b
    return (len(body) + 1).to_bytes(2, "little") + body + bytes([check])


def tap_code(lo, data, name):
    """CODE header + data block (pasmo --tap)."""
    head = (bytes([3]) + name.encode("latin-1", "replace")[:10].ljust(10, b" ")
            + len(data).to_bytes(2, "little") + lo.to_bytes(2, "little") + (0x8000).to_bytes(2, "little"))
    return tap_block(0x00, head) + tap_block(0xFF, data)


def spectrum_number(n):
    """A number in Spectrum Basic: digits + 0Eh + 5 byte integer form."""
    n &= 0xFFFF
    return str(n).encode() + bytes([0x0E, 0, 0, n & 0xFF, n >> 8, 0])


def basic_line(num, body):
    return bytes([num >> 8, num & 0xFF]) + (len(body) + 1).to_bytes(2, "little") + body + b"\x0D"


def basic_loader(lo, entry):
    """10 CLEAR lo-1 / 20 POKE 23610,255 / 30 LOAD "" CODE / [40 RANDOMIZE USR entry]"""
    CLEAR, POKE, LOAD, CODE, RANDOMIZE, USR = b"\xFD", b"\xF4", b"\xEF", b"\xAF", b"\xF9", b"\xC0"
    basic = basic_line(10, CLEAR + spectrum_number(lo - 1))
    basic += basic_line(20, POKE + spectrum_number(23610) + b"," + spectrum_number(255))
    basic += basic_line(30, LOAD + b'""' + CODE)
    if entry is not None:
        basic += basic_line(40, RANDOMIZE + USR + spectrum_number(entry))
    return basic


def plus3_loader(lo, entry, file):
    """Basic loader DISK of --dsk-plus3: 10 CLEAR lo-1 / 20 LOAD "file" CODE /
    [30 RANDOMIZE USR entry]"""
    CLEAR, LOAD, CODE, RANDOMIZE, USR = b"\xFD", b"\xEF", b"\xAF", b"\xF9", b"\xC0"
    basic = basic_line(10, CLEAR + spectrum_number(lo - 1))
    basic += basic_line(20, LOAD + b'"' + file.encode() + b'"' + CODE)
    if entry is not None:
        basic += basic_line(30, RANDOMIZE + USR + spectrum_number(entry))
    return basic


def dsk_plus3(lo, data, entry, name):
    """Spectrum +3 disk image .dsk (--dsk-plus3, pypasmo extension): the +3DOS file
    NAME.BIN with the code and the Basic loader DISK (autostart), which the "Loader" of the
    +3 menu runs. 1 reserved track with the disk specification (+3 / PCW format 0)."""
    file = cpm_name(name) + ".BIN"
    basic = plus3_loader(lo, entry, file)
    return cpm_dsk([("DISK", "", plus3dos(0, basic, autostart=10)), (cpm_name(name), "BIN", plus3dos(lo, data))],
                   1, reserved=1, boot=PCW_DISK_SPEC)



def tape_warnings(asm, fmt, starts, basic=None, clear=None, extra=0):
    """Warnings for a tape (pypasmo extension, the file stays the same): code in the ROM,
    which LOAD can not write, and a CLEAR of the Basic loader that the ROM refuses. It needs
    RAMTOP about 157 bytes above the end of the loader (5CCBh + its length; measured in the
    simulator of SkoolKit), else the loader stops with "M RAMTOP no good" or "4 Out of
    memory". Code in the video RAM is allowed; it gives this warning with a loader."""
    def warn(msg):
        if msg not in asm.warnings:
            asm.warnings.append(msg)
    if any(s < 0x4000 for s in starts):
        warn(f"warning: {option(fmt)}: code at 0000h-3FFFh is in the ROM, LOAD can not put it there")
        return
    lowest = 0x5CCB + len(basic) + 157 + extra if basic is not None else 0
    if clear is not None and clear < lowest:
        warn(f"warning: {option(fmt)}: the Basic loader does CLEAR {clear} ({clear:04X}h), the ROM needs about "
             f"{lowest} ({lowest:04X}h) or more: the code starts too low, the loader would stop with "
             f"\"M RAMTOP no good\" or \"4 Out of memory\"")


def tap_basic(basic):
    """Basic header "loader" with autostart at line 10 + the program block."""
    size = len(basic).to_bytes(2, "little")
    head = bytes([0]) + b"loader    " + size + (10).to_bytes(2, "little") + size
    return tap_block(0x00, head) + tap_block(0xFF, basic)


def tap_loads(blocks):
    """(start, screen?) of each CODE block of TAPE_BLOCK / TAPE_BLOCK_SCREEN / TAP_INCLUDE;
    an included CODE 16384,6912 is a screen. Other included blocks are not loaded."""
    loads = []
    for kind, name, *rest in blocks:
        if kind != "tap":
            loads.append((rest[0], kind == "screen"))
            continue
        for body in split_tap(rest[0], name):
            if body[0] == 0 and len(body) == 19 and body[1] == 3:       # CODE header
                start, length = int.from_bytes(body[14:16], "little"), int.from_bytes(body[12:14], "little")
                loads.append((start, start == 0x4000 and length == 6912))
    return loads


def tape_blocks_loader(blocks, entry):
    """Basic loader for TAPE_BLOCK (pypasmo extension), one line for each CODE block:
        10 CLEAR lo-1 (lo = the lowest block except the screen) / 20 POKE 23610,255 /
        LOAD "" SCREEN$: POKE 23739,111 (no "Bytes:" messages over the picture) /
        LOAD "" CODE ... / POKE 23739,244: RANDOMIZE USR entry (244 = the ROM value)"""
    CLEAR, POKE, LOAD, CODE, SCREEN, RANDOMIZE, USR = (b"\xFD", b"\xF4", b"\xEF", b"\xAF", b"\xAA",
                                                       b"\xF9", b"\xC0")
    loads = tap_loads(blocks)
    lines = []
    code = [start for start, screen in loads if not screen]
    if code:
        lines.append(CLEAR + spectrum_number(min(code) - 1))
    lines.append(POKE + spectrum_number(23610) + b"," + spectrum_number(255))
    for start, screen in loads:
        if screen:
            lines.append(LOAD + b'""' + SCREEN + b":" + POKE + spectrum_number(23739) + b"," + spectrum_number(111))
        else:
            lines.append(LOAD + b'""' + CODE)
    end = b""
    if any(screen for start, screen in loads):
        end = POKE + spectrum_number(23739) + b"," + spectrum_number(244)
    if entry is not None:
        end += (b":" if end else b"") + RANDOMIZE + USR + spectrum_number(entry)
    if end:
        lines.append(end)
    return b"".join(basic_line(10 * i, body) for i, body in enumerate(lines, 1))


def tap_listed_blocks(asm, basic_loader_too, fmt):
    """--tap / --tapbas with TAPE_BLOCK / TAP_INCLUDE: only the listed blocks (+ their loader)."""
    loads = tap_loads(asm.tape_blocks)
    code = [start for start, screen in loads if not screen]
    basic = tape_blocks_loader(asm.tape_blocks, asm.entry)
    if basic_loader_too:
        tape_warnings(asm, fmt, [start for start, screen in loads], basic, min(code) - 1 if code else None)
    else:
        tape_warnings(asm, fmt, [start for start, screen in loads])
    out = tap_basic(basic) if basic_loader_too else b""
    for kind, name, *rest in asm.tape_blocks:
        if kind == "tap":
            out += rest[0]
        else:
            start, length = rest
            out += tap_code(start, bytes(asm.mem.get(a, 0) for a in range(start, start + length)), name)
    return out


# --- ZX Spectrum 48K snapshots (--sna-48k, --z80-48k, pypasmo extension) ---
# The state of a 48K Spectrum when the Basic program
#     10 CLEAR VAL "32767": RANDOMIZE USR VAL "32768"
# starts the machine code: system variables with the program (5C00h-5D0Ch), the machine
# stack below RAMTOP (its return addresses lead back to Basic), the UDG characters (copied
# from the ROM at start-up) and the registers. Made by tools/devel/make_sna_template.py (with
# the ROM and the Z80 simulator of SkoolKit), see there.
SNA_SYSVARS = bytes.fromhex(
    "FF000000FF00230D0D23050000000000010006000B00010001000600100000000000000000000000"
    "0000000000000000000000000000003C4000FFCD01FC7F0000000A00FF0A0002380000E45C0000B6"
    "5CB65CCB5CE45CCA5CE55CE85CE35C135DEA5CF65CF65C2D925C10020000000000000000B61A0000"
    "05000058FF000021005B21170040E050211821170138003800000000000000000000000000000000"
    "000000000000000000000000000000000000FF7FFFFFF409A8104BF409C41553810FC41552F409C4"
    "155080000A1500FDB0223332373637223AF9C0B0223332373638220D80EF22220D8033323736380E"
    "00000080000D0000008000000A00006465722020202019000A0019000D"
)
SNA_STACK = bytes.fromhex(
    "2B2D65330000ED100D000900851C101C521B761B0313003E"
)
SNA_UDG = bytes.fromhex(
    "003C42427E424200007C427C42427C00003C424040423C000078444242447800007E407C40407E00"
    "007E407C40404000003C42404E423C000042427E42424200003E080808083E000002020242423C00"
    "00444870484442000040404040407E000042665A42424200004262524A464200003C424242423C00"
    "007C42427C404000003C4242524A3C00007C42427C444200003C403C02423C0000FE101010101000"
    "0042424242423C00"
)
SNA_REGS = {"i": 0x3F, "hl2": 0x2758, "de2": 0x369B, "bc2": 0x1621, "af2": 0xFF45, "hl": 0x2D2B,
            "de": 0x5CF6, "iy": 0x5C3A, "ix": 0x5CE4, "iff2": 1, "r": 0x10, "af": 0x0054, "im": 1,
            "border": 7}
SNA_MIN_RAMTOP = 0x5D29      # the lowest CLEAR the ROM accepts here (STKEND + 32h + 1)


def spectrum48_state(asm, fmt, also=()):
    """(RAM 4000h-FFFFh, registers) of a 48K Spectrum whose Basic program did CLEAR
    start-1 (like --tapbas) and has just called the entry point (END address, else the
    start of the code) with RANDOMIZE USR; RET returns to Basic. If the code starts below
    the lowest possible CLEAR, RAMTOP stays at the default FF57h. The return address to
    USR is on the stack, PC (= entry) also below it, where the .sna format needs it.
    also: more addresses that the checks of the stack and the system variables cover (128K:
    BANK 5 / BANK 2 code at 4000h / 8000h)."""
    if not asm.mem:
        raise AsmError(f"{option(fmt)}: no code")
    lo = min(asm.mem)
    if lo < 0x4000:
        raise AsmError(f"{option(fmt)}: code at 0000h-3FFFh, that is the ROM")
    entry = lo if asm.entry is None else asm.entry
    ramtop = lo - 1 if lo - 1 >= SNA_MIN_RAMTOP else 0xFF57
    sp = ramtop + 1 - len(SNA_STACK)
    used = set(asm.mem) | set(also)
    if any(sp - 2 <= a <= ramtop for a in used):
        raise AsmError(f"{option(fmt)}: the code uses {sp - 2:04X}h-{ramtop:04X}h, the place of the Basic stack")
    sysvars = 0x5C00 + len(SNA_SYSVARS) - 1
    if any(0x5C00 <= a <= sysvars for a in used):
        raise AsmError(f"{option(fmt)}: the code uses 5C00h-{sysvars:04X}h, the system variables and the Basic "
                       "program (the ROM interrupt and RET to Basic need them); start it from 5D0Dh")
    ram = bytearray(0xC000)                          # 4000h-FFFFh

    def put(addr, data):
        ram[addr - 0x4000:addr - 0x4000 + len(data)] = data
    put(0x5800, b"\x38" * 0x300)                     # attributes: black ink, white paper
    put(0x5C00, SNA_SYSVARS)
    put(0xFF58, SNA_UDG)
    put(0x5C3D, (ramtop - 3).to_bytes(2, "little"))  # ERR_SP
    put(0x5CB2, ramtop.to_bytes(2, "little"))        # RAMTOP
    for addr, digits in ((0x5CD2, ramtop), (0x5CDD, entry), (0x5CEA, entry)):   # VAL "....."
        put(addr, f"{digits:05d}".encode())
    put(sp, SNA_STACK)
    for addr, b in asm.mem.items():
        ram[addr - 0x4000] = b
    put(sp - 2, entry.to_bytes(2, "little"))         # the .sna format takes PC from the stack
    return ram, dict(SNA_REGS, bc=entry, sp=sp, pc=entry)


def sna_header(r, sp):
    """The 27 byte header of a .sna snapshot."""
    head = bytes([r["i"]]) + b"".join(r[k].to_bytes(2, "little") for k in ("hl2", "de2", "bc2", "af2",
                                                                         "hl", "de", "bc", "iy", "ix"))
    head += bytes([r["iff2"] << 2, r["r"]]) + r["af"].to_bytes(2, "little") + sp.to_bytes(2, "little")
    return head + bytes([r["im"], r["border"]])


def sna(asm):
    """48K .sna snapshot (--sna-48k): 27 byte header + RAM; PC is pushed on the stack."""
    ram, r = spectrum48_state(asm, "sna-48k")
    return sna_header(r, r["sp"] - 2) + bytes(ram)


PORT_7FFD = 0x10        # 128K: ROM 1 (48 BASIC), bank 0 at C000h, paging not locked


def spectrum128_state(asm, fmt):
    """({bank: 16 KB}, registers): the --sna-48k state on a Spectrum 128K in 48 BASIC
    (ROM 1) with paging not locked (7FFDh and BANKM = 10h), so the program can page the
    banks; 4000h-7FFFh is bank 5, 8000h-BFFFh bank 2, C000h-FFFFh bank 0, the code of
    BANK n goes to bank n."""
    fixed = {5: 0x4000, 2: 0x8000}                   # banks 5 and 2 are also at 4000h / 8000h
    also = {a - 0xC000 + at for bank, at in fixed.items() for a in asm.banks.get(bank, {})}
    ram, r = spectrum48_state(asm, fmt, also)
    if 0x5B5C in asm.mem or 0x5B5C in also:
        raise AsmError(f"{option(fmt)}: the code uses 5B5Ch, the system variable BANKM of the 128K")
    if r["sp"] >= 0xC000 and asm.banks:
        raise AsmError(f"{option(fmt)}: the code starts below 5D2Ah, so the Basic stack is at {r['sp']:04X}h in bank 0"
                       " and paging another bank in would take it away; start the code from 5D2Ah")
    if r["pc"] >= 0xC000 and r["pc"] not in asm.mem:
        raise AsmError(f"{option(fmt)}: the start address {r['pc']:04X}h is not in bank 0, which is at C000h "
                       "when the program starts; start at 4000h-BFFFh and page the bank in")
    ram[0x5B5C - 0x4000] = PORT_7FFD                 # BANKM: the last value written to 7FFDh
    pages = {5: ram[:0x4000], 2: ram[0x4000:0x8000], 0: ram[0x8000:]}
    banks = {}
    for bank in range(8):
        page = pages.get(bank, bytearray(0x4000))
        for a, b in asm.banks.get(bank, {}).items():
            if bank in fixed and a - 0xC000 + fixed[bank] in asm.mem:
                raise AsmError(f"{option(fmt)}: BANK {bank} at {a:04X}h and the code at "
                               f"{a - 0xC000 + fixed[bank]:04X}h are the same byte of bank {bank}")
            page[a - 0xC000] = b
        banks[bank] = bytes(page)
    return banks, r


def sna128(asm):
    """128K .sna snapshot (--sna-128k), see spectrum128_state: header + banks 5, 2, 0
    (4000h-FFFFh) + PC, 7FFDh, TR-DOS paged (0) + banks 1, 3, 4, 6, 7; PC is not on the
    stack here."""
    banks, r = spectrum128_state(asm, "sna-128k")
    out = sna_header(r, r["sp"]) + banks[5] + banks[2] + banks[0]
    out += r["pc"].to_bytes(2, "little") + bytes([PORT_7FFD, 0])
    return out + b"".join(banks[b] for b in (1, 3, 4, 6, 7))


def z80_compress(data):
    """The RLE of the .z80 format: 5 and more equal bytes (and 2 and more EDh) are
    ED ED count byte; the byte after a single EDh is written as it is."""
    out, i, n = bytearray(), 0, len(data)
    while i < n:
        b, j = data[i], i
        while j < n and data[j] == b and j - i < 255:
            j += 1
        if j - i >= 5 or b == 0xED and j - i >= 2:
            out += bytes([0xED, 0xED, j - i, b])
            i = j
        else:
            out.append(b)
            i += 1
            if b == 0xED and i < n:
                out.append(data[i])
                i += 1
    return bytes(out)


def z80(asm, k128=False):
    """.z80 snapshot, version 3: --z80-48k the same state as --sna-48k with PC in the
    header, the RAM in three compressed 16 KB pages (8 = 4000h, 4 = 8000h, 5 = C000h);
    --z80-128k the state of --sna-128k, machine 128K, port 7FFDh, pages 3-10 = banks 0-7."""
    if k128:
        banks, r = spectrum128_state(asm, "z80-128k")
        pages = [(b + 3, banks[b]) for b in range(8)]
    else:
        ram, r = spectrum48_state(asm, "z80-48k")
        pages = [(8, ram[:0x4000]), (4, ram[0x4000:0x8000]), (5, ram[0x8000:])]

    def w(n):
        return n.to_bytes(2, "little")
    head = bytes([r["af"] >> 8, r["af"] & 0xFF]) + w(r["bc"]) + w(r["hl"]) + w(0) + w(r["sp"])
    head += bytes([r["i"], r["r"] & 0x7F, r["r"] >> 7 | r["border"] << 1]) + w(r["de"])
    head += w(r["bc2"]) + w(r["de2"]) + w(r["hl2"]) + bytes([r["af2"] >> 8, r["af2"] & 0xFF])
    head += w(r["iy"]) + w(r["ix"]) + bytes([r["iff2"], r["iff2"], r["im"]])
    ext = bytearray(54)                              # version 3; machine 0 = 48K, no AY
    ext[0:2] = w(r["pc"])
    if k128:
        ext[2:4] = bytes([4, PORT_7FFD])             # machine 4 = 128K (version 3), port 7FFDh
    ext[29:31] = b"\xFF\xFF"                         # 0000h-3FFFh is ROM
    out = head + w(len(ext)) + bytes(ext)
    for page, data in pages:
        data = z80_compress(data)
        out += w(len(data)) + bytes([page]) + data
    return out


# --- ZX Spectrum 128K: BANK, --tap128, --tapbas128 (from the Pasmo 0.5.5.paged fork) ---
def spectrum128_blocks(asm):
    """Code blocks (bank, start, data) of a program that uses BANK: 4000h-7FFFh is
    bank 5, 8000h-BFFFh bank 2, C000h-FFFFh bank 0 or the bank set by BANK."""
    if any(a < 0x4000 for a in asm.mem):
        raise AsmError("code at 0000h-3FFFh: that is ROM on the Spectrum 128K")
    for bank, fixed in ((5, 0x4000), (2, 0x8000)):        # banks 5 and 2 are also at 4000h / 8000h
        for a in asm.banks.get(bank, {}):
            if a - 0xC000 + fixed in asm.mem:
                raise AsmError(f"BANK {bank} at {a:04X}h and the code at {a - 0xC000 + fixed:04X}h "
                               f"are the same byte of bank {bank}")
    blocks = []
    for lo, hi, bank in ((0x4000, 0x7FFF, 5), (0x8000, 0xBFFF, 2), (0xC000, 0xFFFF, 0)):
        part = {a: b for a, b in asm.mem.items() if lo <= a <= hi}
        if part:
            blocks.append((bank,) + image(part))
    for bank, part in asm.banks.items():
        blocks.append((bank,) + image(part))
    return sorted(blocks)


def spectrum128_loader(lo, banks, entry):
    """Basic loader of the 0.5.5.paged fork. Line 1 holds machine code in a REM that
    pages in the bank from RASP (23608) and keeps BANKM (23388) up to date:
        1 REM <DI: LD A,(23388): AND F8h: LD B,A: LD A,(23608): OR B: LD (23388),A:
               LD BC,7FFDh: OUT (C),A: EI: RET>
        10 CLEAR lo-1: LET c=(PEEK 23635+256*PEEK 23636)+5      (c = address of the code)
        20 LET a=PEEK 23608
        40 READ b
        50 IF b<8 THEN POKE 23608,b: RANDOMIZE USR c: LOAD "" CODE: GO TO 40
        60 POKE 23608,0: RANDOMIZE USR c: POKE 23608,a[: RANDOMIZE USR entry]
        110 DATA <bank of each code block>, 8
    Numbers are written as VAL "n" like in the fork."""
    REM, CLEAR, LET, PEEK, READ, IF, THEN, POKE, RANDOMIZE, USR, LOAD, CODE, GOTO, DATA = (
        b"\xEA", b"\xFD", b"\xF1", b"\xBE", b"\xE3", b"\xFA", b"\xCB", b"\xF4", b"\xF9", b"\xC0",
        b"\xEF", b"\xAF", b"\xEC", b"\xE4")

    def val(n):
        return b'\xB0"' + str(n & 0xFFFF).encode() + b'"'
    switch = bytes([0xF3, 0x3A, 0x5C, 0x5B, 0xE6, 0xF8, 0x47, 0x3A, 0x38, 0x5C, 0xB0, 0x32,
                    0x5C, 0x5B, 0x01, 0xFD, 0x7F, 0xED, 0x79, 0xFB, 0xC9])
    basic = basic_line(1, REM + switch)
    basic += basic_line(10, CLEAR + val(lo - 1) + b":" + LET + b"c=(" + PEEK + val(23635) + b"+"
                        + val(256) + b"*" + PEEK + val(23636) + b")+" + val(5))
    basic += basic_line(20, LET + b"a=" + PEEK + val(23608))
    basic += basic_line(40, READ + b"b")
    basic += basic_line(50, IF + b"b<" + val(8) + THEN + POKE + val(23608) + b",b:" + RANDOMIZE
                        + USR + b"c:" + LOAD + b'""' + CODE + b":" + GOTO + val(40))
    # pypasmo: page bank 0 in again before the start (the fork leaves the last loaded
    # bank at C000h, so code of bank 0 at C000h did not run); no STOP: the program runs
    # to its end, "0 OK" (the fork: "9 STOP statement" after GO TO 40 in line 70)
    end = POKE + val(23608) + b"," + val(0) + b":" + RANDOMIZE + USR + b"c:" + POKE + val(23608) + b",a"
    if entry is not None:
        end += b":" + RANDOMIZE + USR + val(entry)
    basic += basic_line(60, end)
    basic += basic_line(110, DATA + b",".join(val(b) for b in banks) + b"," + val(8))
    return basic


def memmap_text(asm):
    """--memmap (idea from the 0.5.5.paged fork, own format): the 16 KB pages of the
    64 KB address space and the RAM banks of the Spectrum 128K with the used ranges."""
    def used(part):
        if not part:
            return "-"
        lo, hi = min(part), max(part)
        return f"{lo:04X}h-{hi:04X}h  {hi - lo + 1:5} bytes"
    out = ["Memory map:"]
    for page in range(4):
        lo = page * 0x4000
        part = {a for a in asm.mem if lo <= a < lo + 0x4000}
        where = ("ROM on the Spectrum", "Spectrum 128K bank 5", "Spectrum 128K bank 2",
                 "Spectrum 128K bank 0 (BANK 0)")[page]
        out.append(f"  page {page}  {lo:04X}h-{lo + 0x3FFF:04X}h  {where:30} used: {used(part)}")
    if asm.banks:
        out.append("Banks set by BANK (at C000h-FFFFh):")
        for bank, part in sorted(asm.banks.items()):
            out.append(f"  bank {bank}  used: {used(part)}")
        out.append("Blocks of --tap-128k / --tap-wloader-128k (bank, start, length):")
        try:
            for bank, start, data in spectrum128_blocks(asm):
                out.append(f"  bank {bank}  {start:04X}h  {len(data):5} bytes")
        except AsmError as e:
            out.append(f"  {e}")
    return "\n".join(out) + "\n"


def tap128(asm, name, basic_loader_too, fmt=None):
    """--tap128 / --tapbas128: without BANK the same as --tap / --tapbas (like the fork),
    with BANK one CODE block "bankN.tap" per bank and page (+ the 128K loader). fmt: the
    format for the messages (--tzx-128k ... use these tap blocks too)."""
    lo, data = image(asm.mem)
    fmt = fmt or ("tapbas128" if basic_loader_too else "tap128")
    if not asm.banks:
        code = tap_code(lo, data, name)
        basic = basic_loader(lo, asm.entry)
        tape_warnings(asm, fmt, [lo] if data else [], basic if basic_loader_too else None,
                      lo - 1 if data else None)
        return tap_basic(basic) + code if basic_loader_too else code
    blocks = spectrum128_blocks(asm)
    out = b""
    if basic_loader_too:
        lo = min(b[1] for b in blocks)
        basic = spectrum128_loader(lo, [b[0] for b in blocks], asm.entry)
        tape_warnings(asm, fmt, [], basic, lo - 1, extra=20)     # + the variables a, b, c
        out = tap_basic(basic)
    for bank, start, part in blocks:
        out += tap_code(start, part, f"bank{bank}.tap")
    return out


# --- ZX Spectrum .tzx (tzx.cxx in Pasmo) ---
TZX_HEAD = b"ZXTape!\x1A\x01\x0D"     # signature, TZX version 1.13 (.cdt files use it too)


def tzx(tap):
    """.tzx from .tap data: every tap block becomes a standard speed block (ID 10h,
    pause 1000 ms), whose content is the same as the tap block (length + data)."""
    out = bytearray(TZX_HEAD)
    pos = 0
    while pos < len(tap):
        size = 2 + int.from_bytes(tap[pos:pos + 2], "little")
        out += b"\x10" + (1000).to_bytes(2, "little") + tap[pos:pos + size]
        pos += size
    return bytes(out)


# --- ZX Spectrum .pzx (pypasmo extension; format 1.0 by Patrik Rak, pzx_format.txt) ---
def pzx_chunk(tag, data):
    return tag + len(data).to_bytes(4, "little") + data


def pzx(tap):
    """.pzx from .tap data: a header PZXT (version 1.0) and for every tap block the
    pulses of the ROM loader as the specification gives them: PULS (pilot tone of 8063
    pulses for a header, 3223 for data, 2168 T each, sync 667 + 735 T), DATA (the bits of
    flag + data + checksum starting high, bit 0 = 2x 855 T, bit 1 = 2x 1710 T, tail
    945 T) and PAUS (1 s low, as the pause of the .tzx blocks)."""
    w16 = lambda *v: b"".join(x.to_bytes(2, "little") for x in v)       # noqa: E731
    out = bytearray(pzx_chunk(b"PZXT", b"\x01\x00"))
    pos = 0
    while pos < len(tap):
        size = int.from_bytes(tap[pos:pos + 2], "little")
        body = tap[pos + 2:pos + 2 + size]
        pilot = 8063 if body[0] < 128 else 3223
        out += pzx_chunk(b"PULS", w16(0x8000 + pilot, 2168, 667, 735))
        out += pzx_chunk(b"DATA", (0x80000000 + 8 * size).to_bytes(4, "little")
                         + w16(945) + b"\x02\x02" + w16(855, 855, 1710, 1710) + body)
        out += pzx_chunk(b"PAUS", (3500000).to_bytes(4, "little"))
        pos += 2 + size
    return bytes(out)
