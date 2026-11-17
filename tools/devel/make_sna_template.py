"""Make the ZX Spectrum 48K state that pypasmo --sna-48k puts around the code (SNA_* in
pypasmo/out_spectrum.py). Needs SkoolKit (pip install skoolkit), which has the 48K ROM and a Z80
simulator; pypasmo itself does not need it.

The state is a real one: SkoolKit loads a tape with the Basic program
    10 CLEAR VAL "32767": RANDOMIZE USR VAL "32768"
in a simulated 48K Spectrum and stops when the machine code would start (PC = 32768).
The numbers are written with VAL "....." so that the program has the same length for
every address. Taken from it: the system variables and the Basic program (5C00h-5D0Ch),
the machine stack below RAMTOP (return addresses into the ROM; a RET of the code returns
to Basic), the UDG characters and the registers.

usage: python tools/devel/make_sna_template.py WORKDIR     (prints the Python code)
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pypasmo  # noqa: E402
from skoolkit.snapshot import Snapshot  # noqa: E402

RAMTOP, ENTRY = 32767, 32768


def main():
    work = Path(sys.argv[1])
    work.mkdir(parents=True, exist_ok=True)
    body = (b'\xFD\xB0"' + f"{RAMTOP:05d}".encode() + b'":\xF9\xC0\xB0"' + f"{ENTRY:05d}".encode() + b'"')
    (work / "template.tap").write_bytes(pypasmo.tap_basic(pypasmo.basic_line(10, body)))
    snap = work / "template.z80"
    if snap.exists():
        snap.unlink()
    # relative file names: tap2sna reads "C:\..." as an URL
    subprocess.run([sys.executable, "-c", "import sys; from skoolkit import tap2sna; tap2sna.main(sys.argv[1:])",
                    "--start", str(ENTRY), "template.tap", "template.z80"], cwd=work, check=True,
                   env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)))
    s = Snapshot.get(str(snap))
    ram = bytes(s.ram(-1))

    def mem(lo, hi):                     # lo..hi inclusive
        return ram[lo - 0x4000:hi - 0x4000 + 1]
    sysvars = mem(0x5C00, 0x5D0C)
    assert s.pc == ENTRY and s.bc == ENTRY and mem(0x5CB2, 0x5CB3) == RAMTOP.to_bytes(2, "little")
    assert mem(0x5CD2, 0x5CD6) == b"32767" and mem(0x5CDD, 0x5CE1) == b"32768"
    assert mem(0x5CEA, 0x5CEE) == b"32768"      # VAL "..." leaves the digits in the workspace
    assert set(mem(0x4000, 0x57FF)) == {0} and set(mem(0x5800, 0x5AFF)) == {0x38}
    stack = mem(s.sp, RAMTOP)
    assert mem(0x5C3D, 0x5C3E) == (RAMTOP - 3).to_bytes(2, "little")    # ERR_SP
    regs = {"i": s.i, "hl2": s.hl2, "de2": s.de2, "bc2": s.bc2, "af2": s.a2 << 8 | s.f2, "hl": s.hl,
            "de": s.de, "iy": s.iy, "ix": s.ix, "iff2": s.iff2, "r": s.r, "af": s.a << 8 | s.f,
            "im": s.im, "border": s.border}

    def hexlines(name, data):
        h = data.hex().upper()
        rows = [h[k:k + 80] for k in range(0, len(h), 80)]
        return f"{name} = bytes.fromhex(\n" + "".join(f'    "{r}"\n' for r in rows) + ")"
    print(hexlines("SNA_SYSVARS", sysvars))
    print(hexlines("SNA_STACK", stack))
    print(hexlines("SNA_UDG", mem(0xFF58, 0xFFFF)))
    print("SNA_REGS = {" + ", ".join(f'"{k}": 0x{v:04X}' for k, v in regs.items()) + "}")


main()
