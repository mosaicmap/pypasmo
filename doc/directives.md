# Directives

Back to the [index](index.md).

pypasmo has three groups of directives: those of Pasmo 0.5.5, those of the 0.5.5.paged
fork by Jouni Korhonen, and its own *(pypasmo extension)*, taken from MACRO-80 and
sjasmplus.

- [Quick reference](#quick-reference)
- [Pasmo 0.5.5 directives](#pasmo-055-directives)
- [Fork directives (Pasmo 0.5.5.paged)](#fork-directives-pasmo-055paged)
- [pypasmo directives](#pypasmo-directives)
- [Macros](#macros)

## Quick reference

All directives by what they are for; the last column links to the full description.

| Directive | What it does | From |
|---|---|---|
| **Addresses and memory** | | |
| `ORG` | set the address of the following code | [Pasmo](#pasmo-055-directives) |
| `PHASE` / `DEPHASE` | code that runs at another address than where it is loaded | [pypasmo](#phase--dephase) |
| `ALIGN` | go on at the next multiple of n | [pypasmo](#pypasmo-directives) |
| `DS`, `DEFS` | n bytes, filled or only skipped | [Pasmo](#pasmo-055-directives) |
| `BANK` | the following code goes into a RAM bank of the ZX Spectrum 128K | [fork](#bank-zx-spectrum-128k) |
| **Data** | | |
| `DB`, `DEFB`, `DEFM` | bytes and strings | [Pasmo](#pasmo-055-directives) |
| `DW`, `DEFW` | words (16 bits, low byte first) | [Pasmo](#pasmo-055-directives) |
| `DZ`, `DC` | strings ending with a zero byte / with bit 7 set in the last character | [pypasmo](#pypasmo-directives) |
| `DG` | bytes written as bit patterns (`DG --XXXX--`) | [fork](#fork-directives-pasmo-055paged) |
| `D_ZX81`, `D_ZX81I`, `DC_ZX81` | strings in the ZX81 character set | [pypasmo](#pypasmo-directives) |
| `STRUCT` / `ENDS` | offsets of the fields of a record | [fork](#struct) |
| **Symbols** | | |
| `EQU` | a constant | [Pasmo](#pasmo-055-directives) |
| `DEFL` | a variable (can be set again) | [Pasmo](#pasmo-055-directives) |
| `PROC` / `ENDP`, `LOCAL` | local names | [Pasmo](#pasmo-055-directives) |
| `PUBLIC` | names for the public symbol file | [Pasmo](#pasmo-055-directives) |
| `BANK_OF` | the 128K bank of a label (an operator in expressions) | [pypasmo](#bank_of-pypasmo-extension) |
| **Files** | | |
| `INCLUDE` | another source file | [Pasmo](#pasmo-055-directives) |
| `INCBIN` | a binary file, or a part of it | [Pasmo, pypasmo](#incbin-with-offset-and-length) |
| `END` | the end of the source and the entry point | [Pasmo](#pasmo-055-directives) |
| **Conditions** | | |
| `IF` / `ELSE` / `ENDIF` | conditional assembly | [Pasmo](#pasmo-055-directives) |
| `ELSEIF` | another condition between `IF` and `ELSE` | [pypasmo](#pypasmo-directives) |
| `IFDEF`, `IFNDEF` | is a symbol defined | [Pasmo](#pasmo-055-directives) |
| `IFB`, `IFNB` | is a macro argument blank | [pypasmo](#macros) |
| **Repeating and macros** | | |
| `REPT` / `ENDM`, `DUP` / `EDUP` | repeat a block n times | [Pasmo](#pasmo-055-directives), [fork](#fork-directives-pasmo-055paged) |
| `IRP` / `ENDM` | repeat a block for each value | [Pasmo](#pasmo-055-directives) |
| `MACRO` / `ENDM`, `EXITM`, `.SHIFT` | macros | [Pasmo](#macros) |
| **Messages and checks** | | |
| `.ERROR`, `.WARNING` | an error / a warning with a text | [Pasmo](#pasmo-055-directives) |
| `ASSERT` | an error when a condition is false | [pypasmo](#pypasmo-directives) |
| `DISPLAY` | print texts and values while assembling | [pypasmo](#pypasmo-directives) |
| **ZX Spectrum tapes** | | |
| `TAPE_BLOCK` | a block of the code on the tape | [pypasmo](machines/zx-spectrum.md#tape_block) |
| `TAPE_BLOCK_SCREEN` | a loading screen on the tape | [pypasmo](machines/zx-spectrum.md#tape_block_screen) |
| `TAP_INCLUDE` | the blocks of a ready `.tap` file | [pypasmo](machines/zx-spectrum.md#tap_include) |
| **Other** | | |
| `.Z80`, `.8080` | accepted / an error (no 8080 mode) | [Pasmo](#pasmo-055-directives) |

## Pasmo 0.5.5 directives

| Directive | Description |
|---|---|
| `ORG address` | set the assembly address |
| `name EQU expr` | constant; can not be redefined; may refer to later symbols |
| `name DEFL expr` | variable; can be redefined |
| `DB`, `DEFB`, `DEFM` | bytes and strings; `?` only skips a byte |
| `DW`, `DEFW` | words (low byte first) |
| `DS`, `DEFS n[,fill]` | n bytes (fill 0); `DS n,?` only reserves space |
| `INCLUDE file` | include source; name in `"..."`, `'...'` or up to a blank; nothing may follow |
| `INCBIN file` | include a binary file (pypasmo: also a part of it, see [INCBIN](#incbin-with-offset-and-length)) |
| `IF expr` / `ELSE` / `ENDIF` | conditional assembly, can be nested |
| `IFDEF x`, `IFNDEF x` | short for `IF DEFINED x` / `IF ! DEFINED x` |
| `END [address]` | end of the source, the rest of the file is ignored; address = entry point |
| `PROC` / `ENDP` | a block for `LOCAL` |
| `LOCAL a, b` | local names in PROC, MACRO, REPT or IRP |
| `MACRO` / `ENDM` / `EXITM` / `.SHIFT` | macros, see [Macros](#macros) |
| `REPT n[, counter[, start[, step]]]` | repeat a block; `REPT -1` = until `EXITM` (at most 65535 times) |
| `IRP param, a, b, c` | repeat a block for each value |
| `.ERROR text`, `.WARNING text` | error / warning (only in an active IF branch) |
| `PUBLIC a, b` | names for the public symbol file |
| `.Z80` | accepted, does nothing |
| `.8080` | error "8080 mode not supported" (the same as in Pasmo 0.5.5) |

### Files

Files are searched in the current directory, then in one more directory, then in the
`-I` directories. The one more directory is that of the file with the directive for
`INCLUDE`, and that of the main source file for `INCBIN`, `TAP_INCLUDE` and the picture of
`TAPE_BLOCK_SCREEN`. (Pasmo: the current directory and the `-I` directories only, see
[Differences](pasmo-differences.md#different).)

### The 64 KB limit

Code that goes past FFFFh (for example `DS` with a negative size) wraps around to 0000h
with the warning "64KB limit passed", like in Pasmo. Use `--werror` to make it an error.

## Fork directives (Pasmo 0.5.5.paged)

Directives from the Pasmo 0.5.5.paged fork (by Jouni Korhonen), **not in Pasmo 0.5.5**:

| Directive | Description |
|---|---|
| `DG pattern` | bit pattern from the Zeus assembler, 8 characters per byte: `.` `-` `_` are 0, any other character is 1, spaces are ignored, may be in quotes: `DG --XXXX--` = 3Ch, `DG "X.X.X.X."` = AAh |
| `DUP n` / `EDUP` | the same as `REPT n` / `ENDM` (from sjasm) |
| `STRUCT name` / `ENDS` | defines offsets, no code, see [STRUCT](#struct) |
| `BANK n` | the code at C000h-FFFFh goes to RAM bank n (0..7) of the ZX Spectrum 128K, see [BANK](#bank-zx-spectrum-128k) |

These six words are reserved in pypasmo (as in the fork), so they can not be used as
labels; with `--pasmo-syntax-055` they are normal names and the directives are off.

### STRUCT

```
        STRUCT obj           ; obj.x = 0, obj.y = 1, obj.speed = 2, obj.name = 4
x       DB 0
y       DB 0
speed   DW 0
name    DS 8
        ENDS                 ; obj = 12 (the size)

        ld a,(ix+obj.speed)
        ld de,obj            ; size of one object
table:  DS 10*obj
```

Inside `STRUCT` only `DB`/`DEFB`/`DEFM`, `DW`/`DEFW` and `DS`/`DEFS` are allowed; their
values are ignored, only the size counts. The labels become `name.label` (constants like
`EQU`), `name` is the size. A field without a label is padding. STRUCTs can not be nested.

### BANK (ZX Spectrum 128K)

The 128K has eight 16 KB RAM banks: bank 5 is always at 4000h, bank 2 at 8000h and
C000h-FFFFh shows one of the banks 0..7 (port 7FFDh). `BANK n` says that the following code
at C000h-FFFFh belongs to bank n (`BANK 0` = normal memory, the default). `BANK` does not
change the address, write `ORG 0C000h` after it:

```
        org 8000h            ; main program (bank 2)
        ...
        bank 1
        org 0C000h           ; data in bank 1
level1: ...
        bank 3
        org 0C000h           ; data in bank 3
level2: ...
```

- Code at 0000h-3FFFh is an error (ROM); banked code with other formats than the 128K
  ones is an error.
- The output formats for banked code (`--tap-128k`, `--tap-wloader-128k`, `--tzx-128k`,
  `--tzx-wloader-128k`, `--pzx-128k`, `--pzx-wloader-128k`, `--sna-128k`, `--z80-128k`,
  `--dbgsym-sld`) and the 128K loader are described in
  [ZX Spectrum 128K and +3](machines/zx-spectrum-128k.md#spectrum-128k).

### `BANK_OF` *(pypasmo extension)*

`BANK_OF label` (or `BANK_OF(label)`) gives the bank of a label, so the bank numbers are
not written by hand twice:

```
        ld a, BANK_OF level2     ; 3
        call page_in             ; your routine: bank A at C000h (port 7FFDh, BANKM)
        ld hl, level2
```

- The bank of `BANK n` for a label at C000h-FFFFh (0 without `BANK`), 5 at 4000h-7FFFh,
  2 at 8000h-BFFFh; with `PHASE` the load address counts (where the bytes are).
- Labels defined later can be used. An `EQU` symbol or a label at 0000h-3FFFh is an error.
- Not a reserved word: `BANK_OF` alone is a normal name; off with `--pasmo-syntax-055`.

## pypasmo directives

Directives of pypasmo, **not in Pasmo 0.5.5** (from MACRO-80 and sjasmplus):

| Directive | Description |
|---|---|
| `PHASE address` / `DEPHASE` | assemble code for another address than where it is loaded, see [PHASE](#phase--dephase) (also `.PHASE` / `.DEPHASE`) |
| `ALIGN n[,byte]` | `$` to the next multiple of n (a power of 2: 2, 4, ... 32768); the bytes are filled with byte, without it they are only skipped like `DS n,?` |
| `ASSERT expr[,"message"]` | error "ASSERT failed" if expr is 0 (false); checked in the final pass, so it may use labels defined later |
| `INCBIN file,offset[,length]` | only a part of the file, see [INCBIN](#incbin-with-offset-and-length) |
| `DZ` | like `DB`, with a zero byte at the end: `DZ "kip"` = `DB "kip",0` |
| `DC` | like `DB`, bit 7 set in the last character of each string (as in the ZX Spectrum ROM): `DC "Hello",13` = `48 65 6C 6C EF 0D`; one character in apostrophes is a number (`DC 'A'` = 41h, `DC "A"` = C1h), as in sjasmplus |
| `D_ZX81` | like `DB`, the strings in the ZX81 character set, see [ZX81](machines/zx81.md#the-zx81-character-set): `D_ZX81 "Hi", 76h` = `2D AE 76` |
| `D_ZX81I` | the same, all inverse except lower case letters: `D_ZX81I "Hi 1"` = `AD 2E 80 9D` |
| `DC_ZX81` | like `D_ZX81`, bit 7 (inverse) in the last character of each string, as in the keyword table of the ZX81 ROM: `DC_ZX81 "RUN"` = `37 3A B3`; an inverse character before the end is an error |
| `TAPE_BLOCK "name",start,length` | a CODE block of the assembled code on the tape (<nobr>`--tap-48k`</nobr>, <nobr>`--tap-wloader-48k`</nobr>, <nobr>`--tzx-48k`</nobr>, <nobr>`--tzx-wloader-48k`</nobr>, <nobr>`--pzx-48k`</nobr>, <nobr>`--pzx-wloader-48k`</nobr>), see [ZX Spectrum](machines/zx-spectrum.md#several-blocks-on-a-tape) |
| `TAPE_BLOCK_SCREEN "name"[,"file"]` | the screen 4000h-5AFFh (6912 bytes) as a block for `LOAD "" SCREEN$`; with a file the picture is put there first, see [ZX Spectrum](machines/zx-spectrum.md#several-blocks-on-a-tape) |
| `TAP_INCLUDE file` | the blocks of a `.tap` file unchanged on the tape (e.g. an own Basic loader), see [ZX Spectrum](machines/zx-spectrum.md#several-blocks-on-a-tape) |
| `DISPLAY "text", expr, ...` | print texts and values (decimal and hex) to the standard output in the last pass, so labels defined later can be used: `DISPLAY "free: ", 0FFFFh-$` gives `free: 4660 (1234h)` (like sjasmplus) |
| `ELSEIF expr` | between `IF` and `ELSE` / `ENDIF`: the code of the first true condition is assembled, `ELSE` when none is true (like MASM, sjasmplus); as in `IF`, the symbols must be defined before; `ELSEIF` after `ELSE` is an error: `IF n = 1` … `ELSEIF n = 2` … `ELSE` … `ENDIF` |
| `IFB text` / `IFNB text` | conditional assembly: is the text (a macro argument) blank / not blank; also `IFB <text>` (like MASM), see [Macros](#macros) |
| `BANK_OF label` | an operator in expressions, see [BANK_OF](#bank_of-pypasmo-extension) |

Also from pypasmo: default values of macro parameters ([Macros](#macros)) and the local
labels `.name` ([Source format](source-format.md#local-labels-name-pypasmo-extension-like-sjasmplus)).

### Not reserved words

These words are **not reserved**: a source for Pasmo that uses them as labels or macro
names still assembles. `align: db 1`, `align equ 4`, `align nop` (a label without colon
before an instruction) define a label, a macro named `align` is called instead of the
directive. Only a line with the bare word (`phase` as a label without colon and nothing
after it) is read as the directive; `--pasmo-syntax-055` turns all of them off.

`--pasmo-syntax-055` turns off all pypasmo directives, the default values of macro
parameters, the `INCBIN` offset, the `.name` local labels and the fork directives `DG`,
`DUP`, `EDUP`, `STRUCT`, `ENDS`, `BANK`; their names are normal identifiers then (see
[Command line](command-line.md#options)).

### PHASE / DEPHASE

For code that the program copies to another address before it runs there (an interrupt
routine, code moved out of the way of loaded data, ...). `ORG` would change both the
address of the labels and the place where the bytes go. Inside `PHASE` the labels and `$`
count from the given address, but the bytes go on after the previous code; `DEPHASE`
continues after them:

```
        org 8000h
start:  ld hl,copy          ; copy from (800Eh) ...
        ld de,routine       ; ... to FE00h
        ld bc,end-routine
        ldir
        jp routine
copy:
        phase 0FE00h
routine: ld a,(data)        ; 3A 08 FE: data is FE08h
        inc a
        ld (data),a
        ret
data:   db 0
end:
        dephase             ; $ = 8017h again
```

- A label on the `PHASE` line gets the new address (like on `ORG`); the load address is
  the label before it (`copy`).
- The listing shows `$` (the address the code runs at), like MACRO-80; the `PHASE` and
  `DEPHASE` lines show the load address.
- `BANK` takes the load address: code loaded at C000h-FFFFh goes to the bank.
- Errors: `PHASE` inside `PHASE`, `ORG` inside `PHASE`, `DEPHASE` without `PHASE`,
  `PHASE` without `DEPHASE` at the end of the source.

### INCBIN with offset and length

`INCBIN file,offset[,length]` includes only a part of the file: from offset (counted from
0), length bytes (default: to the end). The file name is read as in Pasmo (unquoted: up to
a blank), so the comma goes after quotes or a blank: `INCBIN "a.scr",6144`,
`INCBIN a.scr, 6144` (`INCBIN a.scr,6144` is the file `a.scr,6144`, as in Pasmo). Every
`INCBIN` line that Pasmo accepts means the same in pypasmo.

## Macros

```
set_reg MACRO reg, value        ; or:  MACRO set_reg, reg, value
        LD reg, value
        ENDM

        set_reg a, 5            ; -> LD a, 5
```

- A missing argument is empty (test it with `IF NUL param`, or `IFB param`). Extra
  arguments can be reached with `.SHIFT`.
- *(pypasmo extension)* A parameter can have a default value, used when the argument
  is missing or empty: `fill MACRO val, n=2, reg=a` - `fill 5` is `fill 5, 2, a`,
  `fill 9, , b` is `fill 9, 2, b`. The default is text up to the next comma (commas in
  strings and brackets do not count), like an argument.
- *(pypasmo extension)* `IFB param` / `IFNB param` (`IFB <param>`, like MASM): assemble
  the following lines if the argument is blank / not blank, with `ELSE` and `ENDIF` as
  `IF`. A parameter with a default value is not blank.
- `EXITM` ends the macro expansion, or ends a `REPT` / `IRP` early.
- `ENDM` also closes unterminated `IF`s inside the macro.
- `##` joins identifiers (`lbl##n`).
- Parameters of an outer macro are replaced inside `REPT` and `IRP` too.
- Inside a macro, `.name` local labels are local to each expansion (like `LOCAL`).
- A macro parameter written twice (`m MACRO x, x`) is an error (Pasmo silently uses the
  first one).
