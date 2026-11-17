r"""Differential test: run a real Pasmo executable and pypasmo on the same sources and
compare the output files byte for byte (not part of the unit tests, Pasmo is not
distributed with pypasmo).

usage: python tools/devel/compare_with_pasmo.py PASMO_EXE WORKDIR SRC.asm... [-- options]
    options: --only-FORMAT (e.g. --only-bin, may be repeated), -v (print SAME too),
             anything else is passed to both assemblers
Prints DIFF / ONLY-PASMO-OK / ONLY-PY-OK lines and a summary.
Edge case sources: python tools/devel/edge_cases.py DIR

PASMO_EXE must be one executable file; for a Pasmo built under WSL use a .cmd wrapper
that runs it with "wsl" and converts C:\... paths to /mnt/c/... (see CLAUDE.md).

Example:
    python tools/devel/edge_cases.py work/cases
    python tools/devel/compare_with_pasmo.py pasmo.exe work/out work/cases/*.asm -- --only-bin
"""
import subprocess
import sys
from pathlib import Path

PY = Path(__file__).resolve().parents[2] / "run_pypasmo.py"
FORMATS = ["bin", "hex", "tap", "tapbas", "tzx", "tzxbas", "plus3dos", "amsdos",
           "cdt", "cdtbas", "msx", "prl"]


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 999, b"TIMEOUT"
    return r.returncode, r.stdout + r.stderr


def main():
    exe, work = Path(sys.argv[1]), Path(sys.argv[2])
    args = sys.argv[3:]
    extra = []
    if "--" in args:
        k = args.index("--")
        args, extra = args[:k], args[k + 1:]
    fmts = [f for f in FORMATS if f"--only-{f}" in extra] or FORMATS
    extra = [e for e in extra if not e.startswith("--only-")]
    work.mkdir(parents=True, exist_ok=True)
    stats = {}
    for src in args:
        src = Path(src).resolve()
        for fmt in fmts:
            out_p = work / f"{src.stem}.{fmt}.pasmo"
            out_y = work / f"{src.stem}.{fmt}.py"
            for o in (out_p, out_y):
                if o.exists():
                    o.unlink()
            name = ["--name", "T"] if fmt != "bin" else []
            rp, mp = run([str(exe), f"--{fmt}", *name, *extra, src.name, str(out_p)], src.parent)
            ry, my = run([sys.executable, str(PY), f"--{fmt}", *name, *extra, src.name, str(out_y)], src.parent)
            okp = rp == 0 and out_p.exists()
            oky = ry == 0 and out_y.exists()
            if okp and oky:
                same = out_p.read_bytes() == out_y.read_bytes()
                res = "SAME" if same else "DIFF"
            elif okp:
                res = "ONLY-PASMO-OK"
            elif oky:
                res = "ONLY-PY-OK"
            else:
                res = "BOTH-FAIL"
            stats[res] = stats.get(res, 0) + 1
            if res != "SAME" and res != "BOTH-FAIL" or "-v" in extra:
                print(f"{res:14} {fmt:9} {src.name}")
                if res.startswith("ONLY") or res == "DIFF":
                    print("    pasmo:", mp.decode("latin-1").strip().replace("\n", " | ")[:300])
                    print("    py   :", my.decode("latin-1").strip().replace("\n", " | ")[:300])
    print("summary:", stats)


main()
