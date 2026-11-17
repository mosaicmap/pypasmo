#!/usr/bin/env python3
"""Make the release files of pypasmo in dist/ (only the standard library is needed):

    pypasmo-X.Y.Z.zip     the package, run_pypasmo.py, the documentation, the examples and
                          the tests; unpack and run "python run_pypasmo.py ..." (no
                          installation), "python tests/run_tests.py" runs the tests
    pypasmo-X.Y.Z.pyz     the whole assembler in one file: "python pypasmo-X.Y.Z.pyz ..."
                          (on Linux / macOS also "./pypasmo-X.Y.Z.pyz ...")
    pypasmo-X.Y.Z-doc.zip the documentation (README.md and doc/) as HTML pages, made by
                          tools/md2html.py; open index.html
    pypi/pypasmo-X.Y.Z-py3-none-any.whl, pypi/pypasmo-X.Y.Z.tar.gz
                          wheel and sdist for pip / PyPI (python -m twine upload dist/pypi/*),
                          only when the package "build" is installed (python -m pip install
                          build); the sdist has the same files as the .zip
    SHA256SUMS.txt        checksums of the files above

usage: python tools/make_release.py [--skip-tests] [--no-build]

The tests run first; when they fail, nothing is made. The version comes from
pypasmo/__init__.py. The files in dist/ of the same version are replaced.
"""
import argparse
import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipapp
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md2html  # noqa: E402  (tools/md2html.py)

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PYPI = DIST / "pypi"                             # only files for PyPI (twine upload dist/pypi/*)

# files and folders of the .zip (relative to ROOT); folders are taken whole. The sdist must
# have the same files (MANIFEST.in), check_sdist compares them. tools/ is not released.
ZIP_FILES = ["run_pypasmo.py", "README.md", "LICENSE", "AUTHORS", "pyproject.toml", "MANIFEST.in", "pypasmo", "doc", "tests"]
EXECUTABLE = {"run_pypasmo.py", "tests/run_tests.py"}   # get the Unix x permission in the .zip
# made by setuptools in the sdist, not in the .zip
SDIST_ONLY = re.compile(r"^(PKG-INFO|setup\.cfg|pypasmo\.egg-info/.*)$")
SKIP = re.compile(r"(^|/)(__pycache__|\.pytest_cache)(/|$)|\.pyc$")


def version():
    text = (ROOT / "pypasmo" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        sys.exit("make_release: no __version__ in pypasmo/__init__.py")
    return m.group(1)


def run(cmd, **kw):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(ROOT), **kw).returncode


def files_of(rel):
    p = ROOT / rel
    found = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
    if not found:
        sys.exit(f"make_release: {rel} is missing")
    return [q for q in found if not SKIP.search(q.relative_to(ROOT).as_posix())]


def add_file(z, name, data, mode=0o644):
    """Add a file with a fixed date (the same bytes every time) and Unix permissions."""
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100000 | mode) << 16     # regular file + permissions
    info.create_system = 3                           # Unix, so unzip uses the mode
    z.writestr(info, data)


def make_zip(ver):
    top = f"pypasmo-{ver}"
    target = DIST / f"{top}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in ZIP_FILES:
            for p in files_of(rel):
                name = p.relative_to(ROOT).as_posix()
                add_file(z, f"{top}/{name}", p.read_bytes(),
                         0o755 if name in EXECUTABLE else 0o644)
    return target


def make_doc_zip(ver):
    """The documentation as HTML pages (tools/md2html.py), index.html = README.md."""
    top = f"pypasmo-{ver}-doc"
    target = DIST / f"{top}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        files = md2html.build(tmp)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                add_file(z, f"{top}/{p.relative_to(tmp).as_posix()}", p.read_bytes())
    return target


def make_pyz(ver):
    target = DIST / f"pypasmo-{ver}.pyz"
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(str(ROOT / "pypasmo"), str(Path(tmp, "pypasmo")),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        Path(tmp, "__main__.py").write_text("from pypasmo.cli import cli\ncli()\n", encoding="utf-8")
        zipapp.create_archive(tmp, str(target), interpreter="/usr/bin/env python3", compressed=True)
    return target


def check_pyz(pyz):
    """The .pyz must assemble an example to the same bytes as the ready file."""
    src = ROOT / "tests/output_formats/zx_spectrum/hello_spectrum.asm"
    ready = ROOT / "tests/output_formats/zx_spectrum_results/hello_spectrum.tap"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp, "hello_spectrum.tap")
        rc = run([sys.executable, str(pyz), "--tap-wloader-48k", "--name", "hello",
                  str(src), str(out)])
        if rc or out.read_bytes() != ready.read_bytes():
            sys.exit(f"make_release: {pyz.name} does not give {ready.name}")


def make_wheel_sdist(ver):
    if importlib.util.find_spec("build") is None:
        print("make_release: the package 'build' is not installed, no wheel and sdist "
              "(python -m pip install build)")
        return []
    with tempfile.TemporaryDirectory() as tmp:
        if run([sys.executable, "-m", "build", "--outdir", tmp]):
            sys.exit("make_release: python -m build failed")
        made = []
        for p in sorted(Path(tmp).iterdir()):
            if ver not in p.name:
                sys.exit(f"make_release: unexpected file {p.name} (version {ver}?)")
            made.append(Path(shutil.copy2(str(p), str(PYPI / p.name))))
    # the build leaves pypasmo.egg-info / build in the project folder
    shutil.rmtree(str(ROOT / "pypasmo.egg-info"), ignore_errors=True)
    shutil.rmtree(str(ROOT / "build"), ignore_errors=True)
    return made


def check_sdist(zip_path, made):
    """The sdist must have the same files as the .zip (apart from its metadata)."""
    with zipfile.ZipFile(str(zip_path)) as z:
        in_zip = {n.split("/", 1)[1] for n in z.namelist()}
    for p in made:
        if p.name.endswith(".tar.gz"):
            with tarfile.open(str(p)) as t:
                in_sdist = {m.name.split("/", 1)[1] for m in t.getmembers()
                            if m.isfile() and "/" in m.name}
            in_sdist = {n for n in in_sdist if not SDIST_ONLY.match(n)}
            if in_zip != in_sdist:
                sys.exit("make_release: the sdist and the .zip differ (MANIFEST.in?)\n"
                         f"  only in the .zip: {sorted(in_zip - in_sdist)}\n"
                         f"  only in the sdist: {sorted(in_sdist - in_zip)}")


def main():
    ap = argparse.ArgumentParser(description="Make the release files in dist/.")
    ap.add_argument("--skip-tests", action="store_true", help="do not run the tests first")
    ap.add_argument("--no-build", action="store_true", help="no wheel and sdist")
    args = ap.parse_args()

    ver = version()
    print(f"pypasmo {ver}")
    if not args.skip_tests and run([sys.executable, "tests/run_tests.py", "-q"]):
        sys.exit("make_release: the tests failed, nothing made")

    PYPI.mkdir(parents=True, exist_ok=True)
    for old in list(DIST.glob(f"pypasmo-{ver}*")) + list(PYPI.glob(f"pypasmo-{ver}*")):
        old.unlink()
    made = [make_zip(ver), make_pyz(ver), make_doc_zip(ver)]
    check_pyz(made[1])
    if not args.no_build:
        built = make_wheel_sdist(ver)
        check_sdist(made[0], built)
        made += built

    names = [p.relative_to(DIST).as_posix() for p in made]
    sums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {n}\n"
                   for p, n in zip(made, names))
    (DIST / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")
    print()
    for p, n in zip(made, names):
        print(f"{p.stat().st_size:>9}  dist/{n}")
    print("          dist/SHA256SUMS.txt")


if __name__ == "__main__":
    main()
