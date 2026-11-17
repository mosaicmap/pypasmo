# CLAUDE.md – pypasmo

pypasmo is a Z80 assembler in pure Python (standard library only, Python >= 3.8). It is a
port of the **Pasmo 0.5.5** assembler (C++) with the extensions of the fork Pasmo
0.5.5.paged (`DG`, `DUP/EDUP`, `STRUCT/ENDS`, `BANK`, 128K tapes) and its own additions:
output formats for many Z80 machines, a few directives, listings with T-states, debug
symbols for DeZog. License GPL-3.0-only.

## Documentation

- `README.md` – short introduction, start here.
- `doc/index.md` – the user documentation (English, several files): command line, source
  format, directives, output formats, debugging, Python API, development, and one page per
  machine in `doc/machines/`.
- `doc/pasmo-differences.md` – **the binding list of intended differences from Pasmo
  0.5.5**. Every change of behaviour against Pasmo must be written there.
- `pasmo_0.5.5_orig/` – the original Pasmo 0.5.5 sources (tar.gz) and its HTML
  documentation. The source of truth is `asm.cxx` in the tar.gz, not the documentation
  (they differ, e.g. `&X` is binary).

## Layout

- `pypasmo/` – the package. Run with `python -m pypasmo ...`, `python run_pypasmo.py ...`,
  or `pypasmo` after `pip install .` (`pypasmo.cli:cli`). Modules depend in one direction
  only:
  - `__init__.py` – `__version__` (the only place of the version; `pyproject.toml` reads
    it) and re-exports of the public functions (tests and tools use `pypasmo.X`);
  - `common.py` – `AsmError`, opcode tables, reserved words, shared helpers;
  - `lexer.py` – tokenizer of one line; `expr.py` – expressions (precedence exactly as Pasmo);
  - `z80.py` – operands, T-states, instruction encoding (`Z80Encoder`);
  - `assembler.py` – `Assembler`: passes, symbols, files, directives (`d_*`), macros, IF;
  - `out_spectrum.py`, `out_other.py`, `cpc_state.py` – output formats;
  - `cli.py` – command line (its docstring is the `--help` text), listing, symbol files.
- `tests/` – `run_tests.py`, `test_pypasmo.py` (own tests), `test_pasmo_suite.py` (the
  original Pasmo tests), `output_formats/<machine>/` examples with their ready files in
  `output_formats/<machine>_results/`.
- `tools/make_release.py` – the release files in `dist/`; `tools/md2html.py` – the
  documentation as HTML, link check; `tools/devel/` – development
  tools (comparison with the real Pasmo, edge cases, snapshot templates); `tools/` is not
  released.

## Tests

```
python tests/run_tests.py
```

All tests must pass. pytest is not needed (unittest from the standard library).

- `tests/pasmo_0.5.5_original_tests/` and `tests/pasmo_0.5.5_original_test_results/` are
  the files and outputs of the real Pasmo 0.5.5: **never change them**.
- The ready example files in `tests/output_formats/*_results/` must be reproduced byte for
  byte (test `Examples`).
- Expected values in tests are computed by hand, not copied from pypasmo output.

## Rules

- For a bug or a new feature: first a test that fails, then the change.
- Only the standard library, no dependencies.
- Goal: the same behaviour as Pasmo 0.5.5. Differ only where Pasmo produces nonsense code
  or has an obvious bug, and always document it in `doc/pasmo-differences.md`.
- New directives must not break Pasmo sources: they are not reserved words (a label of the
  same name stays a label, a macro of the same name wins) and `--pasmo-syntax-055` turns
  them off (`EXT_DIRECTIVES`, `FORK_DIRECTIVES` in `common.py`).
- Comments and documentation in English, short, in the style of the surrounding code.
- When behaviour changes, update `doc/` (and `README.md` if it is mentioned there).
- Marks in the user documentation and `--help`: *(early version)* and **IN DEVELOPMENT**.
  In the documentation an option with a file has the extension: `--lst FILE.lst`,
  `--dbgsym-list FILE.list`, `--dbgsym-sld FILE.sld`. Each example command goes into its
  own ``` block with its description before it.
- Line endings: `pypasmo/*.py`, tests and `.md` files are CRLF; `tools/**/*.py`,
  `run_pypasmo.py`, `tests/run_tests.py` (shebang) and `.gitattributes` are LF. Keep
  them; do not use `sed -i` on CRLF files.
- Not implemented on purpose: `--cmd`, `--sdrel`, `--86`, `--pass3`, `.8080` (an error as
  in Pasmo).
- Ignore `!_zip_archive/` (old backups) and `_tmp/` (local files).

## Comparison with the real Pasmo 0.5.5

There is no Windows build of Pasmo 0.5.5, but it builds in WSL (`./configure && make` in
the unpacked tar.gz). `tools/devel/pasmo_wsl.py` runs it, `tools/devel/edge_cases.py`
generates small sources, `tools/devel/compare_with_pasmo.py` compares the outputs byte for
byte. Details in `doc/development.md`.

## Release

```
python tools/make_release.py
```

Runs the tests and makes in `dist/`: the `.zip` (package, docs, tests), the `.pyz`
(zipapp), the `-doc.zip` (the documentation as HTML), and in `dist/pypi/` the wheel and
sdist (only with the package `build`; the sdist has the same files as the `.zip`). See
`doc/development.md`.

After a change of the documentation check its links and anchors:

```
python tools/md2html.py --check
```
