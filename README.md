# pypasmo

A **Z80 assembler** in pure *Python 3* with no dependencies, compatible with the syntax and the
command line of the **[Pasmo](https://pasmo.speccy.org/)** assembler by Julián Albo.

Source code written for Pasmo should assemble with pypasmo without changes and with the
same result. The whole Z80 instruction set gives *byte for byte the same output as the
original Pasmo* (checked with Pasmo's own tests).

**pypasmo** adds output formats for more Z80 machines, a few directives (not reserved words, so Pasmo sources keep working), 
up to 10 errors at once, T-states in the listing and
debug symbols for the DeZog debugger, and more.

Documentation: **[doc/index.md](doc/index.md)**.

## Install and run

Python 3.10 or newer, nothing else. In the project folder, without installing:

```
python -m pypasmo [options] input.asm output.bin [symbols.txt [publics.txt]]
```

The start script does the same, also from another folder (with its full path):

```
python run_pypasmo.py [options] input.asm output.bin
```

Or install it as a `pypasmo` command (in the project folder), with pipx (recommended for
command line tools):

```
pipx install .
```

or with pip (best inside a virtual environment):

```
python -m pip install .
```

## Example

```
        org 8000h
start:  ld a,2          ; red border
        out (0FEh),a
        ret
        end start
```

```
python -m pypasmo --tap-wloader-48k --name demo demo.asm demo.tap
```

`demo.tap` loads in a ZX Spectrum emulator with `LOAD ""`. A longer example:
`tests/output_formats/zx_spectrum/hello_spectrum.asm`.

## Supported machines

| Machine | Output options | Page |
|---|---|---|
| any Z80 system | <nobr>`--bin`</nobr> (default), <nobr>`--hex`</nobr> | [Output formats](doc/output-formats.md) |
| ZX Spectrum 48K | <nobr>`--tap-48k`</nobr>, <nobr>`--tap-wloader-48k`</nobr>, <nobr>`--tzx-48k`</nobr>, <nobr>`--tzx-wloader-48k`</nobr>, <nobr>`--pzx-48k`</nobr>, <nobr>`--pzx-wloader-48k`</nobr>, <nobr>`--sna-48k`</nobr>, <nobr>`--z80-48k`</nobr> | [ZX Spectrum 48K](doc/machines/zx-spectrum.md) |
| ZX Spectrum 128K / +3 | <nobr>`--tap-128k`</nobr>, <nobr>`--tap-wloader-128k`</nobr>, <nobr>`--tzx-128k`</nobr>, <nobr>`--tzx-wloader-128k`</nobr>, <nobr>`--pzx-128k`</nobr>, <nobr>`--pzx-wloader-128k`</nobr> **IN DEVELOPMENT**, <nobr>`--sna-128k`</nobr>, <nobr>`--z80-128k`</nobr>, <nobr>`--plus3dos`</nobr>, <nobr>`--dsk-plus3`</nobr> | [ZX Spectrum 128K and +3](doc/machines/zx-spectrum-128k.md) |
| ZX81 | <nobr>`--p-zx81`</nobr> | [ZX81](doc/machines/zx81.md) |
| Amstrad CPC | <nobr>`--amsdos`</nobr>, <nobr>`--cdt`</nobr>, <nobr>`--cdt-wloader`</nobr>, <nobr>`--dsk-cpc`</nobr>, <nobr>`--sna-cpc6128`</nobr>, <nobr>`--sna-cpc464`</nobr> | [Amstrad CPC](doc/machines/amstrad-cpc.md) |
| MSX | <nobr>`--msx`</nobr>, <nobr>`--rom-msx`</nobr>, <nobr>`--cas-msx`</nobr>, <nobr>`--dsk-msx`</nobr> | [MSX](doc/machines/msx.md) |
| Sega Master System / Game Gear | <nobr>`--rom-sms`</nobr>, <nobr>`--rom-gg`</nobr> | [Sega](doc/machines/other.md#sega-master-system-game-gear) |
| TRS-80 | <nobr>`--cas-trs`</nobr> **IN DEVELOPMENT**, <nobr>`--trs`</nobr> | [TRS-80](doc/machines/other.md#trs-80) |
| CP/M Plus | <nobr>`--prl`</nobr> | [CP/M Plus](doc/machines/other.md#cpm-plus) |
| Robotron KC 85 / Z 1013 | <nobr>`--kcc-kc85`</nobr>, <nobr>`--z80-z1013`</nobr> | [Robotron](doc/machines/other.md#robotron-kc-85-z-1013) |
| Sharp MZ-700 / MZ-800 | <nobr>`--mzf`</nobr> | [Sharp MZ](doc/machines/other.md#sharp-mz-700-mz-800) |
| Amstrad PCW | <nobr>`--dsk-pcw`</nobr> **IN DEVELOPMENT** | [Amstrad PCW](doc/machines/other.md#amstrad-pcw) |
| ColecoVision | <nobr>`--rom-coleco`</nobr> **IN DEVELOPMENT** | [ColecoVision](doc/machines/other.md#colecovision) |
| Jupiter Ace | <nobr>`--tap-ace`</nobr> **IN DEVELOPMENT** | [Jupiter Ace](doc/machines/other.md#jupiter-ace) |

All formats: [doc/output-formats.md](doc/output-formats.md).

## Documentation

- [Overview, origin, requirements](doc/index.md)
- [Command line](doc/command-line.md) - options, errors, listing, symbol files
- [Source format](doc/source-format.md) - labels, numbers, strings, expressions, instructions
- [Directives](doc/directives.md) - Pasmo, fork and pypasmo directives, macros
- [Debugging with DeZog](doc/debugging.md) (in short: [ZX Spectrum](doc/machines/zx-spectrum.md#debugging-in-vs-code-with-dezog))
- [Output formats](doc/output-formats.md) and the [machine pages](doc/index.md#machines)
- [Differences from Pasmo 0.5.5](doc/pasmo-differences.md)
- [Using it from Python](doc/python-api.md)
- [Development](doc/development.md) - tests, comparison with the real Pasmo
- Original Pasmo documentation: <https://pasmo.speccy.org/pasmodoc.html>

## License

**GNU GPL v3** (`GPL-3.0-only`, the same as Pasmo), see [LICENSE](LICENSE).

© Martin Pokorný, 2026