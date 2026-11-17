# pypasmo - Z80 assembler in Python, compatible with the Pasmo assembler
# Copyright (C) 2026 Martin Pokorný
# SPDX-License-Identifier: GPL-3.0-only  (see pypasmo/__init__.py and LICENSE)
"""Lexer: splits a source line into tokens (numbers, strings, identifiers, operators)."""
import re

from .common import AsmError


class Tok:
    __slots__ = ("kind", "val", "raw")

    def __init__(self, kind, val, raw=None):
        self.kind = kind    # 'num', 'str', 'id', 'op'
        self.val = val
        self.raw = val if raw is None else raw

    def up(self):
        """Upper case name for comparison with reserved words. An identifier written
        with '$' (like h$l) is never a reserved word, the same as in Pasmo 0.5.5."""
        if self.kind != "id":
            return None
        return "" if "$" in self.raw else self.val.upper()

    def __repr__(self):
        return f"{self.kind}:{self.val!r}"


ID_START = re.compile(r"[A-Za-z_?@.]")
ID_CHARS = re.compile(r"[A-Za-z0-9_?@.$]*")
HEX = "0123456789abcdefABCDEF"
OPS2 = ("<<", ">>", "<=", ">=", "!=", "==", "&&", "||", "##")
OPS1 = "+-*/%&|~!<>=()[]?:,$"
C_ESC = {"n": 10, "r": 13, "t": 9, "a": 7, "\\": 92, '"': 34, "'": 39}


def parse_int(digits, base, orig):
    """A number above FFFFh is an error (Pasmo silently truncates a number that starts
    with a digit, like 70000; pypasmo does not)."""
    digits = digits.replace("$", "")
    try:
        if not digits:
            raise ValueError
        v = int(digits, base)
    except ValueError:
        raise AsmError(f"invalid number {orig}") from None
    if v > 0xFFFF:
        raise AsmError(f"number {orig} is greater than FFFFh")
    return v


def comment_of(text):
    """The comment of a source line: from the first ';' outside of strings ('' and \\" in
    strings, the apostrophe of AF' starts no string)."""
    quote, i, n = None, 0, len(text)
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 1
            elif c == quote:
                quote = None
        elif c == ";":
            return text[i:]
        elif c == '"' or c == "'" and text[max(0, i - 2):i].upper() != "AF":
            quote = c
        i += 1
    return ""


def lex(text):
    """Split one source line into tokens (stops at a ';' comment)."""
    toks, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        nx = text[i + 1] if i + 1 < n else ""
        if c in " \t\r\f":
            i += 1
        elif c == ";":
            break
        elif c == "'":
            s, j = "", i + 1
            while True:
                if j >= n:
                    raise AsmError("unterminated string")
                if text[j] == "'":
                    if text[j + 1:j + 2] == "'":        # '' is a quote inside the string
                        s, j = s + "'", j + 2
                        continue
                    break
                s, j = s + text[j], j + 1
            toks.append(Tok("str", s, text[i:j + 1]))      # raw: with the quotes (DC)
            i = j + 1
        elif c == '"':
            s, j = "", i + 1
            while True:
                if j >= n:
                    raise AsmError("unterminated string")
                ch = text[j]
                if ch == '"':
                    break
                if ch == "\\" and j + 1 < n:
                    e = text[j + 1]
                    if e in C_ESC:
                        s, j = s + chr(C_ESC[e]), j + 2
                    elif e in "xX":              # \x without hex digits is 0 (Pasmo)
                        m = re.match(r"[0-9A-Fa-f]{0,2}", text[j + 2:])
                        s, j = s + chr(int(m.group(0) or "0", 16)), j + 2 + len(m.group(0))
                    elif e in "01234567":
                        m = re.match(r"[0-7]{1,3}", text[j + 1:])
                        s, j = s + chr(int(m.group(0), 8) & 0xFF), j + 1 + len(m.group(0))
                    else:                        # other escapes: the character itself (Pasmo)
                        s, j = s + e, j + 2
                    continue
                s, j = s + ch, j + 1
            toks.append(Tok("str", s, text[i:j + 1]))      # raw: with the quotes (DC)
            i = j + 1
        elif c in "0123456789":                  # not str.isdigit: latin-1 has B2h, B3h, B9h
            m = re.match(r"[0-9A-Za-z$]*", text[i:])
            w = m.group(0)
            u = w.upper().replace("$", "")
            if u.startswith("0X"):
                v = parse_int(u[2:], 16, w)
            elif u.endswith("H"):
                v = parse_int(u[:-1], 16, w)
            elif u.endswith("B") and re.fullmatch(r"[01]+B", u):
                v = parse_int(u[:-1], 2, w)
            elif u[-1] in "OQ":
                v = parse_int(u[:-1], 8, w)
            elif u.endswith("D"):
                v = parse_int(u[:-1], 10, w)
            else:
                v = parse_int(u, 10, w)
            toks.append(Tok("num", v))
            i += len(w)
        elif c in "$#" and nx and nx in HEX:
            m = re.match(r"[0-9A-Fa-f$]*", text[i + 1:])
            toks.append(Tok("num", parse_int(m.group(0), 16, c + m.group(0))))
            i += 1 + len(m.group(0))
        elif c == "&" and nx and (nx in HEX or nx in "HhOoXx"):
            m = re.match(r"[0-9A-Za-z$]*", text[i + 1:])
            w = m.group(0)
            # &X is binary in the Pasmo 0.5.5 code (its documentation says hexadecimal)
            if w[0] in "Hh" and len(w) > 1 and w[1] in HEX:
                v = parse_int(w[1:], 16, "&" + w)
            elif w[0] in "Xx":
                v = parse_int(w[1:], 2, "&" + w)
            elif w[0] in "Oo":
                v = parse_int(w[1:], 8, "&" + w)
            else:
                v = parse_int(w, 16, "&" + w)
            toks.append(Tok("num", v))
            i += 1 + len(w)
        elif c == "%" and nx in ("0", "1"):
            m = re.match(r"[01$]*", text[i + 1:])
            toks.append(Tok("num", parse_int(m.group(0), 2, "%" + m.group(0))))
            i += 1 + len(m.group(0))
        elif ID_START.match(c) and not (c == "?" and not re.match(r"[A-Za-z0-9_?@.]", nx)):
            m = ID_CHARS.match(text, i + 1)
            raw = c + m.group(0)
            name = raw.replace("$", "")
            i = m.end()
            if raw.upper() == "AF" and text[i:i + 1] == "'":
                name = raw = raw + "'"
                i += 1
            toks.append(Tok("id", name, raw))
        elif text[i:i + 2] in OPS2:
            toks.append(Tok("op", text[i:i + 2]))
            i += 2
        elif c in OPS1:
            toks.append(Tok("op", c))
            i += 1
        else:
            raise AsmError(f"unexpected character {c!r}")
    return toks


def after_keyword(text, word):
    """The text after the directive `word` (INCLUDE, INCBIN, .ERROR ...). The word must
    stand alone, so a label like 'my_include:' before it does not match."""
    m = re.search(r"(?i)(?<![\w?@.$])" + re.escape(word) + r"(?![\w?@.$])", text)
    return text[m.end():] if m else ""


def split_commas(toks):
    """Split tokens at commas that are not inside brackets."""
    parts, cur, depth = [], [], 0
    for t in toks:
        if t.kind == "op" and t.val in "([":
            depth += 1
        elif t.kind == "op" and t.val in ")]":
            depth -= 1
        if t.kind == "op" and t.val == "," and depth == 0:
            parts.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur or parts:
        parts.append(cur)
    return parts


def split_text_args(text):
    """Macro arguments as text, split at commas outside of brackets and strings."""
    args, cur, depth, quote = [], "", 0, None
    for ch in text:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            cur += ch
        elif ch == ";":
            break
        elif ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            depth += ch in "(["
            depth -= ch in ")]"
            cur += ch
    if cur.strip() or args:
        args.append(cur.strip())
    return args


def subst_idents(text, func):
    """Replace identifiers outside strings and comments by func(name) (None = keep),
    then join tokens around '##'."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == ";":
            out.append(text[i:])
            break
        if c in "'\"":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if (c == '"' and text[j] == "\\") else 1
            out.append(text[i:j + 1])
            i = j + 1
            continue
        prev = text[i - 1] if i else ""
        # letters after $ # & % belong to a number like $FF, unless it is the ## operator
        after_number_prefix = prev in ("$", "&", "%") or (prev == "#" and text[i - 2:i] != "##")
        if ID_START.match(c) and not (re.match(r"[A-Za-z0-9]", prev) or after_number_prefix):
            m = ID_CHARS.match(text, i + 1)
            word = c + m.group(0)
            rep = func(word)
            out.append(word if rep is None else rep)
            i = m.end()
            continue
        out.append(c)
        i += 1
    return re.sub(r"\s*##\s*", "", "".join(out))
