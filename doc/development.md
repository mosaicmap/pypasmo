# Development

Back to the [index](index.md).

- [How the passes work](#how-the-passes-work)
- [Package layout](#package-layout)
- [Tests](#tests)
- [Comparison with the real Pasmo](#comparison-with-the-real-pasmo)
- [Release files](#release-files)
- [License](#license)

## How the passes work

An assembler must know the address of every label before it can generate code that jumps
forward (`JP later` comes before `later:`). So the source is read more than once:

1. **Preparation pass:** every line is processed, instruction sizes are computed and each
   label gets its address. A symbol that is not known yet counts as 0, no errors are
   reported for it.
2. **More preparation passes** run while some symbol value still changes. This is needed
   for chains of forward references like `x EQU y+1`, `y EQU z+1`, `z EQU 5`. Usually the
   second pass already gives the same values and the loop stops. Pasmo does the same with
   an automatic 3rd pass ("Switching to 3 pass mode").
3. **Final pass:** all symbols are known, the code is generated and every error is
   reported (undefined symbol, jump out of range, ...). If a label gets a different value
   than in the previous pass, it is a "phase error" (this should not happen for valid
   code).

Instruction sizes on the Z80 never depend on the value of an operand, so the label
addresses are right after the first pass in almost all programs. The number of passes is
not limited to 3, so `--pass3` of Pasmo is not needed.

`ASSERT`, `DISPLAY` and the `TAPE_BLOCK...` directives take their values from the last
pass, so they may use labels defined later. The values that decide the addresses (`ORG`,
`DS`, `IF` ...) must be defined above, as in Pasmo (see
[Forward references](source-format.md#forward-references)); so the addresses never
depend on a guess from the previous pass.

## Package layout

| Module | Contents |
|---|---|
| `__init__.py` | the version and the public names (`pypasmo.assemble_text` ...) |
| `__main__.py` | `python -m pypasmo` |
| `lexer.py` | tokens |
| `expr.py` | expressions |
| `z80.py` | instructions, T-states |
| `assembler.py` | passes, directives, macros |
| `out_spectrum.py`, `out_other.py` | output formats |
| `cpc_state.py` | the Basic state of the CPC snapshots (made by `tools/devel/make_cpc_sna_template.py`) |
| `cli.py` | command line, listing, symbol files |
| `common.py` | shared tables |

## Tests

Run all tests:

```
python tests/run_tests.py
```

It is the same as `python -m unittest discover -s tests -v`. `-q` prints less; test
names run only some tests, for example `python tests/run_tests.py test_pypasmo.Labels`.

The tests use **unittest** from the Python standard library, so nothing has to be
installed. `pytest`, if installed, can run them too.

- `tests/test_pasmo_suite.py` uses the test files of Pasmo 0.5.5 in
  `tests/pasmo_0.5.5_original_tests/` (unchanged, GPL v3):
  - `all.asm` (the whole instruction set) and `allb.asm` (the same with `[ ]`, in
    `--bracket` mode) must give **byte for byte the same as `all.check`**, the binary made
    by the original Pasmo;
  - `--w8080`: the 8080 part of `all.asm` gives no warning, and `black.asm` passes with
    `--w8080 --werror` like in Pasmo's `test_cli.sh`;
  - autolocal mode, `PUBLIC`, `reserv.asm`, the 64KB limit, macros (`tmacro.asm`) with
    results checked by hand;
  - files that must assemble (including the Pasmo sample programs) or fail, as in
    `test_cli.sh`;
  - the binaries of 33 test sources must be the same as the output of the real Pasmo
    0.5.5 in `tests/pasmo_0.5.5_original_test_results/` (`limit64.bin` is the documented
    64 KB difference).
- `tests/test_pypasmo.py` has pypasmo's own tests of directives, expressions, literals,
  errors, output formats and the command line. The expected values are computed by hand
  from the Pasmo documentation and source code. The example files in
  `tests/output_formats/<machine>_results/` (made from `tests/output_formats/<machine>/`)
  must be reproduced byte for byte (`hello_spectrum.tap` / `.tzx` are also the same as
  Pasmo 0.5.5 makes).
- The Pasmo 0.6.0.20070113 snapshot has no tests.

The ZX Spectrum, Amstrad CPC and MSX output follows the Pasmo source (`tap.cxx`,
`tzx.cxx`, `spectrum.cxx`, `cpc.cxx`, `emitplus3dos`, `emitmsx`). The CPC tape CRC is
checked against `binascii.crc_hqx` from the standard library.

## Comparison with the real Pasmo

`tools/devel/compare_with_pasmo.py` runs a Pasmo executable and pypasmo on the same sources
and compares the output files byte for byte; `tools/devel/edge_cases.py` writes about 300 small
edge case sources.

With **Pasmo 0.5.5** built from `pasmo_0.5.5_orig/pasmo-0.5.5_src.tar.gz` (g++ under
WSL / Linux: `./configure && make`):
- all 12 output formats of the 49 Pasmo test sources (and of `align.asm`, `if.asm`,
  `include.asm` from the tarball): the same output or the same failure, except
  `limit64.asm` (64 KB of code, see the [differences](pasmo-differences.md#different));
- symbol files the same, also with `--nocase`, `--alocal`, `--bracket`, `--public`,
  `-E`, `-I`;
- about 300 edge case sources and hand-written special cases (empty `DB`, reserved words
  as macro parameters, line ends, `(IX+LOW x)`, line numbers, forward references ...):
  the same output or the same failure except the [differences](pasmo-differences.md).

Other development tools in `tools/devel/` (`check_tstates.py`, `make_sna_template.py` and
`plus3run.py` need [SkoolKit](https://skoolkit.ca/)); they are not needed to use or test
pypasmo:

| Tool | What it does |
|---|---|
| `pasmo_wsl.py` | runs a Pasmo built under WSL from Windows (for `compare_with_pasmo.py`) |
| `check_tstates.py` | checks the T-states of the listing against the SkoolKit Z80 simulator |
| `make_sna_template.py` | makes the ZX Spectrum Basic state of <nobr>`--sna-48k`</nobr> |
| `make_cpc_sna_template.py` | makes `pypasmo/cpc_state.py`, the CPC Basic state of <nobr>`--sna-cpc6128`</nobr> / <nobr>`--sna-cpc464`</nobr>, from emulator snapshots |
| `plus3run.py` | runs a Spectrum +3 (its ROMs, e.g. from JSpeccy, with a simple floppy controller) with a <nobr>`--dsk-plus3`</nobr> image and prints the screen: "Loader" runs the loader and the code |

Earlier with Pasmo 0.5.4.beta2 (the newest Windows build) the differences were the
0.5.5 features (Amsdos name padding, Intel HEX end record, `$` in names, `DB ?` ...).

## Release files

```
python tools/make_release.py
```

runs the tests and makes the release files in `dist/` (only the standard library is
needed):

| File | What it is |
|---|---|
| `pypasmo-X.Y.Z.zip` | the package, `run_pypasmo.py`, the documentation, the examples and the tests: unpack and run `python run_pypasmo.py ...` (or `pip install .` in the unpacked folder) |
| `pypasmo-X.Y.Z.pyz` | the whole assembler in one file (a Python zip application): `python pypasmo-X.Y.Z.pyz ...`, on Linux / macOS after `chmod +x` also `./pypasmo-X.Y.Z.pyz ...` |
| `pypasmo-X.Y.Z-doc.zip` | the documentation (`README.md` and `doc/`) as HTML pages: unpack and open `index.html` |
| `pypi/pypasmo-X.Y.Z-py3-none-any.whl`, `pypi/pypasmo-X.Y.Z.tar.gz` | wheel and sdist for pip and PyPI (only when the package `build` is installed: `python -m pip install build`); the sdist has the same files as the `.zip` |
| `SHA256SUMS.txt` | checksums |

`--skip-tests` skips the tests, `--no-build` the wheel and sdist. The version comes from
`pypasmo/__init__.py`, as `X.Y.Z` or a pre-release such as `0.7.0b1` (beta 1; the form
of PEP 440, which PyPI and the file names use). The folder `tools/` is not in any release
file.

### The HTML documentation

`tools/md2html.py` converts `README.md` and `doc/` to simple HTML pages (only the
standard library; only the Markdown that the documentation uses). It also checks every
link and anchor (`#heading`, made as on GitHub), so run it after a change of the
documentation.

Check the links and anchors only:

```
python tools/md2html.py --check
```

Write the HTML pages into a folder (`index.html` is the README):

```
python tools/md2html.py html
```

A link to a file outside `README.md` and `doc/` (an example in `tests/` ...) keeps its
text without the link in the HTML pages. `make_release.py` stops when a link is broken.

## License

GNU General Public License version 3 (`GPL-3.0-only`, the same as Pasmo), full text in
[LICENSE](../LICENSE). pypasmo is new code, but it takes its behaviour from the Pasmo source
code and documentation, so it is a derived work. The test files in
`tests/pasmo_0.5.5_original_tests/` are unchanged copies from Pasmo, together with its
`COPYING` and `AUTHORS`.

Thanks to Julián Albo for Pasmo.
