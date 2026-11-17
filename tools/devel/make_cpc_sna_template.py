"""Make the Amstrad CPC states that pypasmo --sna-cpc6128 and --sna-cpc464 put around the
code (pypasmo/cpc_state.py) from snapshots of a real CPC 6128 and CPC 464 in Basic (Ready).

Each snapshot must be an uncompressed .sna (version 1 or 2, a 64 KB or 128 KB memory dump),
saved by an emulator while the CPC waits for a key at the Ready prompt (the ones used for
pypasmo were saved by JavaCPC). Taken from it: the header (registers, Gate Array, CRTC,
PPI, PSG) and the non-zero parts of the first 64 KB of RAM (the restart vectors at 0000h,
the firmware (and AMSDOS) above HIMEM, the screen with the Basic start-up text). HIMEM + 1
is the lowest non-zero address from 0100h on.

usage: python tools/devel/make_cpc_sna_template.py 6128=64k.sna 464=464_64k.sna > pypasmo/cpc_state.py
"""
import sys

GAP = 32          # zero gaps shorter than this stay inside a range
WIDTH = 64        # hex characters per line
TYPES = {"464": 0, "664": 1, "6128": 2}


def ranges(ram):
    out, start, zeros = [], None, 0
    for i, b in enumerate(ram):
        if b:
            if start is None:
                start = i
            zeros = 0
        elif start is not None:
            zeros += 1
            if zeros >= GAP:
                out.append((start, i - zeros + 1))
                start, zeros = None, 0
    if start is not None:
        out.append((start, len(ram) - zeros))
    return out


def finish(model, head, ram):
    """The state must not be inside a routine that keeps something in the RAM: the code runs
    before it goes on. The CPC 464 snapshot of pypasmo is at 1D1Ah in the routine that takes
    a key from the buffer (1D15h: LD HL,B53Eh: OR A: DEC (HL): JR Z,1D2Ah ... 1D2Ah: INC (HL):
    RET), the buffer empty: the counter is 0 for a moment. Finish it (INC (HL), RET), so the
    counter is 1 again (empty) and PC is the return address (1B61h, JR NC = no key)."""
    pc, sp = head[0x23] | head[0x24] << 8, head[0x21] | head[0x22] << 8
    if model == "464" and pc == 0x1D1A:
        if not head[0x11] & 0x40 or (head[0x17] | head[0x18] << 8) != 0xB53E or ram[0xB53E]:
            sys.exit("CPC 464 at 1D1Ah: the key buffer is not empty")
        ram[0xB53E] += 1
        head[0x11] &= 0x01                           # F after INC 0 -> 1, the carry kept
        head[0x23:0x25], head[0x21:0x23] = ram[sp:sp + 2], (sp + 2).to_bytes(2, "little")
    elif (model, pc) not in (("6128", 0x1CE6), ("464", 0x1B61)):
        sys.exit(f"CPC {model} at {pc:04X}h: check that the firmware is not inside a routine")


def state(model, path):
    snap = open(path, "rb").read()
    if snap[:8] != b"MV - SNA" or snap[0x10] not in (1, 2):
        sys.exit(f"{path}: not an uncompressed CPC .sna (version 1 or 2)")
    if (snap[0x6B] | snap[0x6C] << 8) not in (64, 128) or len(snap) < 256 + 0x10000:
        sys.exit(f"{path}: the snapshot needs a memory dump of 64 or 128 KB")
    head, ram = bytearray(snap[:0x6D]), bytearray(snap[256:256 + 0x10000])
    finish(model, head, ram)
    himem = next(i for i in range(0x100, 0xC000) if ram[i])
    lines = [f"# CPC {model}: {path.replace(chr(92), '/').split('/')[-1]}, HIMEM {himem - 1:04X}h",
             f"CPC{model}_HIMEM = 0x{himem:04X}", "", f"CPC{model}_HEADER = bytes.fromhex("]
    hx = head.hex()
    lines += [f'    "{hx[i:i + WIDTH]}"' for i in range(0, len(hx), WIDTH)]
    lines += [")", "", f"CPC{model}_RAM = ("]
    for a, b in ranges(ram):
        hx = ram[a:b].hex()
        lines.append(f"    (0x{a:04X}, bytes.fromhex(")
        lines += [f'        "{hx[i:i + WIDTH]}"' for i in range(0, len(hx), WIDTH)]
        lines.append("    )),")
    return lines + [")", ""]


def main():
    args = [a.split("=", 1) for a in sys.argv[1:]]
    if not args or any(len(a) != 2 or a[0] not in TYPES for a in args):
        sys.exit(__doc__.strip().splitlines()[-1])
    lines = ['"""The states of Amstrad CPCs in Basic (Ready) for --sna-cpc6128 and --sna-cpc464, made',
             "by tools/devel/make_cpc_sna_template.py from snapshots saved by an emulator.",
             "CPCn_HEADER: bytes 00h-6Ch of the .sna header (registers, Gate Array, CRTC, PPI, PSG);",
             "CPCn_RAM: the non-zero parts of the 64 KB of RAM, (address, bytes); CPCn_HIMEM: HIMEM + 1;",
             'CPC_STATE: {CPC type of the .sna header: (HEADER, RAM, HIMEM)}."""', ""]
    for model, path in args:
        lines += state(model, path)
    lines.append("CPC_STATE = {")
    lines += [f"    {TYPES[m]}: (CPC{m}_HEADER, CPC{m}_RAM, CPC{m}_HIMEM)," for m, _ in args]
    lines.append("}")
    sys.stdout.buffer.write(("\r\n".join(lines) + "\r\n").encode("ascii"))


main()
