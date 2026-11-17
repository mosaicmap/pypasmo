# MSX

Back to the [index](../index.md).

pypasmo writes MSX tape images, disk images, cartridge ROMs and `BLOAD` files.

- [Quick start](#quick-start)
- [Options](#options)
- [Cartridge ROM (`--rom-msx`)](#cartridge-rom---rom-msx)
- [Tape image (`--cas-msx`)](#tape-image---cas-msx)
- [Disk image (`--dsk-msx`)](#disk-image---dsk-msx)
- [Trying it in an emulator](#trying-it-in-an-emulator)

## Quick start

`hello.asm` prints a text with the BIOS and returns to Basic:

```
CHPUT   equ 00A2h           ; BIOS: print the character in A

        org 9000h
start:  ld hl,text
next:   ld a,(hl)
        or a                ; 0 = end of the text
        ret z               ; back to Basic: Ok
        call CHPUT
        inc hl
        jr next
text:   db "Hello from pypasmo!", 13, 10, 0
        end start
```

A tape image:

```
python -m pypasmo --cas-msx --name hello hello.asm hello.cas
```

Drag `hello.cas` into the window of [WebMSX](https://webmsx.org/) in a web browser and
type in MSX Basic:

```
BLOAD "CAS:",R
```

The text appears, then `Ok`.

A disk image, the program starts by itself when the MSX starts with the disk:

```
python -m pypasmo --dsk-msx --name hello hello.asm hello.dsk
```

Drag `hello.dsk` into WebMSX and reset the MSX (see
[Commands for the disk](#commands-for-the-disk-in-msx-disk-basic)).

## Options

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--msx`</nobr> | file for `BLOAD "file",R`: 7 byte header (`FEh`, start, end, execution address from `END`, or 0) + code | the same bytes as Pasmo 0.5.5 |
| <nobr>`--rom-msx`</nobr> | cartridge ROM `.rom` (8, 16 or 32 KB, padded with FFh) *(pypasmo extension)* | *(early version)* |
| <nobr>`--cas-msx`</nobr> | `.cas` tape image (MSX emulators) with a binary file for `BLOAD "CAS:",R` *(pypasmo extension)* | |
| <nobr>`--dsk-msx`</nobr> | `.dsk` disk image (720 KB, MSX-DOS FAT12) with the code and `AUTOEXEC.BAS`, which runs it, see [below](#disk-image---dsk-msx) *(pypasmo extension)* | *(early version)* |

Examples: `tests/output_formats/msx/hello_msx.asm` (`.cas`, `.dsk`) and
`tests/output_formats/msx/hello_msx_rom.asm` (`.rom`); the ready files are in
`tests/output_formats/msx_results/`.

A tape image:

```
python -m pypasmo --cas-msx --name hello tests/output_formats/msx/hello_msx.asm hello_msx.cas
```

A disk image (the program starts by itself):

```
python -m pypasmo --dsk-msx --name hello tests/output_formats/msx/hello_msx.asm hello_msx.dsk
```

A cartridge ROM:

```
python -m pypasmo --rom-msx tests/output_formats/msx/hello_msx_rom.asm hello_msx_rom.rom
```

The MSX output of `--msx` follows the Pasmo source (`emitmsx`).

## Cartridge ROM (`--rom-msx`)

The source writes the 16 byte header of the ROM itself, at 4000h (or 8000h); the BIOS
finds it at start-up and calls INIT:

```
        org 4000h
        db "AB"         ; ID
        dw init         ; INIT (start address)
        dw 0, 0, 0      ; STATEMENT, DEVICE, TEXT
        ds 6            ; reserved
init:   ...
```

pypasmo checks the start address and the "AB" and pads the file with FFh to the next
size of 8, 16 or 32 KB (32 KB only from 4000h: 4000h-BFFFh). Larger (MegaROM) cartridges
are not supported.

*Early version:* the format follows the MSX documentation. Example:
`tests/output_formats/msx/hello_msx_rom.asm` (the ready file is
`tests/output_formats/msx_results/hello_msx_rom.rom`).

## Tape image (`--cas-msx`)

`--cas-msx` writes two blocks, each starting with the sync header
`1F A6 DE BA CC 13 7D 74`:

1. the file header: 10 x `D0h` (= binary file) and the name: `--name` or the output file
   name up to the first dot, 6 characters (without the directory);
2. the data: start, end, execution address (from `END`, else the start), then the code.

Zeros follow each block, so that every sync header is at a multiple of 8 bytes (some
emulators look for it only there). In the emulator: `BLOAD "CAS:",R`. Example:
`tests/output_formats/msx/hello_msx.asm` (the ready file is
`tests/output_formats/msx_results/hello_msx.cas`).

## Disk image (`--dsk-msx`)

*(pypasmo extension, early version)*

- The image is a 720 KB MSX disk (2DD: 80 tracks, 2 sides, 9 sectors of 512 bytes, raw
  sectors without a header), the FAT12 file system of MSX-DOS (media F9h, 2 sectors per
  cluster, 112 root directory entries). It can be read on a PC too.
- Two files: `NAME.BIN`, the `BLOAD` file (the same as `--msx`, but the execution address
  is the start of the code without `END`), and `AUTOEXEC.BAS` (Basic as ASCII text), which
  Disk BASIC runs at start-up:

  ```
  10 CLEAR 200,&H8FFF:BLOAD"HELLO.BIN",R
  ```

  `CLEAR` sets HIMEM just below the code (start - 1), so that Basic keeps its strings
  and its stack below the code (`BLOAD` does not overwrite them).
- The file name is `--name` or the output file name without its directory, up to the
  first character that is not a letter or a digit, upper case, 8 characters at most, with
  the extension `BIN` (`out/hello.dsk` -> `HELLO.BIN`).
- The code must be in 8800h-DE3Fh, else that is an error. Below 8000h is the ROM; from
  8000h Basic keeps its program, and `CLEAR 200` needs room for 200 bytes of strings and
  the Basic stack under the code, so the code starts at 8800h at the earliest. Above
  DE3Fh is the work area of the disk ROM (the MSX2 Technical Handbook gives 8000h-DE3Fh as
  the RAM for programs with disk drives).
- When the code returns (`RET`), Basic goes on after `BLOAD` (`Ok`).
- The boot sector has no MSX-DOS boot code (only `RET`), so the MSX starts Disk BASIC
  and not MSX-DOS.

Example: `tests/output_formats/msx/hello_msx.asm` (the ready file is
`tests/output_formats/msx_results/hello_msx.dsk`).

## Trying it in an emulator

**Files:** `tests/output_formats/msx_results/hello_msx.cas`, `hello_msx.dsk` and
`hello_msx_rom.rom`

- **Online:** [WebMSX](https://webmsx.org/): drag the file into the window.
  `.cas`: type `BLOAD "CAS:",R`. The `.rom` starts by itself. The `.dsk` goes into the
  disk drive; reset the MSX (or start WebMSX with the disk) and the program runs.

### Commands for the disk in MSX Disk BASIC

Disk BASIC runs `AUTOEXEC.BAS` only when the MSX starts with the disk in drive A:. If
the disk was inserted later (or is in drive B:), reset the MSX, or start the program by
hand. Upper or lower case does not matter.

The files on the disk (`HELLO.BIN` and `AUTOEXEC.BAS`):

```
FILES
```

Run `AUTOEXEC.BAS`, the same as at start-up:

```
RUN "AUTOEXEC.BAS"
```

Load the code and run it at once (`,R`), without the Basic program:

```
BLOAD "HELLO.BIN",R
```

Load the Basic program and show it (`RUN` then runs it):

```
LOAD "AUTOEXEC.BAS"
LIST
```

Only load the code, then call it (here at 9000h, the start of `hello_msx.asm`):

```
BLOAD "HELLO.BIN"
DEFUSR=&H9000:A=USR(0)
```

The commands use the current drive; another drive is a prefix of the name, such as
`FILES "B:"` or `RUN "B:AUTOEXEC.BAS"`. The program prints its text and returns to Basic
(`Ok`).
