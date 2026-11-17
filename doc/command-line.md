# Command line

Back to the [index](index.md).

- [Usage](#usage)
- [Output format options](#output-format-options)
- [Options](#options)
- [Header name](#header-name)
- [Errors](#errors)
- [Warnings](#warnings)
- [Listing](#listing)
- [Symbol files](#symbol-files)

## Usage

```
python -m pypasmo [options] input.asm output.bin [symbols.txt [publics.txt]]
```

(or `python run_pypasmo.py ...`, or `pypasmo ...` when installed). The third file is the
[symbol table](#symbol-files), the fourth the public symbols; more file names give the
warning "extra arguments ignored" (as in Pasmo). Options may also come after the file
names (`--` ends the options).

The exit code is 0 on success and not 0 on an error. Errors and warnings go to the
standard error output as `file:line: message` (errors to the standard output with
`--err`).

## Output format options

One option selects the format of the output file; without one it is `--bin`. All of
them, with the machine and their status, are in [Output formats](output-formats.md).

| Group | Options |
|---|---|
| <nobr>*any machine*</nobr> | <nobr>`--bin`</nobr> (default), <nobr>`--hex`</nobr> |
| <nobr>ZX Spectrum</nobr> | <nobr>`--tap-48k`</nobr> <nobr>(`--tap`)</nobr>, <nobr>`--tap-wloader-48k`</nobr> <nobr>(`--tapbas`)</nobr>, <nobr>`--tzx-48k`</nobr> <nobr>(`--tzx`)</nobr>, <nobr>`--tzx-wloader-48k`</nobr> <nobr>(`--tzxbas`)</nobr>, <nobr>`--pzx-48k`</nobr>, <nobr>`--pzx-wloader-48k`</nobr>, <nobr>`--tap-128k`</nobr> <nobr>(`--tap128`)</nobr>, <nobr>`--tap-wloader-128k`</nobr> <nobr>(`--tapbas128`)</nobr>, <nobr>`--tzx-128k`</nobr>, <nobr>`--tzx-wloader-128k`</nobr>, <nobr>`--pzx-128k`</nobr>, <nobr>`--pzx-wloader-128k`</nobr>, <nobr>`--sna-48k`</nobr>, <nobr>`--z80-48k`</nobr>, <nobr>`--sna-128k`</nobr>, <nobr>`--z80-128k`</nobr>, <nobr>`--plus3dos`</nobr>, <nobr>`--dsk-plus3`</nobr> |
| <nobr>Amstrad CPC</nobr> | <nobr>`--amsdos`</nobr>, <nobr>`--cdt`</nobr>, <nobr>`--cdt-wloader`</nobr> <nobr>(`--cdtbas`)</nobr>, <nobr>`--dsk-cpc`</nobr>, <nobr>`--sna-cpc6128`</nobr>, <nobr>`--sna-cpc464`</nobr> |
| MSX | <nobr>`--msx`</nobr>, <nobr>`--rom-msx`</nobr>, <nobr>`--cas-msx`</nobr>, <nobr>`--dsk-msx`</nobr> |
| other | <nobr>`--p-zx81`</nobr>, <nobr>`--tap-ace`</nobr>, <nobr>`--kcc-kc85`</nobr>, <nobr>`--z80-z1013`</nobr>, <nobr>`--rom-sms`</nobr>, <nobr>`--rom-gg`</nobr>, <nobr>`--cas-trs`</nobr>, <nobr>`--trs`</nobr>, <nobr>`--prl`</nobr>, <nobr>`--mzf`</nobr>, <nobr>`--dsk-pcw`</nobr>, <nobr>`--rom-coleco`</nobr> |

The names with the machine (`--tap-48k` ...) are pypasmo's main names; the Pasmo / fork
names in brackets work the same, so old build scripts need no change.

## Options

| Option | Meaning |
|---|---|
| <nobr>`--nocase`</nobr> | identifiers are case insensitive |
| `-I DIR` | another directory to search for `INCLUDE` and `INCBIN` files |
| `-E` / <nobr>`--equ NAME[=VALUE]`</nobr> | predefine a symbol; without a value it is FFFFh |
| `-B` / <nobr>`--bracket`</nobr> | bracket only mode: only `[ ]` is an indirection, `( )` only groups expressions |
| <nobr>`--alocal`</nobr> | autolocal mode: labels starting with `_` are local, see [Source format](source-format.md#autolocal-mode---alocal) |
| `-8` / <nobr>`--w8080`</nobr> | warn about each instruction that the Intel 8080 does not have |
| <nobr>`--werror`</nobr> | treat warnings as errors (exit code 1) |
| <nobr>`--pasmo-syntax-055`</nobr> | only the source syntax of Pasmo 0.5.5, for old sources whose labels collide with newer directives: the pypasmo directives `PHASE`, `DEPHASE`, `ALIGN`, `ASSERT`, `DZ`, `DC`, `TAPE_BLOCK`, `TAPE_BLOCK_SCREEN`, `TAP_INCLUDE`, `DISPLAY`, `D_ZX81`, `D_ZX81I`, `DC_ZX81`, `ELSEIF`, `IFB`, `IFNB`, `BANK_OF`, default values of macro parameters, the `INCBIN` offset, the `.name` local labels and the fork directives `DG`, `DUP`, `EDUP`, `STRUCT`, `ENDS`, `BANK` are off, their names are normal identifiers *(pypasmo extension)* |
| <nobr>`--public`</nobr> | the symbol file contains only `PUBLIC` symbols |
| `-d` | print the listing to the standard output |
| <nobr>`--lst FILE.lst`</nobr> | write the listing to FILE.lst *(pypasmo extension)* |
| <nobr>`--dbgsym-list FILE.list`</nobr> | list file for the DeZog debugger: debugging in the list file, see [Debugging](debugging.md#debugging-in-a-list-file---dbgsym-list) *(pypasmo extension)* |
| <nobr>`--dbgsym-sld FILE.sld`</nobr> | SLD file (Source Level Debugging) for DeZog: stepping in the `.asm` source, see [Debugging](debugging.md#debugging-in-the-source---dbgsym-sld) *(pypasmo extension, ZX Spectrum 48K and 128K)* |
| <nobr>`--memmap`</nobr> | print the used part of each 16 KB page, the banks set by `BANK` and the blocks of <nobr>`--tap-128k`</nobr> *(from the 0.5.5.paged fork)* |
| <nobr>`--version`</nobr>, `-h` / <nobr>`--help`</nobr> | print the version / the help |
| <nobr>`--name NAME`</nobr> | name in the tape / disk header, see [below](#header-name) |
| <nobr>`--err`</nobr> | assembly errors go to the standard output instead of the standard error output (option errors do not); warnings stay on the standard error output, as in Pasmo |
| `-v`, `-1` | accepted for compatibility, do nothing |
| `--` | end of options, the rest are file names |

`--memmap` prints its own, shorter table; the fork dumps its internal page and bank
structures.

## Header name

`--name NAME` sets the name that goes into the file headers (and onto the disk images).
Without it the output file name is used. The formats of Pasmo, and the ZX Spectrum tapes
made from the same blocks (`--pzx-48k`, the 128K tapes), take it **as given on the command
line**, like Pasmo (with a path, `build/game.tap`, the name gets the directory too, so use
`--name` then); the other formats of pypasmo take the file name without the directory.

| Format | Where the name goes | Length, rules |
|---|---|---|
| <nobr>`--tap-48k`</nobr>, <nobr>`--tzx-48k`</nobr>, <nobr>`--pzx-48k`</nobr>, <nobr>`--tap-wloader-48k`</nobr>, <nobr>`--tzx-wloader-48k`</nobr>, <nobr>`--pzx-wloader-48k`</nobr> | the CODE header on the tape (the Basic loader is always `loader`) | 10 characters |
| <nobr>`--tap-128k`</nobr>, <nobr>`--tap-wloader-128k`</nobr>, <nobr>`--tzx-128k`</nobr>, <nobr>`--tzx-wloader-128k`</nobr>, <nobr>`--pzx-128k`</nobr>, <nobr>`--pzx-wloader-128k`</nobr> | without `BANK` the same as the 48K tapes; with `BANK` the blocks are named `bank1.tap`, `bank2.tap` ... (as in the fork) and `--name` is not used | 10 characters |
| <nobr>`--cdt`</nobr>, <nobr>`--cdt-wloader`</nobr> | the tape header of the code (the Basic loader is always `LOADER`) | 16 characters |
| <nobr>`--amsdos`</nobr> | the Amsdos header | 8 + 3 characters, split at the first dot |
| <nobr>`--dsk-cpc`</nobr> | the file `NAME.BIN` on the disk and its Amsdos header | 8 characters, upper case, up to the first character that is not a letter or a digit |
| <nobr>`--dsk-plus3`</nobr> | the file `NAME.BIN` on the disk (the Basic loader `DISK` loads it) | as <nobr>`--dsk-cpc`</nobr> |
| <nobr>`--dsk-msx`</nobr> | the file `NAME.BIN` on the disk (`AUTOEXEC.BAS` loads it) | as <nobr>`--dsk-cpc`</nobr> |
| <nobr>`--dsk-pcw`</nobr> | the CP/M program `NAME.COM` on the disk | as <nobr>`--dsk-cpc`</nobr> |
| <nobr>`--mzf`</nobr> | the `.mzf` header | 16 characters, upper case |
| <nobr>`--cas-msx`</nobr> | the `.cas` header (`BLOAD "CAS:",R` loads any name) | 6 characters, up to the first dot |
| <nobr>`--tap-ace`</nobr> | the loader file: `0 0 BLOAD name` (the code file is always `code`) | 10 characters, up to the first dot |
| <nobr>`--kcc-kc85`</nobr> | the `.kcc` header | 8 characters, upper case, up to the first character that is not a letter or a digit |
| <nobr>`--z80-z1013`</nobr> | the header | 16 characters, up to the first dot |
| <nobr>`--cas-trs`</nobr> | the name on the tape (`SYSTEM`, then the name) | 6 characters, upper case, up to the first character that is not a letter or a digit |

Not used by `--bin`, `--hex`, `--prl`, `--plus3dos`, the snapshots (`--sna-48k` ...),
`--msx`, `--rom-msx`, `--p-zx81`, `--rom-sms`, `--rom-gg`, `--rom-coleco`, `--trs`, `--sna-cpc6128` and
`--sna-cpc464` (their files have no name).
`TAPE_BLOCK` blocks have their own names; `--name` is not used for them (see
[ZX Spectrum](machines/zx-spectrum.md#several-blocks-on-a-tape)).

## Errors

pypasmo reports **up to 10 errors** at once (Pasmo stops at the first one): a line with
an error is skipped and the assembly goes on. An error in a line that opens or closes a
block (`IF`/`ELSE`/`ENDIF`, `MACRO`/`ENDM`, `REPT`, `IRP`, `DUP`/`EDUP`, `PROC`/`ENDP`,
`STRUCT`/`ENDS`, `PHASE`/`DEPHASE`, `END`) stops at once, because the following errors
would only be its consequences. No output file is written when there is an error.

The messages are not word for word the same as Pasmo's.

## Warnings

Warnings go to the standard error output and do not stop the assembly; the output file is
written. `--werror` makes every warning an error (exit code 1). Warnings of pypasmo
include:

- "64KB limit passed": code that goes past FFFFh (for example `DS` with a negative size)
  wraps around to 0000h, like in Pasmo;
- "looks like a non existent instruction": parentheses taken as an expression where no
  indirection exists (`LD B,(5)`), like in Pasmo, see
  [Instructions](source-format.md#instructions);
- "not a 8080 instruction" with `--w8080`;
- `OUT (C),0` and `IN F,(C)` / `IN (C)`, which Pasmo does not know;
- a byte value outside -256..255 (Pasmo silently takes the low byte, so with `--werror`
  such a source fails in pypasmo, although Pasmo accepts it);
- `.WARNING text` in the source;
- tape loaders that can not work (a too low `CLEAR`, code in the ROM), see
  [ZX Spectrum](machines/zx-spectrum.md#warnings-of-the-tape-loaders);
- a `TAPE_BLOCK_SCREEN` without the whole picture;
- the ZX81 `.p` file with less than 256 bytes free under 8000h, see [ZX81](machines/zx81.md).

## Listing

`-d` and `--lst` print each line with its address, the generated bytes in memory order
(a 16 bit operand low byte first: `CD 6B 0D` is `CALL 0D6Bh`) and the source text (`+`
marks lines from macros, `REPT` and `IRP`). The **T-states** of an instruction are added
at the end of the line as a comment:

```
8000  CD 6B 0D            start:  call CLS  ;17T
800B  7E                  print:  ld a,(hl)       ; next character  ;7T
800E  28 04                       jr z,release  ;12/7T
```

`CALL` and `RST` show the time of the instruction itself, not of the called routine.
Two numbers: with the condition true / false (`JR cc`, `CALL cc`, `RET cc`, `DJNZ`), or
repeating / last time (`LDIR`, `CPIR`, ...). Contended memory and I/O of the ZX Spectrum
(slower access to 4000h-7FFFh) are not counted. The listing ends with the symbol table.

Inside `PHASE` the listing shows `$` (the address the code runs at), see
[PHASE](directives.md#phase--dephase). `.name` local labels appear with their full name
(`print.loop`).

### Routine totals *(pypasmo extension)*

For a simple routine the listing also gives the total: from a label to an unconditional
`RET` (`RETI`, `RETN`), when there is no jump, call, condition, repeating block
instruction (`LDIR` ...), `HALT`, data or `ORG`/`PHASE` in between (then the time does not
depend on the data). The total includes the `RET`, not the `CALL` of the routine (17T); a
label in the middle starts a new sum:

```
8013  B1                          or c  ;4T
8014  6F                          ld l,a  ;4T
8015  C9                          ret  ;10T
      ; scr_addr: 90T from the label to RET
```

## Symbol files

The third file is the **symbol table** in Pasmo format; it can be `INCLUDE`d in another
source:

```
start		EQU 08000H
```

Local symbols (LOCAL, macros, autolocal) appear as 8 digit hex numbers, as in Pasmo
(numbered from `00000000`). `DEFL` symbols and predefined symbols are not listed. The
fourth file gets only the symbols named in `PUBLIC` (with `--public` the third file does
that instead). `.name` local labels appear with their full name (`print.loop`).
