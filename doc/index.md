# pypasmo documentation

pypasmo is a **Z80 assembler** written in pure Python 3. It copies the syntax, the behaviour
and the command line of the **Pasmo** assembler.

This documentation describes what **pypasmo** does and where it differs from Pasmo. 

See also original Pasmo documentation [Pasmo pasmodoc](https://pasmo.speccy.org/pasmodoc.html)


Back to the [README](../README.md).

## Contents

| Page | What it covers |
|---|---|
| [Command line](command-line.md) | usage, all options |
| [Source format](source-format.md) | lines, labels, identifiers, numbers, strings, expressions, local labels, instructions |
| [Directives](directives.md) | Pasmo directives, fork directives, pypasmo directives, PHASE, STRUCT, BANK, macros |
| [Debugging with DeZog](debugging.md) | <nobr>`--dbgsym-sld`</nobr>, <nobr>`--dbgsym-list`</nobr>, `WPMEM` / `LOGPOINT` / `ASSERTION` |
| [Output formats](output-formats.md) | all output options in one table with their status, <nobr>`--bin`</nobr>, <nobr>`--hex`</nobr>, ... |
| [Differences from Pasmo 0.5.5](pasmo-differences.md) | the complete list of deliberate differences |
| [Using it from Python](python-api.md) | the Python API |
| [Development](development.md) | tests, comparison with the real Pasmo, how the passes work, license |

### Machines

| Machine | Page |
|---|---|
| **ZX Spectrum 48K** | [machines/zx-spectrum.md](machines/zx-spectrum.md) |
| ZX Spectrum 128K (early version),<br/> ZX Spectrum +3 (early version) | [machines/zx-spectrum-128k.md](machines/zx-spectrum-128k.md) |
| ZX81 (early version) | [machines/zx81.md](machines/zx81.md) |
| Amstrad CPC | [machines/amstrad-cpc.md](machines/amstrad-cpc.md) |
| MSX | [machines/msx.md](machines/msx.md) |
|||
| Sega Master System (early version),<br/> Sega Game Gear (early version) | [machines/other.md#sega-master-system-game-gear](machines/other.md#sega-master-system-game-gear) |
| TRS-80 (in development) | [machines/other.md#trs-80](machines/other.md#trs-80) |
| Robotron KC 85 (early version),<br/> Robotron Z 1013 (early version) | [machines/other.md#robotron-kc-85-z-1013](machines/other.md#robotron-kc-85-z-1013) |
| Sharp MZ-700 (early version),<br/> Sharp MZ-800 (early version) | [machines/other.md#sharp-mz-700-mz-800](machines/other.md#sharp-mz-700-mz-800) |
| CP/M Plus | [machines/other.md#cpm-plus](machines/other.md#cpm-plus) |
| Amstrad PCW (in development) | [machines/other.md#amstrad-pcw](machines/other.md#amstrad-pcw) |
| ColecoVision (in development) | [machines/other.md#colecovision](machines/other.md#colecovision) |
| Jupiter Ace (in development) | [machines/other.md#jupiter-ace](machines/other.md#jupiter-ace) |

## Origin

| | |
|---|---|
| Original project | **Pasmo**, a multiplatform Z80 cross-assembler |
| Pasmo author | **Julián** "NotFound" **Albo**  |
| Home page | <https://pasmo.speccy.org/> |
| Original documentation | <https://pasmo.speccy.org/pasmodoc.html> |
| pypasmo is derived from | **Pasmo 0.5.5** (documentation dated 2022-03-05), `pasmo-0.5.5.tar.gz` |
| Pasmo license | GNU GPL v3 |
| Extensions taken from | **Pasmo 0.5.5.paged** fork by **Jouni Korhonen** (jounikor), <https://github.com/jounikor/pasmo>, GPL v3: `DG`, `DUP`/`EDUP`, `STRUCT`/`ENDS`, `BANK`, <nobr>`--tap128`</nobr>, <nobr>`--tapbas128`</nobr> (in pypasmo <nobr>`--tap-128k`</nobr>, <nobr>`--tap-wloader-128k`</nobr>, the fork names work too), <nobr>`--memmap`</nobr>, the 128K Basic loader, the `(IX-n+m)` fix |

The development snapshot **Pasmo 0.6.0.20070113** was checked too. It is **older** than
0.5.5: an unfinished rewrite (bison parser, relocatable code), while the later bug fix
releases 0.5.4 and 0.5.5 came from the stable 0.5 branch. Its fix for `$` in identifiers is
in 0.5.5 and in pypasmo. The new 0.6.0 features (`IF1`, `IF2`, `IRPC`, `.PHASE`, segments,
REL files, 8080 syntax) are not in pypasmo, because the released Pasmo 0.5.5 does not have
them either. (pypasmo has its own `PHASE` / `.PHASE`, taken from MACRO-80, see
[Directives](directives.md#phase--dephase).)

pypasmo has its own version numbers; every version is **based on Pasmo 0.5.5**
(`python -m pypasmo --version` prints for example `pypasmo 0.7.0b1 (based on Pasmo 0.5.5)`).

## What pypasmo adds

All of it is marked *(pypasmo extension)* in this documentation.

- Output formats for more machines: ZX Spectrum snapshots and disk images, ZX81, MSX
  cartridges, tapes and disks, Jupiter Ace, Robotron, Sega, Sharp MZ, Amstrad PCW, ColecoVision, TRS-80 tapes, CPC
  disk images and snapshots ([Output formats](output-formats.md)).
- Directives `PHASE`/`DEPHASE`, `ALIGN`, `ASSERT`, `INCBIN` with offset and length, `DZ`,
  `DC`, `D_ZX81`, `D_ZX81I`, `DC_ZX81`, `TAPE_BLOCK`, `TAPE_BLOCK_SCREEN`, `TAP_INCLUDE`,
  `DISPLAY`, `ELSEIF`, `IFB`/`IFNB`, `BANK_OF`, default values of macro parameters
  ([Directives](directives.md)). They are not reserved words, so Pasmo sources keep
  working; `--pasmo-syntax-055` turns them off.
- Local labels `.name` (like sjasmplus: `.loop` belongs to the previous label, so each
  routine can have its own), see
  [Source format](source-format.md#local-labels-name-pypasmo-extension-like-sjasmplus).
- Up to 10 errors at once, a listing file with T-states, debug symbols for DeZog
  ([Command line](command-line.md), [Debugging](debugging.md)).

## Requirements

- **Python 3.10 or newer**, nothing else (no packages to install). Tested on Python 3.14
  and 3.10. Older versions are not supported (Python 3.9 and older are more than five years
  old and get no more updates).
- The assembler is the Python package in the folder `pypasmo/`. Three ways to run it:
  - `python -m pypasmo ...` in the project folder (the folder that contains `pypasmo/`);
  - `python run_pypasmo.py ...`, a small start script in the project folder (it can
    also be started with its full path from any folder);
  - the `pypasmo` command after `pipx install .` or `python -m pip install .` (the
    package is described in `pyproject.toml`).
- Parts of the package: `lexer.py` (tokens), `expr.py` (expressions), `z80.py`
  (instructions, T-states), `assembler.py` (passes, directives, macros),
  `out_spectrum.py`, `out_other.py` and `cpc_state.py` (output formats), `cli.py`
  (command line, listing, symbol files), `common.py` (shared tables).

## Quick start

```
        org 8000h
start:  ld a,1
        ret
        end start
```

Raw binary (`--bin`, the default):

```
python -m pypasmo prog.asm prog.bin
```

ZX Spectrum tape with a Basic loader:

```
python -m pypasmo --tap-wloader-48k --name prog prog.asm prog.tap
```

ZX Spectrum snapshot (runs at once in an emulator):

```
python -m pypasmo --sna-48k prog.asm prog.sna
```

Raw binary and a listing with T-states:

```
python -m pypasmo --lst prog.lst prog.asm prog.bin
```

Ready examples for each machine are in `tests/output_formats/<machine>/`, the files made
from them in `tests/output_formats/<machine>_results/`; the header of each source gives
the command that makes its file. How to try each file in an emulator is on the machine
pages.
