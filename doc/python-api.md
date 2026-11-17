# Using it from Python

Back to the [index](index.md).

pypasmo is a normal Python package (`import pypasmo`); the command line is only a thin
layer over it. From Python a build script, a test or a tool can assemble a source, look at
the symbols and the bytes, and write any of the output files, without a temporary file or
a subprocess. *(early version)*: the names below are used by the tests and the tools of
pypasmo, but they may still change before version 1.0.

- [Assemble a source and write a tape](#assemble-a-source-and-write-a-tape)
- [Assemble a file with options](#assemble-a-file-with-options)
- [Errors and warnings](#errors-and-warnings)
- [The result](#the-result)
- [Output formats](#output-formats)
- [Running the command line](#running-the-command-line)
- [Reference](#reference)

## Assemble a source and write a tape

```python
import pypasmo

source = """
        org 8000h
start:  ld a,2
        call 1601h      ; ROM: open channel 2 (the upper screen)
        ld a,'A'
        rst 10h         ; ROM: print the character in A
        ret
        end start
"""

asm = pypasmo.assemble_text(source)
print(hex(asm.entry), asm.symbols)                  # 0x8000 {'start': 32768}

tap = pypasmo.output_bytes(asm, "tapbas", "hello")  # the same as --tap-wloader-48k
with open("hello.tap", "wb") as f:
    f.write(tap)
```

`assemble_text` takes the source as a string; `INCLUDE` and `INCBIN` look for their files
in the current directory then. `output_bytes` gives the bytes of one output file, here a
tape with the Basic loader; the third argument is the name in the tape header (`--name`).

## Assemble a file with options

`Assembler` takes the command line options as arguments; `assemble` reads the file (and
its `INCLUDE` files):

```python
import pypasmo

asm = pypasmo.Assembler(include_dirs=["inc"], predefined={"DEBUG": 1})
asm.assemble("game.asm")            # -I inc -E DEBUG=1 game.asm
with open("game.sna", "wb") as f:
    f.write(pypasmo.output_bytes(asm, "sna-48k", "game"))
with open("game.lst", "w") as f:
    f.write(pypasmo.listing_text(asm))
```

The arguments (all optional) and their options: `nocase` = `--nocase`, `include_dirs` =
`-I`, `predefined` = `-E` (a dict name: value), `bracket` = `--bracket`, `alocal` =
`--alocal`, `w8080` = `--w8080`, `werror` = `--werror`, `pasmo_syntax` =
`--pasmo-syntax-055`. `assemble_text(text, **options)` takes the same ones.

## Errors and warnings

Assembly errors raise `pypasmo.AsmError`; `e.errors` is the list of the messages (up to
10, as on the command line). Each message is `file:line: text`, followed by the source
line:

```python
try:
    pypasmo.assemble_text(" ld a,\n jp nowhere\n")
except pypasmo.AsmError as e:
    for msg in e.errors:
        print(msg)
# <source>:1: empty operand
#     ld a,
# <source>:2: undefined symbol nowhere
#     jp nowhere
```

Warnings do not stop the assembly; they are in the list `asm.warnings`
(`<source>:3: warning: ...`). `output_bytes` adds the warnings of the output format (for
example a tape loader whose `CLEAR` is too low) to the same list. With `werror=True` a
warning is an `AsmError`.

## The result

After `assemble` / `assemble_text`:

| Name | What it is |
|---|---|
| `asm.mem` | the assembled bytes, a dict `{address: byte}` |
| `pypasmo.image(asm.mem)` | `(lowest address, bytes)`: the bytes from the lowest to the highest used address, the gaps filled with 0 (as `--bin`) |
| `asm.symbols` | the symbols, a dict `{name: value}` (upper case names with `nocase=True`) |
| `asm.entry` | the address from `END`, or `None` |
| `asm.warnings` | the warnings, a list of strings |
| `asm.displays` | the texts of `DISPLAY`, a list of strings |
| `pypasmo.listing_text(asm)` | the listing (`--lst`) as a string |
| `pypasmo.symbol_text(asm)` | the symbol file (the third file name on the command line) as a string |
| `pypasmo.memmap_text(asm)` | the memory map (`--memmap`) as a string |
| `pypasmo.sld_text(asm)`, `pypasmo.list_dbgsym_text(asm)` | the debug data for DeZog (`--dbgsym-sld`, `--dbgsym-list`) |

```python
asm = pypasmo.assemble_text(" org 8000h\nstart: ld a,1\n ret\n end start\n")
lo, data = pypasmo.image(asm.mem)       # (0x8000, b'>\x01\xc9')
print(pypasmo.symbol_text(asm))         # start           EQU 08000H
```

## Output formats

`pypasmo.output_bytes(asm, fmt, name)` returns the bytes of an output file. `fmt` is one
of `pypasmo.FORMATS`: the option without `--`, except the formats that come from Pasmo
and the fork, which keep their Pasmo / fork names:

| `fmt` | Option |
|---|---|
| `"tap"`, `"tapbas"` | <nobr>`--tap-48k`</nobr>, <nobr>`--tap-wloader-48k`</nobr> |
| `"tzx"`, `"tzxbas"` | <nobr>`--tzx-48k`</nobr>, <nobr>`--tzx-wloader-48k`</nobr> |
| `"pzx-48k"`, `"pzx-wloader-48k"` | <nobr>`--pzx-48k`</nobr>, <nobr>`--pzx-wloader-48k`</nobr> |
| `"tap128"`, `"tapbas128"` | <nobr>`--tap-128k`</nobr>, <nobr>`--tap-wloader-128k`</nobr> |
| `"tzx-128k"`, `"tzx-wloader-128k"` | <nobr>`--tzx-128k`</nobr>, <nobr>`--tzx-wloader-128k`</nobr> |
| `"pzx-128k"`, `"pzx-wloader-128k"` | <nobr>`--pzx-128k`</nobr>, <nobr>`--pzx-wloader-128k`</nobr> |
| `"cdtbas"` | <nobr>`--cdt-wloader`</nobr> |
| `"bin"`, `"hex"`, `"sna-48k"`, `"p-zx81"`, `"dsk-msx"`, ... | <nobr>`--bin`</nobr>, <nobr>`--hex`</nobr>, <nobr>`--sna-48k`</nobr>, <nobr>`--p-zx81`</nobr>, <nobr>`--dsk-msx`</nobr>, ... |

`name` is the name in the headers (tapes, disks), as `--name`. A format that can not hold
the code (for example `BANK` with a 48K format) raises `AsmError`. `"hex"` gives the text
of the Intel HEX file as bytes.

## Running the command line

`pypasmo.main(argv)` runs the command line with a list of arguments and returns its exit
code (0 = no errors); the messages go to the standard output and error, as from the
command line:

```python
import pypasmo

rc = pypasmo.main(["--sna-48k", "--lst", "hello.lst", "hello.asm", "hello.sna"])
if rc:
    raise SystemExit("assembly failed")
```

## Reference

| Name | What it does |
|---|---|
| `pypasmo.assemble_text(text, name="<source>", **options)` | assemble a source given as a string (as UTF-8, like a file), returns the `Assembler`; `name` is the file name in the messages |
| `pypasmo.Assembler(**options)` | the assembler, see [Assemble a file with options](#assemble-a-file-with-options) |
| `Assembler.assemble(file)` | assemble a source file |
| `pypasmo.output_bytes(asm, fmt, name)` | the bytes of an output file, see [Output formats](#output-formats) |
| `pypasmo.FORMATS` | the names of all output formats |
| `pypasmo.image(mem)` | the lowest used address and the bytes up to the highest one |
| `pypasmo.listing_text(asm)`, `pypasmo.symbol_text(asm)`, `pypasmo.memmap_text(asm)` | the listing, the symbol file and the memory map as text |
| `pypasmo.sld_text(asm)`, `pypasmo.list_dbgsym_text(asm)` | the DeZog debug data as text |
| `pypasmo.tstates(code)` | the T-states of one instruction given as bytes, as in the listing: `pypasmo.tstates(b"\x10\xfe")` = `"13/8"` (DJNZ: jumps / goes on) |
| `pypasmo.main(argv)` | the command line, returns the exit code |
| `pypasmo.AsmError` | the exception for assembly errors; `e.errors` is the list of errors (up to 10) |
| `pypasmo.__version__` | the version of pypasmo, e.g. `"0.7.0b1"` |
