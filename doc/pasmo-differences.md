# Differences from Pasmo 0.5.5

Back to the [index](index.md).

This is the binding list of the deliberate differences between pypasmo and Pasmo 0.5.5.
Where nothing is said here, pypasmo behaves like Pasmo 0.5.5.

## Not supported

- output formats `--cmd` (CP/M-86) and `--sdrel` (object file for the SDCC linker);
- 8086 code generation (`--86`);
- `--pass3` (more passes run automatically when needed).

## Added (from the Pasmo 0.5.5.paged fork by Jouni Korhonen, not in Pasmo 0.5.5)

- directives `DG`, `DUP`/`EDUP`, `STRUCT`/`ENDS`, `BANK` and the output formats
  `--tap128`, `--tapbas128` (in pypasmo `--tap-128k`, `--tap-wloader-128k`, the fork names
  work too; see [Directives](directives.md#fork-directives-pasmo-055paged)). The six words
  are reserved, so a source that uses one of them as a label needs `--pasmo-syntax-055`;
- differences to the fork: `DG` takes any characters (the fork reads tokens, so register
  names confuse it), `STRUCT` allows fields without a label and any expression in `DB`,
  `--tap-128k` makes a separate block when one bank has code both at its fixed address and
  at C000h (the fork warns), `--tap-48k` and other formats do not check the ROM area;
  the `--tap-wloader-128k` loader pages bank 0 in at C000h before the start (the fork
  leaves the last loaded bank there, so code of bank 0 at C000h did not run) and ends with
  "0 OK" (the fork: `STOP`); `--tap-128k` gives an error when `BANK 5` / `BANK 2` at C000h
  and the code at 4000h / 8000h write the same byte;
  `--memmap` prints its own, shorter table (the fork dumps its internal page and bank
  structures).

## Different

- pypasmo also has `--lst` (listing to a file, with T-states also in `-d`), `--version`,
  the debug symbol files `--dbgsym-sld` / `--dbgsym-list` and many more output formats
  (marked *(pypasmo extension)* in [Output formats](output-formats.md));
- pypasmo reports up to 10 errors, Pasmo only the first one (see
  [Command line](command-line.md#errors));
- pypasmo also has the directives `PHASE`/`DEPHASE`, `ALIGN`, `ASSERT`, `DZ`, `DC`,
  `TAPE_BLOCK`, `TAPE_BLOCK_SCREEN`, `TAP_INCLUDE`, `DISPLAY`, `D_ZX81`, `D_ZX81I`,
  `DC_ZX81`, `ELSEIF`, `IFB`, `IFNB`, `BANK_OF`, default values of macro parameters and
  `INCBIN` with offset and length (see [Directives](directives.md#pypasmo-directives)).
  They are not reserved words, so Pasmo sources that use these names still assemble,
  except a line with the bare word as a label without colon (`--pasmo-syntax-055` turns
  the directives off). Every `INCBIN` line that Pasmo accepts means the same in pypasmo;
- labels starting with a dot are local labels (see
  [Local labels](source-format.md#local-labels-name-pypasmo-extension-like-sjasmplus)); in
  Pasmo they are normal names. Off with `--pasmo-syntax-055`;
- `OUT (C),0` and `IN F,(C)` are assembled with a warning;
- a number above FFFFh (`70000`, `12345h`) is an error, Pasmo silently truncates it;
- an extra warning that Pasmo does not give: a byte value outside -256..255 (Pasmo
  silently takes the low byte). With `--werror` such a source fails in pypasmo, although
  Pasmo accepts it;
- `INCLUDE` also searches the directory of the including file, `INCBIN` the directory
  of the main file (Pasmo: the current directory and `-I` directories only);
- `LD (HL),IXL` and similar (an index half register with `(HL)`) is an error, because
  the Z80 has no such instruction; Pasmo generates `FD 75`, which the CPU reads as
  `LD (IY+d),L` with the next byte as d. Also an error: an index half register with
  `H` / `L` (`LD IXH,H`; Pasmo generates `DD 64` = `LD IXH,IXH`) and a shift or bit
  instruction with a half register (`SLA IXH`; Pasmo generates the incomplete `DD CB 24`);
- forms that Pasmo rejects but that mean one instruction only are accepted:
  `ADD B` = `ADD A,B` (also `ADC`, `SBC`), `SUB A,B` = `SUB B` (also `AND`, `OR`, `XOR`,
  `CP`), `EX AF,AF` = `EX AF,AF'`;
- a macro parameter written twice (`m MACRO x, x`) is an error; Pasmo silently uses the
  first one;
- `JR` / `DJNZ` may jump across the 64 KB boundary like the Z80 does (`JR 5` at
  0FFF0h gives `18 13`); Pasmo reports it as out of range;
- a single character >= 80h used as a number, see [Strings](source-format.md#strings);
- the offset of `(IX±...)` / `(IY±...)` is computed from left to right: `(IX-12+13)`
  is `IX+1`. Pasmo computes `IX-(12+13)` = `IX-25` (a bug, fixed the same way in the
  0.5.5.paged fork by Jouni Korhonen). The range is -128..255 like in Pasmo;
- with `--tap-48k`, `--cdt` and the other tape / disk formats, code that fills the whole
  64 KB is an error (Pasmo writes a header with length 0); `--bin` and `--hex` write all
  of it (Pasmo writes an empty file / only the end record);
- a source without code gives an empty `--bin` file (Pasmo writes 2 zero bytes); `--trs`
  writes only the transfer record (Pasmo also a load record of 2 bytes at FFFFh);
  `--tap-48k`, `--tap-wloader-48k`, `--tzx-48k`, `--tzx-wloader-48k` and `--plus3dos`
  write an empty CODE file at 0000h (Pasmo 2 bytes at FFFFh, its loader does CLEAR 65534);
- options may also come after the file names (Pasmo takes everything after the first file
  name as a file name, `a.asm a.bin -d` writes the symbols to a file `-d`); `-1` (debug
  output of all passes in Pasmo) is ignored;
- a few things that Pasmo rejects are accepted: a forward reference in `IM` / `RST`,
  `##` that pastes a parameter onto a word in a macro (`lbl##p:`), a label before `ENDM`;
- the number of passes is not limited to 3;
- the messages are not word for word the same as Pasmo's.

## The same as in Pasmo, maybe surprising

- `( )` around an operand means memory where the instruction has a memory form:
  `LD A,(5)` loads from address 5, and `LD A,(1)+2` or `LD HL,(5)*2` is an error. Where
  no memory form exists, `( )` only groups: `JR (label)`, `CALL (5)`, `RST (8)`,
  `LD B,(1)+2`, `CP (1+2)*3` (`LD B,(5)` and `ADD A,(5)` give the warning "looks like a
  non existent instruction"). To be sure, write `0+(...)` for a value.
- values that the assembler needs at once (`ORG`, `DS`, `ALIGN`, `IF`, `REPT`, `BANK`,
  `PHASE`, the offset and length of `INCBIN`) must be defined above the line; a label
  defined later is an error ("undefined symbol"), see
  [Forward references](source-format.md#forward-references). Instructions and `DB` / `DW`
  may use labels defined later; `DISPLAY` and `TAPE_BLOCK` (pypasmo) too.
- `REPT` and `IRP` have one `LOCAL` level for all repetitions, so a `LOCAL` label inside
  them is defined twice (an error); use a macro with `LOCAL` instead. Local symbols are
  numbered from `00000000` in the symbol file.

## Other notes

- `&X` is binary, as the Pasmo 0.5.5 code does, although its documentation says
  hexadecimal (see [Numbers](source-format.md#numbers)).
- `.8080` is an error "8080 mode not supported", the same as in Pasmo 0.5.5.
- The new features of the development snapshot Pasmo 0.6.0.20070113 (`IF1`, `IF2`,
  `IRPC`, segments, REL files, 8080 syntax) are not in pypasmo, see the
  [index](index.md#origin).
