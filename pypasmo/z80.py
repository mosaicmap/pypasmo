# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""Z80 instructions: operands, encoding into bytes, T-states."""
from .common import (ALU, BITOP, CC, NOARG, R8, REGISTERS, ROT, RP, RP_PUSH, Z80_ONLY_OPCODES,
                     AsmError)
from .lexer import Tok


def _tstates_base(op):
    """T-states of an unprefixed opcode; a pair (taken, not taken) for a condition."""
    if 0x40 <= op <= 0xBF:                              # LD r,r' / ALU r: (HL) costs 7
        return 4 if op == 0x76 else 7 if op & 7 == 6 or (op < 0x80 and op & 0x38 == 0x30) else 4
    y, z = (op >> 3) & 7, op & 7
    if op < 0x40:
        if z == 0:                                       # NOP, EX AF,AF', DJNZ, JR, JR cc
            return (4, 4, (13, 8), 12)[y] if y < 4 else (12, 7)
        return (10 if y % 2 == 0 else 11,                # LD rr,nn / ADD HL,rr
                (7, 7, 7, 7, 16, 16, 13, 13)[y],         # LD (BC),A ... LD A,(nn)
                6,                                       # INC rr / DEC rr
                11 if y == 6 else 4, 11 if y == 6 else 4,    # INC r / DEC r
                10 if y == 6 else 7,                     # LD r,n
                4)[z - 1]                                # RLCA ... CCF
    return ((11, 5),                                     # RET cc
            10 if y % 2 == 0 else (10, 4, 4, 6)[y >> 1],     # POP / RET, EXX, JP (HL), LD SP,HL
            10,                                          # JP cc
            (10, 0, 11, 11, 19, 4, 4, 4)[y],             # JP, -, OUT (n),A, IN A,(n), EX (SP),HL ...
            (17, 10),                                    # CALL cc
            11 if y % 2 == 0 else 17,                    # PUSH / CALL
            7, 11)[z]                                    # ALU n, RST


def tstates(code):
    """T-states of one instruction (its bytes) for the listing: "7", or "12/7" for an
    instruction with a condition (condition true / false) or a repeating block
    instruction (repeats / ends). Contended memory (ZX Spectrum) is not counted."""
    op = code[0]
    if op == 0xCB:
        return "12" if code[1] & 0xC7 == 0x46 else "15" if code[1] & 7 == 6 else "8"
    if op == 0xED:
        e = code[1]
        if 0xA0 <= e <= 0xBB:                            # block instructions
            return "21/16" if e >= 0xB0 else "16"
        t = {0: 12, 1: 12, 2: 15, 3: 20, 4: 8, 5: 14, 6: 8}.get(e & 7)
        if e & 7 == 7:
            t = 18 if e in (0x67, 0x6F) else 9
        return str(t)
    if op in (0xDD, 0xFD):
        if code[1] == 0xCB:                              # DD CB d op
            return "20" if code[3] & 0xC0 == 0x40 else "23"
        b = code[1]
        mem = (b in (0x34, 0x35, 0x36) or (0x40 <= b <= 0xBF and b != 0x76 and
               (b & 7 == 6 or (b < 0x80 and b & 0x38 == 0x30))))
        if mem:                                          # (IX+d)
            return "23" if b in (0x34, 0x35) else "19"
        t = _tstates_base(b)
        return f"{t[0] + 4}/{t[1] + 4}" if isinstance(t, tuple) else str(t + 4)
    t = _tstates_base(op)
    return f"{t[0]}/{t[1]}" if isinstance(t, tuple) else str(t)



class Operand:
    """s is the operand signature: 'A', '(HL)', 'HL', '(IX+d)', '(BC)', '(C)', '(nn)', 'n', ...
    toks holds the expression of 'n', '(nn)' and '(IX+d)'."""

    def __init__(self, s, toks=None, name=None, paren=False):
        self.s, self.toks, self.name = s, toks or [], name
        # paren: written with ( ) (not [ ]); for '(nn)' Pasmo takes it as a plain value
        # where no memory form exists (JR (5), RST (8)); for 'n' it starts with '(' but
        # the bracket closes earlier, like (1)+2
        self.paren = paren

    def is_value(self):
        """A plain value: n, or (n) where the instruction has no (nn) form."""
        return self.s == "n" or (self.s == "(nn)" and self.paren)

    @property
    def cc(self):
        return self.name if self.name in CC else None


def parse_operand(toks, bracket_only=False):
    if not toks:
        raise AsmError("empty operand")
    if len(toks) == 1 and toks[0].kind == "id" and toks[0].up() in REGISTERS | set(CC):
        u = toks[0].up()
        return Operand(u, name=u)
    first = toks[0]
    openers = "[" if bracket_only else "(["
    if first.kind == "op" and first.val in openers:
        close = ")" if first.val == "(" else "]"
        depth = 0
        for k, t in enumerate(toks):
            if t.kind == "op" and t.val in "([":
                depth += 1
            elif t.kind == "op" and t.val in ")]":
                depth -= 1
                if depth == 0:
                    break
        # indirection only if the bracket opened first closes at the very end
        if k == len(toks) - 1 and toks[-1].val == close:
            inner = toks[1:-1]
            if len(inner) == 1 and inner[0].kind == "id" and inner[0].up() in ("BC", "DE", "HL", "SP", "C", "IX", "IY"):
                return Operand(f"({inner[0].up()})")
            if inner and inner[0].kind == "id" and inner[0].up() in ("IX", "IY"):
                if not (inner[1].kind == "op" and inner[1].val in "+-"):
                    raise AsmError("expected + or - after IX/IY")
                return Operand(f"({inner[0].up()}+d)", inner[1:])
            return Operand("(nn)", inner, paren=first.val == "(")
        return Operand("n", toks, paren=first.val == "(")
    return Operand("n", toks)



class Z80Encoder:
    """Encoding of Z80 instructions, a part of Assembler (it uses self.expr, self.warn,
    self.final, self.stmt_pc)."""

    def byte(self, toks):
        v = self.expr(toks)
        if not (v <= 0xFF or v >= 0xFF00):
            self.warn(f"value {v:04X}h does not fit in a byte, truncated")
        return v & 0xFF

    def word(self, toks):
        v = self.expr(toks)
        return [v & 0xFF, v >> 8]

    def rel(self, toks):
        # The Z80 adds the offset modulo 64 KB, so JR 5 at 0FFF0h is valid
        # (Pasmo reports it as out of range).
        d = (self.expr(toks) - (self.stmt_pc + 2)) & 0xFFFF
        d = d - 0x10000 if d >= 0x8000 else d
        if self.final and not -128 <= d <= 127:
            raise AsmError(f"relative jump out of range ({d})")
        return d & 0xFF

    def disp(self, toks):
        """Offset of (IX+d) / (IX-d); toks start with the sign. The offset is computed as
        0+... / 0-..., so (IX-12+13) is IX+1. (Pasmo computes -(12+13) = IX-25, a bug
        fixed also in the 0.5.5.paged fork.) Like Pasmo, 0..255 is allowed (so +0FFh
        means -1), negative values down to -128."""
        if len(toks) > 1 and toks[1].kind == "id" and toks[1].up() in ("HIGH", "LOW", "NOT"):
            v = self.expr(toks[1:])              # bind looser than + -: (IX+LOW x), as Pasmo
            v = -v & 0xFFFF if toks[0].val == "-" else v
        else:
            v = self.expr([Tok("num", 0)] + toks)
        if self.final and not (v <= 0xFF or v >= 0xFF80):
            d = v - 0x10000 if v >= 0x8000 else v
            raise AsmError(f"index offset out of range ({d}, allowed -128..255)")
        return v & 0xFF

    def paren_byte(self, op):
        """Pasmo: LD r,(n) and ADD A,(n) do not exist, so (n) is taken as an expression.
        Pasmo does not warn for LD (IX+d),(n)."""
        if not self.indexed:
            self.warn("looks like a non existent instruction")
        return self.byte(op.toks)

    # ---------- instructions ----------
    def encode(self, mn, ops):
        code = self.encode_z80(mn, ops)
        if self.w8080 and (code[0] in (0xCB, 0xDD, 0xED, 0xFD) or
                           (len(code) <= 2 and code[0] in Z80_ONLY_OPCODES)):
            self.warn("not a 8080 instruction")
        return code

    def encode_z80(self, mn, ops):
        """Handle IX/IY by encoding the HL form and adding the DD/FD prefix (and the
        displacement after the first opcode byte, or after CB)."""
        prefix, disp, half, real_hl, real_hl16 = None, None, False, False, False
        real_mem_hl = any(op.s == "(HL)" for op in ops)     # (HL) written in the source
        for op in ops:
            s = op.s
            if s in ("IX", "IY", "(IX)", "(IY)", "(IX+d)", "(IY+d)", "IXH", "IXL", "IYH", "IYL"):
                p = 0xDD if "IX" in s else 0xFD
                if prefix not in (None, p):
                    raise AsmError("IX and IY can not be used in the same instruction")
                prefix = p
                if s in ("IX", "IY"):
                    op.s = "HL"
                elif s in ("IXH", "IXL", "IYH", "IYL"):
                    op.s, half = s[-1], True
                else:
                    op.s = "(HL)"
                    if mn != "JP":
                        disp = self.disp(op.toks) if op.toks else 0
            elif s in ("H", "L"):
                real_hl = True
            elif s == "HL":
                real_hl16 = True
        if prefix and (half and (disp is not None or real_hl)):
            raise AsmError("invalid combination of registers")
        if prefix and real_mem_hl:         # LD IXH,(HL) would give DD 66 without an offset
            raise AsmError("(HL) can not be used with IX/IY")
        if mn == "JP" and prefix and any(o.toks for o in ops if o.s == "(HL)"):
            raise AsmError("JP (IX+d) does not exist, only JP (IX)")
        self.indexed = disp is not None
        code = self.base(mn, ops)
        if prefix is None:
            return code
        if code[0] == 0xED or code == [0xEB] or real_hl16 or (real_hl and disp is None):
            raise AsmError("this instruction can not be used with IX/IY")
        if code[0] == 0xCB:
            if disp is None:
                raise AsmError("bit and shift instructions with IX/IY need (IX+d)")
            return [prefix, 0xCB, disp, code[1]]
        if disp is not None:
            return [prefix, code[0], disp] + code[1:]
        return [prefix] + code

    def base(self, mn, ops):
        """Encode an instruction without IX/IY."""
        n = len(ops)
        s = [o.s for o in ops]
        bad = AsmError(f"invalid operands: {mn} {', '.join(s)}")
        if n == 0:
            if mn in NOARG:
                return list(NOARG[mn])
            raise bad
        if mn == "LD" and n == 2:
            d, src = s
            if src == "n" and ops[1].paren and d in ("A", "BC", "DE", "HL", "SP"):
                # LD A,(1)+2: Pasmo reads (1) as memory and then finds '+' (error)
                raise AsmError("text after (...): here ( ) means memory, use 0+(...) for a value")
            if d in R8 and src in R8 and not d == src == "(HL)":
                return [0x40 + R8[d] * 8 + R8[src]]
            if d in R8 and src == "n":
                return [0x06 + R8[d] * 8, self.byte(ops[1].toks)]
            if d in R8 and d != "A" and src == "(nn)":
                return [0x06 + R8[d] * 8, self.paren_byte(ops[1])]
            if d == "A":
                if src in ("(BC)", "(DE)"):
                    return [0x0A if src == "(BC)" else 0x1A]
                if src == "(nn)":
                    return [0x3A] + self.word(ops[1].toks)
                if src in ("I", "R"):
                    return [0xED, 0x57 if src == "I" else 0x5F]
            if src == "A":
                if d in ("(BC)", "(DE)"):
                    return [0x02 if d == "(BC)" else 0x12]
                if d == "(nn)":
                    return [0x32] + self.word(ops[0].toks)
                if d in ("I", "R"):
                    return [0xED, 0x47 if d == "I" else 0x4F]
            if d in RP and src == "n":
                return [0x01 + RP[d] * 16] + self.word(ops[1].toks)
            if d in RP and src == "(nn)":
                if d == "HL":
                    return [0x2A] + self.word(ops[1].toks)
                return [0xED, 0x4B + RP[d] * 16] + self.word(ops[1].toks)
            if d == "(nn)" and src in RP:
                if src == "HL":
                    return [0x22] + self.word(ops[0].toks)
                return [0xED, 0x43 + RP[src] * 16] + self.word(ops[0].toks)
            if d == "SP" and src == "HL":
                return [0xF9]
            raise bad
        if mn in ALU:
            if n == 2 and s[0] == "HL" and mn in ("ADD", "ADC", "SBC") and s[1] in RP:
                p = RP[s[1]] * 16
                return {"ADD": [0x09 + p], "ADC": [0xED, 0x4A + p], "SBC": [0xED, 0x42 + p]}[mn]
            # both forms for all eight: ADD A,B / ADD B, SUB B / SUB A,B (Pasmo accepts
            # only ADD A,B and SUB B, but the other form means the same instruction)
            if n == 2 and s[0] == "A":
                op = ops[1]
            elif n == 1:
                op = ops[0]
            else:
                raise bad
            if op.s in R8:
                return [0x80 + ALU[mn] * 8 + R8[op.s]]
            if op.s == "n":
                return [0xC6 + ALU[mn] * 8, self.byte(op.toks)]
            if op.s == "(nn)":
                return [0xC6 + ALU[mn] * 8, self.paren_byte(op)]
            raise bad
        if mn in ("INC", "DEC") and n == 1:
            if s[0] in R8:
                return [(0x04 if mn == "INC" else 0x05) + R8[s[0]] * 8]
            if s[0] in RP:
                return [(0x03 if mn == "INC" else 0x0B) + RP[s[0]] * 16]
            raise bad
        if mn in ROT and n == 1 and s[0] in R8:
            return [0xCB, ROT[mn] * 8 + R8[s[0]]]
        if mn in BITOP and n == 2 and ops[0].is_value() and s[1] in R8:
            b = self.expr(ops[0].toks)
            if not 0 <= b <= 7:
                raise AsmError("bit number must be 0-7")
            return [0xCB, BITOP[mn] + b * 8 + R8[s[1]]]
        if mn == "JP":
            if n == 1 and s[0] == "(HL)":
                return [0xE9]
            if n == 1 and s[0] == "n" and not ops[0].paren:      # JP (1)+2: error in Pasmo
                return [0xC3] + self.word(ops[0].toks)
            if n == 2 and ops[0].cc and ops[1].is_value():
                return [0xC2 + CC[ops[0].cc] * 8] + self.word(ops[1].toks)
            raise bad
        if mn == "JR":
            if n == 1 and ops[0].is_value():
                return [0x18, self.rel(ops[0].toks)]
            if n == 2 and ops[0].cc in ("NZ", "Z", "NC", "C") and ops[1].is_value():
                return [0x20 + CC[ops[0].cc] * 8, self.rel(ops[1].toks)]
            raise bad
        if mn == "DJNZ" and n == 1 and ops[0].is_value():
            return [0x10, self.rel(ops[0].toks)]
        if mn == "CALL":
            if n == 1 and ops[0].is_value():
                return [0xCD] + self.word(ops[0].toks)
            if n == 2 and ops[0].cc and ops[1].is_value():
                return [0xC4 + CC[ops[0].cc] * 8] + self.word(ops[1].toks)
            raise bad
        if mn == "RET" and n == 1 and ops[0].cc:
            return [0xC0 + CC[ops[0].cc] * 8]
        if mn == "RST" and n == 1 and ops[0].is_value():
            v = self.expr(ops[0].toks)
            if v & ~0x38:
                raise AsmError("RST only 0, 8, 10h, ... 38h")
            return [0xC7 + v]
        if mn == "IM" and n == 1 and ops[0].is_value():
            v = self.expr(ops[0].toks)
            if v not in (0, 1, 2):
                raise AsmError("IM only 0, 1 or 2")
            return [0xED, (0x46, 0x56, 0x5E)[v]]
        if mn in ("PUSH", "POP") and n == 1 and s[0] in RP_PUSH:
            return [(0xC5 if mn == "PUSH" else 0xC1) + RP_PUSH[s[0]] * 16]
        if mn == "EX" and n == 2:
            if s[0] == "AF" and s[1] in ("AF'", "AF"):       # EX AF,AF: also accepted
                return [0x08]
            if s == ["DE", "HL"]:
                return [0xEB]
            if s == ["(SP)", "HL"]:
                return [0xE3]
            raise bad
        if mn == "IN":
            if n == 2 and s[1] == "(C)" and s[0] in R8 and s[0] != "(HL)":
                return [0xED, 0x40 + R8[s[0]] * 8]
            if n == 2 and s[0] == "A" and s[1] == "(nn)":
                return [0xDB, self.byte(ops[1].toks)]
            if (n == 2 and ops[0].toks and ops[0].toks[0].up() == "F" and s[1] == "(C)") or (n == 1 and s[0] == "(C)"):
                self.warn("IN F,(C) is not supported by Pasmo")
                return [0xED, 0x70]
            raise bad
        if mn == "OUT" and n == 2:
            if s[0] == "(C)" and s[1] in R8 and s[1] != "(HL)":
                return [0xED, 0x41 + R8[s[1]] * 8]
            if s[0] == "(C)" and s[1] == "n" and self.expr(ops[1].toks) == 0:
                self.warn("OUT (C),0 is not supported by Pasmo, use DB 0EDh,71h for compatibility")
                return [0xED, 0x71]
            if s[0] == "(nn)" and s[1] == "A":
                return [0xD3, self.byte(ops[0].toks)]
            raise bad
        raise bad
