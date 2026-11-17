"""Run a Spectrum +3 with a .dsk image in drive A: (development tool, SkoolKit).

For --dsk-plus3: "Loader" loads the Basic loader DISK, which loads and runs the code.
The same tool is in zxs_bas2tap (tools/devel/plus3run.py).

The +3 (its 4 ROMs: plus3-0.rom ... plus3-3.rom in ROMDIR, e.g. taken from JSpeccy) boots
in the Python simulator of SkoolKit; a small uPD765 floppy controller reads the sectors of
the image (only reading: READ DATA, READ ID, SEEK, RECALIBRATE, SENSE ...). Then the keys
are pressed (default ENTER = "Loader" in the menu: loads and runs the file DISK), "/"
makes a pause of 2 seconds, and after some seconds the screen is printed (characters of
the ROM font, else '?'). About 10 s for a run.

Usage:
    PYTHONPATH=DIR python tools/devel/plus3run.py ROMDIR image.dsk [--log] [KEYS ...]

    plus3run.py roms hello_spectrum.dsk            Loader
    plus3run.py roms game.dsk CS+6 / ENTER / l o a d SPACE '"' g a m e '"' ENTER
                                                   +3 BASIC, LOAD "game"
(Git Bash: MSYS_NO_PATHCONV=1, else "/" becomes a path.) The keys are SkoolKit names.
Not emulated: writing to the disk, the all-RAM paging modes (ROM space is read-only in
the simulator), timing of the drive.
"""

import sys
from pathlib import Path

from skoolkit.kbtracer import get_keys
from skoolkit.simulator import Simulator

FRAME = 70908
SPECIAL = ((0, 1, 2, 3), (4, 5, 6, 7), (4, 5, 6, 3), (4, 7, 6, 3))


class Disk:
    """Extended DSK image: {(track, sector id): bytes}."""

    def __init__(self, data):
        assert data[:8] == b"EXTENDED", "only extended DSK"
        tracks, sides = data[0x30], data[0x31]
        sizes = data[0x34:0x34 + tracks * sides]
        self.sectors = {}
        self.first = {}
        pos = 256
        for t in range(tracks * sides):
            info = data[pos:pos + 256]
            assert info[:10] == b"Track-Info", info[:12]
            n = info[0x15]
            spos = pos + 256
            for s in range(n):
                c, h, r, nn = info[0x18 + 8 * s:0x18 + 8 * s + 4]
                length = info[0x18 + 8 * s + 6] | info[0x18 + 8 * s + 7] << 8
                self.sectors[(c, r)] = data[spos:spos + length]
                self.first.setdefault(c, r)
                spos += length
            pos += sizes[t] * 256
        self.tracks = tracks


class FDC:
    LENGTHS = {0x03: 3, 0x04: 2, 0x07: 2, 0x08: 1, 0x0F: 3, 0x0A: 2, 0x06: 9, 0x0C: 9}

    def __init__(self, disk, log):
        self.disk = disk
        self.log = log
        self.cyl = 0
        self.command = []
        self.data = []
        self.result = []
        self.seek_end = None

    def status(self):
        if self.data:
            return 0xF0
        if self.result:
            return 0xD0
        return 0x90 if self.command else 0x80

    def read(self):
        if self.data:
            value = self.data.pop(0)
            if not self.data:
                self.log.append("  read done")
            return value
        if self.result:
            return self.result.pop(0)
        return 0xFF

    def write(self, value):
        self.command.append(value)
        code = self.command[0] & 0x1F
        if len(self.command) < self.LENGTHS.get(code, 1):
            return
        cmd, self.command = self.command, []
        unit = cmd[1] & 3 if len(cmd) > 1 else 0
        self.log.append("FDC %s" % " ".join("%02X" % b for b in cmd))
        if code == 0x03:                                # SPECIFY
            pass
        elif code == 0x04:                              # SENSE DRIVE STATUS
            st3 = unit | (0x20 | (0x10 if self.cyl == 0 else 0) if unit == 0 else 0)
            self.result = [st3]
        elif code == 0x07:                              # RECALIBRATE
            if unit == 0:
                self.cyl = 0
            self.seek_end = (0x20 | unit) if unit == 0 else (0x68 | unit)
        elif code == 0x0F:                              # SEEK
            if unit == 0:
                self.cyl = cmd[2]
            self.seek_end = (0x20 | unit) if unit == 0 else (0x68 | unit)
        elif code == 0x08:                              # SENSE INTERRUPT STATUS
            if self.seek_end is None:
                self.result = [0x80]
            else:
                self.result = [self.seek_end, self.cyl]
                self.seek_end = None
        elif code == 0x0A:                              # READ ID
            if unit != 0:
                self.result = [0x48 | unit, 0, 0, 0, 0, 0, 0]
            else:
                r = self.disk.first.get(self.cyl, 1)
                self.result = [unit, 0, 0, self.cyl, 0, r, 2]
        elif code in (0x06, 0x0C):                      # READ DATA
            c, h, r, n, eot = cmd[2:7]
            if unit != 0:
                self.result = [0x48 | unit, 0, 0, c, h, r, n]
                return
            data = []
            for sector in range(r, eot + 1):
                part = self.disk.sectors.get((self.cyl, sector))
                if part is None:
                    self.result = [0x40 | unit, 0x04, 0, c, h, sector, n]
                    self.log.append("  no sector %d/%d" % (self.cyl, sector))
                    return
                data += part
            self.data = list(data)
            self.result = [0x40 | unit, 0x80, 0, c, h, eot, n]   # (end of cylinder: no TC)
        else:
            self.result = [0x80]


class Memory:
    """64 KB seen by the Z80: 4 slots of 16 KB, each a ROM or a RAM bank (shared lists)."""

    def __init__(self, slots):
        self.slots = slots

    def __getitem__(self, index):
        return self.slots[index >> 14][index & 0x3FFF]

    def __setitem__(self, index, value):
        self.slots[index >> 14][index & 0x3FFF] = value

    def __len__(self):
        return 0x10000


class Plus3:
    def __init__(self, romdir, disk_data, keys):
        self.roms = [list(Path(romdir, "plus3-%d.rom" % i).read_bytes()) for i in range(4)]
        self.banks = [[0] * 16384 for _ in range(8)]
        self.memory = Memory([None] * 4)
        self.o7ffd = 0
        self.o1ffd = 0
        self.log = []
        self.fdc = FDC(Disk(disk_data), self.log)
        self.keys = keys
        self.page()

    def page(self):
        if self.o1ffd & 1:
            self.memory.slots[:] = [self.banks[b] for b in SPECIAL[(self.o1ffd >> 1) & 3]]
            self.log.append("special paging %02X" % self.o1ffd)
        else:
            rom = ((self.o1ffd >> 1) & 2) | ((self.o7ffd >> 4) & 1)
            self.memory.slots[:] = [self.roms[rom], self.banks[5], self.banks[2],
                                    self.banks[self.o7ffd & 7]]

    def read_port(self, registers, port):
        if port & 0xF002 == 0x2000:
            return self.fdc.status()
        if port & 0xF002 == 0x3000:
            return self.fdc.read()
        if port & 1 == 0 and self.keys:
            kb = self.keys[0]
            if port in kb:
                return kb.pop(port)
        return 0xFF

    def write_port(self, registers, port, value, offset):
        if port & 0xC002 == 0x4000:
            if not self.o7ffd & 0x20:
                self.o7ffd = value
                self.page()
        elif port & 0xF002 == 0x1000:
            self.o1ffd = value
            self.page()
        elif port & 0xF002 == 0x3000:
            self.fdc.write(value)

    def run(self, seconds):
        if not hasattr(self, "sim"):
            self.sim = Simulator(self.memory, {'PC': 0}, {'tstates': 0},
                                 {'frame_duration': FRAME, 'int_active': 32})
            self.sim.set_tracer(self)
        sim = self.sim
        registers, opcodes, memory = sim.registers, sim.opcodes, self.memory
        timeout = registers[25] + seconds * 50 * FRAME
        pc = registers[24]
        while registers[25] < timeout:
            opcodes[memory[pc]]()
            if registers[26] and registers[25] % FRAME < 32:
                if sim.accept_interrupt(registers, memory, pc) and self.keys and not self.keys[0]:
                    self.keys.pop(0)
            pc = registers[24]

    def screen(self):
        self.page()                                 # (memory -> banks)
        screen = self.banks[7 if self.o7ffd & 8 else 5]
        font = self.roms[3][0x3D00:0x4000]
        rows = []
        for row in range(24):
            text = ""
            for col in range(32):
                cells = [screen[(y & 0xC0) << 5 | (y & 7) << 8 | (y & 0x38) << 2 | col]
                         for y in range(row * 8, row * 8 + 8)]
                for c in range(96):
                    if font[c * 8:c * 8 + 8] == cells:
                        text += chr(32 + c)
                        break
                else:
                    text += "?"
            rows.append(text.rstrip())
        return rows


def main(args):
    args = list(args)
    log = "--log" in args
    if log:
        args.remove("--log")
    if len(args) < 2:
        sys.exit(__doc__)
    romdir, image = args[:2]
    keys = args[2:] or ["ENTER"]
    p3 = Plus3(romdir, Path(image).read_bytes(), [])
    p3.run(4)                                       # (boot to the menu)
    for group in " ".join(keys).split(" / "):
        p3.keys = get_keys(group.split(), 13)
        p3.run(2 + len(p3.keys) // 50)
    p3.run(12)
    print("\n".join(p3.screen()).strip("\n"))
    if log:
        print("\n".join(p3.log))


if __name__ == "__main__":
    main(sys.argv[1:])
