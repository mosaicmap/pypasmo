# Source format

Back to the [index](index.md).

pypasmo reads the source format of Pasmo 0.5.5: one statement per line, labels, Z80
instructions, directives and comments, as in most Z80 assemblers. This page describes the
parts of a line, numbers, strings, expressions and labels; the directives (`ORG`, `DB`,
`MACRO` ...) are in [Directives](directives.md).

- [An example](#an-example)
- [Lines, comments, labels](#lines-comments-labels)
- [Identifiers](#identifiers)
- [Numbers](#numbers)
- [Strings](#strings)
- [Expressions](#expressions)
- [Forward references](#forward-references)
- [Local labels](#local-labels)
- [Instructions](#instructions)
- [More examples](#more-examples)

## An example

`hello.asm` prints a text on the ZX Spectrum and returns to Basic:

```
; hello.asm: prints a text on the ZX Spectrum and returns to Basic
CLS     equ 0D6Bh           ; ROM routine: clear the screen
OPEN    equ 1601h           ; ROM routine: open the channel in A

        org 8000h           ; the code starts at 8000h
start:  call CLS            ; a label with a colon
        ld a,2              ; channel 2 = the upper screen
        call OPEN
        ld hl,text          ; text is defined below: fine in an instruction
.next:  ld a,(hl)           ; a local label, its full name is start.next
        or a
        ret z               ; 0 = the end of the text: back to Basic
        rst 10h             ; ROM: print the character in A
        inc hl
        jr .next
text    db "Hello!", 13, 0  ; a label without a colon; a string, 13 = ENTER
        end start           ; the end of the source and the entry point
```

- `CLS` and `OPEN` are constants (`EQU`), `start`, `.next` and `text` are labels: their
  value is the address of their line. See [Lines, comments, labels](#lines-comments-labels).
- `0D6Bh` is a hexadecimal number (it starts with a digit, else it would be a name), `13`
  a decimal one: [Numbers](#numbers).
- `"Hello!"` in `DB` gives the bytes of the text: [Strings](#strings).
- `.next` belongs to `start`, so another routine can have its own `.next`:
  [Local labels](#local-labels).
- `END start` ends the source (the lines after it are not read) and gives the entry point,
  which the tape loaders and snapshots use.

Assemble it to a ZX Spectrum snapshot, with a listing that shows the address and the
bytes of each line:

```
python -m pypasmo --sna-48k --lst hello.lst hello.asm hello.sna
```

The listing begins:

```
0D6B                      CLS     equ 0D6Bh           ; ROM routine: clear the screen
1601                      OPEN    equ 1601h           ; ROM routine: open the channel in A

8000                              org 8000h           ; the code starts at 8000h
8000  CD 6B 0D            start:  call CLS            ; a label with a colon  ;17T
8003  3E 02                       ld a,2              ; channel 2 = the upper screen  ;7T
```

More examples are at the [end of this page](#more-examples).

## Lines, comments, labels

- A line has the form `[label[:]] [instruction or directive [operands]] [; comment]`;
  every part may be missing, so a line can be empty, a comment only or a label only. There
  is one statement on a line.
- A **comment** starts with `;` and goes to the end of the line (outside of strings).
- **Lines** end with LF or CR LF (as in Pasmo; other control characters are not line
  ends). A line may start with a decimal line number followed by a space (from old
  assemblers); it is ignored, before any statement (`10 org 8000h`, `20 include x.asm`).
- A **label** may end with a colon, but does not have to. A word is a label if it is not
  an instruction, a directive or a macro name; the indentation does not matter, also an
  instruction or a directive may start in the first column:
  ```
  start   ld a,1
          loop: djnz loop
  org 9000h
  ret
  ```
- The value of a label is the address of its line (`$`). A label on an `EQU` line gets
  the value of the expression instead (`size equ 10`), on a `DEFL` line too, but it can be
  defined again (`n defl n+1`).
- A label on an `ORG` line gets the new address (`start org 100h` → start = 100h).
- `INCLUDE file` reads another source file at this place. `END` ends the whole source:
  the lines after it are not read (`END` in an included file ends the main file too, as
  in Pasmo).

## Identifiers

- **Identifiers** start with a letter, `_`, `?`, `@` or `.` and continue with letters,
  digits and `_ ? @ . $`.
- They are case sensitive unless `--nocase` is used.
- Mnemonics, registers, conditions and directives are reserved words in any case. The
  pypasmo directives are an exception, they are not reserved, see
  [Directives](directives.md#not-reserved-words).
- **`$` inside an identifier is removed, but only after the reserved word check.**
  So `h$l` is a valid label named `hl`, not the register HL.
- A name starting with a dot is a local label in pypasmo, see
  [below](#local-labels-name-pypasmo-extension-like-sjasmplus).

## Numbers

| Form | Base |
|---|---|
| `123`, `123D` | decimal |
| `0FFh`, `0x1F`, `$1F`, `#1F`, `&1F`, `&H1F` | hexadecimal (`FFh` is an identifier, write `0FFh`) |
| `%1010`, `1010B`, `&X1010` | binary |
| `17O`, `17Q`, `&O17` | octal |

`$` can be used between digits for readability (`%1111$0000`). A number above FFFFh is an
error. (Pasmo silently truncates a number that starts with a digit, like `70000` or
`12345h`, to 16 bits; with a prefix `$ # & %` it is an error in Pasmo too.)

`&X` is binary: that is what the Pasmo 0.5.5 code does, although its documentation says
hexadecimal.

## Strings

- `'...'`: no escapes, a quote is written twice (`'It''s'`).
- `"..."`: C style escapes `\n \r \t \a \\ \xHH \ooo`; any other character after `\` is
  taken as it is (`\"`, `\'`), `\x` without digits is 0 (as in Pasmo).
- A string of 1 or 2 characters can be used as a number: `'A'+80h`, `'AB'` = 4241h
  (the first character is the low byte). A single character with a code of 80h or more
  is 00xxh (`'é'` in a Latin-1 file = 00E9h); in Pasmo it depends on the C compiler,
  the Windows build gives FFE9h. In `DB` it is E9h in both.
- Source files are read **as bytes**, like Pasmo does: the text of a string goes to the
  output byte for byte, so `DB "é"` in a UTF-8 file gives C3h A9h, in a Latin-1 or
  CP1250 file one byte. The listing keeps the bytes of the source too.

## Expressions

All values are 16 bit unsigned, calculated modulo 10000h. True is FFFFh, false is 0.
`$` is the address of the start of the current instruction or directive.

The precedence is **exactly as in Pasmo**, from the highest:

| Level | Operators |
|---|---|
| 1 | `( )`, numbers, symbols, `$`, `DEFINED x`, `NUL ...` |
| 2 | `*` `/` `MOD` `%` `SHL` `<<` `SHR` `>>` |
| 3 | `+` `-` (binary) |
| 4 | `EQ =` `NE !=` `LT <` `LE <=` `GT >` `GE >=` |
| 5 | `NOT ~` `!` and unary `+` `-` |
| 6 | `AND &` |
| 7 | `OR \|` `XOR` |
| 8 | `&&` |
| 9 | `\|\|` |
| 10 | `HIGH` `LOW` |
| 11 | `condition ? a : b` |

Two consequences of Pasmo's rules that pypasmo keeps:
- `-1+2` is `-(1+2)` = FFFDh, because unary minus binds looser than `+`.
- `HIGH x+1` is `HIGH(x+1)`.

A unary operator can not follow a binary one (`2*-1` is an error, as in Pasmo 0.5.5).

`&&`, `||` and `?:` are short circuit: the part that is not evaluated may contain undefined
symbols or a division by zero.

`NUL` is true if nothing follows it on the line (used in macros: `IF NUL param`).

`BANK_OF label` or `BANK_OF(label)` *(pypasmo extension)* is the ZX Spectrum 128K RAM bank
of a label, see [BANK_OF](directives.md#bank_of-pypasmo-extension).

## Forward references

An instruction or `DB` / `DW` may use a label that is defined later:

```
        jp start        ; fine: start is defined below
        ...
start:  ld a,1
```

A value that decides **where the code goes or how much of it there is** must be known when
the line is read, so its symbols must be defined above the line (the same as in Pasmo):
`ORG`, `DS`, `ALIGN`, `IF` / `ELSEIF`, `REPT`, `DUP`, `BANK`, `PHASE` and the offset and
length of `INCBIN`. A label defined later gives "undefined symbol":

```
        ds size         ; error: size is defined below
size    equ 10
```

Put such `EQU`s at the start of the source (or in an `INCLUDE`d file). `ASSERT`,
`DISPLAY` and `TAPE_BLOCK` *(pypasmo)* take their values at the end, so they may use any
label.

## Local labels

Three kinds of local names:

| Kind | Scope | Where |
|---|---|---|
| `LOCAL a, b` | the `PROC`, `MACRO`, `REPT` or `IRP` block | [Directives](directives.md#pasmo-055-directives) |
| `_name` with <nobr>`--alocal`</nobr> | up to the next normal label | [below](#autolocal-mode---alocal) |
| `.name` *(pypasmo extension)* | belongs to the previous normal label | [below](#local-labels-name-pypasmo-extension-like-sjasmplus) |

`REPT` and `IRP` have one `LOCAL` level for all repetitions, so a `LOCAL` label inside
them is defined twice (an error); use a macro with `LOCAL` instead (the same as in Pasmo).

### Autolocal mode (`--alocal`)

Labels starting with `_` are local to a block. The block ends at the next normal label
(also EQU or DEFL) and at `PROC`, `ENDP`, `LOCAL`, `MACRO` and at the end of a macro
expansion.

### Local labels `.name` *(pypasmo extension, like sjasmplus)*

A label starting with a dot belongs to the previous normal label; its full name is
`label.name`, so the same `.loop` can be used in each routine:

```
print:  ld a,(hl)
.loop:  rst 10h             ; print.loop
        djnz .loop
        ret
clear:  ld b,0
.loop:  djnz .loop          ; clear.loop
        jp print.loop       ; from elsewhere: the full name
```

- Only address labels start a new scope; `EQU` / `DEFL` symbols, `LOCAL` and autolocal
  labels do not. Before the first label `.name` is a normal name.
- Inside a macro, `.name` is local to each expansion (like `LOCAL`), so a macro with a
  `.loop` can be used many times.
- The symbol file and the listing show the full names (`print.loop`).
- In Pasmo 0.5.5 `.name` is a normal global name. A Pasmo source that uses such a name
  in two routines gets the error "undefined symbol" in pypasmo, never different code;
  `--pasmo-syntax-055` turns local labels off.

## Instructions

- The whole documented Z80 instruction set including IX/IY and `(IX+d)`.
- Undocumented `IXH IXL IYH IYL` and `SLL`, as in Pasmo.
- **pypasmo extensions:** `OUT (C),0` (ED 71) and `IN F,(C)` / `IN (C)` (ED 70). Pasmo does
  not know them, so pypasmo prints a warning. For portable code use `DB 0EDh,71h`.
- Invalid combinations (`LD H,IXL`, `ADD IX,IY`, `EX DE,IX`, `JP (IX+d)`, ...) are errors.
- Indirection is written with `( )` or `[ ]`: `LD A,(1234h)`, `LD A,[1234h]`.
- Like Pasmo: where an indirection does not exist, parentheses are taken as an expression
  with the warning "looks like a non existent instruction" (`LD B,(5)` is `LD B,5`,
  `OR (2)` is `OR 2`). With `--bracket` this never happens.
- `--w8080` warns "not a 8080 instruction" for everything with a CB, DD, ED or FD prefix and
  for `EX AF,AF'`, `EXX`, `JR` and `DJNZ`.
- The offset of `(IX±...)` / `(IY±...)` is computed from left to right: `(IX-12+13)` is
  `IX+1` (the range is -128..255 like in Pasmo). Pasmo computes `IX-(12+13)`, see
  [Differences](pasmo-differences.md#different).
- `.Z80` is accepted and does nothing; `.8080` is the error "8080 mode not supported"
  (the same as in Pasmo 0.5.5).

Some instruction forms differ from Pasmo (accepted shorter forms, rejected forms that the
Z80 does not have); they are listed in [Differences from Pasmo 0.5.5](pasmo-differences.md).

## More examples

Complete programs, each with the commands to assemble it in its header (the ready output
files are in the folder `..._results` next to it):

| Source | Machine | Shows |
|---|---|---|
| [hello_spectrum.asm](../tests/output_formats/zx_spectrum/hello_spectrum.asm) | ZX Spectrum 48K | ROM calls, a loop, waiting for a key, back to Basic |
| [hello_spectrum128.asm](../tests/output_formats/zx_spectrum/hello_spectrum128.asm) | ZX Spectrum 128K | `BANK`, `BANK_OF`, paging the RAM banks |
| [hello_zx81.asm](../tests/output_formats/zx81/hello_zx81.asm) | ZX81 | `D_ZX81` texts in the ZX81 character set |
| [hello_cpc.asm](../tests/output_formats/cpc/hello_cpc.asm) | Amstrad CPC | firmware calls |
| [hello_msx.asm](../tests/output_formats/msx/hello_msx.asm), [hello_msx_rom.asm](../tests/output_formats/msx/hello_msx_rom.asm) | MSX | a `BLOAD` program, a cartridge ROM with its header |
| [tests/output_formats/other/](../tests/output_formats/other/) | Sega, TRS-80, Robotron, Jupiter Ace | the other machines |

The test files of Pasmo 0.5.5 in
[tests/pasmo_0.5.5_original_tests/](../tests/pasmo_0.5.5_original_tests/) show the rest of
the syntax: `all.asm` has every Z80 instruction, others show macros, `PROC` / `LOCAL`,
`IF`, `REPT` and the directives.
