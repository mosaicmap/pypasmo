# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""Expression evaluator with the operator precedence of Pasmo 0.5.5."""
from .common import FALSE, TRUE, AsmError


class Expr:
    """Expression evaluator. Structure and precedence follow the Pasmo 0.5.5 parser
    (asm.cxx, parsebase .. parsevalue), including its unusual parts."""

    def __init__(self, asm, toks, required=False):
        self.asm, self.toks, self.i, self.required = asm, toks, 0, required

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def is_op(self, *names):
        t = self.peek()
        if t is None:
            return None
        if t.kind == "op" and t.val in names:
            return t.val
        if t.kind == "id" and t.up() in names:
            return t.up()
        return None

    def run(self):
        if not self.toks:
            raise AsmError("missing expression")
        v = self.cond(False)
        if self.i != len(self.toks):
            raise AsmError(f"unexpected {self.peek().val} in expression")
        return v

    # The 'ign' flag is set in branches that are skipped by && || ?: (short circuit);
    # undefined symbols and division by zero are allowed there.
    def cond(self, ign):
        v = self.highlow(ign)
        if self.is_op("?"):
            self.take()
            first = v != 0
            a = self.cond(ign or not first)
            if not self.is_op(":"):
                raise AsmError("missing ':' in ?: expression")
            self.take()
            b = self.cond(ign or first)
            v = a if first else b
        return v

    def highlow(self, ign):
        op = self.is_op("HIGH", "LOW")
        if op:
            self.take()
            v = self.highlow(ign)
            return (v >> 8) if op == "HIGH" else (v & 0xFF)
        return self.boolor(ign)

    def boolor(self, ign):
        v = self.booland(ign)
        if self.is_op("||"):
            r = v != 0
            while self.is_op("||"):
                self.take()
                r |= self.booland(ign or r) != 0
            v = TRUE if r else FALSE
        return v

    def booland(self, ign):
        v = self.orxor(ign)
        if self.is_op("&&"):
            r = v != 0
            while self.is_op("&&"):
                self.take()
                r &= self.orxor(ign or not r) != 0
            v = TRUE if r else FALSE
        return v

    def orxor(self, ign):
        v = self.and_(ign)
        while True:
            op = self.is_op("OR", "|", "XOR")
            if not op:
                return v
            self.take()
            w = self.and_(ign)
            v = (v ^ w) if op == "XOR" else (v | w)

    def and_(self, ign):
        v = self.not_(ign)
        while self.is_op("AND", "&"):
            self.take()
            v &= self.not_(ign)
        return v

    def not_(self, ign):
        # Unary operators bind looser than + - and the relational operators (Pasmo).
        op = self.is_op("NOT", "~", "!", "+", "-")
        if op:
            self.take()
            v = self.not_(ign)
            if op in ("NOT", "~"):
                return ~v & 0xFFFF
            if op == "!":
                return TRUE if v == 0 else FALSE
            return (-v) & 0xFFFF if op == "-" else v
        return self.rel(ign)

    REL = {"EQ": "==", "=": "==", "==": "==", "NE": "!=", "!=": "!=",
           "LT": "<", "<": "<", "LE": "<=", "<=": "<=", "GT": ">", ">": ">", "GE": ">=", ">=": ">="}

    def rel(self, ign):
        v = self.plusmin(ign)
        while True:
            op = self.is_op(*self.REL)
            if not op:
                return v
            self.take()
            w = self.plusmin(ign)
            r = {"==": v == w, "!=": v != w, "<": v < w, "<=": v <= w,
                 ">": v > w, ">=": v >= w}[self.REL[op]]
            v = TRUE if r else FALSE

    def plusmin(self, ign):
        v = self.muldiv(ign)
        while True:
            op = self.is_op("+", "-")
            if not op:
                return v
            self.take()
            w = self.muldiv(ign)
            v = (v + w if op == "+" else v - w) & 0xFFFF

    def muldiv(self, ign):
        v = self.open(ign)
        while True:
            op = self.is_op("*", "/", "MOD", "%", "SHL", "<<", "SHR", ">>")
            if not op:
                return v
            self.take()
            w = self.open(ign)
            if op in ("/", "MOD", "%") and w == 0:
                if not ign and (self.required or self.asm.final):
                    raise AsmError("division by zero")
                v = 0
            elif op == "*":
                v = v * w
            elif op == "/":
                v = v // w
            elif op in ("MOD", "%"):
                v = v % w
            elif op in ("SHL", "<<"):
                v = v << w if w < 16 else 0
            else:
                v = v >> w
            v &= 0xFFFF

    def open(self, ign):
        if self.is_op("("):
            self.take()
            v = self.cond(ign)
            if not self.is_op(")"):
                raise AsmError("missing ')'")
            self.take()
            return v
        return self.value(ign)

    def value(self, ign):
        t = self.take()
        if t is None:
            raise AsmError("missing value in expression")
        if t.kind == "num":
            return t.val
        if t.kind == "str":
            if len(t.val) == 1:          # 'é' (byte E9h) is 00E9h (in Pasmo it depends on
                return ord(t.val) & 0xFF     # the C compiler: FFE9h with a signed char)
            if len(t.val) == 2:          # 'AB': first character is the low byte
                return (ord(t.val[0]) & 0xFF) | (ord(t.val[1]) & 0xFF) << 8
            raise AsmError("a string used as a number must have 1 or 2 characters")
        if t.kind == "op" and t.val == "$":
            return self.asm.stmt_pc
        if t.kind == "id":
            u = t.up()
            if u == "NUL":
                rest = len(self.toks) - self.i
                self.i = len(self.toks)
                return TRUE if rest == 0 else FALSE
            if u == "DEFINED":
                n = self.take()
                if n is None or n.kind != "id":
                    raise AsmError("DEFINED needs an identifier")
                return TRUE if self.asm.is_defined(n.val) else FALSE
            if u == "BANK_OF" and not self.asm.pasmo_syntax:
                # BANK_OF label / BANK_OF(label) (pypasmo extension); else a normal name
                rest = self.toks[self.i:self.i + 3]
                if rest and rest[0].kind == "id":
                    self.i += 1
                    return self.asm.bank_of(rest[0].val, self.required, ign)
                if (len(rest) == 3 and rest[0].kind == "op" and rest[0].val == "(" and rest[1].kind == "id"
                        and rest[2].kind == "op" and rest[2].val == ")"):
                    self.i += 3
                    return self.asm.bank_of(rest[1].val, self.required, ign)
            if u in self.asm.reserved:
                raise AsmError(f"reserved word {t.val} in expression")
            return self.asm.get_symbol(t.val, self.required, ign)
        raise AsmError(f"value expected, found {t.val}")
