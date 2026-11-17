# ZX Spectrum 128K and +3

Back to the [index](../index.md). The 48K page, [ZX Spectrum 48K](zx-spectrum.md), describes
the tapes, the Basic loader, `TAPE_BLOCK` and the snapshots in detail; this page adds what
is different on the 128K (the RAM banks) and on the +3 (the disk).

- [Spectrum 128K](#spectrum-128k)
- [A 128K example](#a-128k-example)
- [128K output](#128k-output)
- [128K snapshots](#128k-snapshots)
- [The 128K Basic loader](#the-128k-basic-loader)
- [Spectrum +3](#spectrum-3)
- [Trying it in an emulator](#trying-it-in-an-emulator)
- [Example files](#example-files)
- [All ZX Spectrum 128K and +3 options](#all-zx-spectrum-128k-and-3-options)

## Spectrum 128K

The 128K has eight RAM banks of 16 KB, numbered 0-7. Bank 5 is always at 4000h-7FFFh
(it holds the screen) and bank 2 at 8000h-BFFFh. At C000h-FFFFh the program chooses one of
the banks 0-7 by writing to port 7FFDh (bank 0 after reset; it is the "normal" memory of
a 48K program). So the code at C000h-FFFFh can exist up to eight times, once in each bank,
and the assembler must be told which bank each part belongs to.

**`BANK n`** says that the following code at C000h-FFFFh goes into bank n (0-7). It is
valid until the next `BANK`. It does not change the address: write `ORG 0C000h` after it.
Code below C000h is not changed by `BANK`: 4000h-7FFFh is always bank 5, 8000h-BFFFh
bank 2. `BANK 0` (the default) is the normal memory at C000h.

```
        org 8000h       ; the main program: bank 2, always at 8000h
        ...
        bank 1
        org 0C000h      ; this goes into bank 1
level1: ...
        bank 3
        org 0C000h      ; this into bank 3, at the same addresses
level2: ...
```

**`BANK_OF label`** *(pypasmo extension)* is a number in expressions: the bank of the
label, so the bank numbers are not written twice by hand. It is the `n` of `BANK n` for a
label at C000h-FFFFh, 5 for 4000h-7FFFh and 2 for 8000h-BFFFh (`BANK_OF level2` = 3
above). The program uses it to page the right bank in before it calls or reads the label,
see the example below. Labels defined later can be used too.

Both are also described in [Directives](../directives.md#bank-zx-spectrum-128k).

### A 128K example

The main program is in bank 2 (8000h); it pages bank 1 in at C000h and calls code there:

```
BANKM   equ 5B5Ch       ; system variable: the last value written to port 7FFDh

        org 8000h       ; bank 2, always at 8000h
start:  call 0D6Bh      ; ROM: clear the screen
        ld a,2
        call 1601h      ; ROM: open channel 2 (the upper screen)
        ld a,BANK_OF hello1
        call page       ; bank 1 at C000h
        call hello1
        xor a
        call page       ; bank 0 at C000h again, as Basic expects
        ret

page:   ld b,a          ; page in RAM bank A at C000h
        ld a,(BANKM)
        and 0F8h        ; keep the ROM and screen bits
        or b
        di
        ld (BANKM),a    ; keep BANKM up to date
        ld bc,7FFDh
        out (c),a
        ei
        ret

        bank 1
        org 0C000h
hello1: ld hl,text      ; code and text in bank 1
next:   ld a,(hl)
        or a
        ret z
        rst 10h
        inc hl
        jr next
text:   db "Hello from bank 1", 13, 0

        end start
```

A tape with the 128K Basic loader:

```
python -m pypasmo --tap-wloader-128k hello128.asm hello128.tap
```

A 128K snapshot:

```
python -m pypasmo --sna-128k hello128.asm hello128.sna
```

Load the tape in 128K mode ("Tape Loader" in the menu, or `LOAD ""` in 128 BASIC); the
snapshot runs at once. The text is printed and Basic says `0 OK`.

`--memmap` shows where the code is, here with the tape without a loader:

```
python -m pypasmo --tap-128k --memmap hello128.asm hello128.tap
```

It prints:

```
Memory map:
  page 0  0000h-3FFFh  ROM on the Spectrum            used: -
  page 1  4000h-7FFFh  Spectrum 128K bank 5           used: -
  page 2  8000h-BFFFh  Spectrum 128K bank 2           used: 8000h-8026h     39 bytes
  page 3  C000h-FFFFh  Spectrum 128K bank 0 (BANK 0)  used: -
Banks set by BANK (at C000h-FFFFh):
  bank 1  used: C000h-C01Ch     29 bytes
Blocks of --tap-128k / --tap-wloader-128k (bank, start, length):
  bank 1  C000h     29 bytes
  bank 2  8000h     39 bytes
```

### 128K output

- `--tap-wloader-128k` (also `--tapbas128`): a Basic loader `loader` and a CODE block
  `bank1.tap`, `bank2.tap` ... for each bank (the names of the fork; `--name` is not
  used). The loader pages in the bank of each block and loads it, then runs the program
  at the `END` address. Load it in 128K mode (Tape Loader); when the program starts,
  bank 0 is at C000h again (the fork leaves the last loaded bank there).
- `--tap-128k` (also `--tap128`): only the CODE blocks, for your own loader.
- `--tzx-wloader-128k`, `--tzx-128k`, `--pzx-wloader-128k`, `--pzx-128k` *(pypasmo
  extension)* **IN DEVELOPMENT**: the same blocks as `--tap-wloader-128k` / `--tap-128k`
  in a `.tzx` or `.pzx` tape image, converted as for the 48K (see
  [Tapes](zx-spectrum.md#tapes)): each block as a standard speed block with a pause of
  1 s.
- `--sna-128k`, `--z80-128k`: a 128K snapshot with all banks, see
  [128K snapshots](#128k-snapshots).
- `--dbgsym-sld` describes the 128K memory when `BANK` is used, see
  [Debugging](../debugging.md#debugging-in-the-source---dbgsym-sld).
- Without `BANK` (or with `BANK 0` only) `--tap-128k`/`--tap-wloader-128k` give the same
  file as `--tap-48k`/`--tap-wloader-48k` (and the `.tzx` / `.pzx` ones the same as the 48K
  ones).
- `TAPE_BLOCK` with a 128K tape is an error (not done yet).
- Code at 0000h-3FFFh is an error (ROM); banked code with other formats is an error.
- `--tap-128k` makes a separate block when one bank has code both at its fixed address
  and at C000h (the fork warns); it gives an error when `BANK 5` / `BANK 2` at C000h and
  the code at 4000h / 8000h write the same byte.
- `--memmap` prints the used part of each 16 KB page, the banks and the blocks of
  `--tap-128k` (see [Command line](../command-line.md#options)).

### 128K snapshots

*(pypasmo extension)* The state is the one of the 48K snapshots (see
[The state of a snapshot](zx-spectrum.md#the-state-of-a-snapshot)), on a Spectrum 128K:

- `--sna-128k`: in 48 BASIC (ROM 1) with the paging not locked (port 7FFDh and BANKM =
  10h: bank 0 at C000h), so the program can page the banks itself (`BANK n` puts the code
  into bank n). `RET` returns to 48 BASIC (example:
  `tests/output_formats/zx_spectrum_results/hello_spectrum128.sna`).
- Keep the stack below C000h (code from C000h on gives RAMTOP FF57h, then the Basic stack
  is in bank 0 and paging another bank in would take it away).
- `--z80-128k`: the state of `--sna-128k` as `.z80` (version 3, machine 128K, port
  7FFDh in the header, pages 3-10 = banks 0-7).
- Errors: the same as for the [48K snapshots](zx-spectrum.md#snapshot-errors), and also
  code at 5B5Ch (BANKM), a start address at C000h-FFFFh that is not in bank 0, and `BANK`
  with the code below 5D2Ah (the Basic stack would be in bank 0).

### The 128K Basic loader

The loader comes from the 0.5.5.paged fork; see
`tests/output_formats/zx_spectrum/hello_spectrum128.asm`. In
pypasmo it looks like this:

```
 1 REM <21 bytes of machine code>
10 CLEAR VAL "lowest-1": LET c=(PEEK VAL "23635"+VAL "256"*PEEK VAL "23636")+VAL "5"
20 LET a=PEEK VAL "23608"
40 READ b
50 IF b<VAL "8" THEN POKE VAL "23608",b: RANDOMIZE USR c: LOAD "" CODE: GO TO VAL "40"
60 POKE VAL "23608",VAL "0": RANDOMIZE USR c: POKE VAL "23608",a: RANDOMIZE USR VAL "entry"
110 DATA VAL "1",VAL "2",VAL "3",VAL "8"
```

- `c` is the address of the machine code in line 1: PROG (23635) is the start of the
  Basic program, +5 skips the line number, the line length and the REM token.
- The bank number is passed to the machine code in the system variable RASP (23608,
  length of the keyboard warning beep); line 20 saves it and line 60 restores it.
- Line 60 pages bank 0 in at C000h before the start (the fork leaves the last loaded bank
  there, so code of bank 0 at C000h did not run). Without `END address` there is no
  `RANDOMIZE USR VAL "entry"`. The loader ends with "0 OK" (the fork: `STOP`).
- `DATA` lists the bank of each CODE block in the order on the tape, 8 is the end mark
  (for the example above: `DATA VAL "1",VAL "2",VAL "8"`).
- `RANDOMIZE USR` calls the machine code without printing anything; `VAL "n"` stores a
  number in fewer bytes than the normal form.

### The paging routine of the 128K loader

The machine code in line 1 (a routine that does not depend on its address, so it can run
anywhere the Basic program is):

```
DI                  ; no interrupt between writing BANKM and the port
LD A,(23388)        ; BANKM: the last value written to port 7FFDh
AND 0F8h            ; keep ROM, screen and lock bits, clear the bank (bits 0-2)
LD B,A
LD A,(23608)        ; the bank number from RASP
OR B
LD (23388),A        ; keep BANKM up to date (the 128K ROM pages from it)
LD BC,7FFDh
OUT (C),A           ; page in the bank at C000h
EI
RET
```

## Spectrum +3

*(early version)*

| Option | Output |
|---|---|
| <nobr>`--dsk-plus3`</nobr> | a +3 disk image `.dsk` with the code `NAME.BIN` and the Basic loader `DISK`; "Loader" in the +3 menu runs it *(pypasmo extension)* |
| <nobr>`--plus3dos`</nobr> | one +3DOS file: a 128 byte header (type CODE), the code, padded to a multiple of 128 bytes (the same bytes as Pasmo 0.5.5) |

```
python -m pypasmo --dsk-plus3 --name hello hello.asm hello.dsk
```

The disk holds `HELLO.BIN` and `DISK` (autostart at line 10):

```
10 CLEAR lo-1
20 LOAD "HELLO.BIN" CODE
30 RANDOMIZE USR start        (without END no line 30)
```

"Loader" in the menu of the +3 runs `DISK`, or type `LOAD "disk"`. The warning of the
tape loaders about a too low `CLEAR` applies here too. Emulators do not load a bare
`--plus3dos` file; put it on a disk with `--dsk-plus3`.

### The +3 disk image

`--dsk-plus3` writes an Extended DSK disk image (40 tracks, 1 side, 9 sectors of 512
bytes, 180 KB, the CP/M file system of the +3; the common part is in
[Output formats](../output-formats.md#disk-images---dsk-cpc---dsk-plus3---dsk-pcw---dsk-msx)):

- the +3 format: sectors 1-9; track 0 is reserved and holds the disk specification
  (format 0, 40 tracks, 9 sectors, 1 KB blocks);
- two +3DOS files: `NAME.BIN` (the same as `--plus3dos`) and the Basic program `DISK`;
- the file name is `--name` or the output file name without its directory, up to the
  first character that is not a letter or a digit, upper case, 8 characters at most, with
  the extension `BIN` (`out/hello.dsk` -> `HELLO.BIN`).

## Trying it in an emulator

**Files:** `tests/output_formats/zx_spectrum_results/hello_spectrum128.tap`, `.tzx`, `.pzx`,
`.sna`, `.z80` (128K) and `hello_spectrum.dsk` (+3). The emulators are listed on the
[48K page](zx-spectrum.md#trying-it-in-an-emulator); the online JSSpeccy and ZX Play
(also on a phone) and Fuse, JSpeccy and ZEsarUX have the 128K, Fuse and ZEsarUX the +3
with disks.

- The 128K tape is loaded in 128K mode ("Tape Loader" in the menu, or `LOAD ""` in
  128 BASIC); the snapshots run at once. The `.tzx` and `.pzx` (**IN DEVELOPMENT**) hold
  the same blocks as the `.tap`; Fuse and ZEsarUX read both.
- **Expected result** (`hello_spectrum128`): the texts from the banks 1 and 3, then
  `0 OK, 110:1`.
- After a tape loaded with "Tape Loader" ends, a key goes back to the Tape Loader screen
  and the menu; this is what the 128K ROM does for every tape (also a 48K one). With
  `LOAD ""` typed in 128 BASIC, it goes back to 128 BASIC (the loader is listed).

### The +3 disk in Fuse

**File:** `tests/output_formats/zx_spectrum_results/hello_spectrum.dsk` (holds `HELLO.BIN`
and the Basic loader `DISK`). No online +3 emulator with disks was found, so use
**Fuse**:

1. Machine → Select… → **Spectrum +3**.
2. Media → Disk → +3 → Drive A: → **Insert…** → choose `hello_spectrum.dsk`.
3. In the start menu of the +3 choose **Loader** (Enter). The +3 loads the program `DISK`
   from the disk, which loads `HELLO.BIN` and runs it.
4. Or type `LOAD "disk"` in +3 BASIC.

**Expected result:** a text, the border flashes, after a key back to Basic.
`CAT` shows the files `DISK` and `HELLO.BIN` on the disk.

## Example files

**Source:** `tests/output_formats/zx_spectrum/hello_spectrum128.asm` (128K: `BANK`, texts
in banks 1 and 3 at C000h); the ready files `hello_spectrum128.tap`, `.tzx`, `.pzx`, `.sna`,
`.z80` are in
`tests/output_formats/zx_spectrum_results/`, and also `hello_spectrum.dsk`, the +3 disk
made from the 48K example `hello_spectrum.asm`. Run in the folder
`tests/output_formats/zx_spectrum/`:

128K tape with a loader:

```
python -m pypasmo --tap-wloader-128k hello_spectrum128.asm hello_spectrum128.tap
```

The same as `.tzx` or `.pzx` (**IN DEVELOPMENT**):

```
python -m pypasmo --tzx-wloader-128k hello_spectrum128.asm hello_spectrum128.tzx
```

```
python -m pypasmo --pzx-wloader-128k hello_spectrum128.asm hello_spectrum128.pzx
```

128K snapshot:

```
python -m pypasmo --sna-128k hello_spectrum128.asm hello_spectrum128.sna
```

+3 disk:

```
python -m pypasmo --dsk-plus3 --name hello hello_spectrum.asm hello_spectrum.dsk
```

## All ZX Spectrum 128K and +3 options

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--tap-128k`</nobr> (also <nobr>`--tap128`</nobr>, as in the 0.5.5.paged fork) | Spectrum 128K: a CODE block for each RAM bank used with `BANK`, see [128K](#spectrum-128k) | *(early version)* |
| <nobr>`--tap-wloader-128k`</nobr> (also <nobr>`--tapbas128`</nobr>) | the same with a Basic loader that pages the banks in | *(early version)* |
| <nobr>`--tzx-128k`</nobr> | the blocks of <nobr>`--tap-128k`</nobr> in a `.tzx` tape image *(pypasmo extension)* | **IN DEVELOPMENT** |
| <nobr>`--tzx-wloader-128k`</nobr> | the blocks of <nobr>`--tap-wloader-128k`</nobr> in a `.tzx` tape image *(pypasmo extension)* | **IN DEVELOPMENT** |
| <nobr>`--pzx-128k`</nobr> | the blocks of <nobr>`--tap-128k`</nobr> in a `.pzx` tape image *(pypasmo extension)* | **IN DEVELOPMENT** |
| <nobr>`--pzx-wloader-128k`</nobr> | the blocks of <nobr>`--tap-wloader-128k`</nobr> in a `.pzx` tape image *(pypasmo extension)* | **IN DEVELOPMENT** |
| <nobr>`--sna-128k`</nobr> | 128K snapshot `.sna` with the banks set by `BANK` *(pypasmo extension)* | *(early version)* |
| <nobr>`--z80-128k`</nobr> | the same as a 128K `.z80` snapshot (version 3, compressed) *(pypasmo extension)* | *(early version)* |
| <nobr>`--plus3dos`</nobr> | Spectrum +3 disk file: 128 byte +3DOS header (type CODE), padded to a multiple of 128 bytes | *(early version)*, the same bytes as Pasmo 0.5.5 |
| <nobr>`--dsk-plus3`</nobr> | Spectrum +3 disk image `.dsk` with the code `NAME.BIN` and the Basic loader `DISK`, which "Loader" in the +3 menu runs, see [Spectrum +3](#spectrum-3) *(pypasmo extension)* | *(early version)* |
| <nobr>`--dbgsym-sld FILE.sld`</nobr> | debug data for DeZog (stepping in the `.asm`), 48K and 128K, see [Debugging: the 128K](../debugging.md#the-128k) *(pypasmo extension)* | |
| <nobr>`--name NAME`</nobr> | the name of `NAME.BIN` on <nobr>`--dsk-plus3`</nobr>, and of the CODE block of the 128K tapes without `BANK` (10 characters); with `BANK` the blocks are `bank1.tap` ... and the Basic loader is always `loader`; without it the output file name, see [Header name](../command-line.md#header-name) | |
| <nobr>`--memmap`</nobr> | prints the used part of each 16 KB page, the 128K banks and the blocks of <nobr>`--tap-128k`</nobr>, see [128K](#spectrum-128k) *(from the 0.5.5.paged fork)* | |

The 48K options (`--tap-48k`, `--sna-48k` ...) are in
[ZX Spectrum 48K](zx-spectrum.md#all-zx-spectrum-48k-options), the options for every
machine in [Command line](../command-line.md#options). The +3 output follows the Pasmo
source (`emitplus3dos`), the 128K tapes the 0.5.5.paged fork.
