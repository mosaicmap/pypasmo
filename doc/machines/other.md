# Other machines

Back to the [index](../index.md).

The less common machines, ordered by how much they are used:

1. [Sega Master System, Game Gear](#sega-master-system-game-gear)
2. [TRS-80](#trs-80)
3. [CP/M Plus](#cpm-plus)
4. [Robotron KC 85, Z 1013](#robotron-kc-85-z-1013)
5. [Sharp MZ-700, MZ-800](#sharp-mz-700-mz-800)
6. [Amstrad PCW](#amstrad-pcw)
7. [ColecoVision](#colecovision)
8. [Jupiter Ace](#jupiter-ace)

| Option | Machine | Status |
|---|---|---|
| <nobr>`--bin`</nobr> | any (also CP/M `.COM`) | |
| <nobr>`--hex`</nobr> | any (Intel HEX) | |
| <nobr>`--rom-sms`</nobr> | Sega Master System | *(early version)* |
| <nobr>`--rom-gg`</nobr> | Sega Game Gear | *(early version)* |
| <nobr>`--cas-trs`</nobr> | TRS-80 Model I / III (tape) | **IN DEVELOPMENT** |
| <nobr>`--trs`</nobr> | TRS-80 Model I / III / 4 (DOS) | *(early version)* |
| <nobr>`--prl`</nobr> | CP/M Plus | *(early version)* |
| <nobr>`--kcc-kc85`</nobr> | Robotron KC 85/2-4 | *(early version)* |
| <nobr>`--z80-z1013`</nobr> | Robotron Z 1013 | *(early version)* |
| <nobr>`--mzf`</nobr> | Sharp MZ-700 / MZ-800 | *(early version)* |
| <nobr>`--dsk-pcw`</nobr> | Amstrad PCW (CP/M Plus) | **IN DEVELOPMENT** |
| <nobr>`--rom-coleco`</nobr> | ColecoVision | **IN DEVELOPMENT** |
| <nobr>`--tap-ace`</nobr> | Jupiter Ace | **IN DEVELOPMENT** |

`--bin` and `--hex` are described in
[Output formats](../output-formats.md#raw-binary-and-intel-hex).

## Sega Master System, Game Gear

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--rom-sms`</nobr> | Sega Master System cartridge ROM `.sms`, 32 KB, the header with the checksum *(pypasmo extension)* | *(early version)* |
| <nobr>`--rom-gg`</nobr> | the same for the Sega Game Gear, `.gg`: region 7 (Game Gear international) in the header *(pypasmo extension)* | *(early version)* |

Examples: `tests/output_formats/other/hello_sms.asm` and
`tests/output_formats/other/hello_gg.asm`; the ready files are in
`tests/output_formats/other_results/` (run in `tests/output_formats/other/`).

The Master System ROM:

```
python -m pypasmo --rom-sms hello_sms.asm hello_sms.sms
```

The Game Gear ROM:

```
python -m pypasmo --rom-gg hello_gg.asm hello_gg.gg
```

The layout is that of z88dk (appmake).

### The Sega ROM

- 32 KB from 0000h (where the Z80 starts; nothing at 0000h is an error), padded with FFh.
- No mapper: code at 8000h and above is an error.

### The Sega header and the checksum

The header at 7FF0h:

| Field | Value |
|---|---|
| ID | `TMR SEGA`, two spaces |
| checksum | the 16 bit sum of 0000h-7FEFh, low byte first |
| product code | 0 |
| version | 0 |
| region | 4 (export SMS); 7 (Game Gear international) with <nobr>`--rom-gg`</nobr> |
| size | C (32 KB) |

The export BIOS checks the checksum
([SMS Power](https://www.smspower.org/Development/ROMHeader)). A source may write its own
header at 7FF0h (product code, version): it must start with `TMR SEGA` and have size C,
pypasmo only fills in the checksum.

The examples `tests/output_formats/other/hello_sms.asm` and `hello_gg.asm` change the
backdrop colour (the Game Gear colours have 12 bits, two bytes in the CRAM).

### Trying the Sega ROMs in an emulator

**Files:** `tests/output_formats/other_results/hello_sms.sms` and `hello_gg.gg`

- **Master System online:** [Miracle](https://miracle.xania.org/) (Matt Godbolt, the author
  of Compiler Explorer): "Open ROM file".
- **Game Gear:** Miracle emulates only the Master System. Desktop: Emulicious (Java, an
  emulator and debugger for homebrew developers) or Kega Fusion. Open the file with
  File → Open; the extension `.gg` tells the emulator that it is a Game Gear ROM.
- **Expected result:** the whole screen changes its colour about twice a second.
- **The header checksum** is checked only by an emulator with the BIOS turned on (export
  SMS). Emulicious can be set up with a BIOS, but the BIOS file must be found separately.

## TRS-80

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--cas-trs`</nobr> | TRS-80 Model I / III tape `.cas` (SYSTEM tape, 500 baud): loaded from BASIC, no DOS needed *(pypasmo extension)* | **IN DEVELOPMENT** |
| <nobr>`--trs`</nobr> | TRS-80 Model I / III / 4 `/CMD` file for a DOS: load records and the entry point (a format of Pasmo 0.5.5) | *(early version)* |

There are two ways to load machine code into a TRS-80: from a tape in Level II BASIC
(`--cas-trs`), or from a disk with a DOS (`--trs`). The tape is the easier one in an
emulator: no disk and no DOS are needed.

### From a tape (`--cas-trs`)

**IN DEVELOPMENT:** the layout is the same as that of the SYSTEM tapes in the `.cas`
archives, but it may still change.

```
python -m pypasmo --cas-trs --name hello hello_trs80_tape.asm hello_trs80.cas
```

In Level II BASIC:

```
SYSTEM
```

At the prompt `*?` type the name on the tape (`HELLO`); the tape is loaded. At the next
`*?` type `/` and Enter: the program starts at its entry point (`/12345` starts it at
another address). On the Model III answer `L` (low speed, 500 baud) at `Cass?`.

The tape (as the emulators keep it in a `.cas` file):

- 256 zero bytes (the leader) and the sync byte `A5h`;
- `55h` and the name: `--name` or the output file name without its directory, up to the
  first character that is not a letter or a digit, upper case, 6 characters, filled with
  spaces;
- blocks: `3Ch`, the length (1-255, 0 = 256 bytes), the load address, the data, the
  checksum (the sum of the two address bytes and the data, the low byte);
- `78h` and the entry point (`END address`, else the load address).

Code at 0000h-3FFFh (the ROM) is an error. The program returns to BASIC with
`JP 1A19h` (`READY`).

### From a disk (`--trs`)

```
python -m pypasmo --trs hello_trs80.asm hello_trs80.cmd
```

A DOS (TRSDOS, LDOS, NEWDOS/80 ...) loads and runs a `/CMD` file when its name is typed
(`HELLO`). `--name` is not used: the file has no name in it.

- load records: `01h`, the length (the number of data bytes + 2, the low byte: 256 bytes
  give `02h`), the load address, up to 256 bytes of code;
- the transfer record `02h 02h` and the entry point (`END address`, else 0); it also marks
  the end of the file.
- As in Pasmo the code is one block from the lowest to the highest used address (gaps
  filled with zeros); the bytes are the same as Pasmo 0.5.5 makes.

### The TRS-80 code

- The RAM starts at 4000h. Level II BASIC uses it up to 42E8h, a DOS up to about 5200h,
  so a program is usually from 5200h on. The examples are at 7000h, so they fit into
  16 KB.
- The examples use the ROM routines of the Model I / III: 01C9h (clear the screen), 0033h
  (print the character in A), 0049h (wait for a key).
- At the end the tape example returns to BASIC (`JP 1A19h`), the `/CMD` example to the
  DOS (`JP 402Dh`, `DOS Ready`). A `/CMD` program loaded without a DOS has nothing at
  402Dh, so use the tape example then.

### Trying the TRS-80 files in an emulator

**Files:** `tests/output_formats/other_results/hello_trs80.cas` (source
`tests/output_formats/other/hello_trs80_tape.asm`) and `hello_trs80.cmd` (source
`hello_trs80.asm`)

- **Desktop:** [trs80gp](http://48k.ca/trs80gp.html) (George Phillips; Windows, macOS,
  Linux; free; the ROMs are built in), Model I (or III). Other emulators that load `.cas`
  files, such as [sdltrs](https://gitlab.com/jengun/sdltrs) or MAME (`trs80l2`), need the
  ROM files of the machine.
- **The tape:** insert `hello_trs80.cas` as the cassette (the menu of the emulator), then
  in BASIC `SYSTEM`, `HELLO`, `/`.
- **The `/CMD` file:** trs80gp can load it directly (given on its command line or dragged
  into its window); or copy it to a DOS disk image and type `HELLO` in the DOS.
- **Expected result:** a clear screen with three lines of text; after a key `READY` (tape)
  or the DOS (`/CMD`).

## CP/M Plus

A normal CP/M program (`.COM`) needs no special format: `ORG 100h` and `--bin`.

| Option | Meaning |
|---|---|
| <nobr>`--prl`</nobr> | *(early version)* relocatable `.prl` file, used by CP/M Plus for RSX extensions (rename it to `.rsx`) |

- The source is assembled twice, starting at 0 and at 100h, so it **must not use an
  absolute `ORG`**; bytes that differ by 1 are address high bytes and get a bit in the
  relocation bitmap.
- The file: a 256 byte header (the code length at offset 1, the rest zeros, as in Pasmo),
  the code assembled for 100h, the bitmap (1 bit per code byte, highest bit first).
- Like Pasmo, MP/M PRL files are not specially supported.
- `--cmd` (CP/M-86) of Pasmo is not supported, see [Differences](../pasmo-differences.md#not-supported).

No trustworthy and easy to use emulator for `--prl` (CP/M Plus) was found yet.

## Robotron KC 85, Z 1013

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--kcc-kc85`</nobr> | Robotron KC 85/2-4 `.kcc` file with autostart *(pypasmo extension)* | *(early version)* |
| <nobr>`--z80-z1013`</nobr> | Robotron Z 1013 `.z80` file (headersave; not the ZX Spectrum snapshot) *(pypasmo extension)* | *(early version)* |

Examples: `tests/output_formats/other/hello_kc85.asm` and
`tests/output_formats/other/hello_z1013.asm`; the ready files are in
`tests/output_formats/other_results/` (run in `tests/output_formats/other/`).

The KC 85 file:

```
python -m pypasmo --kcc-kc85 hello_kc85.asm hello_kc85.kcc
```

The Z 1013 file:

```
python -m pypasmo --z80-z1013 hello_z1013.asm hello_z1013.z80
```

The layouts are those of z88dk (appmake), the names in the headers come from `--name` or
the output file name without its directory.

### `.kcc` (KC 85/2-4)

128 byte header and the code padded with zeros to a multiple of 128 bytes. The header:

- the name: 8 characters, upper case, up to the first character that is not a letter or a
  digit;
- `KCC`;
- 3 addresses = autostart: load, end + 1, start.

### `.z80` (Z 1013)

32 byte header and the code. The header: load, end (= the last byte), start, 6 zeros, `C`
(= executable), `D3 D3 D3`, the name of 16 characters (up to the first dot).

### Trying the Robotron files in an emulator

**Files:** `tests/output_formats/other_results/hello_kc85.kcc` and `hello_z1013.z80`

- **Online:** [CHIPS / tiny8bit](https://floooh.github.io/tiny8bit/) (KC 85/2-4, Z 1013):
  drag the file into the window.
- **Desktop:** [JKCEMU](https://github.com/lipro-cpm4l/jkcemu) (Java).
- **Expected result:** the KC 85 prints two lines and returns to CAOS. The Z 1013 prints a
  text and waits in a loop (back with a reset). If the Z 1013 does not start by itself,
  type `J 100` in the monitor.

## Sharp MZ-700, MZ-800

| Option | Meaning |
|---|---|
| <nobr>`--mzf`</nobr> | `.mzf` tape file of the Sharp MZ-700 / MZ-800: 128 byte header + code *(pypasmo extension, early version)* |

The header:

| Field | Value |
|---|---|
| attribute | 01h (machine code) |
| name | <nobr>`--name`</nobr> or the output file name (without the directory), upper case, at most 16 characters, ended and filled with 0Dh |
| size | the size of the code |
| load address | the load address of the code |
| start address | `END address`, else the load address |
| comment | 104 bytes (zeros) |

*Early version:* the layout follows the header of other MZ tools.

## Amstrad PCW

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--dsk-pcw`</nobr> | Amstrad PCW disk image `.dsk` with the CP/M program `NAME.COM` *(pypasmo extension)* | **IN DEVELOPMENT** |

The PCW 8256 / 8512 / 9512 runs CP/M Plus, so a program for it is a CP/M program
(`.COM`): the code from `ORG 100h`, CP/M loads it at 100h and starts it there; it calls
the BDOS at 0005h and ends with `RET` (or `JP 0`).

- The disk has the format of the PCW and the Spectrum +3 (the same as
  [`--dsk-plus3`](zx-spectrum-128k.md#spectrum-3)): Extended DSK, 40 tracks, 1 side,
  9 sectors of 512 bytes, track 0 reserved with the disk specification in its first
  sector, the CP/M directory in track 1.
- One file on it: `NAME.COM` (from `--name` or the output file name, as for the other
  disks), the code without a header.
- A start other than 100h (`ORG`, or `END` with another address) is an error.
- The disk does not start by itself: CP/M Plus is not on it (it is not free to copy).
  Start CP/M Plus from its own disk, then run the program by its name.

Example: `tests/output_formats/other/hello_pcw.asm` prints two lines with BDOS function 9
(the code works on any CP/M); the ready file is
`tests/output_formats/other_results/hello_pcw.dsk`:

```
python -m pypasmo --dsk-pcw --name hello hello_pcw.asm hello_pcw.dsk
```

### Trying the PCW disk in an emulator

**File:** `tests/output_formats/other_results/hello_pcw.dsk`

- **Online:** no PCW emulator that loads own disks was found.
- **Desktop:** [JOYCE](https://www.seasip.info/Unix/Joyce/) (John Elliott: Windows,
  Linux; PCW 8256 / 8512 / 9512) or the RetroArch core ZEsarPCW (from ZEsarUX). Both need
  a CP/M Plus start disk (`.dsk`) of the PCW, which is not part of pypasmo.
- Start CP/M Plus, put `hello_pcw.dsk` into drive B: (or into A: after the start) and
  type `B:HELLO` (or `HELLO`).
- **Expected result:** the two lines of text, then the CP/M prompt again.

## ColecoVision

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--rom-coleco`</nobr> | ColecoVision cartridge ROM `.col` from 8000h, padded to 8, 16, 24 or 32 KB *(pypasmo extension)* | **IN DEVELOPMENT** |

The ColecoVision (1982) is a game console with a Z80, a TMS9928A video chip (the same
family as MSX 1) and 1 KB of RAM at 7000h-73FFh. The BIOS (8 KB at 0000h) starts the
cartridge, which is at 8000h-FFFFh.

- The source writes the cartridge header at 8000h; the ROM must start with `AAh 55h`
  or `55h AAh` (else it is an error):

| Address | Content |
|---|---|
| 8000h | `AAh 55h`: the BIOS shows its title screen (about 12 s) first; `55h AAh`: no title screen (the sources differ in which is which, so keep a title text at 8024h with both) |
| 8002h-8009h | 4 pointers to BIOS tables (sprites, a buffer, the controllers); 0 when the BIOS routines are not used |
| 800Ah | the start of the program |
| 800Ch-8020h | 7 jumps of 3 bytes: RST 08h, 10h, 18h, 20h, 28h, 30h, 38h (= the maskable interrupt) |
| 8021h | a jump for the NMI (the VDP frame interrupt) |
| 8024h | the title text: `LINE/LINE/YEAR` |

- pypasmo pads the ROM with FFh to 8, 16, 24 or 32 KB (8 KB ROM chips). Larger ROMs
  (MegaCart, with banks) are not supported.
- The video chip is at ports BEh (data) and BFh (control: a value, then 80h + the
  register number).

Example: `tests/output_formats/other/hello_coleco.asm` turns the display off and changes
the backdrop colour (VDP register 7) about twice a second, as the Sega examples do; the
ready file is `tests/output_formats/other_results/hello_coleco.col`:

```
python -m pypasmo --rom-coleco hello_coleco.asm hello_coleco.col
```

### Trying the ColecoVision ROM in an emulator

**File:** `tests/output_formats/other_results/hello_coleco.col`

- **Online:** no ColecoVision emulator that loads own ROMs was found yet.
- **Desktop:** ColEm (Marat Fayzullin), Gearcoleco (open source, no BIOS file needed),
  blueMSX, MAME (`coleco`). Most of them need the BIOS file `coleco.rom` (8 KB), which is
  not part of pypasmo.
- **Expected result:** maybe the title screen first, then the whole screen changes its
  colour about twice a second.

## Jupiter Ace

| Option | Meaning | Status |
|---|---|---|
| <nobr>`--tap-ace`</nobr> | Jupiter Ace `.tap` tape: a loader and the code *(pypasmo extension)* | **IN DEVELOPMENT** |

**IN DEVELOPMENT:** the Ace format follows the files of z88dk (appmake) and may still
change. The example is `tests/output_formats/other/hello_ace.asm`, the files are in
`tests/output_formats/other_results/`.

```
python -m pypasmo --tap-ace --name hello hello_ace.asm hello_ace.tap
```

### The Ace tape

The tape holds two "bytes" files. Each is a header block (type 32, name of 10 characters,
length, load address, 10 spaces) and a data block; each block has its length (with the
check byte) before it and the XOR of its bytes after it. The names come from `--name` or
the output file name without its directory.

### The Ace loader trick

- The first file (the name up to the first dot) is 32 bytes for 22E0h, the input line on
  the screen: the command `0 0 BLOAD code <start> CALL`.
- So `0 0 BLOAD hello` loads it, then Forth runs that line: it loads the code (the file
  `code`) and calls it (start = `END`, else the load address).
- The loader needs an emulator that loads the tape through the ROM (`0 0 BLOAD name`
  typed in Forth); an emulator that puts "bytes" files into the memory itself never runs
  the command of the loader.

### The Ace code

- The code returns to Forth with `JP (IY)`.
- Code below 2000h (the ROM) is an error.
- The example code is at 4000h, so it needs the 16K RAM pack.

### Trying the Jupiter Ace in an emulator

**File:** `tests/output_formats/other_results/hello_ace.tap` (**IN DEVELOPMENT**)

No online emulator that loads the tape through the ROM was found. The page
jupiteraceemulator.com puts the files into the memory directly, so the loader does not work
there.

**Desktop:** EightyOne (Windows, open source, Mike Wynne; it emulates the ZX80, ZX81,
Spectrum and Ace; download from
[Spectrum Computing](https://www.spectrumcomputing.co.uk/tool/54/EightyOne)):

1. Options → Hardware → **Jupiter Ace**, memory at least **19K** (the 16K RAM pack: the
   code is at 4000h).
2. Open the tape (Tools → Tape Manager, or File → Open Tape…), `hello_ace.tap`.
3. Type `0 0 BLOAD hello` (Enter) and start the tape (if it does not start itself).
4. **Expected result:** the loader is loaded into the input line, Forth runs it, loads the
   code and calls it. On line 4 in inverse `PYPASMO ON THE JUPITER ACE`, two lines lower
   `Hello, World! (Forth: JP (IY))`, then Forth answers `OK`.
