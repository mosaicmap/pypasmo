# Debugging with DeZog

Back to the [index](index.md).

[DeZog](https://github.com/maziac/DeZog) is a Z80 debugger for Visual Studio Code. It has
its own ZX Spectrum simulator (`zsim`) and can also connect to the emulators ZEsarUX,
CSpect and MAME. DeZog has no assembler of its own: it reads the debug data that an
assembler writes. pypasmo writes two kinds of it *(pypasmo extension)*:

| Option | What DeZog gets | Machines |
|---|---|---|
| <nobr>`--dbgsym-sld FILE.sld`</nobr> (**recommended**) | stepping and breakpoints directly in the `.asm` source files | ZX Spectrum 48K and 128K (with `BANK`) |
| <nobr>`--dbgsym-list FILE.list`</nobr> | a list file: stepping and breakpoints in this file, the address and bytes of each line | ZX Spectrum 48K only |

- [Step by step: a ZX Spectrum 48K program in VS Code](#step-by-step-a-zx-spectrum-48k-program-in-vs-code)
- [Debugging](#debugging)
- [The 128K](#the-128k)
- [Debugging in the source (`--dbgsym-sld`)](#debugging-in-the-source---dbgsym-sld)
- [Debugging in a list file (`--dbgsym-list`)](#debugging-in-a-list-file---dbgsym-list)
- [WPMEM, LOGPOINT, ASSERTION](#wpmem-logpoint-assertion)
- [Problems](#problems)

## Step by step: a ZX Spectrum 48K program in VS Code

### What you need

- [Visual Studio Code](https://code.visualstudio.com/) with the extension **DeZog**
  (Extensions → search "DeZog" → Install).
- pypasmo installed as the `pypasmo` command (`pipx install .` or `python -m pip install .`
  in the pypasmo folder, see [the README](../README.md#install-and-run)).

The program is loaded into the simulator of DeZog as a snapshot (`--sna-48k`), so it runs
in the state of a 48K Spectrum in Basic, with the ROM; see
[Snapshots](machines/zx-spectrum.md#snapshots).

### The project folder

VS Code must open the **folder** of the project (File → Open Folder), not only the file:

```
hello/
    hello.asm
    .vscode/
        launch.json        how DeZog starts the program
        tasks.json         assembles the program before each start
```

`hello.asm` prints a text and returns to Basic; the comments on the `next` and `text`
lines are DeZog commands (see [below](#wpmem-logpoint-assertion)):

```
; hello.asm: prints a text and returns to Basic
        org 8000h
start:  call 0D6Bh      ; ROM: clear the screen
        ld a,2          ; channel 2 = the upper screen
        call 1601h      ; ROM: open the channel
        ld hl,text
next:   ld a,(hl)       ; LOGPOINT [PRINT] char ${A} from ${HL:hex16}
        or a            ; 0 = end of the text
        ret z           ; back to Basic: "0 OK"
        rst 10h         ; ROM: print the character in A
        inc hl
        jr next
text:   db "Hello from pypasmo!", 13, 0  ; WPMEM text, 3, r
        end start
```

### Assembling

The snapshot and the SLD file, **in the project folder** (the `.sld` has the file names
relative to the current folder, and DeZog looks for them in the project folder):

```
pypasmo --sna-48k --dbgsym-sld hello.sld hello.asm hello.sna
```

With `tasks.json` (below) VS Code runs this command itself before each start.

### `.vscode/launch.json`

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "dezog",
            "request": "launch",
            "name": "DeZog: hello (48K)",
            "remoteType": "zsim",
            "zsim": {
                "preset": "spectrum",
                "memoryModel": "ZX48K"
            },
            "sjasmplus": [
                {
                    "path": "hello.sld",
                    "srcDirs": [""]
                }
            ],
            "load": "hello.sna",
            "preLaunchTask": "pypasmo: hello",
            "startAutomatically": false,
            "rootFolder": "${workspaceFolder}"
        }
    ]
}
```

- `remoteType: "zsim"`: the simulator built into DeZog; `preset: "spectrum"` gives it the
  screen, the keyboard and the ROM of the ZX Spectrum.
- `memoryModel`: `"ZX48K"`; `"ZX128K"` for a program with `BANK` (see
  [The 128K](#the-128k)).
- `sjasmplus`: yes, sjasmplus: pypasmo writes SLD in the format of the sjasmplus
  assembler (`--sld`). `path` is the file of `--dbgsym-sld`; `srcDirs: [""]` means the
  source files are in the project folder.
- `load`: the snapshot that is loaded into the simulator.
- `preLaunchTask`: the `label` of the task in `tasks.json` that assembles the program
  before each start. Without `tasks.json` leave the line out and assemble by hand.
- `startAutomatically: false`: the program stops at its entry point (`END start`).

More configurations (e.g. 48K and 128K) go one after another into `configurations`; VS
Code then lets you choose one at the top of the Run and Debug pane.

### `.vscode/tasks.json`

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "pypasmo: hello",
            "type": "process",
            "command": "pypasmo",
            "args": ["--sna-48k", "--dbgsym-sld", "hello.sld", "hello.asm", "hello.sna"],
            "options": { "cwd": "${workspaceFolder}" },
            "group": "build",
            "presentation": { "reveal": "silent", "clear": true },
            "problemMatcher": {
                "owner": "pypasmo",
                "fileLocation": ["relative", "${workspaceFolder}"],
                "pattern": {
                    "regexp": "^ERROR: (.*):(\\d+): (.*)$",
                    "file": 1,
                    "line": 2,
                    "message": 3
                }
            }
        }
    ]
}
```

- `label` must be the same as `preLaunchTask` in `launch.json`.
- `command` / `args`: the pypasmo command. Without installing pypasmo use
  `"command": "python"` and the path to `run_pypasmo.py` as the first argument, e.g.
  `"args": ["C:/tools/pypasmo/run_pypasmo.py", "--sna-48k", ...]`.
- `options.cwd`: pypasmo runs in the project folder (for the file names in the `.sld`).
- `problemMatcher`: errors of pypasmo (`ERROR: file:line: message`) appear in the
  PROBLEMS pane and as red lines in the source; a click goes to the line. When the
  assembly fails, VS Code asks whether to debug anyway: choose "Show Errors".
- `group: "build"`: **Ctrl+Shift+B** assembles without debugging.

## Debugging

| Key | What it does |
|---|---|
| F5 | start debugging (with `preLaunchTask` it assembles first) / continue to the next breakpoint |
| F10 | step over (a `CALL` runs whole) |
| F11 | step into (into a `CALL`) |
| Shift+F11 | step out (up to the `RET`) |
| F9, or a click left of the line number | a breakpoint in the `.asm` |
| Ctrl+Shift+F5 | restart (with `preLaunchTask` it assembles again) |
| Shift+F5 | stop debugging |

- **After a change of the source** assemble and restart (Ctrl+Shift+F5): DeZog reads the
  `.sld` and the snapshot only at the start.
- **WATCH**: add a label (e.g. `text`); DeZog shows the memory at its address. The
  registers are shown as label + offset too (HL = `text+3`).
- **DEBUG CONSOLE**: the messages of DeZog ("Breakpoint hit @8011h", the T-states since
  the last stop) and the output of `LOGPOINT`; DeZog commands can be typed there
  (`-help`).
- **OUTPUT** (choose "DeZog"): warnings when DeZog reads the `.sld` (it should be empty).
- The simulator shows the Spectrum screen in its own tab; the program runs there and can
  be stopped at any time (F6, Pause).

## The 128K

For a program with `BANK` (code in the 128K RAM banks, see
[Spectrum 128K](machines/zx-spectrum-128k.md#spectrum-128k)):

- assemble with `--sna-128k` instead of `--sna-48k` (the `.sld` then describes the 128K
  memory by itself);
- in `launch.json` use `"memoryModel": "ZX128K"`.

DeZog knows from the paging (port 7FFDh) which bank is at C000h, so it shows the right
source line also when several banks have code at the same address.

## Debugging in the source (`--dbgsym-sld`)

`--dbgsym-sld FILE.sld` writes Source Level Debugging data in the format of sjasmplus
(`--sld`, SLD version 1). With it DeZog steps and stops at breakpoints directly in the
`.asm` source files (also the `INCLUDE`d ones), not in a list file.

- **The ZX Spectrum 48K or 128K**: without `BANK` the file describes the 48K memory, with
  `BANK` the 128K memory (the `Z` line that DeZog takes as ZX48K / ZX128K). With the 128K
  each address has its RAM bank: the `BANK` at C000h-FFFFh, 5 at 4000h-7FFFh, 2 at
  8000h-BFFFh.
- Each instruction has its source file and line (an instruction from a macro: the line
  of the macro call); labels and `EQU` with the line where they are defined.
- The file names are written relative to the current folder, so run pypasmo in the
  folder that DeZog has in `srcDirs` (the workspace folder).
- The format follows the SLD parser of DeZog (`src/labels/sjasmplussldlabelparser.ts`).

## Debugging in a list file (`--dbgsym-list`)

`--dbgsym-list FILE.list` writes a list file in the "revEng" format of DeZog: each line
of code as `ADDR BYTES  label: ; source line`, the `EQU` constants as `name: EQU value`,
the other source lines as comments. Breakpoints and stepping then work in this file, not
in the `.asm` source. It is useful to see the address and the bytes of each line;
otherwise **`--dbgsym-sld` is recommended**.

```
pypasmo --sna-48k --dbgsym-list hello.list hello.asm hello.sna
```

In `launch.json` instead of `"sjasmplus"` (the rest is the same, `"memoryModel": "ZX48K"`):

```json
"revEng": [{ "path": "hello.list", "reloadOnSave": true }]
```

A line of the list file looks like `8000 CD 6B 0D  start: ; start:  call 0D6Bh`.

- Labels and `EQU`; `DEFL`, `-E` symbols and `LOCAL` / autolocal names are left out;
  `.name` local labels have their full name (`main.loop`).
- Only for the 48K: with `BANK` it is an error (the bank numbers are not written yet).
- Both files at once work too (`--dbgsym-sld hello.sld --dbgsym-list hello.list`);
  `launch.json` then has the section you want to use.
- The format follows the parser of DeZog (`src/labels/reverseengineeringlabelparser.ts`).

## WPMEM, LOGPOINT, ASSERTION

A comment of the source with `WPMEM`, `LOGPOINT` or `ASSERTION` is a DeZog command, with
both `--dbgsym-sld` and `--dbgsym-list`. Each kind is turned on or off in the
BREAKPOINTS pane of VS Code.

| Command | What it does | Example |
|---|---|---|
| `WPMEM [address [, length [, r/w/rw]]]` | a watch point: stops when the program reads / writes the memory (without an address: the address of the line, length 1, rw) | `buf: defs 10 ; WPMEM, 10, w` |
| `LOGPOINT [group] text ${expression}` | does not stop, only prints the text to the DEBUG CONSOLE; the expression can be a register, a label, `b@(HL)` (byte), `w@(HL)` (word), with a format `:hex8`, `:hex16` ... | `; LOGPOINT [PRINT] char ${A} from ${HL:hex16}` |
| `ASSERTION condition` | stops when the condition is **false**; checked **before** the instruction of the line | `; ASSERTION A < 8` |

- `--dbgsym-sld` writes the command with the address of its line (a line without code:
  `$`, the next instruction). `--dbgsym-list` keeps it because the source line is a
  comment in the list file.
- An `ASSERTION` on the line `ld a,c` checks A before the load; put it on the next line.
- `LOGPOINT` groups can be turned on separately: in the BREAKPOINTS pane the pencil at
  "LOGPOINTs", then the names of the groups separated by spaces.
- DeZog reads the commands only at the start; after a change restart (Ctrl+Shift+F5).
- A comment that only mentions one of these words (`; a LOGPOINT would help here`) is
  taken as a command too, so do not use them otherwise in comments.
- The simulator `zsim` knows all three; with other emulators see the DeZog documentation.

## Problems

- **The line is not highlighted in the source / a breakpoint stays grey:** the `.sld` is
  old (assemble again and restart), or pypasmo did not run in the project folder (wrong
  file names in the `.sld`), or `"srcDirs": [""]` is missing.
- **"Unsupported sjasmplus memory model":** the `.sld` is from another assembler or
  damaged.
- **A program with `BANK` and `"memoryModel": "ZX48K"`:** the banks are not told apart;
  use `"ZX128K"` and `--sna-128k`.
- **A label in WATCH shows strange values:** DeZog shows the memory at the address of the
  label, not the address itself; while the program runs it shows "not available".
- **"pypasmo" is not found when the task runs:** pypasmo is not installed or not on the
  PATH of VS Code; use `python` and `run_pypasmo.py` in `tasks.json` (see above), or
  restart VS Code after the installation.
