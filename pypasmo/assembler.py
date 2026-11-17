# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""The assembler: passes, symbols, source files, directives, macros, conditional assembly."""
import re
from pathlib import Path

from .common import (BLOCK_END, BLOCK_START, DIRECTIVES, EXT_DIRECTIVES, FORK_DIRECTIVES, MNEMONICS, ZX81_CODES,
                     RESERVED, AsmError, readable, split_tap)
from .expr import Expr
from .lexer import after_keyword, lex, split_commas, split_text_args, subst_idents
from .z80 import Z80Encoder, parse_operand, tstates

MAX_ERRORS = 10
# An error in one of these lines breaks the block structure: the pass stops at once
# (going on would only give follow-up errors).
STOP_WORDS = {"IF", "IFDEF", "IFNDEF", "IFB", "IFNB", "ELSE", "ELSEIF", "ENDIF", "MACRO", "ENDM", "EXITM", "REPT", "IRP",
              "DUP", "EDUP", "PROC", "ENDP", "STRUCT", "ENDS", "PHASE", ".PHASE", "DEPHASE",
              ".DEPHASE", "END"}


MAX_NESTING = 1000      # MACRO / REPT / IRP levels (a recursive macro without an end)


def strip_line_number(text):
    """A line number from old assemblers before the statement ("10 db 1") is ignored."""
    return re.sub(r"^[0-9]+", "", text) if re.match(r"^[0-9]+\s", text) else text


class StopPass(Exception):
    """Too many errors, or an error that the pass can not go on after."""


class Frame:
    """A source of lines: the main file, an expanded macro, REPT or IRP."""

    def __init__(self, lines, kind="file", subst=None, reps=1, on_iter=None):
        self.lines, self.kind, self.subst = lines, kind, subst
        self.i, self.reps, self.on_iter = 0, reps, on_iter
        self.cond_depth = 0
        self.scope_depth = 0


class Assembler(Z80Encoder):
    """Two (or more) pass assembler. After assemble(): mem {address: byte}, symbols,
    entry (address from END or None), warnings, listing, publics."""

    def __init__(self, nocase=False, include_dirs=(), predefined=None, bracket=False,
                 alocal=False, w8080=False, werror=False, pasmo_syntax=False, base=0):
        # the arguments, to assemble the same source again (--prl)
        self.options = dict(nocase=nocase, include_dirs=include_dirs, predefined=predefined,
                            bracket=bracket, alocal=alocal, w8080=w8080, werror=werror,
                            pasmo_syntax=pasmo_syntax)
        # --pasmo-syntax-055: no EXT_DIRECTIVES and INCBIN offset, FORK_DIRECTIVES are names
        self.pasmo_syntax = pasmo_syntax
        off = FORK_DIRECTIVES if pasmo_syntax else set()
        self.reserved = RESERVED - off
        self.keywords = (MNEMONICS | DIRECTIVES) - off
        self.block_start, self.block_end = BLOCK_START - off, BLOCK_END - off
        self.start_pc = base     # address at the start of each pass (--prl: 0 and 100h)
        self.nocase = nocase
        self.include_dirs = [Path(d) for d in include_dirs]
        self.predefined = {self.norm(k): v & 0xFFFF for k, v in (predefined or {}).items()}
        self.bracket = bracket
        self.alocal = alocal
        self.w8080 = w8080
        self.werror = werror
        self.symbols = dict(self.predefined)
        self.symkind = {k: "equ" for k in self.predefined}
        self.label_bank = {}     # label: its 128K RAM bank (BANK_OF), None outside the RAM
        self.label_loc = {}      # label: ("file:line" where it is defined, BANK) (--dbgsym-sld)
        self.src_files = {}      # file name in "file:line": the path of the file
        self.warnings = []

    # ---------- symbols ----------
    def norm(self, name):
        return name.upper() if self.nocase else name

    def resolve(self, name):
        """Internal name of a symbol: LOCAL / autolocal names get a unique hex name,
        .name (pypasmo extension) belongs to the previous label: main.name; in a macro it
        is local to the expansion, like LOCAL."""
        name = self.norm(name)
        if self.dot_local(name):
            for f in reversed(self.frames):
                if f.kind == "macro":
                    scope = self.scopes[f.scope_depth]
                    if name not in scope:
                        scope[name] = self.local_name()
                    return scope[name]
            return self.last_label + name
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if self.alocal and name.startswith("_"):
            key = (self.alocal_block, name)
            if key not in self.autolocals:
                self.autolocals[key] = self.local_name()
            return self.autolocals[key]
        return name

    def dot_local(self, name):
        """A .name local label? (with --pasmo-syntax-055 a normal name, as in Pasmo)"""
        return name.startswith(".") and len(name) > 1 and not self.pasmo_syntax

    def end_autolocal_block(self):
        self.alocal_block += 1

    def is_defined(self, name):
        r = self.resolve(name)
        return r in self.defined_now or r in self.predefined

    def get_symbol(self, name, required, ignored):
        r = self.resolve(name)
        # a required value (ORG, DS, IF ...) must be defined above, as in Pasmo; the value
        # of a later definition from the previous pass is only for code
        if r in self.symbols and (r in self.defined_now or not required and self.symkind.get(r) != "defl"):
            return self.symbols[r]
        if ignored:
            return 0
        if required or self.final:
            raise AsmError(f"undefined symbol {name}")
        return 0

    def define(self, name, value, kind, dollar=False):
        """kind: 'label', 'equ' or 'defl'. dollar=True: the name was written with '$'
        (like h$l) and may match a reserved word."""
        if not dollar and self.norm(name).upper() in self.reserved:
            raise AsmError(f"{name} is a reserved word")
        n = self.norm(name)
        if self.alocal and not n.startswith("_") and not self.dot_local(n):
            self.end_autolocal_block()       # a normal label ends the autolocal block
        r = self.resolve(name)
        if kind == "label" and r == n and not self.dot_local(n):
            self.last_label = n              # scope of the .name labels (not LOCAL ones)
        value &= 0xFFFF
        if kind == "defl":
            if r in self.defined_now and self.symkind.get(r) != "defl":
                raise AsmError(f"{name} is already defined, but not with DEFL")
        else:
            if r in self.defined_now:
                raise AsmError(f"symbol {name} is defined twice")
            old = self.prev.get(r) if self.final and self.prev else None
            if old is not None and old != value:
                raise AsmError(f"phase error: {name} was {old:04X}h in the previous pass, "
                               f"now {value:04X}h")
        self.symbols[r] = value
        self.symkind[r] = kind
        self.defined_now.add(r)
        if self.final and kind in ("label", "equ"):
            self.label_loc[r] = (self.top_loc(), self.bank)
        if kind == "label":
            if self.final:
                self.routine = [name, 0]                 # the listing sums from here to RET
            load = (value + self.phase_off) & 0xFFFF     # BANK_OF: where the bytes are loaded
            self.label_bank[r] = (self.bank if load >= 0xC000 else 2 if load >= 0x8000
                                  else 5 if load >= 0x4000 else None)

    def bank_of(self, name, required, ignored):
        """BANK_OF label (pypasmo extension): the ZX Spectrum 128K RAM bank of a label: the
        BANK at C000h-FFFFh, 5 at 4000h-7FFFh, 2 at 8000h-BFFFh (with PHASE: the load address)."""
        self.get_symbol(name, required, ignored)         # an undefined label: as in a value
        r = self.resolve(name)
        if r not in self.symbols:
            return 0
        if self.symkind.get(r) != "label":
            raise AsmError(f"BANK_OF {name}: not a label")
        if self.label_bank.get(r) is None:
            raise AsmError(f"BANK_OF {name}: {self.symbols[r]:04X}h is not in a RAM bank")
        return self.label_bank[r]

    def local_name(self):
        """Next internal name of a local symbol: 00000000, 00000001 ... (Pasmo)."""
        name = f"{self.local_counter:08X}"
        self.local_counter += 1
        return name

    def check_name(self, toks, what):
        """A name in MACRO, IRP, LOCAL, PUBLIC: one identifier, not a reserved word (as in
        Pasmo: "Identifier expected")."""
        if len(toks) != 1 or toks[0].kind != "id":
            raise AsmError(what)
        if toks[0].up() in self.reserved:
            raise AsmError(f"{what}, {toks[0].val} is a reserved word")
        return toks[0].val

    def new_local(self, name):
        if self.norm(name) in self.scopes[-1]:
            self.warn(f"redeclared LOCAL {name}")      # ignored, like in Pasmo
            return
        self.scopes[-1][self.norm(name)] = self.local_name()

    def expr(self, toks, required=False):
        return Expr(self, toks, required).run()

    def warn(self, msg):
        if self.final:
            self.warnings.append(f"{self.loc}: warning: {msg}")

    # ---------- output ----------
    def emit(self, data, listed=None, t=""):
        if self.final:
            addr = (self.pc + self.phase_off) & 0xFFFF     # where the bytes go (PHASE: not $)
            if max(self.pc, addr) + len(data) > 0x10000:
                self.warn("64KB limit passed")
            for b in data:
                if b is not None:            # None = DB ?, the byte is only skipped
                    if self.screen_file and 0x4000 <= addr < 0x5B00:
                        raise AsmError(f"code at {addr:04X}h overwrites the picture of TAPE_BLOCK_SCREEN")
                    if addr >= 0xC000 and self.bank:         # BANK 1..7 (0 = normal memory)
                        self.banks.setdefault(self.bank, {})[addr] = b & 0xFF
                    else:
                        self.mem[addr] = b & 0xFF
                addr = (addr + 1) & 0xFFFF
                self.pc = (self.pc + 1) & 0xFFFF
            if listed is None:
                listed = ["--" if b is None else b for b in data]
            self.list_line(self.stmt_pc, listed, t)
            self.routine_tstates(data, t)
        else:
            self.pc = (self.pc + len(data)) & 0xFFFF

    def routine_tstates(self, code, t):
        """Listing (pypasmo extension): the T-states of a simple routine, from a label to an
        unconditional RET, RETI or RETN, without jumps, calls, conditions, repeating block
        instructions, HALT and data in between."""
        if self.routine is None:
            return
        op = code[0] if code else None
        if (not t or "/" in t or op in (0xC3, 0x18, 0xCD, 0xE9, 0x76) or op & 0xC7 in (0xC2, 0xC7)
                or op in (0xDD, 0xFD) and code[1] == 0xE9):
            self.routine = None                      # data, a jump, a condition: no sum
            return
        self.routine[1] += int(t)
        if list(code) in ([0xC9], [0xED, 0x4D], [0xED, 0x45]):
            self.routine_totals[len(self.listing) - 1] = tuple(self.routine)
            self.routine = None

    def list_line(self, addr, data, t=""):
        """t: T-states of an instruction (see tstates())."""
        if self.final:
            self.listing.append((addr, data, t, self.cur_text, self.cur_depth))
            self.listing_src[len(self.listing) - 1] = (self.top_loc(), self.bank, self.pc)

    def top_loc(self):
        """"file:line" of the current line in a source file (for a macro: the call)."""
        f = self.frames[0] if self.frames else None
        return f.lines[f.i - 1][0] if f and f.i else self.loc

    # ---------- source files ----------
    def find_file(self, name, rel_to):
        for base in [Path.cwd(), Path(rel_to).parent] + self.include_dirs:
            p = base / name
            if p.is_file():
                return p
        raise AsmError(f"file {name} not found")

    @staticmethod
    def file_arg(text):
        """File name of INCLUDE / INCBIN: "name", 'name' or up to the first blank."""
        text = text.strip()
        if text and text[0] in "'\"":
            end = text.find(text[0], 1)
            if end < 0:
                raise AsmError("unterminated file name")
            name, rest = text[1:end], text[end + 1:]
        else:
            name = re.split(r"[ \t]", text, maxsplit=1)[0]
            rest = text[len(name):]
        if not name:
            raise AsmError("missing file name")
        if rest.strip():
            raise AsmError(f"unexpected text after the file name: {rest.strip()}")
        return name

    def load(self, path, depth=0, text=None):
        """Read a file and expand INCLUDE (Pasmo also does this before the passes)."""
        if depth > 20:
            raise AsmError("INCLUDE nested too deep")
        if text is None:
            # Pasmo works with bytes: latin-1 maps each byte to one character, so
            # strings keep their bytes (a UTF-8 "é" gives C3h A9h, as in Pasmo).
            text = Path(path).read_text(encoding="latin-1")
        lines = []
        name = Path(path).name                       # in messages "file:line"
        if self.src_files.get(name, str(path)) != str(path):
            name = str(path)                         # another file with the same name
        self.src_files.setdefault(name, str(path))
        rows = text.split("\n")                    # not splitlines: it also splits at 85h, 0Ch ...
        if rows and rows[-1] == "":
            rows.pop()
        for no, raw in enumerate(rows, 1):
            raw = raw[:-1] if raw.endswith("\r") else raw
            loc = f"{name}:{no}"
            try:
                toks = lex(strip_line_number(raw))
            except AsmError:
                toks = []
            kw, at = self.keyword(toks)
            if kw == "INCLUDE":
                try:
                    rest = after_keyword(strip_line_number(raw), "INCLUDE")
                    inc = self.find_file(self.file_arg(rest.split(";")[0]), path)
                except AsmError as e:
                    raise AsmError(f"{loc}: {e}") from None
                lines.append((loc, raw, 0))
                lines += self.load(inc, depth + 1)
                continue
            lines.append((loc, raw, 0))
        return lines

    def ext_directive(self, tok):
        """Is the token a pypasmo directive (EXT_DIRECTIVES)? Not with --pasmo-syntax-055 or
        when a macro has the same name."""
        return (tok.kind == "id" and tok.up() in EXT_DIRECTIVES and not self.pasmo_syntax
                and self.norm(tok.val) not in self.macros)

    def keyword(self, toks):
        """Return (directive or mnemonic, its index) of a line, skipping a label."""
        if not toks or toks[0].kind != "id":
            return None, 0
        if toks[0].up() in self.reserved:
            return toks[0].up(), 0
        k = 2 if len(toks) > 1 and toks[1].kind == "op" and toks[1].val == ":" else 1
        if len(toks) > k and toks[k].kind == "id" and toks[k].up() in self.reserved:
            return toks[k].up(), k
        return None, 0

    # ---------- passes ----------
    def assemble(self, path, text=None):
        """Assemble the file `path`; if `text` is given it is used instead of the file content."""
        self.lines = self.load(path, text=text)
        self.path = Path(path)
        self.text = text
        # Repeat the preparation passes while symbol values change (forward references
        # in EQU, even chained ones). Pasmo switches to a 3rd pass for this. Then the
        # final pass generates the code.
        self.prev = None
        for n in range(1, 10):
            self.one_pass(final=False)
            snap = {k: v for k, v in self.symbols.items() if self.symkind.get(k) != "defl"}
            if snap == self.prev:
                break
            self.prev = snap
        else:
            raise AsmError(f"{self.path.name}: symbol values did not settle after {n} passes")
        prep_errors = self.errors
        self.one_pass(final=True)
        # (an error of a preparation pass is never lost, even if the final pass has none)
        errors = self.errors or prep_errors
        if errors:
            if len(errors) > MAX_ERRORS:
                errors = errors[:MAX_ERRORS - 1] + [errors[MAX_ERRORS - 1] + f"\n(stopped after {MAX_ERRORS} errors)"]
            e = AsmError("\n".join(errors))
            e.errors = errors
            raise e
        if self.werror and self.warnings:
            raise AsmError("warnings treated as errors (--werror):\n" + "\n".join(self.warnings))
        return self.mem

    def one_pass(self, final):
        self.final = final
        self.pc = self.stmt_pc = self.start_pc
        self.mem = {}
        self.listing = []
        self.listing_src = {}    # listing index: ("file:line", BANK, $) (--dbgsym-sld)
        self.warnings = []
        self.defined_now = set(self.predefined)
        self.macros = {}
        self.scopes = []         # local name maps (PROC, macro, REPT, IRP)
        self.scope_kind = []
        self.cond = []           # IF stack: [active, branch already taken]
        self.local_counter = 0
        self.last_label = ""     # the label that the .name labels belong to
        self.alocal_block = 0
        self.autolocals = {}
        self.publics = []
        self.bank = 0            # BANK n: bank at C000h-FFFFh (Spectrum 128K)
        self.banks = {}          # {bank: {address: byte}} code at C000h+ in banks 1..7
        self.phased = False      # inside PHASE ... DEPHASE
        self.phase_off = 0       # load address - $
        self.entry = None
        self.displays = []       # DISPLAY texts of the last pass
        self.routine = None      # [label, T-states] of a simple routine (listing)
        self.routine_totals = {}  # listing index of its RET: (label, T-states)
        self.tape_blocks = []     # ("code"|"screen", name, start, length) or ("tap", file, data)
        self.screen_locs = []    # (where, file data or None) of TAPE_BLOCK_SCREEN
        self.screen_file = False  # a TAPE_BLOCK_SCREEN file is at 4000h-5AFFh
        self.frames = [Frame(self.lines)]
        self.errors = []         # "loc: message\n    line" (pypasmo goes on after an error)
        try:
            self.run()
            if self.cond:
                raise AsmError(f"{self.path.name}: missing ENDIF")
            if self.phased:
                raise AsmError(f"{self.path.name}: missing DEPHASE")
            if self.scopes:
                raise AsmError(f"{self.path.name}: missing ENDP")
        except StopPass:
            return
        except AsmError as e:
            self.errors.append(str(e))
        for loc, data in self.screen_locs if final else ():
            if data is None and any(a not in self.mem for a in range(0x4000, 0x5B00)):
                self.warnings.append(f"{loc}: warning: TAPE_BLOCK_SCREEN: the code does not fill 4000h-5AFFh")

    def active(self):
        return all(c[0] for c in self.cond)

    def run(self):
        while self.frames:
            f = self.frames[-1]
            if f.i >= len(f.lines):
                f.reps -= 1
                if f.reps > 0:
                    # Pasmo has one LOCAL level for all repetitions of REPT / IRP
                    # (LOCAL x with a label x inside REPT 2 is an error there too)
                    del self.cond[f.cond_depth:]
                    f.i = 0
                    if f.on_iter:
                        f.on_iter()
                    continue
                self.pop_frame()
                continue
            loc, raw, depth = f.lines[f.i]
            f.i += 1
            text = f.subst(raw) if f.subst else raw
            self.loc, self.cur_text, self.cur_depth = loc, text, len(self.frames) - 1
            try:
                self.statement(text, f)
            except AsmError as e:
                # skip the line and go on (in every pass, so the addresses stay the same)
                self.errors.append(f"{loc}: {e}\n    {readable(text.strip())}")
                if len(self.errors) > MAX_ERRORS or self.stops_pass(text):
                    raise StopPass from None

    @staticmethod
    def stops_pass(text):
        """Is the line one of STOP_WORDS (maybe after a label)?"""
        try:
            toks = lex(strip_line_number(text))
        except AsmError:
            return False
        return any(t.kind == "id" and t.up() in STOP_WORDS for t in toks[:3])

    def open_frame_scope(self, f):
        f.cond_depth = len(self.cond)
        f.scope_depth = len(self.scopes)
        self.scopes.append({})
        self.scope_kind.append("block")

    def close_frame_scope(self, f):
        del self.cond[f.cond_depth:]     # ENDM also closes unterminated IFs
        del self.scopes[f.scope_depth:]
        del self.scope_kind[f.scope_depth:]

    def push_frame(self, f):
        if len(self.frames) > MAX_NESTING:
            raise AsmError(f"MACRO / REPT / IRP nested too deep (more than {MAX_NESTING} levels)")
        self.frames.append(f)
        self.open_frame_scope(f)
        if f.on_iter:
            f.on_iter()

    def pop_frame(self):
        f = self.frames.pop()
        if f.kind != "file":
            self.close_frame_scope(f)
            self.end_autolocal_block()   # ENDM ends an autolocal block

    def collect_block(self, f):
        """Read the body of MACRO / REPT / IRP up to the matching ENDM."""
        body, depth = [], 1
        while f.i < len(f.lines):
            loc, raw, d = f.lines[f.i]
            f.i += 1
            try:
                kw, _ = self.keyword(lex(strip_line_number(raw)))
            except AsmError:
                kw = None
            if kw in self.block_start:
                depth += 1
            elif kw in self.block_end:
                depth -= 1
                if depth == 0:
                    if self.final:
                        self.listing.append((None, [], "", raw, len(self.frames) - 1))
                    return body
            body.append((loc, raw, d))
            if self.final:
                self.listing.append((None, [], "", raw, len(self.frames) - 1))
        raise AsmError("missing ENDM")

    def statement(self, text, frame):
        self.stmt_pc = self.pc
        text = strip_line_number(text)
        # the text after .ERROR / .WARNING / DG is free text, the lexer does not read it
        free = r"\.ERROR|\.WARNING" if self.pasmo_syntax else r"\.ERROR|\.WARNING|DG"
        m = re.match(r"(?i)^(\s*(?:[A-Za-z_?@.][\w?@.$]*:?\s+)?)(" + free + r")(?![\w?@.$])", text)
        try:
            toks = lex(text[:m.end()] if m else text)
        except AsmError:
            if self.active():
                raise
            toks = []                            # skipped IF branch: content does not matter

        # --- conditional assembly (also tracked in skipped branches because of nesting)
        kw, at = self.keyword(toks)
        if (kw is None and toks and toks[0].up() in ("IFB", "IFNB", "ELSEIF") and self.ext_directive(toks[0])
                and not (len(toks) > 1 and (toks[1].kind == "op" and toks[1].val == ":"
                                            or toks[1].up() in ("EQU", "DEFL", "MACRO")))):
            kw, at = toks[0].up(), 0             # IFB, IFNB, ELSEIF (pypasmo extension, not reserved)
        if kw in ("IF", "IFDEF", "IFNDEF", "IFB", "IFNB", "ELSE", "ELSEIF", "ENDIF"):
            arg = toks[at + 1:]
            if kw in ("IF", "IFDEF", "IFNDEF", "IFB", "IFNB"):
                if not self.active():
                    self.cond.append([False, True])
                else:
                    if kw == "IF":
                        v = self.expr(arg, required=True) != 0
                    elif kw in ("IFB", "IFNB"):
                        # IFB text: is the text (a macro argument) blank? also IFB <text>
                        rest = ",".join(split_text_args(after_keyword(text, kw))).strip()
                        if rest[:1] == "<" and rest[-1:] == ">":
                            rest = rest[1:-1].strip()
                        v = (rest == "") == (kw == "IFB")
                    else:
                        if len(arg) != 1 or arg[0].kind != "id":
                            raise AsmError(f"{kw} needs a symbol name")
                        v = self.is_defined(arg[0].val) == (kw == "IFDEF")
                    self.cond.append([v, v])
            elif not self.cond:
                raise AsmError(f"{kw} without IF")
            elif kw == "ELSEIF":
                # ELSEIF expr (pypasmo extension): the branch of the first true condition;
                # not evaluated after a true branch or in a skipped IF (c[1] is True there)
                c = self.cond[-1]
                if len(c) > 2:
                    raise AsmError("ELSEIF after ELSE")
                if c[1]:
                    c[0] = False
                else:
                    c[0] = c[1] = self.expr(arg, required=True) != 0
            elif kw in ("ELSE", "ENDIF") and arg:
                raise AsmError(f"{kw}: end of line expected")
            elif kw == "ELSE":
                c = self.cond[-1]
                c[0], c[1] = not c[1], True
                c[2:] = [True]                   # ELSE seen (for ELSEIF)
            else:
                self.cond.pop()
            self.list_line(None, [])
            return
        if not self.active():
            self.list_line(None, [])
            # like Pasmo: a skipped MACRO / REPT / IRP is skipped up to its ENDM (IF and
            # ENDIF inside it do not count), and ENDM stops the skipping (here: an error)
            if kw in self.block_start:
                self.collect_block(frame)
            elif kw in self.block_end:
                self.d_endm(toks[at + 1:], text, frame)
            return
        if not toks:
            self.list_line(None, [])
            return

        # --- label
        label = None
        pos = 0
        t0 = toks[0]
        if t0.kind == "id" and t0.up() not in self.reserved:
            colon = len(toks) > 1 and toks[1].kind == "op" and toks[1].val == ":"
            defines = len(toks) > 1 and toks[1].up() in ("MACRO", "EQU", "DEFL")
            if colon or defines or self.norm(t0.val) not in self.macros:
                label, pos = t0.val, (2 if colon else 1)
            # "align 4" is the directive, "align: ...", "align equ 4", "align nop" a label
            if (label and not colon and not defines and self.ext_directive(t0)
                    and not (len(toks) > 1 and toks[1].kind == "id" and toks[1].up() in self.keywords)):
                label, pos = None, 0
        dollar = label is not None and "$" in t0.raw
        rest = toks[pos:]
        mn = rest[0].up() if rest and rest[0].kind == "id" else None
        args = rest[1:]
        if rest and mn is None:
            raise AsmError(f"instruction expected, found {rest[0].val}")
        # a directive that is off: a macro call (or an error)
        ext_off = (mn in EXT_DIRECTIVES and not self.ext_directive(rest[0])
                   or mn in FORK_DIRECTIVES and self.pasmo_syntax)

        if mn in ("EQU", "DEFL"):
            if not label:
                raise AsmError(f"{mn} without a label")
            v = self.expr(args)
            self.define(label, v, "equ" if mn == "EQU" else "defl", dollar)
            self.list_line(v, [])
            return
        if mn == "MACRO":
            if label:
                name, params = label, split_commas(args)
            else:
                parts = split_commas(args)
                if not parts or len(parts[0]) != 1:
                    raise AsmError("MACRO without a name")
                name, params = parts[0][0].val, parts[1:]
            raw = split_text_args(after_keyword(text, "MACRO"))[0 if label else 1:]
            pnames, defaults = [], {}
            for p, r in zip(params, raw + [""] * len(params)):
                if (len(p) > 2 and p[0].kind == "id" and p[1].kind == "op" and p[1].val == "="
                        and not self.pasmo_syntax):
                    # name=default (pypasmo extension): for a missing or empty argument
                    defaults[self.norm(p[0].val)] = r.split("=", 1)[1].strip()
                    p = p[:1]
                pname = self.norm(self.check_name(p, "a macro parameter must be an identifier"))
                if pname in pnames:          # Pasmo silently uses the first one
                    raise AsmError(f"the macro parameter {p[0].val} is there twice")
                pnames.append(pname)
            self.end_autolocal_block()
            self.list_line(None, [])
            self.macros[self.norm(name)] = (pnames, self.collect_block(frame), defaults)
            return
        if mn == "STRUCT" and not ext_off:
            if label:
                raise AsmError("STRUCT name, not name STRUCT")
            self.d_struct(args, frame)
            return
        if mn == "ORG" or mn in ("PHASE", ".PHASE") and not ext_off:
            self.dirs[mn](self, args, text, frame)      # a label gets the new address (Pasmo)
            if label:
                self.define(label, self.pc, "label", dollar)
            return
        if label:
            self.define(label, self.pc, "label", dollar)
        if mn is None:
            if rest:
                raise AsmError("unexpected text")
            self.list_line(self.pc, [])
            return

        if mn in MNEMONICS:
            ops = [parse_operand(p, self.bracket) for p in split_commas(args)]
            code = self.encode(mn, ops)
            self.emit(code, t=tstates(code))
            return
        if mn in self.dirs and not ext_off:
            self.dirs[mn](self, args, text, frame)
            return
        name = self.norm(rest[0].val)
        if name in self.macros:
            self.expand_macro(name, text, rest)
            return
        raise AsmError(f"unknown instruction or macro {rest[0].val}")

    # ---------- macros ----------
    def expand_macro(self, name, text, rest):
        params, body, defaults = self.macros[name]
        m = None
        for m in re.finditer(r"(?<![\w?@.$])" + re.escape(rest[0].raw) + r"(?![\w?@.$])", text):
            if not re.match(r"\s*:", text[m.end():]):    # not a label of the same name (mm: mm 5)
                break
        call_args = split_text_args(text[m.end():]) if m else []
        state = {"args": call_args}

        def subst(line):
            args = state["args"]
            bind = {p: (args[k] if k < len(args) else "") or defaults.get(p, "") for k, p in enumerate(params)}
            return subst_idents(line, lambda w: bind.get(self.norm(w)))
        f = Frame(body, "macro", subst)
        f.state = state
        self.list_line(None, [])
        self.push_frame(f)

    def d_rept(self, args, text, frame):
        parts = split_commas(args)
        if not parts or not parts[0]:
            raise AsmError("REPT needs a count")
        count = self.expr(parts[0], required=True)     # unsigned: REPT -1 = 65535 times
        body = self.collect_block(frame)
        if count == 0:
            return
        f = Frame(body, "rept", frame.subst, reps=count)
        if len(parts) > 1:
            if len(parts[1]) != 1 or parts[1][0].kind != "id":
                raise AsmError("REPT counter must be an identifier")
            var = parts[1][0].val
            start = self.expr(parts[2]) if len(parts) > 2 else 0
            step = self.expr(parts[3]) if len(parts) > 3 else 1
            it = {"v": start, "first": True}

            def on_iter():                      # the counter is local to the REPT
                if it["first"]:
                    self.new_local(var)
                    it["first"] = False
                self.define(var, it["v"], "defl")
                it["v"] = (it["v"] + step) & 0xFFFF
            f.on_iter = on_iter
        self.push_frame(f)

    def d_irp(self, args, text, frame):
        parts = split_commas(args)
        if len(parts) < 2 or len(parts[0]) != 1:          # Pasmo: "Expected ','"
            raise AsmError("IRP needs: parameter, list of values")
        param = self.norm(self.check_name(parts[0], "the IRP parameter must be an identifier"))
        after = text[text.index(",") + 1:] if "," in text else ""
        values = split_text_args(after)
        body = self.collect_block(frame)
        if not values:                                    # IRP x, (the block is skipped)
            raise AsmError("IRP without values")
        outer = frame.subst
        it = {"k": -1}

        def subst(line):
            line = outer(line) if outer else line
            return subst_idents(line, lambda w: values[it["k"]] if self.norm(w) == param else None)

        def on_iter():
            it["k"] += 1
        f = Frame(body, "irp", subst, reps=len(values), on_iter=on_iter)
        self.push_frame(f)

    def d_exitm(self, args, text, frame):
        self.list_line(None, [])
        if self.frames[-1].kind == "file":
            raise AsmError("EXITM outside of MACRO, REPT or IRP")
        f = self.frames[-1]
        f.i, f.reps = len(f.lines), 1

    def d_shift(self, args, text, frame):
        for f in reversed(self.frames):
            if f.kind == "macro":
                f.state["args"] = f.state["args"][1:]
                self.list_line(None, [])
                return
        raise AsmError(".SHIFT outside of a macro")

    def d_dg(self, args, text, frame):
        """DG (0.5.5.paged fork, from the Zeus assembler): a bit pattern, 8 characters
        per byte; '.', '-' and '_' are 0, any other character is 1, spaces are ignored.
        The pattern may be written in quotes."""
        pat = after_keyword(text, "DG").strip()
        if pat and pat[0] in "'\"":
            end = pat.find(pat[0], 1)
            if end < 0:
                raise AsmError("unterminated string")
            pat, rest = pat[1:end], pat[end + 1:]
            if rest.strip() and not rest.strip().startswith(";"):
                raise AsmError(f"unexpected text after DG: {rest.strip()}")
        else:
            pat = pat.split(";")[0]
        pat = re.sub(r"\s", "", pat)
        if not pat or len(pat) % 8:
            raise AsmError(f"DG needs a multiple of 8 characters, found {len(pat)}")
        data = [int("".join("0" if c in ".-_" else "1" for c in pat[k:k + 8]), 2)
                for k in range(0, len(pat), 8)]
        self.emit(data)

    def d_struct(self, args, frame):
        """STRUCT name ... ENDS (0.5.5.paged fork): only defines symbols, no code.
        Each field label gets its offset (name.field), name gets the size. Fields are
        DB/DEFB/DEFM, DW/DEFW and DS/DEFS; their values are ignored."""
        if len(args) != 1 or args[0].kind != "id":
            raise AsmError("STRUCT needs a name")
        name = args[0].val
        self.list_line(None, [])
        size = 0
        while True:
            if frame.i >= len(frame.lines):
                raise AsmError("STRUCT without ENDS")
            loc, raw, _ = frame.lines[frame.i]
            frame.i += 1
            text = frame.subst(raw) if frame.subst else raw
            if self.final:
                self.listing.append((None, [], "", text, len(self.frames) - 1))
            toks = lex(text)
            if not toks:
                continue
            kw, at = self.keyword(toks)
            if kw == "ENDS":
                break
            if kw == "STRUCT":
                raise AsmError(f"{loc}: nested STRUCT is not supported")
            if kw not in ("DB", "DEFB", "DEFM", "DW", "DEFW", "DS", "DEFS"):
                raise AsmError(f"{loc}: only DB, DW and DS can be used in STRUCT")
            if at:                                   # field label
                self.define(f"{name}.{toks[0].val}", size, "equ")
            parts = split_commas(toks[at + 1:])
            if kw in ("DB", "DEFB", "DEFM"):
                size += sum(len(q[0].val) if len(q) == 1 and q[0].kind == "str" else 1
                            for q in parts)
            elif kw in ("DW", "DEFW"):
                size += 2 * len(parts)
            else:
                if not parts or not parts[0]:
                    raise AsmError(f"{loc}: DS needs a size")
                size += self.expr(parts[0], required=True)
        self.define(name, size, "equ")

    def d_ends(self, args, text, frame):
        raise AsmError("ENDS without STRUCT")

    def d_bank(self, args, text, frame):
        """BANK n (0.5.5.paged fork): the code at C000h-FFFFh goes to 16 KB bank n of
        the ZX Spectrum 128K (0..7). Output with --tap128 / --tapbas128."""
        n = self.expr(args, required=True)
        if n > 7:
            raise AsmError(f"BANK {n}: the Spectrum 128K has banks 0..7")
        self.bank = n
        self.list_line(None, [])

    def d_endm(self, args, text, frame):
        raise AsmError("ENDM without MACRO, REPT or IRP")

    # ---------- other directives ----------
    def d_org(self, args, text, frame):
        self.routine = None
        if self.phased:
            raise AsmError("ORG inside PHASE (DEPHASE first)")
        self.pc = self.expr(args, required=True)
        self.list_line(self.pc, [])

    def d_phase(self, args, text, frame):
        """PHASE addr ... DEPHASE (pypasmo extension, from MACRO-80): the code is assembled
        for addr ($ and labels), but its bytes go on after the previous code; for code
        that the program copies to addr. The listing shows the load address on these two lines."""
        if self.phased:
            raise AsmError("PHASE inside PHASE (DEPHASE missing)")
        if not args:
            raise AsmError("PHASE needs an address")
        addr = self.expr(args, required=True)
        self.list_line(self.pc, [])
        self.phased, self.phase_off = True, (self.pc - addr) & 0xFFFF
        self.pc = addr
        self.routine = None

    def d_dephase(self, args, text, frame):
        if not self.phased:
            raise AsmError("DEPHASE without PHASE")
        if args:
            raise AsmError("unexpected text after DEPHASE")
        self.pc = (self.pc + self.phase_off) & 0xFFFF
        self.phased, self.phase_off = False, 0
        self.routine = None
        self.list_line(self.pc, [])

    def d_align(self, args, text, frame):
        """ALIGN n[,byte] (pypasmo extension, like sjasmplus): $ to the next multiple of n
        (a power of 2); the bytes are filled with byte, without it only skipped (DS n,?)."""
        parts = split_commas(args)
        if not parts or not parts[0] or len(parts) > 2:
            raise AsmError("ALIGN needs: size[, fill byte]")
        n = self.expr(parts[0], required=True)
        if n == 0 or n & (n - 1):
            raise AsmError(f"ALIGN {n}: the size must be a power of 2")
        self.emit_fill(-self.pc % n, self.byte(parts[1]) if len(parts) > 1 else None)

    def d_assert(self, args, text, frame):
        """ASSERT expr[,"message"] (pypasmo extension, like sjasmplus): an error if expr is
        0 (false). Checked in the last pass, so expr may use labels defined later."""
        parts = split_commas(args)
        if not parts or not parts[0] or len(parts) > 2:
            raise AsmError('ASSERT needs: expression[, "message"]')
        if len(parts) > 1 and (len(parts[1]) != 1 or parts[1][0].kind != "str"):
            raise AsmError("ASSERT: the message must be a string")
        if self.final and self.expr(parts[0]) == 0:
            raise AsmError("ASSERT failed" + (f": {readable(parts[1][0].val)}" if len(parts) > 1 else ""))
        self.list_line(None, [])

    def d_display(self, args, text, frame):
        """DISPLAY "text", expr, ... (pypasmo extension, like sjasmplus): print texts and
        values (decimal and hex) in the last pass, so the values may use labels defined later."""
        parts = split_commas(args)
        if not parts or not all(parts):
            raise AsmError('DISPLAY needs: "text" or expression[, ...]')
        out = ""
        for p in parts:
            if len(p) == 1 and p[0].kind == "str":
                piece = readable(p[0].val)
            else:
                v = self.expr(p)            # also labels below (the final pass checks them)
                piece = f"{v} ({v:04X}h)"
            # a blank between the parts, not before punctuation or where one is already
            out += ("" if not out or out[-1].isspace() or piece[:1] in " ,.;:)!?" else " ") + piece
        if self.final:
            self.displays.append(out)
        self.list_line(None, [])

    def d_tape_block(self, args, text, frame, screen=False):
        """TAPE_BLOCK "name", start, length (pypasmo extension): a CODE block on the tape
        with bytes of the assembled code. With TAPE_BLOCK the tape formats write only the
        listed blocks, in this order."""
        parts = split_commas(args)
        what = 'TAPE_BLOCK_SCREEN needs: "name"[, "file"]' if screen else 'TAPE_BLOCK needs: "name", start, length'
        if (len(parts) not in ((1, 2) if screen else (3,))
                or any(len(p) != 1 or p[0].kind != "str" for p in parts[:2 if screen else 1])):
            raise AsmError(what)
        name = parts[0][0].val
        if len(name) > 10:
            raise AsmError(f"{what.split()[0]}: the name {readable(name)} is longer than 10 characters")
        if screen:
            start, length = 0x4000, 6912
            data = None
            if len(parts) > 1:
                # the picture file: like ORG 4000h + INCBIN, but $ stays where it is
                data = self.find_file(parts[1][0].val, self.path).read_bytes()
                if len(data) != 6912:
                    raise AsmError(f"TAPE_BLOCK_SCREEN: {parts[1][0].val} has {len(data)} bytes, not 6912")
                if any(a in self.mem for a in range(0x4000, 0x5B00)):
                    raise AsmError("TAPE_BLOCK_SCREEN: there is code at 4000h-5AFFh already")
                for i, b in enumerate(data):
                    self.mem[0x4000 + i] = b
                self.screen_file = True
            self.screen_locs.append((self.loc, data))
        else:
            start, length = (self.expr(p) for p in parts[1:])   # also labels below
            if self.final and not (0 < length and start + length <= 0x10000):
                raise AsmError(f"TAPE_BLOCK: wrong block {start:04X}h, length {length}")
        self.tape_blocks.append(("screen" if screen else "code", name, start, length))
        self.list_line(None, [])

    def d_tape_block_screen(self, args, text, frame):
        """TAPE_BLOCK_SCREEN "name"[, "file"]: TAPE_BLOCK "name", 4000h, 6912 for LOAD "" SCREEN$;
        with a file (6912 bytes) the picture is put at 4000h first."""
        self.d_tape_block(args, text, frame, screen=True)

    def d_tap_include(self, args, text, frame):
        """TAP_INCLUDE file (pypasmo extension): the blocks of a .tap file go unchanged on
        the tape at this place, between the TAPE_BLOCK blocks (e.g. an own Basic loader)."""
        name = self.file_arg(after_keyword(text, "TAP_INCLUDE").split(";")[0])
        data = self.find_file(name, self.path).read_bytes()
        split_tap(data, name)
        self.tape_blocks.append(("tap", name, data))
        self.list_line(None, [])

    def d_db(self, args, text, frame):
        self.emit(self.db_data(args))

    def d_dz(self, args, text, frame):
        """DZ (pypasmo extension, like sjasmplus): DB with a zero byte at the end."""
        self.emit(self.db_data(args) + [0])

    def d_dc(self, args, text, frame):
        """DC (pypasmo extension, like sjasmplus): DB with bit 7 set in the last character
        of each string (strings of the ZX Spectrum ROM). One character in apostrophes is a
        number, as in sjasmplus: DC 'A' = 41h, DC "A" = C1h."""
        self.emit(self.db_data(args, dc=True))

    def d_zx81(self, args, text, frame, inverse=False, dc=False):
        """D_ZX81 (pypasmo extension): DB with the strings in the ZX81 character set, lower
        case letters inverse (code + 128). Numbers are not changed."""
        what = "DC_ZX81" if dc else "D_ZX81I" if inverse else "D_ZX81"
        data = []
        for part in split_commas(args) or [[]]:          # nothing: an error, as in DB
            if not (part and part[0].kind == "str"):
                data.append(self.byte(part))
                continue
            if len(part) > 1:
                raise AsmError(f"{what}: expected ',' after the string, found {part[1].val}")
            s = part[0].val
            codes = []
            for c in s:
                lower = "a" <= c <= "z"
                if (c.upper() if lower else c) not in ZX81_CODES:
                    shown = f"'{c}'" if " " <= c <= "~" else "outside ASCII"
                    raise AsmError(f'{what}: no ZX81 character {shown} in "{readable(s)}"')
                codes.append(ZX81_CODES[c.upper() if lower else c] | (0x80 if lower != inverse else 0))
            if dc and codes:
                if any(x & 0x80 for x in codes[:-1]):
                    raise AsmError(f'DC_ZX81: an inverse character before the end of "{readable(s)}"')
                codes[-1] |= 0x80
            data += codes
        self.emit(data)

    def d_zx81i(self, args, text, frame):
        """D_ZX81I: like D_ZX81, but all inverse except lower case letters."""
        self.d_zx81(args, text, frame, inverse=True)

    def dc_zx81(self, args, text, frame):
        """DC_ZX81: like D_ZX81 with bit 7 (inverse) in the last character of each string,
        as in the keyword table of the ZX81 ROM (inverse characters before it: error)."""
        self.d_zx81(args, text, frame, dc=True)

    def db_data(self, args, dc=False):
        data = []
        for part in split_commas(args) or [[]]:          # DB alone: an error, as in Pasmo
            one_dq = dc and len(part) == 1 and part[0].kind == "str" and part[0].raw.startswith('"')
            if part and part[0].kind == "str" and (len(part[0].val) != 1 or one_dq):
                if len(part) > 1:            # DB "AB"+1: Pasmo expects ',' after a string
                    raise AsmError(f"expected ',' after the string, found {part[1].val}")
                s = [ord(c) & 0xFF for c in part[0].val]
                if dc and s:
                    s[-1] |= 0x80
                data += s
            elif len(part) == 1 and part[0].kind == "op" and part[0].val == "?":
                data.append(None)
            else:
                data.append(self.byte(part))
        return data

    def d_dw(self, args, text, frame):
        data = []
        for part in split_commas(args) or [[]]:          # DW alone: an error, as in Pasmo
            data += self.word(part)
        self.emit(data)

    def d_ds(self, args, text, frame):
        parts = split_commas(args)
        if not parts or not parts[0]:
            raise AsmError("DS needs a size")
        count = self.expr(parts[0], required=True)
        if len(parts) > 1 and len(parts[1]) == 1 and parts[1][0].kind == "op" and parts[1][0].val == "?":
            fill = None                  # DS n,? only reserves space, like DB ?
        else:
            fill = self.byte(parts[1]) if len(parts) > 1 else 0
        # Like Pasmo, a DS past 64KB (e.g. a negative size) wraps around with a warning.
        self.emit_fill(count, fill)

    def emit_fill(self, count, fill):
        """count bytes fill (None = only skipped), listed as up to 4 bytes and '...'."""
        self.emit([fill] * count, (["--" if fill is None else fill] * min(count, 4)) + (["..."] if count > 4 else []))

    def d_incbin(self, args, text, frame):
        arg = after_keyword(text, "INCBIN").split(";")[0]
        opt = None
        if not self.pasmo_syntax:
            # INCBIN file,offset[,length] (pypasmo extension, like sjasmplus). The name is
            # read as in Pasmo (unquoted up to a blank: "data.bin,1" is a file name), the
            # offset follows a quoted name or a blank: "data.bin" ,1 / data.bin, 1 / data.bin ,1
            m = re.match(r"""\s*("[^"]*"|'[^']*'|[^ \t]+)(.*)""", arg)
            name, rest = (m.group(1), m.group(2).strip()) if m else ("", "")
            if rest.startswith(","):
                arg, opt = name, split_commas(lex(rest[1:]))
            elif rest and name.endswith(",") and name[0] not in "'\"":
                arg, opt = name[:-1], split_commas(lex(rest))
        name = self.file_arg(arg)
        data = self.find_file(name, self.path).read_bytes()
        if opt is not None:
            if not opt or len(opt) > 2 or not all(opt):
                raise AsmError("INCBIN needs: file[, offset[, length]]")
            start = self.expr(opt[0], required=True)
            end = start + self.expr(opt[1], required=True) if len(opt) > 1 else len(data)
            if end > len(data) or start > len(data):
                raise AsmError(f"INCBIN: offset and length past the end of {name} ({len(data)} bytes)")
            data = data[start:end]
        self.emit(list(data), list(data[:4]) + (["..."] if len(data) > 4 else []))

    def d_include(self, args, text, frame):
        self.list_line(None, [])     # already expanded while loading

    def d_end(self, args, text, frame):
        if args:
            self.entry = self.expr(args)
        self.list_line(None, [])
        self.frames.clear()

    def d_proc(self, args, text, frame):
        self.scopes.append({})
        self.scope_kind.append("proc")
        self.end_autolocal_block()
        self.list_line(None, [])

    def d_endp(self, args, text, frame):
        if not self.scope_kind or self.scope_kind[-1] != "proc":
            raise AsmError("ENDP without PROC")
        self.scopes.pop()
        self.scope_kind.pop()
        self.end_autolocal_block()
        self.list_line(None, [])

    def d_local(self, args, text, frame):
        if not self.scopes:
            raise AsmError("LOCAL only inside PROC, MACRO, REPT or IRP")
        for p in split_commas(args) or [[]]:
            self.new_local(self.check_name(p, "LOCAL needs a list of identifiers"))
        self.end_autolocal_block()
        self.list_line(None, [])

    def d_error(self, args, text, frame):
        msg = after_keyword(text, ".ERROR").strip()
        raise AsmError(f".ERROR {readable(msg)}")

    def d_warning(self, args, text, frame):
        msg = after_keyword(text, ".WARNING").strip()
        self.warn(readable(msg))
        self.list_line(None, [])

    def d_public(self, args, text, frame):
        for p in split_commas(args) or [[]]:
            name = self.norm(self.check_name(p, "PUBLIC needs a list of identifiers"))
            self.publics.append(self.last_label + name if self.dot_local(name) else p[0].val)
        self.list_line(None, [])

    def d_ignore(self, args, text, frame):
        self.list_line(None, [])

    def d_8080(self, args, text, frame):
        raise AsmError("8080 mode not supported")      # the same error as in Pasmo 0.5.5

    dirs = {
        "ORG": d_org, "DB": d_db, "DEFB": d_db, "DEFM": d_db, "DW": d_dw, "DEFW": d_dw,
        "DS": d_ds, "DEFS": d_ds, "INCBIN": d_incbin, "INCLUDE": d_include, "END": d_end,
        "PROC": d_proc, "ENDP": d_endp, "LOCAL": d_local, "REPT": d_rept, "IRP": d_irp,
        "EXITM": d_exitm, ".SHIFT": d_shift, "ENDM": d_endm, ".ERROR": d_error,
        "DUP": d_rept, "EDUP": d_endm, "DG": d_dg, "ENDS": d_ends, "BANK": d_bank,
        ".WARNING": d_warning, "PUBLIC": d_public, ".Z80": d_ignore, ".8080": d_8080,
        # pypasmo extensions (EXT_DIRECTIVES)
        "PHASE": d_phase, ".PHASE": d_phase, "DEPHASE": d_dephase, ".DEPHASE": d_dephase,
        "ALIGN": d_align, "ASSERT": d_assert, "DZ": d_dz, "DC": d_dc,
        "TAPE_BLOCK": d_tape_block, "TAPE_BLOCK_SCREEN": d_tape_block_screen,
        "TAP_INCLUDE": d_tap_include, "DISPLAY": d_display,
        "D_ZX81": d_zx81, "D_ZX81I": d_zx81i, "DC_ZX81": dc_zx81,
    }


def assemble_text(text, name="<source>", **opts):
    """Assemble source code from a string and return the Assembler (asm.mem,
    asm.symbols, asm.entry, ...). opts are the Assembler arguments. The text is
    treated like a UTF-8 file (a string "é" gives the bytes C3h A9h)."""
    asm = Assembler(**opts)
    asm.assemble(name, text=text.encode("utf-8").decode("latin-1"))
    return asm
