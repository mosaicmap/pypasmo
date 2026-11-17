"""Run a Pasmo built under WSL (Linux) from Windows, for tools/devel/compare_with_pasmo.py.
Windows paths in the arguments (C:\\...) are converted to /mnt/c/...

usage: python tools/devel/pasmo_wsl.py [pasmo options and files]
    PASMO_WSL      path of the pasmo executable inside WSL (required), e.g.
                   /mnt/c/work/pasmo-0.5.5/pasmo
    PASMO_WSL_DIST WSL distribution (default: the default one)

compare_with_pasmo.py needs one executable, so use a pasmo.cmd with:
    @python C:\\path\\to\\tools\\devel\\pasmo_wsl.py %*
"""
import os
import re
import subprocess
import sys


def conv(arg):
    m = re.match(r"^([A-Za-z]):[/\\](.*)$", arg)
    if m:
        return "/mnt/" + m.group(1).lower() + "/" + m.group(2).replace("\\", "/")
    return arg


def main():
    exe = os.environ.get("PASMO_WSL")
    if not exe:
        sys.exit("set PASMO_WSL to the path of pasmo inside WSL")
    dist = os.environ.get("PASMO_WSL_DIST")
    cmd = ["wsl"] + (["-d", dist] if dist else []) + ["--", exe]
    sys.exit(subprocess.run(cmd + [conv(a) for a in sys.argv[1:]]).returncode)


main()
