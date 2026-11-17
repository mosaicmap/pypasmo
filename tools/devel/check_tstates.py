"""Check pypasmo.tstates() (T-states in the listing) against the Z80 simulator of
SkoolKit (pip install skoolkit) for every instruction of all.asm and undoc.asm.
Conditional and repeating instructions run with several register setups, so that both
times (condition true / false, repeat / end) are seen.

usage: python tools/devel/check_tstates.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pypasmo  # noqa: E402
from skoolkit.simulator import Simulator  # noqa: E402

T = 25                                  # index of the T-state counter in Simulator.registers
SETUPS = [
    {"F": 0x00, "B": 1, "C": 1, "A": 0, "H": 0x90, "L": 0},    # conditions false, DJNZ ends
    {"F": 0xFF, "B": 2, "C": 2, "A": 1, "H": 0x90, "L": 0},    # conditions true, loops repeat
    {"F": 0x00, "B": 0, "C": 1, "A": 0, "H": 0x90, "L": 0},    # BC = 1: LDIR ... end
]


def measure(code, regs):
    mem = bytearray(65536)
    mem[0x8000:0x8000 + len(code)] = bytes(code)
    mem[0x9000] = 0x55
    sim = Simulator(mem, dict(regs, PC=0x8000, SP=0xF000, IX=0x9000, IY=0x9000, D=0x90, E=0x10))
    t0 = sim.registers[T]
    sim.run(0x8000)
    return sim.registers[T] - t0


def main():
    bad = n = 0
    seen = set()
    for src in ("all.asm", "undoc.asm"):
        a = pypasmo.Assembler()
        a.assemble(ROOT / "tests" / "pasmo_0.5.5_original_tests" / src)
        for addr, data, t, text, depth in a.listing:
            if not t or tuple(data) in seen:
                continue
            seen.add(tuple(data))
            n += 1
            got = sorted({measure(data, s) for s in SETUPS}, reverse=True)
            if got != sorted({int(x) for x in t.split("/")}, reverse=True):
                bad += 1
                print(f"{' '.join(f'{b:02X}' for b in data):14} {text.strip():24} pypasmo {t:6} simulator {got}")
    print(f"{n} instructions, {bad} differences")
    return 1 if bad else 0


sys.exit(main())
