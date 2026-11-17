# Amstrad CPC

Back to the [index](../index.md).

pypasmo writes Amstrad CPC snapshots, disk images, tapes and Amsdos files.

- [Quick start](#quick-start)
- [Options](#options)
- [Header name](#header-name)
- [RUN vs. LOAD + CALL](#run-vs-load--call)
- [Basic loader (`--cdt-wloader`)](#basic-loader---cdt-wloader)
- [Disk image (`--dsk-cpc`)](#disk-image---dsk-cpc)
- [Snapshots (`--sna-cpc6128`, `--sna-cpc464`)](#snapshots---sna-cpc6128---sna-cpc464)
- [Trying it in an emulator](#trying-it-in-an-emulator)

## Quick start

`hello.asm` prints a text with the firmware and returns to Basic:

```
TXT_OUTPUT equ 0BB5Ah       ; firmware: print the character in A

        org 4000h
start:  ld hl,text
next:   ld a,(hl)
        or a                ; 0 = end of the text
        ret z               ; back to Basic: Ready
        call TXT_OUTPUT
        inc hl
        jr next
text:   db "Hello from pypasmo!", 13, 10, 0
        end start
```

A snapshot of a CPC 6128, the quickest way to try it:

```
python -m pypasmo --sna-cpc6128 hello.asm hello.sna
```

Start the CPC 6128 emulator of [CHIPS / tiny8bit](https://floooh.github.io/tiny8bit/) in a
web browser and drag `hello.sna` into its window. The program runs at once: the text,
then `Ready`.

A disk image:

```
python -m pypasmo --dsk-cpc --name hello hello.asm hello.dsk
```

Drag `hello.dsk` into the emulator and type `LOAD"hello":CALL &4000`. (With `RUN"hello"`
the CPC resets after the `RET`, see [RUN vs. LOAD + CALL](#run-vs-load--call).)

## Options

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--amsdos`</nobr> | disk file with a 128 byte Amsdos header (binary file, load address, entry point from `END`); load it with `LOAD "file",address` or run with `RUN "file"` | |
| <nobr>`--cdt`</nobr> | `.cdt` tape image (TZX format, turbo blocks with CPC timing): the code in blocks of max. 2 KB, each a header and a data record with CRCs; start it with `RUN ""` | *(early version)*, the same bytes as Pasmo 0.5.5 |
| <nobr>`--cdt-wloader`</nobr> (also <nobr>`--cdtbas`</nobr>, as in Pasmo) | `.cdt` with a Locomotive Basic loader `LOADER` before the code, see [below](#basic-loader---cdt-wloader) | *(early version)*, the same bytes as Pasmo 0.5.5 |
| <nobr>`--dsk-cpc`</nobr> | disk image `.dsk` (DATA format) with the Amsdos file `NAME.BIN`: `RUN "name"`, see [below](#disk-image---dsk-cpc) *(pypasmo extension)* | *(early version)* |
| <nobr>`--sna-cpc6128`</nobr> | CPC 6128 snapshot `.sna`: the code runs at once, `RET` goes back to Basic, see [below](#snapshots---sna-cpc6128---sna-cpc464) *(pypasmo extension)* | *(early version)* |
| <nobr>`--sna-cpc464`</nobr> | the same for the CPC 464 *(pypasmo extension)* | *(early version)* |

Example: `tests/output_formats/cpc/hello_cpc.asm` prints three lines of text, waits for a
key and returns. The ready files are in `tests/output_formats/cpc_results/`.

A snapshot for the CPC 6128, the quickest way to try the code in an emulator:

```
python -m pypasmo --sna-cpc6128 hello_cpc.asm hello_cpc6128.sna
```

A snapshot for the CPC 464:

```
python -m pypasmo --sna-cpc464 hello_cpc.asm hello_cpc464.sna
```

An Amsdos file (for a disk, or dropped into an emulator):

```
python -m pypasmo --amsdos --name hello hello_cpc.asm hello_cpc.bin
```

A disk image:

```
python -m pypasmo --dsk-cpc --name hello hello_cpc.asm hello_cpc.dsk
```

A tape, the code only (`RUN ""`):

```
python -m pypasmo --cdt --name hello hello_cpc.asm hello_cpc.cdt
```

A tape with a Basic loader:

```
python -m pypasmo --cdt-wloader --name hello hello_cpc.asm hello_cpc_bas.cdt
```

The CPC output follows the Pasmo source (`cpc.cxx`). The CPC tape CRC is checked against
`binascii.crc_hqx` from the standard library.

## Header name

`--name NAME` sets the name in the Amsdos header (8 + 3 characters, split at the first dot)
and in the `.cdt` header (max. 16). Without it the output file name **as given on the
command line** is used, like in Pasmo, so with a path use `--name`. `--dsk-cpc` takes the
file name without the directory, see [below](#disk-image---dsk-cpc).

## RUN vs. LOAD + CALL

A program started with `RUN "name"` (also `RUN ""` from a tape) has no Basic to return to.
When the code returns (`RET`), the CPC **resets**, as on the real machine. That is why the
example waits for a key, so that the text can be seen. To get back to Basic (`Ready`):

```
LOAD "hello": CALL &4000
```

## Basic loader (`--cdt-wloader`)

```
10 MEMORY &<lowest address - 1>
20 LOAD "!",&<lowest address>
30 CALL &<address from END>               (only if END has an argument)
```

Start it with `RUN ""`. `LOAD "!"` loads the code that follows on the tape without
messages. The same as `cpc.cxx` in Pasmo.

## Disk image (`--dsk-cpc`)

*(pypasmo extension, early version)* An Extended DSK image (40 tracks,
1 side, 9 sectors of 512 bytes, 180 KB, the CP/M file system; the common part is in
[Output formats](../output-formats.md#disk-images---dsk-cpc---dsk-plus3---dsk-pcw---dsk-msx)):

- the DATA format of Amsdos (sectors C1h-C9h, no reserved track) with the Amsdos file (the
  same as `--amsdos`);
- `RUN "hello"` starts it (`END` address, else 0), `LOAD "hello"` only loads it;
- CPC 664 / 6128 (or a 464 with a disk drive);
- after `RUN` the CPC resets when the code returns, see [above](#run-vs-load--call);
- the file name is `--name` or the output file name without its directory, up to the
  first character that is not a letter or a digit, upper case, 8 characters at most, with
  the extension `BIN` (`out/hello.dsk` -> `HELLO.BIN`).

## Snapshots (`--sna-cpc6128`, `--sna-cpc464`)

*(pypasmo extension, early version)* A `.sna` snapshot opens in an emulator and runs at
once, without loading a disk or a tape.

- `--sna-cpc6128` is for the CPC 6128, `--sna-cpc464` for the CPC 464. The two machines
  have another firmware (and the 464 has no disk, so no AMSDOS), so each has its own state;
  a snapshot of one model does not work on the other.
- The state is that of a real CPC in Basic at the `Ready` prompt, saved by an emulator:
  the firmware (and AMSDOS on the 6128) is ready, the screen shows the Basic start-up
  text. So the code can use the firmware (`TXT OUTPUT` at BB5Ah ...).
- The code is put into it; the program starts at `END address`, else at its first byte.
- A small routine just below HIMEM switches the lower ROM off (`KL L ROM DISABLE`, as
  for `CALL` from Basic, so code below 4000h runs in the RAM) and calls the code. When the
  code returns (`RET`), it sets the registers and the ROM state of the saved state again
  and goes on with the firmware: the CPC is back in Basic, as after `CALL` (not reset as
  after `RUN`).
- The code must not use 0000h-003Fh (the restart vectors in the RAM), the routine and the
  memory above HIMEM (the firmware, AMSDOS, the stack); that is an error. The screen
  (C000h-FFFFh) may be written:

  | Option | HIMEM | The routine | Used above HIMEM | Free for the code |
  |---|---|---|---|---|
  | `--sna-cpc6128` | A67Bh | A641h-A67Bh | A67Ch-BFFFh | 0040h-A640h |
  | `--sna-cpc464` | AB7Fh | AB45h-AB7Fh | AB80h-BFFFh | 0040h-AB44h |

- The code must keep the alternate register BC' (the firmware keeps the Gate Array port
  there), as for any code called from Basic.
- 64 KB of RAM; the snapshot is version 2 (the CPC type, 6128 or 464, is in the header).

## Trying it in an emulator

### `.sna` (snapshot)

- **Online:** [CHIPS / tiny8bit](https://floooh.github.io/tiny8bit/): start the CPC 6128
  emulator and drag `tests/output_formats/cpc_results/hello_cpc6128.sna` into the browser
  window. The text appears at once; after a key `Ready`.
- **Desktop:** WinAPE: File → Snapshot → Load; set the emulator to the model of the
  snapshot (`hello_cpc6128.sna` CPC 6128, `hello_cpc464.sna` CPC 464).

### `.bin` (Amsdos file)

- **Online:** [CHIPS / tiny8bit](https://floooh.github.io/tiny8bit/) (Andre Weissflog):
  start the CPC emulator and drag `tests/output_formats/cpc_results/hello_cpc.bin` into the
  browser window. It is loaded and run.

### `.dsk` (disk)

**File:** `tests/output_formats/cpc_results/hello_cpc.dsk` (holds `HELLO.BIN`)

- **Online:** CHIPS / tiny8bit: the CPC emulator (6128, it has a disk drive), drag the
  `.dsk` file into the window, then type:
  ```
  RUN"hello
  ```
  (the closing quote is not needed). The text appears, after a key the CPC resets. With
  the return to Basic: `LOAD"hello":CALL &4000`. `CAT` lists the disk.
- **Desktop:** [WinAPE](http://www.winape.net/) (Windows, for years the standard of the CPC
  community): File → Drive A: → Insert Disc Image…, then `RUN"hello`.

### `.cdt` (tape)

**Files:** `tests/output_formats/cpc_results/hello_cpc.cdt` (`--cdt`, the code runs at once)
and `hello_cpc_bas.cdt` (`--cdt-wloader`, the Basic loader first).

CHIPS **does not support `.cdt`**. An emulator with a tape recorder is needed, for example
WinAPE, JavaCPC or Retro Virtual Machine. In WinAPE:

1. Choose the **CPC 464** (it has a tape recorder), or on the 6128 first type `|TAPE`
   (Enter), else `RUN""` looks on the disk. The `|` character is Shift + `@` on the CPC.
2. File → Tape → **Insert Tape Image…** → choose the `.cdt`.
3. Type `RUN""` (Enter), then any key (the CPC prints "Press PLAY then any key"). WinAPE
   starts the tape itself (else Tape → Play).
4. **Expected result:** after loading three lines of text, after a key a reset (started
   with `RUN`). With `hello_cpc_bas.cdt` the Basic `LOADER` is loaded first, then it loads
   the code.
