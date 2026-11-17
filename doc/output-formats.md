# Output formats

Back to the [index](index.md).

One option on the command line selects the format of the output file; without one it is
`--bin`. The machine pages describe the formats in detail and how to try the files in an
emulator.

## All output options

| Option | Machine | File | Meaning | Status | Page |
|---|---|---|---|---|---|
| <nobr>`--bin`</nobr> (default) | any | `.bin` | raw binary from the lowest to the highest used address | | [here](#raw-binary-and-intel-hex) |
| <nobr>`--hex`</nobr> | any | `.hex` | Intel HEX | | [here](#raw-binary-and-intel-hex) |
| <nobr>`--tap-48k`</nobr> <nobr>(`--tap`)</nobr> | ZX Spectrum | `.tap` | a CODE header and a data block | the same bytes as Pasmo 0.5.5 | [ZX Spectrum](machines/zx-spectrum.md#tapes) |
| <nobr>`--tap-wloader-48k`</nobr> <nobr>(`--tapbas`)</nobr> | ZX Spectrum | `.tap` | a Basic loader and the code | the same bytes as Pasmo 0.5.5 | [ZX Spectrum](machines/zx-spectrum.md#tapes) |
| <nobr>`--tzx-48k`</nobr> <nobr>(`--tzx`)</nobr> | ZX Spectrum | `.tzx` | the blocks of <nobr>`--tap-48k`</nobr> | the same bytes as Pasmo 0.5.5 | [ZX Spectrum](machines/zx-spectrum.md#tapes) |
| <nobr>`--tzx-wloader-48k`</nobr> <nobr>(`--tzxbas`)</nobr> | ZX Spectrum | `.tzx` | the blocks of <nobr>`--tap-wloader-48k`</nobr> | the same bytes as Pasmo 0.5.5 | [ZX Spectrum](machines/zx-spectrum.md#tapes) |
| <nobr>`--pzx-48k`</nobr> | ZX Spectrum | `.pzx` | the blocks of <nobr>`--tap-48k`</nobr> *(pypasmo extension)* | *(early version)* | [ZX Spectrum](machines/zx-spectrum.md#tapes) |
| <nobr>`--pzx-wloader-48k`</nobr> | ZX Spectrum | `.pzx` | the blocks of <nobr>`--tap-wloader-48k`</nobr> *(pypasmo extension)* | *(early version)* | [ZX Spectrum](machines/zx-spectrum.md#tapes) |
| <nobr>`--tap-128k`</nobr> <nobr>(`--tap128`)</nobr> | ZX Spectrum 128K | `.tap` | a CODE block for each RAM bank | *(from the 0.5.5.paged fork)*, *(early version)* | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-output) |
| <nobr>`--tap-wloader-128k`</nobr> <nobr>(`--tapbas128`)</nobr> | ZX Spectrum 128K | `.tap` | the same with a Basic loader that pages the banks in | *(from the 0.5.5.paged fork)*, *(early version)* | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-output) |
| <nobr>`--tzx-128k`</nobr> | ZX Spectrum 128K | `.tzx` | the blocks of <nobr>`--tap-128k`</nobr> *(pypasmo extension)* | **IN DEVELOPMENT** | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-output) |
| <nobr>`--tzx-wloader-128k`</nobr> | ZX Spectrum 128K | `.tzx` | the blocks of <nobr>`--tap-wloader-128k`</nobr> *(pypasmo extension)* | **IN DEVELOPMENT** | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-output) |
| <nobr>`--pzx-128k`</nobr> | ZX Spectrum 128K | `.pzx` | the blocks of <nobr>`--tap-128k`</nobr> *(pypasmo extension)* | **IN DEVELOPMENT** | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-output) |
| <nobr>`--pzx-wloader-128k`</nobr> | ZX Spectrum 128K | `.pzx` | the blocks of <nobr>`--tap-wloader-128k`</nobr> *(pypasmo extension)* | **IN DEVELOPMENT** | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-output) |
| <nobr>`--sna-48k`</nobr> | ZX Spectrum 48K | `.sna` | snapshot, runs at once *(pypasmo extension)* | *(early version)* | [ZX Spectrum](machines/zx-spectrum.md#snapshots) |
| <nobr>`--z80-48k`</nobr> | ZX Spectrum 48K | `.z80` | snapshot (version 3, compressed) *(pypasmo extension)* | *(early version)* | [ZX Spectrum](machines/zx-spectrum.md#snapshots) |
| <nobr>`--sna-128k`</nobr> | ZX Spectrum 128K | `.sna` | snapshot with the banks of `BANK` *(pypasmo extension)* | *(early version)* | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-snapshots) |
| <nobr>`--z80-128k`</nobr> | ZX Spectrum 128K | `.z80` | snapshot (version 3, compressed) *(pypasmo extension)* | *(early version)* | [ZX Spectrum 128K](machines/zx-spectrum-128k.md#128k-snapshots) |
| <nobr>`--plus3dos`</nobr> | ZX Spectrum +3 | any | +3DOS disk file (128 byte header) | *(early version)*, the same bytes as Pasmo 0.5.5 | [ZX Spectrum +3](machines/zx-spectrum-128k.md#spectrum-3) |
| <nobr>`--dsk-plus3`</nobr> | ZX Spectrum +3 | `.dsk` | disk image with the code and a Basic loader *(pypasmo extension)* | *(early version)* | [ZX Spectrum +3](machines/zx-spectrum-128k.md#spectrum-3) |
| <nobr>`--p-zx81`</nobr> | ZX81 | `.p` | the code in a REM line, runs at once *(pypasmo extension)* | *(early version)* | [ZX81](machines/zx81.md) |
| <nobr>`--amsdos`</nobr> | Amstrad CPC | `.bin` | disk file with an Amsdos header | | [Amstrad CPC](machines/amstrad-cpc.md) |
| <nobr>`--cdt`</nobr> | Amstrad CPC | `.cdt` | tape image | *(early version)*, the same bytes as Pasmo 0.5.5 | [Amstrad CPC](machines/amstrad-cpc.md) |
| <nobr>`--cdt-wloader`</nobr> <nobr>(`--cdtbas`)</nobr> | Amstrad CPC | `.cdt` | tape image with a Locomotive Basic loader | *(early version)*, the same bytes as Pasmo 0.5.5 | [Amstrad CPC](machines/amstrad-cpc.md#basic-loader---cdt-wloader) |
| <nobr>`--sna-cpc6128`</nobr> | Amstrad CPC 6128 | `.sna` | snapshot in Basic, runs at once *(pypasmo extension)* | *(early version)* | [Amstrad CPC](machines/amstrad-cpc.md#snapshots---sna-cpc6128---sna-cpc464) |
| <nobr>`--sna-cpc464`</nobr> | Amstrad CPC 464 | `.sna` | snapshot in Basic, runs at once *(pypasmo extension)* | *(early version)* | [Amstrad CPC](machines/amstrad-cpc.md#snapshots---sna-cpc6128---sna-cpc464) |
| <nobr>`--dsk-cpc`</nobr> | Amstrad CPC | `.dsk` | disk image with the Amsdos file *(pypasmo extension)* | *(early version)* | [Amstrad CPC](machines/amstrad-cpc.md#disk-image---dsk-cpc) |
| <nobr>`--msx`</nobr> | MSX | any | file for `BLOAD "file",R` | the same bytes as Pasmo 0.5.5 | [MSX](machines/msx.md) |
| <nobr>`--rom-msx`</nobr> | MSX | `.rom` | cartridge ROM, 8/16/32 KB *(pypasmo extension)* | *(early version)* | [MSX](machines/msx.md#cartridge-rom---rom-msx) |
| <nobr>`--cas-msx`</nobr> | MSX | `.cas` | tape image for `BLOAD "CAS:",R` *(pypasmo extension)* | | [MSX](machines/msx.md#tape-image---cas-msx) |
| <nobr>`--dsk-msx`</nobr> | MSX | `.dsk` | disk image 720 KB, `AUTOEXEC.BAS` runs the code *(pypasmo extension)* | *(early version)* | [MSX](machines/msx.md#disk-image---dsk-msx) |
| <nobr>`--tap-ace`</nobr> | Jupiter Ace | `.tap` | a loader and the code *(pypasmo extension)* | **IN DEVELOPMENT** | [Jupiter Ace](machines/other.md#jupiter-ace) |
| <nobr>`--kcc-kc85`</nobr> | Robotron KC 85/2-4 | `.kcc` | file with autostart *(pypasmo extension)* | *(early version)* | [Robotron](machines/other.md#robotron-kc-85-z-1013) |
| <nobr>`--z80-z1013`</nobr> | Robotron Z 1013 | `.z80` | headersave file *(pypasmo extension)* | *(early version)* | [Robotron](machines/other.md#robotron-kc-85-z-1013) |
| <nobr>`--rom-sms`</nobr> | Sega Master System | `.sms` | 32 KB cartridge ROM with the header checksum *(pypasmo extension)* | *(early version)* | [Sega](machines/other.md#sega-master-system-game-gear) |
| <nobr>`--rom-gg`</nobr> | Sega Game Gear | `.gg` | the same for the Game Gear *(pypasmo extension)* | *(early version)* | [Sega](machines/other.md#sega-master-system-game-gear) |
| <nobr>`--prl`</nobr> | CP/M Plus | `.prl` / `.rsx` | relocatable file | *(early version)* | [Other](machines/other.md#cpm-plus) |
| <nobr>`--cas-trs`</nobr> | TRS-80 Model I / III | `.cas` | SYSTEM tape (500 baud), loaded from BASIC *(pypasmo extension)* | **IN DEVELOPMENT** | [TRS-80](machines/other.md#from-a-tape---cas-trs) |
| <nobr>`--trs`</nobr> | TRS-80 Model I / III / 4 | `.cmd` | `/CMD` file: load records and the entry point | *(early version)*, the same bytes as Pasmo 0.5.5 | [TRS-80](machines/other.md#trs-80) |
| <nobr>`--mzf`</nobr> | Sharp MZ-700 / MZ-800 | `.mzf` | tape file *(pypasmo extension)* | *(early version)* | [Other](machines/other.md#sharp-mz-700-mz-800) |
| <nobr>`--dsk-pcw`</nobr> | Amstrad PCW | `.dsk` | disk image with the CP/M program `NAME.COM` *(pypasmo extension)* | **IN DEVELOPMENT** | [Amstrad PCW](machines/other.md#amstrad-pcw) |
| <nobr>`--rom-coleco`</nobr> | ColecoVision | `.col` | cartridge ROM from 8000h *(pypasmo extension)* | **IN DEVELOPMENT** | [ColecoVision](machines/other.md#colecovision) |

The names with the machine (`--tap-48k` ...) are pypasmo's main names; the Pasmo / fork
names in brackets work the same, so old build scripts need no change.

The name in the tape and disk headers comes from `--name` or the output file name, see
[Header name](command-line.md#header-name).

Not supported: the Pasmo formats `--cmd` (CP/M-86) and `--sdrel` (object file for the SDCC
linker), see [Differences](pasmo-differences.md#not-supported).

## Raw binary and Intel HEX

| Option | Output |
|---|---|
| <nobr>`--bin`</nobr> | raw binary from the lowest to the highest used address, gaps filled with zeros (default) |
| <nobr>`--hex`</nobr> | Intel HEX, 16 bytes per record, CRLF line ends; the end record holds the entry point from `END` |

- A source without code gives an empty `--bin` file (Pasmo writes 2 zero bytes).
- Code that fills the whole 64 KB: `--bin` and `--hex` write all of it (Pasmo writes an
  empty file / only the end record); the tape and disk formats give an error.
- A normal CP/M program (`.COM`) needs no special format: `ORG 100h` and `--bin`, see
  [Other machines](machines/other.md#cpm-plus).

## Disk images (`--dsk-cpc`, `--dsk-plus3`, `--dsk-pcw`, `--dsk-msx`)

`--dsk-cpc`, `--dsk-plus3` and `--dsk-pcw` write an Extended DSK image, the format of CPC and Spectrum +3 emulators: 40 tracks,
1 side, 9 sectors of 512 bytes per track (180 KB), the CP/M file system of the machine
(1 KB blocks, a directory of 64 entries in 2 blocks, an entry for each 16 KB of a file).
The file name is `--name` or the output file name without its directory, up to the first
character that is not a letter or a digit, upper case, 8 characters at most, with the
extension `BIN` (`out/hello.dsk` -> `HELLO.BIN`; `HELLO.COM` with `--dsk-pcw`).

The layouts are described on the machine pages:
[`--dsk-cpc`](machines/amstrad-cpc.md#disk-image---dsk-cpc),
[`--dsk-plus3`](machines/zx-spectrum-128k.md#spectrum-3),
[`--dsk-pcw`](machines/other.md#amstrad-pcw) (the disk format of the +3).

`--dsk-msx` is different: a raw 720 KB image (no DSK header) with the FAT12 file system
of MSX-DOS, the same file name rules and an `AUTOEXEC.BAS` that runs the code, see
[MSX](machines/msx.md#disk-image---dsk-msx).

## Example files

The example sources are in `tests/output_formats/<machine>/`, the files made from them in
`tests/output_formats/<machine>_results/` (the header of each source gives the command).
How to try each file in an emulator is on the machine pages.

| Machine | Source | Files |
|---|---|---|
| <nobr>ZX Spectrum 48K</nobr>, +3 | `tests/output_formats/zx_spectrum/hello_spectrum.asm` | `hello_spectrum.tap`, `.tzx`, `.pzx`, `.sna`, `.z80`, `.dsk` |
| <nobr>ZX Spectrum 128K</nobr> | `tests/output_formats/zx_spectrum/hello_spectrum128.asm` | `hello_spectrum128.tap`, `.tzx`, `.pzx`, `.sna`, `.z80` |
| ZX81 | `tests/output_formats/zx81/hello_zx81.asm` | `hello_zx81.p` |
| <nobr>Amstrad CPC</nobr> | `tests/output_formats/cpc/hello_cpc.asm` | `hello_cpc.bin`, `.cdt`, `hello_cpc_bas.cdt`, `hello_cpc.dsk`, `hello_cpc6128.sna`, `hello_cpc464.sna` |
| MSX | `tests/output_formats/msx/hello_msx.asm`, `hello_msx_rom.asm` | `hello_msx.cas`, `hello_msx.dsk`, `hello_msx_rom.rom` |
| TRS-80 | `tests/output_formats/other/hello_trs80_tape.asm`, `hello_trs80.asm` | `hello_trs80.cas`, `hello_trs80.cmd` |
| <nobr>Jupiter Ace</nobr> | `tests/output_formats/other/hello_ace.asm` | `hello_ace.tap` |
| Robotron | `tests/output_formats/other/hello_kc85.asm`, `hello_z1013.asm` | `hello_kc85.kcc`, `hello_z1013.z80` |
| Sega | `tests/output_formats/other/hello_sms.asm`, `hello_gg.asm` | `hello_sms.sms`, `hello_gg.gg` |
| <nobr>Amstrad PCW</nobr> | `tests/output_formats/other/hello_pcw.asm` | `hello_pcw.dsk` |
| ColecoVision | `tests/output_formats/other/hello_coleco.asm` | `hello_coleco.col` |
