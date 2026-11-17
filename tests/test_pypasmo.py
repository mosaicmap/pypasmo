"""pypasmo's own tests: directives, expressions, literals, errors and output formats.

The expected values are computed by hand from the Pasmo documentation and source code,
they are not copied from pypasmo output.
"""
import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT_FORMATS = HERE / "output_formats"      # examples for each machine and their ready files
sys.path.insert(0, str(HERE.parent))
import pypasmo  # noqa: E402


def asm(src, **opts):
    return pypasmo.assemble_text(src, **opts)


def code(src, **opts):
    """Assemble and return the bytes from the lowest used address."""
    return pypasmo.image(asm(src, **opts).mem)[1]


def h(text):
    return bytes.fromhex(text)


def run_main(*argv):
    """Run the command line; return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = pypasmo.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


class Literals(unittest.TestCase):
    def test_number_formats(self):
        src = (" db 90, 90D, 5Ah, 0x5A, $5A, #5A, &5A, &H5A, &X01011010, &O132, 132O, 132Q,"
               " %01011010, 01011010B, %0101$1010, 0$5Ah\n")
        self.assertEqual(code(src), b"\x5A" * 16)

    def test_hex_with_letter_needs_leading_digit(self):
        with self.assertRaises(pypasmo.AsmError):        # FFh is an identifier, not a number
            code(" db FFh\n")

    def test_number_out_of_range(self):
        # an error in pypasmo (Pasmo silently truncates 12345h and 70000)
        for src in (" dw 12345h\n", " dw 70000\n", " dw $10000\n", " dw #10000\n", " dw &H10000\n",
                    " dw %10000000000000000\n"):
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    code(src)

    def test_ampersand_x_is_binary(self):
        # Pasmo 0.5.5 code: &X is binary (its documentation says hexadecimal)
        self.assertEqual(code(" db &X101, &x11\n"), h("05 03"))
        with self.assertRaises(pypasmo.AsmError):
            code(" db &X5A\n")

    def test_c_string_escapes_like_pasmo(self):
        # unknown escapes give the character itself, \x without digits gives 0
        self.assertEqual(code(' db "\\q\\\'\\x"\n'), b"q'\x00")

    def test_non_ascii_bytes_are_kept(self):
        # Pasmo works with bytes: a UTF-8 string gives its UTF-8 bytes; a 1 byte
        # character >= 80h is 00xxh (Pasmo built with a signed char gives FFxxh)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "u.asm")
            src.write_bytes(b' db "\xc3\xa9"\n dw "\xe9"\n')
            a = pypasmo.Assembler()
            a.assemble(src)
            self.assertEqual(pypasmo.image(a.mem)[1], h("C3 A9 E9 00"))

    def test_strings(self):
        self.assertEqual(code(""" db 'It''s', "q\\"q", "\\x41\\101\\n\\r\\t\\\\"\n"""),
                         b"It's" + b'q"q' + b"AA\n\r\t\\")

    def test_char_as_number(self):
        self.assertEqual(code(" db 'A'+1, 'a' AND 0DFh\n dw 'AB'\n ld a,'0'\n"), h("42 41 41 42 3E 30"))

    def test_string_too_long_for_number(self):
        with self.assertRaises(pypasmo.AsmError):
            code(" ld a,'abc'\n")


class Expressions(unittest.TestCase):
    def assertExpr(self, expr, value):
        data = code(f" dw {expr}\n")
        self.assertEqual(data, bytes([value & 0xFF, (value >> 8) & 0xFF]), expr)

    def test_arithmetic(self):
        for e, v in [("2+3*4", 14), ("(2+3)*4", 20), ("17/5", 3), ("17 MOD 5", 2), ("17 % 5", 2),
                     ("1 SHL 4", 16), ("1 << 4", 16), ("80h SHR 3", 16), ("80h >> 3", 16),
                     ("0 - 1", 0xFFFF), ("1000h * 10h", 0)]:
            self.assertExpr(e, v)

    def test_pasmo_precedence_quirks(self):
        self.assertExpr("-1+2", -3)               # unary minus binds looser than +
        self.assertExpr("HIGH 1234h+100h", 0x13)  # HIGH takes the whole expression
        self.assertExpr("NOT 0 AND 0FFh", 0xFF)   # NOT binds tighter than AND
        self.assertExpr("1 OR 2 AND 0", 1)        # AND before OR

    def test_relational_and_logic(self):
        for e, v in [("5 EQ 5", 0xFFFF), ("5 = 5", 0xFFFF), ("5 NE 5", 0), ("5 != 4", 0xFFFF),
                     ("3 LT 4", 0xFFFF), ("3 < 4", 0xFFFF), ("3 GE 4", 0), ("4 >= 4", 0xFFFF),
                     ("3 LE 2", 0), ("3 > 2", 0xFFFF), ("!0", 0xFFFF), ("!5", 0),
                     ("~1", 0xFFFE), ("0F0h AND 3Ch", 0x30), ("0F0h & 3Ch", 0x30),
                     ("0F0h OR 0Fh", 0xFF), ("0F0h | 0Fh", 0xFF), ("0FFh XOR 0Fh", 0xF0),
                     ("1 && 2", 0xFFFF), ("1 && 0", 0), ("0 || 0", 0), ("0 || 3", 0xFFFF),
                     ("1 ? 11h : 22h", 0x11), ("0 ? 11h : 22h", 0x22), ("LOW 1234h", 0x34)]:
            self.assertExpr(e, v)

    def test_short_circuit_ignores_undefined(self):
        self.assertEqual(code(" db 0 && undef, 1 || undef, 1 ? 5 : undef\n"), h("00 FF 05"))

    def test_dollar_is_statement_start(self):
        self.assertEqual(code(" org 100h\n nop\n dw $, $\n jr $\n"), h("00 01 01 01 01 18 FE"))

    def test_undefined_symbol(self):
        with self.assertRaises(pypasmo.AsmError):
            code(" ld a, nowhere\n")

    def test_division_by_zero(self):
        with self.assertRaises(pypasmo.AsmError):
            code(" db 1/0\n")

    def test_unary_after_binary_rejected(self):
        with self.assertRaises(pypasmo.AsmError):     # Pasmo 0.5.5 rejects it too
            code(" db 2*-1\n")


class Labels(unittest.TestCase):
    def test_label_forms(self):
        a = asm(" org 10h\nfirst nop\nsecond: nop\n    third: nop\n    fourth nop\n")
        self.assertEqual({k: a.symbols[k] for k in ("first", "second", "third", "fourth")},
                         {"first": 0x10, "second": 0x11, "third": 0x12, "fourth": 0x13})

    def test_forward_reference(self):
        self.assertEqual(code(" jp later\n nop\nlater: jr later\n"), h("C3 04 00 00 18 FE"))

    def test_case_sensitive_by_default(self):
        with self.assertRaises(pypasmo.AsmError):
            code("Start: jp start\n")
        self.assertEqual(code("Start: jp start\n", nocase=True), h("C3 00 00"))

    def test_mnemonics_are_case_insensitive(self):
        self.assertEqual(code(" LD A,1\n ld b,2\n Ld C,3\n"), h("3E 01 06 02 0E 03"))

    def test_duplicate_label(self):
        with self.assertRaises(pypasmo.AsmError):
            code("x: nop\nx: nop\n")

    def test_reserved_word_as_label(self):
        with self.assertRaises(pypasmo.AsmError):
            code("hl: nop\n")

    def test_dollar_in_identifier(self):
        # '$' is removed from identifiers, but only AFTER the reserved word check,
        # so h$l is a label "hl", not the register (Pasmo 0.5.x, also fixed in 0.6.0)
        a = asm("h$l: nop\n jp h$l\nl$d equ 7\n ld a,l$d\nmy$label: jp mylabel\n")
        self.assertEqual(pypasmo.image(a.mem)[1], h("00 C3 00 00 3E 07 C3 06 00"))
        self.assertEqual(a.symbols["hl"], 0)

    def test_comments_and_line_numbers(self):
        self.assertEqual(code("; just a comment\n ld a,';' ; semicolon in a string\n10 nop\n"), h("3E 3B 00"))

    def test_label_on_org_gets_new_address(self):
        self.assertEqual(asm("start org 100h\n nop\n").symbols["start"], 0x100)

    def test_autolocal(self):
        src = "a1: jp _x\n_x: nop\nb1: jp _x\n_x: nop\n"
        self.assertEqual(code(src, alocal=True), h("C3 03 00 00 C3 07 00 00"))
        with self.assertRaises(pypasmo.AsmError):     # without --alocal _x is defined twice
            code(src)


class Directives(unittest.TestCase):
    def test_org_and_gap(self):
        self.assertEqual(code(" org 100h\n db 1\n org 104h\n db 2\n"), h("01 00 00 00 02"))

    def test_equ(self):
        self.assertEqual(code("v equ 1234h\n ld hl,v\n"), h("21 34 12"))
        with self.assertRaises(pypasmo.AsmError):
            asm("v equ 1\nv equ 2\n")

    def test_equ_forward_references(self):
        # pasmodoc: "is legal to assign a value undefined in the first pass"
        self.assertEqual(code("xx equ yy+1\nyy equ 5\n db xx\n"), h("06"))
        self.assertEqual(code("xx equ yy+1\nyy equ zz+1\nzz equ 5\n db xx, yy, zz\n"), h("07 06 05"))

    def test_defl_redefinition(self):
        self.assertEqual(code("n defl 1\n db n\nn defl n+1\n db n\nn defl n*10\n db n\n"), h("01 02 14"))

    def test_db_dw_ds(self):
        self.assertEqual(code(" db 1, 2, \"ab\"\n defb 3\n defm 'x'\n dw 1234h\n defw 1, 2\n"),
                         h("01 02 61 62 03 78 34 12 01 00 02 00"))
        self.assertEqual(code(" ds 3, 0AAh\n defs 2\n db 1\n"), h("AA AA AA 00 00 01"))

    def test_question_mark_skips_bytes(self):
        self.assertEqual(sorted(asm(" db 1, ?, 3\n").mem.items()), [(0, 1), (2, 3)])
        self.assertEqual(sorted(asm(" db 1\n ds 2, ?\n db 4\n").mem.items()), [(0, 1), (3, 4)])

    def test_ds_past_64k_warns(self):
        # like Pasmo: a negative DS size wraps around with a warning ...
        a = asm(" org 10h\n nop\n ds 8 - $\n")
        self.assertTrue(any("64KB" in w for w in a.warnings))
        with self.assertRaises(pypasmo.AsmError):     # ... which --werror turns into an error
            asm(" org 10h\n nop\n ds 8 - $\n", werror=True)

    def test_include_and_incbin(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "inc.asm").write_text("value equ 42h\n ld a,value\n", encoding="utf-8")
            Path(d, "data.bin").write_bytes(h("DE AD BE EF"))
            Path(d, "main.asm").write_text(' include "inc.asm"\n incbin data.bin\n include \'inc2.asm\'\n',
                                           encoding="utf-8")
            Path(d, "inc2.asm").write_text(" nop\n", encoding="utf-8")
            a = pypasmo.Assembler()
            a.assemble(Path(d, "main.asm"))
            self.assertEqual(pypasmo.image(a.mem)[1], h("3E 42 DE AD BE EF 00"))

    def test_if_else_nested(self):
        src = """
x equ 1
 if x
   db 1
   if 0
     db 2
   else
     db 3
   endif
 else
   db 4
   if 1
     db 5
   endif
 endif
 if x = 1 && 2 > 1
   db 6
 endif
"""
        self.assertEqual(code(src), h("01 03 06"))

    def test_ifdef_ifndef(self):
        src = "x equ 1\n ifdef x\n db 1\n endif\n ifdef y\n db 2\n endif\n ifndef y\n db 3\n endif\n"
        self.assertEqual(code(src), h("01 03"))

    def test_predefined_symbol(self):
        src = " if defined FAST\n db FAST\n else\n db 0\n endif\n"
        self.assertEqual(code(src), h("00"))
        self.assertEqual(code(src, predefined={"FAST": 7}), h("07"))

    def test_end_stops_and_sets_entry(self):
        a = asm(" org 8000h\nstart: nop\n end start\n db 99h\n")
        self.assertEqual(pypasmo.image(a.mem)[1], h("00"))
        self.assertEqual(a.entry, 0x8000)

    def test_proc_local(self):
        src = """
p1 proc
   local loop
loop: djnz loop
   endp
p2 proc
   local loop
loop: djnz loop
   jr loop
   endp
loop: nop
   jp loop
"""
        self.assertEqual(code(src), h("10 FE 10 FE 18 FC 00 C3 06 00"))

    def test_endp_without_proc(self):
        with self.assertRaises(pypasmo.AsmError):
            code(" endp\n")

    def test_macro_both_forms_and_params(self):
        src = """
set_reg macro reg, value
   ld reg, value
   endm
   macro twice, instr
   instr
   instr
   endm
   set_reg a, 5
   set_reg b, 'x'
   twice nop
   twice inc hl
"""
        self.assertEqual(code(src), h("3E 05 06 78 00 00 23 23"))

    def test_macro_local_labels(self):
        src = """
wait macro
   local back
back: djnz back
   endm
   wait
   wait
"""
        self.assertEqual(code(src), h("10 FE 10 FE"))

    def test_macro_nul_shift_exitm(self):
        src = """
pushall macro reg
   rept -1
   if nul reg
   exitm
   endif
   push reg
   .shift
   endm
   endm
   pushall bc, de, hl
"""
        self.assertEqual(code(src), h("C5 D5 E5"))

    def test_macro_identifier_pasting(self):
        src = "mk macro n\nlbl##n: db n\n endm\n mk 1\n mk 2\n dw lbl1, lbl2\n"
        self.assertEqual(code(src), h("01 02 00 00 01 00"))

    def test_rept_with_counter(self):
        src = """
   rept 3
   nop
   endm
   rept 3, k
   db k
   endm
   rept 3, k, 10
   db k
   endm
   rept 3, k, 7, -2
   db k
   endm
   rept 0
   db 99h
   endm
"""
        self.assertEqual(code(src), h("00 00 00 00 01 02 0A 0B 0C 07 05 03"))

    def test_irp(self):
        self.assertEqual(code(" irp reg, bc, de, ix\n push reg\n endm\n"), h("C5 D5 DD E5"))

    def test_unclosed_blocks(self):
        for src in (" if 1\n nop\n", " rept 2\n nop\n", "m macro\n nop\n", "p proc\n nop\n"):
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    code(src)

    def test_error_and_warning(self):
        with self.assertRaisesRegex(pypasmo.AsmError, "my error"):
            code(" .error my error\n")
        a = asm(" .warning take care\n nop\n")
        self.assertTrue(any("take care" in w for w in a.warnings))
        self.assertEqual(code(" if 0\n .error ignored, even with ěščř\n endif\n"), b"")

    def test_werror(self):
        with self.assertRaises(pypasmo.AsmError):
            asm(" .warning x\n", werror=True)

    def test_public(self):
        a = asm(" public a1\na1: nop\nb1: nop\n")
        self.assertEqual(pypasmo.symbol_text(a, a.publics), "a1\t\tEQU 00000H\n")


class Instructions(unittest.TestCase):
    def test_index_registers(self):
        src = """
 ld a,(ix-1)
 ld (iy+7Fh),0
 ld (ix),b
 jp (ix)
 ex (sp),iy
 ld (8000h),ix
 add iy,sp
 bit 7,(ix+2)
 inc (iy-80h)
"""
        self.assertEqual(code(src), h("DD 7E FF FD 36 7F 00 DD 70 00 DD E9 FD E3 DD 22 00 80 FD 39"
                                      " DD CB 02 7E FD 34 80"))

    def test_brackets_as_indirection(self):
        self.assertEqual(code(" ld a,[1234h]\n ld [ix+2],b\n jp [hl]\n"), h("3A 34 12 DD 70 02 E9"))

    def test_bracket_only_mode(self):
        # with --bracket ( ) only groups expressions: ld a,(5) is LD A,5
        self.assertEqual(code(" ld a,(5)\n ld a,[5]\n jp [hl]\n", bracket=True), h("3E 05 3A 05 00 E9"))

    def test_parenthesis_that_is_not_indirection(self):
        # LD B,(n) and OR (n) do not exist, so Pasmo takes (n) as an expression and warns
        a = asm(" ld b,(5)\n or (2)\n ld a,(5)\n")
        self.assertEqual(pypasmo.image(a.mem)[1], h("06 05 F6 02 3A 05 00"))
        self.assertEqual(len(a.warnings), 2)

    def test_undocumented(self):
        self.assertEqual(code(" ld a,ixh\n ld iyl,5\n sll b\n sll (ix+1)\n"),
                         h("DD 7C FD 2E 05 CB 30 DD CB 01 36"))

    def test_extensions_warn(self):
        a = asm(" out (c),0\n in f,(c)\n")
        self.assertEqual(pypasmo.image(a.mem)[1], h("ED 71 ED 70"))
        self.assertEqual(len(a.warnings), 2)

    def test_w8080(self):
        a = asm(" ld a,1\n jr $\n exx\n ld ix,0\n bit 0,a\n out (5),a\n ex de,hl\n jp pe,0\n", w8080=True)
        warned = sorted(int(w.split(":")[1]) for w in a.warnings)
        self.assertEqual(warned, [2, 3, 4, 5])         # jr, exx, ld ix, bit

    def test_relative_jumps(self):
        self.assertEqual(code(" org 100h\n jr 0C8h\n djnz $\n jr nz,$+2\n"), h("18 C6 10 FE 20 00"))
        with self.assertRaises(pypasmo.AsmError):
            code(" org 100h\n jr 200h\n")

    def test_index_offset_range_like_pasmo(self):
        # like Pasmo 0..255 is allowed (0FFh = -1), negative down to -128
        self.assertEqual(code(" ld a,(ix+0FFh)\n ld a,(iy+200)\n ld a,(ix-128)\n"),
                         h("DD 7E FF FD 7E C8 DD 7E 80"))

    def test_index_offset_is_computed_left_to_right(self):
        # Pasmo bug: (IX-12+13) = IX-(12+13) = IX-25; correct is IX+1 (as in the paged fork)
        self.assertEqual(code(" ld a,(ix-12+13)\n ld a,(iy-10-5-10)\n ld a,(ix+2-1-3-2-4-3)\n"),
                         h("DD 7E 01 FD 7E E7 DD 7E F5"))

    def test_half_index_register_with_hl_memory(self):
        # used to give DD 66 (LD H,(IX+d) without the offset byte)
        for line in ("ld ixh,(hl)", "ld (hl),iyl", "ld ixl,(hl)"):
            with self.subTest(line):
                with self.assertRaises(pypasmo.AsmError):
                    code(f" {line}\n")

    def test_invalid(self):
        for line in ["ld (hl),(hl)", "ld ix,hl", "add ix,iy", "ld h,ixl", "ex de,ix", "jp (ix+1)",
                     "rlc ixh", "ld a,(ix+256)", "ld a,(ix-129)", "bit 8,a", "rst 9", "im 3", "adc ix,bc",
                     "ld a,(bc)+1", "jr pe,0", "push sp", "ld sp,de", "out (c),1", "foo a"]:
            with self.subTest(line):
                with self.assertRaises(pypasmo.AsmError):
                    code(f" {line}\n")


class PasmoCompatibility(unittest.TestCase):
    """Cases found by comparing with the real Pasmo exe (0.5.4.beta2, the 0.5.5 source)."""

    def test_empty_lists_are_errors(self):
        # Pasmo 0.5.5 (2026-11-03): "Value expected but '(eol)' found", "Identifier expected",
        # "IRP without parameters"; pypasmo accepted these lines and wrote nothing
        for src in (" db\n", " dw\n", " defm\n", " defb\n", " defw\n", " dz\n", " dc\n", " d_zx81\n",
                    " public\n", " proc\n local\n endp\n", " irp x,\n db x\n endm\n",
                    " irp x,1,,2\n db x\n endm\n"):
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    code(src)

    def test_reserved_words_are_not_parameters_or_local_names(self):
        # Pasmo 0.5.5: "Identifier expected but 'A' found"; in pypasmo "mm macro a" made
        # every register A in the body the argument
        for src in ("mm macro a\n ld a,1\n endm\n mm b\n", "mm macro p1, hl\n db 1\n endm\n",
                    "mm macro nz\n endm\n", "mm macro nop\n endm\n", " irp a,1,2\n db 1\n endm\n",
                    " proc\n local hl\n endp\n", " public a\n",
                    "mm macro p1, p1\n db p1\n endm\n mm 1,2\n"):     # a parameter twice
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    code(src)
        # names of pypasmo directives are not reserved, the fork directives with
        # --pasmo-syntax-055 neither
        self.assertEqual(code("mm macro align\n db align\n endm\n mm 3\n"), h("03"))
        self.assertEqual(code("mm macro bank\n db bank\n endm\n mm 3\n", pasmo_syntax=True), h("03"))

    def test_parenthesis_is_a_value_where_no_memory_form_exists(self):
        src = " rst (8)\n jr ($+2)\n djnz ($)\n call (5)\n jp nz,(5)\n bit (1),a\n im (2)\n"
        self.assertEqual(code(src), h("CF 18 00 10 FE CD 05 00 C2 05 00 CB 4F ED 5E"))

    def test_text_after_memory_parenthesis_is_an_error(self):
        # Pasmo reads (1) as memory and then stops at '+'; it must not become LD A,3
        for line in ("ld a,(1)+2", "ld hl,(5)*2", "ld bc,(1)+(2)", "ld ix,(1)+2", "jp (1)+2"):
            with self.subTest(line):
                with self.assertRaises(pypasmo.AsmError):
                    code(f" {line}\n")
        # where no memory form exists it is an expression (no warning in Pasmo)
        a = asm(" ld b,(1)+2\n cp (1+2)*3\n call (1)+2\n")
        self.assertEqual(pypasmo.image(a.mem)[1], h("06 03 FE 09 CD 03 00"))
        self.assertEqual(a.warnings, [])

    def test_no_paren_warning_for_index_register(self):
        self.assertEqual(asm(" ld (ix+1),(5)\n").warnings, [])
        self.assertEqual(len(asm(" ld (hl),(5)\n").warnings), 1)

    def test_alu_operand_forms(self):
        # both forms give the same instruction (Pasmo accepts only ADD A,B and SUB B)
        self.assertEqual(code(" add a,b\n adc a,1\n sbc a,(hl)\n sub b\n and 1\n cp (hl)\n"),
                         h("80 CE 01 9E 90 E6 01 BE"))
        self.assertEqual(code(" add b\n adc 1\n sbc (hl)\n sub a,b\n and a,1\n cp a,(hl)\n"),
                         h("80 CE 01 9E 90 E6 01 BE"))
        self.assertEqual(code(" ex af,af'\n ex af,af\n"), h("08 08"))

    def test_relative_jump_wraps_around_64k(self):
        # the Z80 adds the offset modulo 64 KB (Pasmo says out of range)
        self.assertEqual(code(" org 0FFF0h\n jr 5\n"), h("18 13"))
        with self.assertRaises(pypasmo.AsmError):
            code(" org 0FFF0h\n jr 100h\n")

    def test_string_followed_by_operator_in_db(self):
        with self.assertRaises(pypasmo.AsmError):
            code(' db "AB"+1\n')
        self.assertEqual(code(" db 'A'+1\n"), h("42"))

    def test_include_without_file_name(self):
        # used to crash with IndexError
        for src in (" include\n", " incbin\n"):
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    code(src)

    def test_irp_needs_a_comma(self):
        with self.assertRaises(pypasmo.AsmError):
            code(" irp x\n db x\n endm\n")

    def test_local_names_start_at_zero(self):
        a = asm(" proc\n local x, y\nx: nop\ny: nop\n endp\n")
        self.assertEqual(pypasmo.symbol_text(a), "00000000\tEQU 00000H\n00000001\tEQU 00001H\n")

    def test_redeclared_local_warns(self):
        a = asm(" proc\n local x, x\nx: nop\n endp\n")
        self.assertEqual(len(a.warnings), 1)
        self.assertIn("redeclared LOCAL", a.warnings[0])

    def test_local_is_shared_by_rept_repetitions(self):
        # one LOCAL level for the whole REPT: the label is defined twice (Pasmo error)
        with self.assertRaises(pypasmo.AsmError):
            code(" rept 2\n local x\nx: jp x\n endm\n")
        # the counter is one local symbol, the next LOCAL gets 00000001
        a = asm(" rept 3, cnt\n db cnt\n endm\n proc\n local zz\nzz: nop\n endp\n")
        self.assertEqual(pypasmo.image(a.mem)[1], h("00 01 02 00"))
        self.assertIn("00000001", pypasmo.symbol_text(a))

    def test_skipped_if_skips_macro_blocks_whole(self):
        # Pasmo (condition_false, parseELSE): in a skipped branch MACRO / REPT / IRP are
        # skipped up to their ENDM, IF / ELSE / ENDIF inside them do not count
        # (ENDM closes an unterminated IF of the body). Checked with Pasmo 0.5.5.
        self.assertEqual(code(" if 0\nm1 macro\n if 1\n db 1\n endm\n endif\n db 2\n"), h("02"))
        self.assertEqual(code(" if 1\n db 3\n else\n rept 2\n if 1\n db 1\n endm\n endif\n db 2\n"),
                         h("03 02"))
        self.assertEqual(code(" if 0\n irp x,1,2\n else\n endm\n db 1\n endif\n db 2\n"), h("02"))

    def test_endm_in_skipped_branch_is_an_error(self):
        # Pasmo stops skipping at ENDM and then reports "ENDM outside of macro"
        with self.assertRaises(pypasmo.AsmError):
            code(" if 0\n endm\n endif\n db 2\n")

    def test_8080_mode_is_an_error(self):
        # Pasmo 0.5.5: .Z80 is accepted, .8080 gives "8080 mode not supported" (8080
        # syntax would assemble to wrong code: JP nn there is "jump if positive")
        self.assertEqual(code(" .z80\n nop\n"), h("00"))
        with self.assertRaises(pypasmo.AsmError):
            code(" .8080\n nop\n")
        with self.assertRaises(pypasmo.AsmError):        # also with a label
            code("x: .8080\n")

    def test_64k_of_code_is_a_clean_error_for_tape_formats(self):
        a = asm(" org 2Bh\n nop\n ds 2Bh-$\n")
        self.assertEqual(len(pypasmo.output_bytes(a, "bin", "")), 0x10000)
        for fmt in ("tap", "plus3dos", "cdt", "msx", "amsdos", "sna-48k", "z80-48k", "tap128", "tapbas128"):
            with self.subTest(fmt):
                with self.assertRaises(pypasmo.AsmError):
                    pypasmo.output_bytes(a, fmt, "x")

    def test_messages_use_the_main_option_names(self):
        # --tap-48k, --tap-wloader-128k ... (--tap, --tapbas128 ... are other names)
        a = asm(" org 2Bh\n nop\n ds 2Bh-$\n")
        for fmt, name in (("tap", "--tap-48k"), ("tapbas", "--tap-wloader-48k"), ("tzx", "--tzx-48k"),
                          ("tzxbas", "--tzx-wloader-48k"), ("tap128", "--tap-128k"),
                          ("tapbas128", "--tap-wloader-128k"), ("cdtbas", "--cdt-wloader"),
                          ("pzx-48k", "--pzx-48k"), ("pzx-wloader-48k", "--pzx-wloader-48k"),
                          ("tzx-128k", "--tzx-128k"), ("pzx-wloader-128k", "--pzx-wloader-128k")):
            with self.subTest(fmt):
                with self.assertRaises(pypasmo.AsmError) as e:
                    pypasmo.output_bytes(a, fmt, "x")
                self.assertIn(f"too big for {name}", str(e.exception))
        with self.assertRaises(pypasmo.AsmError) as e:
            pypasmo.output_bytes(asm(" org 8000h\n ret\n bank 1\n org 0C000h\n nop\n"), "tap", "x")
        self.assertIn("(--tap-128k, --tap-wloader-128k, --tzx-128k, ", str(e.exception))
        with self.assertRaises(pypasmo.AsmError) as e:
            pypasmo.output_bytes(asm(' org 8000h\n ret\n tape_block "a",8000h,1\n'), "tap128", "x")
        self.assertIn("--tap-128k (use --tap-48k, --tap-wloader-48k, --tzx-48k, --tzx-wloader-48k, "
                      "--pzx-48k or --pzx-wloader-48k)", str(e.exception))
        self.assertIn("Blocks of --tap-128k / --tap-wloader-128k",
                      pypasmo.memmap_text(asm(" org 8000h\n ret\n bank 1\n org 0C000h\n nop\n")))

    def test_tap128_with_banks_may_have_more_than_64k(self):
        # the limit is for the 64 KB address space; BANK 1..7 are counted apart
        src = " org 8000h\n ds 8000h, 1\n" + "".join(f" bank {b}\n org 0C000h\n ds 4000h, {b}\n" for b in (1, 3, 4, 6, 7))
        tap = pypasmo.output_bytes(asm(src), "tap128", "x")
        # 8000h-FFFFh is bank 2 + bank 0, so 7 CODE blocks of 16 KB:
        # header 2+19 bytes, data 2+len+2 (flag, checksum)
        self.assertEqual(len(tap), 7 * 21 + 7 * (0x4000 + 4))


class ForkExtensions(unittest.TestCase):
    """DG, DUP/EDUP, STRUCT/ENDS and BANK from the Pasmo 0.5.5.paged fork."""

    def test_dg(self):
        # the example from the fork documentation (its 6th byte 7Bh is a typo: -XXXX--- = 78h)
        src = (" dg ---X----\n dg --XXXX--\n dg -X-X----\n dg \"--XXX---\"\n"
               " dg ---X-X--  ; comment\n dg -XXXX---\n dg - - - X - - - -\n dg ________\n")
        self.assertEqual(code(src), h("10 3C 50 38 14 78 10 00"))
        self.assertEqual(code(" dg xxxx....x.x.x.x.\n"), h("F0 AA"))
        for bad in (" dg xxx\n", " dg\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad)

    def test_dup_edup(self):
        self.assertEqual(code(" dup 3\n db 7\n edup\n dup 2, cnt\n db cnt\n endm\n"), h("07 07 07 00 01"))

    def test_struct(self):
        a = asm("size equ 10\n struct foo\nbuz db 3\nxxx db \"nnnnn\"\nyyyy defb 1,2,3,4\n"
                "bar dw 1\nzzz: ds size\n db 0\n ends\n ld a,(ix+foo.bar)\n db foo\n")
        sym = {k: v for k, v in a.symbols.items() if k.startswith("foo")}
        self.assertEqual(sym, {"foo.buz": 0, "foo.xxx": 1, "foo.yyyy": 6, "foo.bar": 10,
                               "foo.zzz": 12, "foo": 23})
        self.assertEqual(pypasmo.image(a.mem)[1], h("DD 7E 0A 17"))     # no code from STRUCT
        for bad in (" struct s\n nop\n ends\n", " struct s\n db 1\n", " ends\n",
                    " struct s\n struct t\n ends\n ends\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad)

    SRC128 = (" org 8000h\nstart: ld a,1\n ret\n bank 1\n org 0C000h\n db 11h\n"
              " bank 3\n org 0C000h\n db 33h, 34h\n bank 0\n org 0C000h\n db 0\n end start\n")

    def tape_blocks(self, data):
        blocks, pos = [], 0
        while pos < len(data):
            n = int.from_bytes(data[pos:pos + 2], "little")
            blocks.append(data[pos + 2:pos + 2 + n])
            pos += 2 + n
        return blocks

    def test_bank_tap128(self):
        a = asm(self.SRC128)
        self.assertEqual(sorted(a.banks), [1, 3])
        blocks = self.tape_blocks(pypasmo.output_bytes(a, "tap128", "x"))
        heads = [(b[2:12], int.from_bytes(b[12:14], "little"), int.from_bytes(b[14:16], "little"))
                 for b in blocks[0::2]]
        self.assertEqual(heads, [(b"bank0.tap ", 1, 0xC000), (b"bank1.tap ", 1, 0xC000),
                                 (b"bank2.tap ", 3, 0x8000), (b"bank3.tap ", 2, 0xC000)])
        self.assertEqual([b[1:-1] for b in blocks[1::2]], [h("00"), h("11"), h("3E 01 C9"), h("33 34")])

    def test_bank_tapbas128_loader(self):
        blocks = self.tape_blocks(pypasmo.output_bytes(asm(self.SRC128), "tapbas128", "x"))
        self.assertEqual(blocks[0][1:12], b"\x00loader    ")
        basic = blocks[1][1:-1]
        self.assertIn(b'\xFD\xB0"32767"', basic)                         # CLEAR VAL "32767"
        self.assertIn(b'\xE4\xB0"0",\xB0"1",\xB0"2",\xB0"3",\xB0"8"\r', basic)   # DATA
        self.assertIn(b'\xF9\xC0\xB0"32768"\r', basic)                    # RANDOMIZE USR 32768 (no STOP)
        self.assertIn(bytes.fromhex("EA F3 3A 5C 5B E6 F8 47 3A 38 5C B0 32 5C 5B 01 FD 7F ED 79 FB C9"),
                      basic)                                              # 1 REM <bank switch code>
        self.assertEqual(len(blocks), 2 + 8)

    def test_bank_tapbas128_pages_bank_0_before_the_start(self):
        # the last loaded block is the highest bank: page bank 0 in at C000h again before
        # the program starts (the fork leaves the last bank there; code in bank 0 at C000h
        # did not run, tried in the 128K simulator of SkoolKit)
        basic = self.tape_blocks(pypasmo.output_bytes(asm(self.SRC128), "tapbas128", "x"))[1][1:-1]
        val = lambda n: b'\xB0"' + str(n).encode() + b'"'  # noqa: E731
        # 50 IF b<8 THEN POKE 23608,b: RANDOMIZE USR c: LOAD "" CODE: GO TO 40
        self.assertIn(b"\x00\x32", basic)
        self.assertIn(b"\xEF\"\"\xAF:\xEC" + val(40) + b"\r", basic)
        # 60 POKE 23608,0: RANDOMIZE USR c: POKE 23608,a: RANDOMIZE USR 32768 - then the
        # program runs to its end: "0 OK" instead of the "9 STOP statement" of the fork
        self.assertIn(b"\x00\x3C", basic)
        self.assertIn(b"\xF4" + val(23608) + b"," + val(0) + b":\xF9\xC0c:\xF4" + val(23608) + b",a:\xF9\xC0"
                      + val(32768) + b"\r", basic)
        self.assertNotIn(b"\xE2", basic)                                 # no STOP, no line 70
        self.assertNotIn(b"\x00\x46", basic)

    def test_tap128_same_byte_twice_is_an_error(self):
        # 8000h and BANK 2 at C000h are the same byte of bank 2 (as for the 128K snapshots)
        with self.assertRaises(pypasmo.AsmError):
            pypasmo.output_bytes(asm(" org 8000h\n ret\n bank 2\n org 0C000h\n db 1\n"), "tap128", "x")

    def test_loader_clear_too_low_is_a_warning(self):
        # measured in the simulator of SkoolKit: the Basic loaders can not CLEAR below
        # about 160 bytes after their program ("M RAMTOP no good", "4 Out of memory")
        for src, fmt in ((" org 5D00h\nst: ret\n end st\n", "tapbas"),
                         (" org 4000h\nst: ret\n end st\n", "tzxbas"),                 # video RAM: allowed
                         (" org 5D00h\nst: ret\n end st\n", "pzx-wloader-48k"),
                         (' org 5D00h\nst: ret\n tape_block "a", st, 1\n end st\n', "tapbas"),
                         (" org 5D00h\nst: ret\n bank 1\n org 0C000h\n db 1\n end st\n", "tapbas128")):
            with self.subTest(src, fmt=fmt):
                a = asm(src)
                self.assertTrue(pypasmo.output_bytes(a, fmt, "x"))
                self.assertTrue(any("CLEAR" in w for w in a.warnings), a.warnings)
        a = asm(" org 100h\n ret\n")
        pypasmo.output_bytes(a, "tap", "x")
        self.assertTrue(any("ROM" in w for w in a.warnings), a.warnings)
        for fmt in ("tap", "tapbas", "tapbas128"):
            a = asm(" org 8000h\nst: ret\n end st\n")
            pypasmo.output_bytes(a, fmt, "x")
            self.assertEqual(a.warnings, [], fmt)
        a = asm(" org 100h\n ret\n")
        pypasmo.output_bytes(a, "pzx-48k", "x")
        self.assertIn("warning: --pzx-48k: code at 0000h-3FFFh is in the ROM, LOAD can not put it there",
                      a.warnings)
        for fmt in ("tapbas", "tzxbas", "pzx-wloader-48k", "dsk-plus3"):       # no code: no CLEAR warning
            a = asm(" org 8000h\n")
            pypasmo.output_bytes(a, fmt, "x")
            self.assertEqual(a.warnings, [], fmt)

    def test_bank_without_paging_is_a_normal_tap(self):
        a = asm(" org 8000h\n bank 0\n ld a,1\n end 8000h\n")
        self.assertEqual(pypasmo.output_bytes(a, "tap128", "x"), pypasmo.output_bytes(a, "tap", "x"))
        self.assertEqual(pypasmo.output_bytes(a, "tapbas128", "x"), pypasmo.output_bytes(a, "tapbas", "x"))

    def test_memmap(self):
        text = pypasmo.memmap_text(asm(self.SRC128))
        self.assertIn("page 2  8000h-BFFFh", text)
        self.assertIn("8000h-8002h      3 bytes", text)
        self.assertIn("bank 3  used: C000h-C001h      2 bytes", text)
        self.assertIn("bank 2  8000h      3 bytes", text)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "m.asm")
            src.write_text(self.SRC128, encoding="utf-8")
            rc, out, _ = run_main("--memmap", "--tap128", str(src), str(Path(d, "m.tap")))
            self.assertEqual(rc, 0)
            self.assertIn("Memory map:", out)

    def test_bank_errors(self):
        a = asm(self.SRC128)
        with self.assertRaises(pypasmo.AsmError):           # banked code needs a 128K format
            pypasmo.output_bytes(a, "tap", "x")
        with self.assertRaises(pypasmo.AsmError):           # ROM area
            pypasmo.output_bytes(asm(" org 100h\n nop\n bank 1\n org 0C000h\n nop\n"), "tap128", "x")
        with self.assertRaises(pypasmo.AsmError):
            code(" bank 8\n")


class NewDirectives(unittest.TestCase):
    """pypasmo extensions: PHASE/DEPHASE (MACRO-80), ALIGN, ASSERT, INCBIN offset (sjasmplus)."""

    def test_elseif(self):
        # the first true branch only; ELSE when none was true
        chain = " if {}\n db 1\n elseif {}\n db 2\n elseif {}\n db 3\n else\n db 4\n endif\n"
        for conds, out in (((0, 1, 1), "02"), ((1, 1, 1), "01"), ((0, 0, 1), "03"), ((0, 0, 0), "04")):
            with self.subTest(conds):
                self.assertEqual(code(chain.format(*conds)), h(out))
        # nested in a skipped branch: nothing; the expression is not evaluated there and
        # not after a true branch (an undefined symbol is no error)
        self.assertEqual(code(" if 0\n if 1\n db 1\n elseif 1\n db 2\n endif\n endif\n db 5\n"), h("05"))
        self.assertEqual(code(" if 1\n db 1\n elseif nosuch\n db 2\n endif\n"), h("01"))
        self.assertEqual(code(" if 0\n if 0\n elseif nosuch\n endif\n endif\n db 5\n"), h("05"))
        # like IF: the symbols must be defined before (as in Pasmo)
        self.assertEqual(code("x equ 2\n if 0\n db 1\n elseif x = 2\n db 2\n endif\n"), h("02"))

    def test_elseif_errors_names_and_pasmo_syntax(self):
        for bad in (" elseif 1\n", " if 0\n else\n elseif 1\n endif\n", " if 0\n elseif\n endif\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad)
        self.assertEqual(code("elseif: db 1\n ld a,elseif\n"), h("01 3E 00"))
        # --pasmo-syntax-055: a normal name, so in a skipped branch the line does not count
        self.assertEqual(code(" if 0\n elseif 1\n db 1\n endif\n db 2\n", pasmo_syntax=True), h("02"))

    def test_phase(self):
        src = (" org 8000h\n ld hl,src\n jp run\nsrc:\n phase 0FE00h\n"
               "run: ld a,(dat)\n jr run\ndat: db 7\n dephase\nafter: db 1\n")
        a = asm(src)
        self.assertEqual(min(a.mem), 0x8000)
        self.assertEqual(pypasmo.image(a.mem)[1], h("21 06 80 C3 00 FE 3A 05 FE 18 FB 07 01"))
        self.assertEqual([a.symbols[k] for k in ("src", "run", "dat", "after")],
                         [0x8006, 0xFE00, 0xFE05, 0x800C])

    def test_phase_dollar_and_label(self):
        self.assertEqual(code(" org 10h\n phase 200h\n dw $\n dephase\n dw $\n"), h("00 02 12 00"))
        self.assertEqual(asm(" org 10h\nx: phase 100h\n nop\n dephase\n").symbols["x"], 0x100)  # like ORG
        self.assertEqual(code(" .phase 100h\n dw $\n .dephase\n"), h("00 01"))     # MACRO-80 names

    def test_phase_errors(self):
        for bad in (" dephase\n", " phase 1\n phase 2\n dephase\n", " phase 1\n org 2\n dephase\n",
                    " phase 100h\n nop\n", " phase\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad)

    def test_phase_bank_by_load_address(self):
        a = asm(" org 0BFFEh\n bank 1\n phase 100h\n db 1,2,3,4\n dephase\n")
        self.assertEqual(a.mem, {0xBFFE: 1, 0xBFFF: 2})
        self.assertEqual(a.banks, {1: {0xC000: 3, 0xC001: 4}})

    def test_phase_listing_shows_load_address_on_phase_lines(self):
        a = asm(" org 8000h\n phase 0FE00h\n nop\n dephase\n nop\n")
        self.assertEqual([x[0] for x in a.listing], [0x8000, 0x8000, 0xFE00, 0x8001, 0x8001])

    def test_align(self):
        a = asm(" org 8001h\n align 4\n db 1\n")
        self.assertEqual(a.mem, {0x8004: 1})                    # without a fill byte only skipped
        self.assertEqual(code(" org 8001h\n db 9\n align 4, 0FFh\n db 1\n"), h("09 FF FF 01"))
        self.assertEqual(asm(" org 8000h\n align 256\n db 1\n").mem, {0x8000: 1})
        self.assertEqual(asm(" org 8001h\nt: align 16\n").symbols["t"], 0x8001)     # like DS
        # in PHASE the address of the code ($) is aligned
        self.assertEqual(code(" org 8001h\n phase 0FE00h\n db 1\n align 4,0\n db 2\n dephase\n"),
                         h("01 00 00 00 02"))
        for bad in (" align 3\n", " align 0\n", " align\n", " align 4,1,2\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad)

    def test_assert(self):
        self.assertEqual(code(" assert konec <= 8010h\n org 8000h\n nop\nkonec:\n"), h("00"))
        with self.assertRaises(pypasmo.AsmError):
            code(" org 8000h\n ds 20h\nkonec:\n assert konec <= 8010h\n")
        with self.assertRaisesRegex(pypasmo.AsmError, "too long"):
            code(' assert 0, "too long"\n')
        for bad in (" assert\n", " assert 1, 2\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad)

    def test_incbin_offset_length(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "data.bin").write_bytes(bytes(range(16)))

            def inc(line, **opts):
                Path(d, "m.asm").write_text(line + "\n db 0AAh\n", encoding="utf-8")
                a = pypasmo.Assembler(**opts)
                a.assemble(Path(d, "m.asm"))
                return pypasmo.image(a.mem)[1]
            self.assertEqual(inc(" incbin data.bin, 12"), h("0C 0D 0E 0F AA"))
            self.assertEqual(inc(' incbin "data.bin",2,3'), h("02 03 04 AA"))
            self.assertEqual(inc(" incbin data.bin ,2"), h("02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F AA"))
            self.assertEqual(inc(" incbin data.bin, 16, 0 ; nothing"), h("AA"))
            # like Pasmo, an unquoted name ends at a blank: this is the file "data.bin,1"
            Path(d, "data.bin,1").write_bytes(h("77"))
            self.assertEqual(inc(" incbin data.bin,1"), h("77 AA"))
            for bad in (" incbin data.bin, 17", " incbin data.bin, 10, 7", " incbin data.bin ,",
                        " incbin data.bin, 1, 2, 3"):
                with self.subTest(bad):
                    with self.assertRaises(pypasmo.AsmError):
                        inc(bad)
            with self.assertRaises(pypasmo.AsmError):
                inc(" incbin data.bin, 1", pasmo_syntax=True)

    def test_new_names_are_not_reserved(self):
        src = "align: db 1\nphase equ 5\n ld a,phase\ndephase ld a,align\nassert defl 2\n"
        a = asm(src)
        self.assertEqual(pypasmo.image(a.mem)[1], h("01 3E 05 3E 00"))
        self.assertEqual(a.symbols["dephase"], 3)
        # a macro with the same name is used instead of the directive
        self.assertEqual(code("align macro n\n db n\n endm\n align 7\n"), h("07"))

    def test_pasmo_syntax_option(self):
        with self.assertRaises(pypasmo.AsmError):
            code("phase\n db 1\n")                          # PHASE without an address
        a = asm("phase\n db 1\n", pasmo_syntax=True)        # label "phase", like in Pasmo
        self.assertEqual((a.symbols["phase"], pypasmo.image(a.mem)[1]), (0, h("01")))
        with self.assertRaises(pypasmo.AsmError):
            code(" align 4\n", pasmo_syntax=True)
        with tempfile.TemporaryDirectory() as d:
            src, out = str(Path(d, "p.asm")), str(Path(d, "p.bin"))
            Path(src).write_text("phase\n db 1\n", encoding="utf-8")
            self.assertEqual(run_main(src, out)[0], 1)
            self.assertEqual(run_main("--pasmo-syntax-055", src, out)[0], 0)
            self.assertEqual(Path(out).read_bytes(), h("01"))

    def test_pasmo_syntax_option_turns_off_fork_directives(self):
        src = "bank: db 1\ndup equ 2\n ld a,dup\nstruct ld a,bank\nedup\n"
        with self.assertRaises(pypasmo.AsmError):           # reserved words of the fork
            code(src)
        a = asm(src, pasmo_syntax=True)
        self.assertEqual(pypasmo.image(a.mem)[1], h("01 3E 02 3E 00"))
        self.assertEqual((a.symbols["struct"], a.symbols["edup"]), (3, 5))
        self.assertEqual(code("bank macro n\n db n\n endm\n bank 7\n", pasmo_syntax=True), h("07"))
        self.assertEqual(code(" if 0\n dup 2\n endif\n db 1\n", pasmo_syntax=True), h("01"))
        for bad in ("lbl bank 1\n", " dg xxxx....\n", "s struct\n", " dup 2\n nop\n edup\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad, pasmo_syntax=True)


class LocalLabels(unittest.TestCase):
    """.name labels local to the previous normal label (pypasmo extension, like sjasmplus)."""

    def test_local_to_previous_label(self):
        src = "main: ld b,3\n.loop: djnz .loop\n ret\nsub1: ld b,2\n.loop djnz .loop\n jp main.loop\n"
        a = asm(src)
        self.assertEqual(pypasmo.image(a.mem)[1], h("06 03 10 FE C9 06 02 10 FE C3 02 00"))
        self.assertEqual((a.symbols["main.loop"], a.symbols["sub1.loop"]), (2, 7))
        self.assertIn("main.loop\tEQU 00002H", pypasmo.symbol_text(a))

    def test_forward_reference(self):
        self.assertEqual(code("f: jr .x\n nop\n.x: ret\n"), h("18 01 00 C9"))

    def test_only_address_labels_start_a_scope(self):
        a = asm("a1: nop\nk equ 5\n.l: jr .l\n")                 # not EQU / DEFL
        self.assertEqual(a.symbols["a1.l"], 1)
        a = asm("pr: nop\n_q: nop\n.x: nop\n", alocal=True)      # not autolocal labels
        self.assertEqual(a.symbols["pr.x"], 2)
        a = asm(".x equ 3\n ld a,.x\n")                           # before the first label
        self.assertEqual((a.symbols[".x"], pypasmo.image(a.mem)[1]), (3, h("3E 03")))

    def test_local_to_each_macro_expansion(self):
        a = asm("mac macro\n.l: djnz .l\n endm\nstart: mac\n mac\n jr .z\n.z: nop\n")
        self.assertEqual(pypasmo.image(a.mem)[1], h("10 FE 10 FE 18 00 00"))
        self.assertEqual(a.symbols["start.z"], 6)
        self.assertNotIn("start.l", a.symbols)

    def test_other_scope_is_an_error_and_pasmo_syntax(self):
        src = "a1: nop\n.x: nop\nb1: jp .x\n"
        with self.assertRaises(pypasmo.AsmError):
            code(src)
        a = asm(src, pasmo_syntax=True)                           # Pasmo: .x is a normal name
        self.assertEqual((pypasmo.image(a.mem)[1], a.symbols[".x"]), (h("00 00 C3 01 00"), 1))


class StringDirectives(unittest.TestCase):
    """DZ and DC (pypasmo extension, like sjasmplus)."""

    def test_dz(self):
        self.assertEqual(code(' dz "AB"\n'), h("41 42 00"))
        self.assertEqual(code(" dz 1\n"), h("01 00"))
        self.assertEqual(code(' dz "A", 1\n'), h("41 01 00"))

    def test_dc(self):
        # the example from the sjasmplus documentation: three strings, 'A' is a number
        self.assertEqual(code(" dc \"A\", 'AB', \"AB\"\n"), h("C1 41 C2 41 C2"))
        self.assertEqual(code(" dc 'A'\n"), h("41"))
        self.assertEqual(code(' dc "Hello",13\n'), h("48 65 6C 6C EF 0D"))

    def test_names_not_reserved_and_pasmo_syntax(self):
        self.assertEqual(code("dc: db 1\n ld a,dc\ndz equ 2\n ld a,dz\n"), h("01 3E 00 3E 02"))
        for bad in (" dz 1\n", " dc 1\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad, pasmo_syntax=True)


class ZX81(unittest.TestCase):
    """D_ZX81, D_ZX81I, DC_ZX81 and --p-zx81 (pypasmo extension)."""

    def test_d_zx81(self):
        # the ZX81 character set: space 0, " 11, $ 13 ... . 27, 0-9 = 28-37, A-Z = 38-63
        self.assertEqual(code(' d_zx81 "HELLO, 09"\n'), h("2D 2A 31 31 34 1A 00 1C 25"))
        self.assertEqual(code(" d_zx81 '\"$:?()><=+-*/;,.'\n"),
                         h("0B 0D 0E 0F 10 11 12 13 14 15 16 17 18 19 1A 1B"))
        self.assertEqual(code(' d_zx81 "AZ"\n'), h("26 3F"))
        # lower case letters are inverse (+ 128), numbers are not changed
        self.assertEqual(code(' d_zx81 "Ab", "z", \'A\'\n'), h("26 A7 BF 26"))
        self.assertEqual(code(' d_zx81 "A", 76h, 1+1\n'), h("26 76 02"))

    def test_d_zx81i(self):
        # all inverse, lower case letters normal; numbers are not changed
        self.assertEqual(code(' d_zx81i "Ab 1.", 1\n'), h("A6 27 80 9D 9B 01"))

    def test_dc_zx81(self):
        # bit 7 (inverse) in the last character of each string, as in the ZX81 ROM
        self.assertEqual(code(' dc_zx81 "PRINT"\n'), h("35 37 2E 33 B9"))
        self.assertEqual(code(' dc_zx81 "Ab", "C", 76h\n'), h("26 A7 A8 76"))

    def test_errors(self):
        for src, msg in ((' d_zx81 "HI!"\n', "'!'"),                # no ! on the ZX81
                         (' d_zx81 "x@"\n', "'@'"),
                         (' d_zx81 "č"\n', "č"),           # UTF-8 text in the message
                         (' d_zx81i "[A]"\n', "'['"),
                         (' dc_zx81 "aB"\n', "inverse"),             # bit 7 before the end
                         (' d_zx81 "A"+1\n', "expected ','")):
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError) as e:
                    code(src)
                self.assertIn(msg, str(e.exception))

    def test_names_not_reserved_and_pasmo_syntax(self):
        self.assertEqual(code("d_zx81: db 1\n ld a,d_zx81\ndc_zx81 equ 2\n ld a,dc_zx81\n"),
                         h("01 3E 00 3E 02"))
        for bad in (' d_zx81 "A"\n', ' d_zx81i "A"\n', ' dc_zx81 "A"\n'):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad, pasmo_syntax=True)

    @staticmethod
    def word(n):
        return n.to_bytes(2, "little")

    def test_p_zx81(self):
        # system variables from 4009h (VERSN), 1 REM with the code at 16514, 2 RAND USR
        # VAL "16514", the full display file (24 x NEWLINE + 32 spaces, NEWLINE), 80h
        out = pypasmo.output_bytes(asm(" org 16514\n ret\n"), "p-zx81", "x")
        w = self.word
        d_file = 0x407D + 7 + 15                    # 4093h
        vars_ = d_file + 793                        # 43ACh
        sysvars = (h("00") + w(1) + w(d_file) + w(d_file + 1) + w(vars_) + w(0) + w(vars_ + 1)
                   + w(vars_ + 5) + w(0) + w(vars_ + 6) + w(vars_ + 6) + h("00") + w(0x405D) + h("00 02")
                   + w(0) + h("BF FD FF 37") + w(0x407D) + w(0) + h("00") + w(0) + w(0x0C8D) + w(0)
                   + w(63000) + w(0) + h("BC 21 18 40") + bytes(32) + h("76")
                   + bytes(10) + h("84 20") + bytes(20))
        self.assertEqual(len(sysvars), 0x407D - 0x4009)
        line1 = h("00 01 03 00 EA C9 76")
        line2 = h("00 02 0B 00 F9 D4 C5 0B 1D 22 21 1D 20 0B 76")
        display = h("76") + (bytes(32) + h("76")) * 24
        self.assertEqual(out, sysvars + line1 + line2 + display + h("80"))
        # END: the start address in RAND USR VAL "16515"
        out = pypasmo.output_bytes(asm(" org 16514\n nop\nst: ret\n end st\n"), "p-zx81", "x")
        self.assertEqual(out[0x407D - 0x4009 + 8:][:15], h("00 02 0B 00 F9 D4 C5 0B 1D 22 21 1D 21 0B 76"))

    def test_p_zx81_stack_warning(self):
        # less than 256 bytes under 8000h for the stacks of the ROM: a warning, the file
        # stays the same
        size = 0x8000 - 0x407D - 7 - 15 - 793 - 1 - 5      # DS that leaves 0 bytes
        for fill, warned in ((size - 255, True), (size - 256, False)):
            with self.subTest(fill=fill):
                a = asm(f" org 16514\n ret\n ds {fill}\n")
                pypasmo.output_bytes(a, "p-zx81", "x")
                self.assertEqual(any("--p-zx81" in w and "stack" in w for w in a.warnings), warned, a.warnings)

    def test_p_zx81_errors(self):
        for src in (" org 8000h\n ret\n",                   # the code must be at 16514
                    " org 16514\n ret\n ds 16000\n"):       # past 32K with the display file
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    pypasmo.output_bytes(asm(src), "p-zx81", "x")
        self.assertEqual(len(pypasmo.output_bytes(asm(" org 16514\n ret\n ds 15000\n"), "p-zx81", "x")),
                         0x407D - 0x4009 + 7 + 15000 + 15 + 793 + 1)


class OtherMachines(unittest.TestCase):
    """--tap-ace (Jupiter Ace), --kcc-kc85, --z80-z1013 (Robotron), --rom-sms (Sega Master
    System); pypasmo extensions, experimental. The layouts are those of z88dk (appmake)."""

    @staticmethod
    def ace_block(b):
        # a block of the Ace .tap: length (with the check byte), bytes, XOR of the bytes
        x = 0
        for v in b:
            x ^= v
        return (len(b) + 1).to_bytes(2, "little") + b + bytes([x])

    def test_tap_ace(self):
        # loader: bytes file of 32 bytes for 22E0h (the input line on the screen) with the
        # command "0 0 BLOAD code ... CALL"; then the code as bytes file "code"
        out = pypasmo.output_bytes(asm(" org 4000h\n nop\nst: ld a,1\n jp (iy)\n end st\n"), "tap-ace", "hello.tap")
        head1 = h("20") + b"hello     " + h("20 00 E0 22") + b" " * 10
        cmd = b"\x00" + b"0 0 BLOAD code       16385 CALL"
        head2 = h("20") + b"code      " + h("05 00 00 40") + b" " * 10
        self.assertEqual(len(head1), 25)
        self.assertEqual(len(cmd), 32)
        self.assertEqual(out, self.ace_block(head1) + self.ace_block(cmd) + self.ace_block(head2)
                         + self.ace_block(h("00 3E 01 FD E9")))
        # without END: CALL the load address; the name: up to the first dot, 10 characters
        out = pypasmo.output_bytes(asm(" org 8000h\n jp (iy)\n"), "tap-ace", "averylongname.tap")
        self.assertEqual(out[3:13], b"averylongn")
        self.assertIn(b"0 0 BLOAD code       32768 CALL", out)

    def test_tap_ace_errors(self):
        with self.assertRaises(pypasmo.AsmError):           # in the ROM (0000h-1FFFh)
            pypasmo.output_bytes(asm(" org 1000h\n jp (iy)\n"), "tap-ace", "x")

    def test_trs(self):
        # TRS-80 /CMD file (as Pasmo 0.5.5 emittrs): load records 01, length (data + 2,
        # 256 data bytes = 02), address, data; then the transfer record 02 02 address
        out = pypasmo.output_bytes(asm(" org 8000h\nst: ld a,1\n ret\n end st\n"), "trs", "x.cmd")
        self.assertEqual(out, h("01 05 00 80 3E 01 C9 02 02 00 80"))
        # 300 bytes: a full record of 256 bytes, then 44; without END the entry is 0
        out = pypasmo.output_bytes(asm(" org 6000h\n ds 300, 0AAh\n"), "trs", "x.cmd")
        self.assertEqual(out, h("01 02 00 60") + b"\xAA" * 256 + h("01 2E 00 61") + b"\xAA" * 44
                         + h("02 02 00 00"))
        # exactly 256 bytes: one full record
        out = pypasmo.output_bytes(asm(" org 6000h\n ds 256, 1\n"), "trs", "x.cmd")
        self.assertEqual(out, h("01 02 00 60") + b"\x01" * 256 + h("02 02 00 00"))
        # no code: only the transfer record (Pasmo writes 2 bytes from FFFFh)
        self.assertEqual(pypasmo.output_bytes(asm(" org 6000h\n"), "trs", "x.cmd"), h("02 02 00 00"))
        # the main name and the Pasmo name
        self.assertEqual(pypasmo.common.option("trs"), "--trs")

    def test_cas_trs(self):
        # TRS-80 Model I SYSTEM tape (500 baud) .cas: 256 zeros, A5h, 55h, the name (6,
        # upper case, spaces), blocks 3Ch, length (256 = 0), address, data, checksum (the
        # sum of the address bytes and the data), then 78h and the entry (END)
        out = pypasmo.output_bytes(asm(" org 7000h\nst: ld a,1\n ret\n end st\n"), "cas-trs", "out/hi.cas")
        sum_ = (0x00 + 0x70 + 0x3E + 0x01 + 0xC9) & 0xFF
        self.assertEqual(out, bytes(256) + h("A5 55") + b"HI    "
                         + h("3C 03 00 70 3E 01 C9") + bytes([sum_]) + h("78 00 70"))
        # 300 bytes: blocks of 256 (length 0) and 44; without END the entry is the start;
        # the name up to the first character that is not a letter or a digit, 6 characters
        out = pypasmo.output_bytes(asm(" org 7000h\n ds 300, 1\n"), "cas-trs", "averylong_x.cas")
        self.assertEqual(out[256:264], h("A5 55") + b"AVERYL")
        self.assertEqual(out[264:268], h("3C 00 00 70"))
        self.assertEqual(out[268 + 256], (0x00 + 0x70 + 256) & 0xFF)
        self.assertEqual(out[269 + 256:273 + 256], h("3C 2C 00 71"))
        self.assertEqual(out[-3:], h("78 00 70"))
        self.assertEqual(len(out), 264 + 4 + 256 + 1 + 4 + 44 + 1 + 3)
        # code in the ROM, no name: errors
        with self.assertRaises(pypasmo.AsmError):
            pypasmo.output_bytes(asm(" org 3000h\n ret\n"), "cas-trs", "x.cas")
        with self.assertRaises(pypasmo.AsmError):
            pypasmo.output_bytes(asm(" org 7000h\n ret\n"), "cas-trs", "_.cas")

    def test_kcc_kc85(self):
        # 128 byte header: name (8, upper case, zeros), "KCC", 5 zeros, 3 addresses
        # (autostart), load, end + 1, start, 105 zeros; the code padded to 128 bytes
        out = pypasmo.output_bytes(asm(" org 300h\n nop\nst: ld a,1\n ret\n end st\n"), "kcc-kc85", "hello.kcc")
        head = b"HELLO\x00\x00\x00KCC" + bytes(5) + h("03 00 03 04 03 01 03") + bytes(105)
        self.assertEqual(len(head), 128)
        self.assertEqual(out, head + h("00 3E 01 C9") + bytes(124))
        # without END: start = load address; the name up to the first character that is
        # not a letter or a digit
        out = pypasmo.output_bytes(asm(" org 300h\n ret\n"), "kcc-kc85", "my-prog.kcc")
        self.assertEqual(out[:11], b"MY\x00\x00\x00\x00\x00\x00KCC")
        self.assertEqual(out[17:23], h("00 03 01 03 00 03"))
        self.assertEqual(len(out), 256)

    def test_z80_z1013(self):
        # 32 byte header: load, end (the last byte), start, 6 zeros, "C" D3 D3 D3, name (16)
        out = pypasmo.output_bytes(asm(" org 100h\n nop\nst: ld a,1\n ret\n end st\n"), "z80-z1013", "hello.z80")
        head = h("00 01 03 01 01 01") + bytes(6) + h("43 D3 D3 D3") + b"hello" + b" " * 11
        self.assertEqual(len(head), 32)
        self.assertEqual(out, head + h("00 3E 01 C9"))
        out = pypasmo.output_bytes(asm(" org 100h\n ret\n"), "z80-z1013", "a_long_program_name.z80")
        self.assertEqual(out[4:6], h("00 01"))
        self.assertEqual(out[16:32], b"a_long_program_n")

    def test_names_without_the_directory(self):
        # the output file name with a directory: only the file name goes into the header
        a = asm(" org 4000h\n jp (iy)\n")
        for fmt, at, name in (("tap-ace", slice(3, 13), b"hello     "), ("kcc-kc85", slice(0, 8), b"HELLO\0\0\0"),
                              ("z80-z1013", slice(16, 32), b"hello" + b" " * 11),
                              ("mzf", slice(1, 11), b"HELLO.MZF\x0D"), ("cas-msx", slice(18, 24), b"hello ")):
            for path in ("out/dir/hello.mzf", "out\\dir\\hello.mzf"):
                with self.subTest(fmt=fmt, path=path):
                    self.assertEqual(pypasmo.output_bytes(a, fmt, path)[at], name)

    def test_rom_sms(self):
        # 32 KB from 0000h, padded with FFh; the header at 7FF0h: "TMR SEGA", 20h 20h,
        # checksum of 0000h-7FEFh (16 bit, low byte first), product code 0, version 0,
        # region 4 (export SMS) + ROM size C (32 KB)
        out = pypasmo.output_bytes(asm(" org 0\n di\n jr $\n"), "rom-sms", "x")
        self.assertEqual(len(out), 0x8000)
        self.assertEqual(out[:4], h("F3 18 FE FF"))
        total = (0xF3 + 0x18 + 0xFE + 0xFF * (0x7FF0 - 3)) & 0xFFFF
        self.assertEqual(out[0x7FF0:], b"TMR SEGA  " + total.to_bytes(2, "little") + h("00 00 00 4C"))
        # a header written by the source: kept, only the checksum is filled in
        src = ' org 0\n ret\n org 7FF0h\n db "TMR SEGA", 0, 0\n dw 0\n db 26h, 70h, 01h, 4Ch\n'
        out = pypasmo.output_bytes(asm(src), "rom-sms", "x")
        total = (0xC9 + 0xFF * (0x7FF0 - 1)) & 0xFFFF
        self.assertEqual(out[0x7FF0:], b"TMR SEGA\x00\x00" + total.to_bytes(2, "little") + h("26 70 01 4C"))

    def test_rom_gg(self):
        # Game Gear: the same ROM and header, region 7 (Game Gear international)
        out = pypasmo.output_bytes(asm(" org 0\n di\n jr $\n"), "rom-gg", "x")
        total = (0xF3 + 0x18 + 0xFE + 0xFF * (0x7FF0 - 3)) & 0xFFFF
        self.assertEqual(out[0x7FF0:], b"TMR SEGA  " + total.to_bytes(2, "little") + h("00 00 00 7C"))
        with self.assertRaises(pypasmo.AsmError) as e:
            pypasmo.output_bytes(asm(" org 8000h\n ret\n"), "rom-gg", "x")
        self.assertTrue(str(e.exception).startswith("--rom-gg:"), str(e.exception))   # not --rom-sms

    def test_rom_sms_errors(self):
        for src in (" org 8000h\n ret\n",                            # only 32 KB (no mapper)
                    " org 0\n ret\n org 8000h\n ret\n",
                    " org 100h\n ret\n",                              # nothing at 0000h
                    " org 0\n ret\n org 7FF0h\n db 1\n",               # header without TMR SEGA
                    ' org 0\n ret\n org 7FF0h\n db "TMR SEGA",0,0,0,0,0,0,0,4Fh\n'):  # not 32 KB
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    pypasmo.output_bytes(asm(src), "rom-sms", "x")

    def test_rom_coleco(self):
        # ColecoVision cartridge: the code from 8000h as the source writes it (the header
        # 55h AAh / AAh 55h, 4 BIOS pointers, the start at 800Ah), padded with FFh to 8 KB
        out = pypasmo.output_bytes(asm(" org 8000h\n db 55h, 0AAh\n dw 0, 0, 0, 0, 800Ch\n jr $\n"),
                                   "rom-coleco", "x")
        self.assertEqual(out, h("55 AA 00 00 00 00 00 00 00 00 0C 80 18 FE") + b"\xFF" * (8192 - 14))
        out = pypasmo.output_bytes(asm(" org 8000h\n db 0AAh, 55h\n"), "rom-coleco", "x")
        self.assertEqual(out, h("AA 55") + b"\xFF" * 8190)

    def test_rom_coleco_sizes(self):
        # 8, 16, 24 or 32 KB (8 KB ROM chips at 8000h, A000h, C000h, E000h)
        for length, size in ((0x2000, 0x2000), (0x2001, 0x4000), (0x6000, 0x6000), (0x6001, 0x8000),
                             (0x8000, 0x8000)):
            with self.subTest(length=length):
                out = pypasmo.output_bytes(asm(f" org 8000h\n db 55h, 0AAh\n ds {length - 2}, 1\n"),
                                           "rom-coleco", "x")
                self.assertEqual(len(out), size)
                self.assertEqual(out[length - 1:length + 1], b"\x01\xFF"[:size - length + 1])

    def test_rom_coleco_errors(self):
        for src in (" org 4000h\n db 55h, 0AAh\n",                    # not at 8000h
                    " org 8002h\n nop\n",
                    " org 8000h\n db 0, 0\n",                         # no header
                    " org 8000h\n db 55h, 55h\n",
                    " org 8000h\n"):                                   # no code
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError) as e:
                    pypasmo.output_bytes(asm(src), "rom-coleco", "x")
                self.assertIn("--rom-coleco", str(e.exception))


class CpcSnapshot(unittest.TestCase):
    """--sna-cpc6128 and --sna-cpc464 (pypasmo extension): the state of a CPC in Basic (saved
    by an emulator, pypasmo/cpc_state.py) with the code and a routine below HIMEM that calls
    the code and then goes on with the firmware where the snapshot was taken."""

    # (format, CPC type, HIMEM + 1, SP, the routine for the state of the template)
    MODELS = (
        # CPC 6128: AF 0000, BC 0000, DE 0000, HL B688, IX 0000, IY 0000, AF' 0044,
        # BC' 7F89, DE' B63F, HL' B8BF, I 00, IM 1, interrupts on, PC 1CE6h; HIMEM A67Bh
        ("sna-cpc6128", 2, 0xA67C, h("E2 BF"),
         h("F3 08 21 44 00 E5 F1 08 D9 01 89 7F 11 3F B6 21 BF B8 ED 49 D9 3E 00 ED 47 ED 56"
           " 21 00 00 E5 F1 01 00 00 11 00 00 DD 21 00 00 FD 21 00 00 21 88 B6 FB C3 E6 1C")),
        # CPC 464: AF 0000, BC 0000, DE 0000, HL B53E, IX 0000, IY 0000, AF' 0044,
        # BC' 7F89, DE' B4F5, HL' 0000, I 00, IM 1, interrupts on, PC 1B61h (the snapshot was
        # at 1D1Ah in the key buffer routine with F 42h, the template finishes it); HIMEM AB7Fh
        ("sna-cpc464", 0, 0xAB80, h("E2 BF"),
         h("F3 08 21 44 00 E5 F1 08 D9 01 89 7F 11 F5 B4 21 00 00 ED 49 D9 3E 00 ED 47 ED 56"
           " 21 00 00 E5 F1 01 00 00 11 00 00 DD 21 00 00 FD 21 00 00 21 3E B5 FB C3 61 1B")),
    )

    def test_snapshot(self):
        for fmt, cpc, himem, sp, ret in self.MODELS:
            with self.subTest(fmt):
                out = pypasmo.output_bytes(asm(" org 4000h\n nop\nst: ld a,1\n ret\n end st\n"), fmt, "x.sna")
                self.assertEqual(len(out), 256 + 0x10000)
                head, ram = out[:256], out[256:]
                self.assertEqual(head[:8], b"MV - SNA")
                self.assertEqual(head[0x10], 2)                  # version 2: has the CPC type
                self.assertEqual(head[0x6B:0x6E], h("40 00") + bytes([cpc]))   # 64 KB, the CPC
                self.assertEqual(head[0x6E:], bytes(256 - 0x6E))
                stub = himem - 6 - len(ret)                      # just below HIMEM
                self.assertEqual(stub, {0xA67C: 0xA641, 0xAB80: 0xAB45}[himem])
                self.assertEqual(head[0x23:0x25], stub.to_bytes(2, "little"))   # PC
                self.assertEqual(head[0x21:0x23], sp)            # SP of the template
                # KL L ROM DISABLE (the code runs in the RAM, also below 4000h), CALL the code
                self.assertEqual(ram[stub:himem], h("CD 09 B9 CD 01 40") + ret)
                self.assertEqual(ram[0x4000:0x4004], h("00 3E 01 C9"))
                # the template: the restart vectors in the RAM, the firmware above HIMEM
                tpl = bytearray(0x10000)
                for a, b in pypasmo.cpc_state.CPC_STATE[cpc][1]:
                    tpl[a:a + len(b)] = b
                self.assertEqual(ram[:0x4000], tpl[:0x4000])
                self.assertEqual(ram[himem:], tpl[himem:])
                self.assertTrue(any(ram[:0x40]) and any(ram[himem:0xC000]))
                self.assertFalse(any(tpl[0x40:himem]))
                # without END the code starts at its first byte
                out = pypasmo.output_bytes(asm(" org 8000h\n ret\n"), fmt, "x.sna")
                self.assertEqual(out[256 + stub + 3:256 + stub + 6], h("CD 00 80"))
                # code below 4000h (under the lower ROM) is allowed
                out = pypasmo.output_bytes(asm(" org 1000h\n ret\n"), fmt, "x.sna")
                self.assertEqual(out[256 + 0x1000], 0xC9)
                self.assertEqual(out[256 + stub:256 + stub + 6], h("CD 09 B9 CD 00 10"))

    def test_models(self):
        # the two states differ (another firmware): another PC and HIMEM
        s6128, s464 = (pypasmo.output_bytes(asm(" org 4000h\n ret\n"), f, "x") for f in ("sna-cpc6128", "sna-cpc464"))
        self.assertNotEqual(s6128[256 + 0xA67C:256 + 0xC000], s464[256 + 0xA67C:256 + 0xC000])

    def test_key_buffer_464(self):
        # the 464 template is not inside the key buffer routine: its counter (B53Eh) is 1
        # (empty) as after the routine, and the routine is not resumed
        out = pypasmo.output_bytes(asm(" org 4000h\n ret\n"), "sna-cpc464", "x")
        self.assertEqual(out[256 + 0xB53E], 1)
        self.assertEqual(out[0x23:0x25], h("45 AB"))
        self.assertEqual(out[256 + 0xAB7D:256 + 0xAB80], h("C3 61 1B"))

    def test_screen(self):
        # the screen (C000h-FFFFh) may be written
        for fmt, *_ in self.MODELS:
            out = pypasmo.output_bytes(asm(" org 4000h\n ret\n org 0C000h\n db 0FFh\n end 4000h\n"), fmt, "x")
            self.assertEqual(out[256 + 0xC000], 0xFF)

    def test_errors(self):
        for fmt, src in (("sna-cpc6128", " org 0030h\n ret\n"),     # the restart vectors
                         ("sna-cpc6128", " org 0A650h\n ret\n"),    # the routine below HIMEM
                         ("sna-cpc6128", " org 0B000h\n ret\n"),    # the firmware and AMSDOS
                         ("sna-cpc6128", " org 4000h\n"),            # no code
                         ("sna-cpc464", " org 0030h\n ret\n"),
                         ("sna-cpc464", " org 0AB50h\n ret\n"),     # the routine below HIMEM
                         ("sna-cpc464", " org 0B000h\n ret\n"),     # the firmware
                         ("sna-cpc464", " org 4000h\n")):
            with self.subTest(fmt=fmt, src=src), self.assertRaises(pypasmo.AsmError):
                pypasmo.output_bytes(asm(src), fmt, "x.sna")
        # A641h-AB44h is free on the 464 (HIMEM AB7Fh), not on the 6128
        self.assertTrue(pypasmo.output_bytes(asm(" org 0AB00h\n ret\n"), "sna-cpc464", "x"))


class ReviewCore(unittest.TestCase):
    """Bugs found by the review of 2026-11-04 (checked against Pasmo 0.5.5)."""

    def test_lines_split_only_at_newline(self):
        # after latin-1 decoding, str.splitlines also splits at 85h (UTF-8 of "\u0105" is
        # C4h 85h), 0Bh, 0Ch, 1Ch-1Eh; Pasmo splits only at LF (and drops CR)
        self.assertEqual(code(" ld a,1 ; \u0105nop\n db 2\n"), h("3E 01 02"))
        self.assertEqual(code(" ld a,1 ; \u0445\u043e\u0440\u043e\u0448\u043e\n db 2\n"), h("3E 01 02"))
        self.assertEqual(code(" db 1 ; x\x0cnop\r\n db 2\r\n"), h("01 02"))
        self.assertEqual(code(' db "a\x0bb"\n'), b"a\x0bb")
        with self.assertRaises(pypasmo.AsmError) as e:
            asm(" nop ; \u0105\n nop\n ld a,q\n")
        self.assertIn(":3:", str(e.exception))                   # the line numbers stay right

    def test_superscript_digits_are_not_digits(self):
        # latin-1 B2h, B3h, B9h are digits for str.isdigit(): "unexpected character", no crash
        for src in (" db 1\xb3\n", " if 0\n db 1\xb2\n endif\n db \xb9\n"):
            with self.subTest(src), self.assertRaises(pypasmo.AsmError):
                a = pypasmo.Assembler()
                a.assemble("x.asm", text=src)

    def test_index_offset_with_high_low(self):
        # Pasmo (parsedesp) takes a full expression after the sign
        self.assertEqual(code(" ld a,(ix+low(1234h))\n ld a,(iy+high 1234h)\n ld a,(ix-low 1)\n"),
                         h("DD 7E 34 FD 7E 12 DD 7E FF"))

    def test_line_numbers_everywhere(self):
        # a line number before INCLUDE, REPT, MACRO and ENDM (as before other statements)
        self.assertEqual(code("10 rept 2\n20 db 5\n30 endm\n"), h("05 05"))
        self.assertEqual(code("10 mm macro\n20 db 6\n30 endm\n40 mm\n"), h("06"))
        with tempfile.TemporaryDirectory() as dd:
            Path(dd, "inc1.asm").write_text(" db 2\n", encoding="utf-8")
            Path(dd, "p.asm").write_text("10 db 1\n20 include inc1.asm\n30 db 3\n", encoding="utf-8")
            a = pypasmo.Assembler()
            a.assemble(str(Path(dd, "p.asm")))
        self.assertEqual(pypasmo.image(a.mem)[1], h("01 02 03"))

    def test_label_named_like_the_macro(self):
        # "mm: mm 5": the arguments are after the macro name, not after the label
        self.assertEqual(code(" org 8000h\nmm macro pp\n db pp\n endm\nmm: mm 5\n"), h("05"))

    def test_recursive_macro_is_an_error(self):
        with self.assertRaises(pypasmo.AsmError) as e:
            asm("mm macro\n mm\n endm\n mm\n")
        self.assertIn("nested too deep", str(e.exception))

    def test_required_values_must_be_defined_before(self):
        # Pasmo: ORG, DS, ALIGN, BANK, INCBIN offsets, IF need a value defined above
        for src in (" ds fwd\n db 1\nfwd equ 2\n", " org fwd\n db 1\nfwd equ 2\n",
                    " org 8000h\n align fwd\n db 1\nfwd equ 4\n", " if fwd\n db 1\n endif\nfwd equ 1\n"):
            with self.subTest(src), self.assertRaises(pypasmo.AsmError):
                asm(src)
        self.assertEqual(code("n equ 2\n ds n\n db 1\n"), h("00 00 01"))
        self.assertEqual(code(" org 8000h\n jp fwd\nfwd: ret\n"), h("C3 03 80 C9"))   # code: fine

    def test_endif_else_without_junk(self):
        # Pasmo: "End line expected"
        for src in (" if 1\n nop\n endif junk\n", " if 1\n nop\n else junk\n nop\n endif\n"):
            with self.subTest(src), self.assertRaises(pypasmo.AsmError):
                asm(src)
        self.assertEqual(code(" if 1\n nop\n else ; a comment\n halt\n endif ; end\n"), h("00"))


class Disks(unittest.TestCase):
    """--dsk-cpc and --dsk-plus3 (pypasmo extension): Extended DSK images, 40 tracks, 1 side,
    9 sectors of 512 bytes, the CP/M file system of Amsdos (DATA format) and +3DOS."""
    SRC = " org 8000h\nst: ld a,1\n ret\n end st\n"

    @staticmethod
    def sectors(dsk):
        """{(track, sector id): 512 bytes} from an Extended DSK image."""
        self_check = dsk[:34] == b"EXTENDED CPC DSK File\r\nDisk-Info\r\n"
        assert self_check
        tracks, sides = dsk[0x30], dsk[0x31]
        out, at = {}, 256
        for t in range(tracks * sides):
            size = dsk[0x34 + t] * 256
            info = dsk[at:at + 256]
            assert info[:12] == b"Track-Info\r\n" and info[0x10] == t
            pos = at + 256
            for s in range(info[0x15]):
                c, hd, r, n = info[0x18 + 8 * s:0x1C + 8 * s]
                length = int.from_bytes(info[0x1E + 8 * s:0x20 + 8 * s], "little")
                out[(c, r)] = dsk[pos:pos + length]
                pos += length
            at += size
        return out

    def test_dsk_header(self):
        for fmt, first in (("dsk-cpc", 0xC1), ("dsk-plus3", 1)):
            with self.subTest(fmt):
                dsk = pypasmo.output_bytes(asm(self.SRC), fmt, "hello.dsk")
                self.assertEqual(dsk[:34], b"EXTENDED CPC DSK File\r\nDisk-Info\r\n")
                self.assertEqual((dsk[0x30], dsk[0x31]), (40, 1))
                self.assertEqual(dsk[0x34:0x34 + 40], b"\x13" * 40)       # 256 + 9 x 512 bytes
                self.assertEqual(len(dsk), 256 + 40 * 0x1300)
                info = dsk[256:512]
                self.assertEqual(info[0x14:0x18], h("02 09 4E E5"))
                self.assertEqual([info[0x1A + 8 * s] for s in range(9)], list(range(first, first + 9)))
                self.assertEqual(sorted({k[1] for k in self.sectors(dsk)}), list(range(first, first + 9)))

    def test_dsk_cpc(self):
        # the directory: track 0, sectors C1h-C4h (block 0, 1); HELLO.BIN in block 2 =
        # sectors C5h, C6h; the file is the Amsdos file (header + code)
        dsk = pypasmo.output_bytes(asm(self.SRC), "dsk-cpc", "out/hello.dsk")
        s = self.sectors(dsk)
        directory = s[(0, 0xC1)]
        self.assertEqual(directory[:32], h("00") + b"HELLO   BIN" + h("00 00 00 02 02") + bytes(15))
        self.assertEqual(directory[32:64], b"\xE5" * 32)
        amsdos = pypasmo.amsdos(0x8000, h("3E 01 C9"), 0x8000, "HELLO.BIN")
        self.assertEqual(s[(0, 0xC5)][:len(amsdos)], amsdos)

    def test_dsk_cpc_big_file(self):
        # more than 16 KB: a directory entry (extent) for each 16 KB
        dsk = pypasmo.output_bytes(asm(" org 1000h\n ds 20000, 1\n"), "dsk-cpc", "big.dsk")
        directory = self.sectors(dsk)[(0, 0xC1)]
        self.assertEqual(directory[:16], h("00") + b"BIG     BIN" + h("00 00 00 80"))
        self.assertEqual(directory[16:32], bytes(range(2, 18)))
        records = -(-(20000 + 128) // 128) - 128
        self.assertEqual(directory[32:48], h("00") + b"BIG     BIN" + h("01 00 00") + bytes([records]))
        self.assertEqual(directory[48:53], h("12 13 14 15 00"))            # 3744 bytes: 4 blocks

    def test_dsk_plus3(self):
        # track 0 (reserved): the disk specification in sector 1; the directory in track 1;
        # DISK (a Basic loader, autostart 10) and HELLO.BIN (+3DOS files)
        dsk = pypasmo.output_bytes(asm(self.SRC), "dsk-plus3", "hello.dsk")
        s = self.sectors(dsk)
        self.assertEqual(s[(0, 1)][:10], h("00 00 28 09 02 01 03 02 2A 52"))
        directory = s[(1, 1)]
        self.assertEqual(directory[:12], h("00") + b"DISK       ")
        self.assertEqual(directory[32:44], h("00") + b"HELLO   BIN")
        self.assertEqual(directory[64:96], b"\xE5" * 32)
        basic = (pypasmo.basic_line(10, h("FD") + b"32767\x0E\x00\x00\xFF\x7F\x00")
                 + pypasmo.basic_line(20, h("EF") + b'"HELLO.BIN"' + h("AF"))
                 + pypasmo.basic_line(30, h("F9 C0") + b"32768\x0E\x00\x00\x00\x80\x00"))
        disk_file = s[(1, 1 + directory[16] * 2)]          # the first block of DISK
        self.assertEqual(disk_file[:8], b"PLUS3DOS")
        self.assertEqual(disk_file[15:22], bytes([0]) + len(basic).to_bytes(2, "little") + h("0A 00")
                         + len(basic).to_bytes(2, "little"))
        self.assertEqual(disk_file[128:128 + len(basic)], basic)
        code_file = s[(1, 1 + directory[48] * 2)]
        self.assertEqual(code_file[:128 + 3], pypasmo.plus3dos(0x8000, h("3E 01 C9"))[:131])

    PCW_SRC = " org 100h\nst: ld c,9\n ld de,t\n call 5\n ret\nt: db 'Hi$'\n end st\n"

    def test_dsk_pcw(self):
        # the disk format of the PCW and the +3 (format 0: track 0 reserved, the disk
        # specification in its sector 1, the directory in track 1); only the CP/M program
        # HELLO.COM: the bytes from 100h without a header, 12 bytes = 1 record, block 2
        dsk = pypasmo.output_bytes(asm(self.PCW_SRC), "dsk-pcw", "out/hello.dsk")
        self.assertEqual(len(dsk), 256 + 40 * 0x1300)
        self.assertEqual(dsk[:512], pypasmo.output_bytes(asm(self.SRC), "dsk-plus3", "x")[:512])
        s = self.sectors(dsk)
        self.assertEqual(s[(0, 1)][:16], h("00 00 28 09 02 01 03 02 2A 52") + bytes(6))
        directory = s[(1, 1)]
        self.assertEqual(directory[:32], h("00") + b"HELLO   COM" + h("00 00 00 01 02") + bytes(15))
        self.assertEqual(directory[32:64], b"\xE5" * 32)
        code = h("0E 09 11 09 01 CD 05 00 C9") + b"Hi$"            # t = 100h + 9 = 109h
        self.assertEqual(s[(1, 5)][:16], code + b"\xE5" * 4)       # block 2 = sector 5 of track 1

    def test_dsk_pcw_name(self):
        dsk = pypasmo.output_bytes(asm(self.PCW_SRC), "dsk-pcw", "out/longgamename.dsk")
        self.assertEqual(self.sectors(dsk)[(1, 1)][:12], h("00") + b"LONGGAMECOM")

    def test_dsk_pcw_errors(self):
        # CP/M loads a .COM at 100h and starts it there
        for src in (" org 8000h\n ret\n",
                    " org 0FFh\n nop\n ret\n",
                    " org 100h\n nop\nst: ret\n end st\n",
                    " org 100h\n"):                                    # no code
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError) as e:
                    pypasmo.output_bytes(asm(src), "dsk-pcw", "x")
                self.assertIn("--dsk-pcw", str(e.exception))

    def test_dsk_errors(self):
        for fmt in ("dsk-cpc", "dsk-plus3"):
            with self.subTest(fmt):
                with self.assertRaises(pypasmo.AsmError):         # no letter or digit in the name
                    pypasmo.output_bytes(asm(self.SRC), fmt, "_x.dsk")


class MsxDisk(unittest.TestCase):
    """--dsk-msx (pypasmo extension): 720 KB MSX disk image (raw sectors, 80 tracks, 2 sides,
    9 sectors of 512 bytes), FAT12 of MSX-DOS: boot sector, 2 FATs of 3 sectors (1-3, 4-6),
    the root directory of 112 entries (sectors 7-13), clusters of 2 sectors from sector 14
    (cluster 2). AUTOEXEC.BAS (ASCII) loads and runs NAME.BIN (BLOAD ...,R)."""
    SRC = " org 9000h\nst: ld a,1\n ret\n end st\n"

    @staticmethod
    def sector(dsk, n):
        return dsk[n * 512:(n + 1) * 512]

    def test_boot_sector(self):
        dsk = pypasmo.output_bytes(asm(self.SRC), "dsk-msx", "hello.dsk")
        self.assertEqual(len(dsk), 80 * 2 * 9 * 512)
        boot = self.sector(dsk, 0)
        self.assertEqual(boot[:3], h("EB FE 90"))
        # 512 bytes/sector, 2 sectors/cluster, 1 reserved, 2 FATs, 112 entries, 1440
        # sectors, media F9h, 3 sectors/FAT, 9 sectors/track, 2 sides, 0 hidden
        self.assertEqual(boot[0x0B:0x1E], h("00 02 02 01 00 02 70 00 A0 05 F9 03 00 09 00 02 00 00 00"))
        self.assertEqual(boot[0x1E], 0xC9)                       # the boot code: RET (Disk BASIC)

    def test_files(self):
        dsk = pypasmo.output_bytes(asm(self.SRC), "dsk-msx", "out/hello.dsk")
        fat = h("F9 FF FF FF FF FF")                             # clusters 2 and 3: one each
        for n in (1, 4):
            self.assertEqual(self.sector(dsk, n)[:8], fat + h("00 00"))
            self.assertEqual(self.sector(dsk, n)[6:], bytes(506))
        basic = b'10 CLEAR 200,&H8FFF:BLOAD"HELLO.BIN",R\r\n\x1a'
        binary = h("FE 00 90 02 90 00 90 3E 01 C9")              # BLOAD header: start, end, exec
        root = self.sector(dsk, 7)
        self.assertEqual(root[:32], b"AUTOEXECBAS" + h("20") + bytes(10) + h("00 00 21 00 02 00")
                         + len(basic).to_bytes(4, "little"))
        self.assertEqual(root[32:64], b"HELLO   BIN" + h("20") + bytes(10) + h("00 00 21 00 03 00")
                         + h("0A 00 00 00"))
        self.assertEqual(root[64:], bytes(448))
        self.assertEqual(self.sector(dsk, 14)[:len(basic)], basic)      # cluster 2
        self.assertEqual(self.sector(dsk, 16)[:10], binary)             # cluster 3
        self.assertEqual(self.sector(dsk, 16)[10:], bytes(502))

    def test_big_file(self):
        # 1500 bytes of code + 7: two clusters (3, 4), the chain in the FAT
        dsk = pypasmo.output_bytes(asm(" org 0A000h\n ds 1500, 1\n"), "dsk-msx", "big.dsk")
        self.assertEqual(self.sector(dsk, 1)[:10], h("F9 FF FF FF 4F 00 FF 0F 00 00"))
        self.assertEqual(self.sector(dsk, 7)[32 + 26:64], h("03 00 E3 05 00 00"))   # 1507 bytes
        data = self.sector(dsk, 16) + self.sector(dsk, 17) + self.sector(dsk, 18)
        self.assertEqual(data[:7], h("FE 00 A0 DB A5 00 A0"))   # no END: runs from the start
        self.assertEqual(data[7:1507], b"\x01" * 1500)

    def test_clear(self):
        # always CLEAR below the code: without it BLOAD could overwrite the strings and the
        # stack of Basic below HIMEM; so the code starts at 8800h at least (room for Basic)
        dsk = pypasmo.output_bytes(asm(" org 8800h\n ret\n"), "dsk-msx", "low.dsk")
        self.assertEqual(self.sector(dsk, 14)[:39], b'10 CLEAR 200,&H87FF:BLOAD"LOW.BIN",R\r\n\x1a')
        with self.assertRaises(pypasmo.AsmError):
            pypasmo.output_bytes(asm(" org 8400h\n ret\n"), "dsk-msx", "low.dsk")

    def test_errors(self):
        for src in (" org 4000h\n ret\n",          # the ROM (BIOS, BASIC) below 8000h
                    " org 0F000h\n ret\n",         # the disk and system work area
                    " org 8000h\n"):                # no code
            with self.subTest(src), self.assertRaises(pypasmo.AsmError):
                pypasmo.output_bytes(asm(src), "dsk-msx", "x.dsk")


class TapBlocks(unittest.TestCase):
    """TAPE_BLOCK and TAPE_BLOCK_SCREEN (pypasmo extension): own blocks on the tape."""
    SRC = (" org 8000h\nstart: ld a,1\n ret\ndata: db 1,2,3\n"
           ' tape_block "code", start, 3\n tape_block "data", data, 3\n end start\n')
    SCREEN = (" org 4000h\n ds 6912, 0AAh\n org 8000h\nstart: ret\n"
              ' tape_block_screen "pic"\n tape_block "code", start, 1\n')

    @staticmethod
    def head(name, length, start):
        return bytes([3]) + name.ljust(10) + length.to_bytes(2, "little") + start.to_bytes(2, "little") + h("00 80")

    @staticmethod
    def num(n):
        return str(n).encode() + h("0E 00 00") + n.to_bytes(2, "little") + h("00")

    def loader(self, *lines):
        basic = b"".join(bytes([0, 10 * i]) + (len(b) + 1).to_bytes(2, "little") + b + h("0D")
                         for i, b in enumerate(lines, 1))
        n = len(basic).to_bytes(2, "little")
        return Outputs.block(0, bytes([0]) + b"loader    " + n + h("0A 00") + n) + Outputs.block(0xFF, basic)

    def test_tap_has_the_listed_blocks_in_order(self):
        block = Outputs.block
        expected = (block(0, self.head(b"code", 3, 0x8000)) + block(0xFF, h("3E 01 C9"))
                    + block(0, self.head(b"data", 3, 0x8003)) + block(0xFF, h("01 02 03")))
        a = asm(self.SRC)
        self.assertEqual(pypasmo.output_bytes(a, "tap", "ignored"), expected)
        self.assertEqual(pypasmo.output_bytes(a, "tzx", "x"), pypasmo.tzx(expected))
        self.assertEqual(pypasmo.output_bytes(a, "pzx-48k", "x"), pypasmo.pzx(expected))
        # other formats do not change
        self.assertEqual(pypasmo.output_bytes(a, "bin", "x"), h("3E 01 C9 01 02 03"))

    def test_one_block_gives_the_usual_tapbas(self):
        src = " org 8000h\nstart: ld a,1\n ret\n tape_block \"test\", start, 3\n end start\n"
        self.assertEqual(pypasmo.output_bytes(asm(src), "tapbas", "x"),
                         pypasmo.output_bytes(asm(Outputs.SRC), "tapbas", "test"))

    def test_tapbas_with_screen(self):
        CLEAR, POKE, LOAD, CODE, SCREEN, RANDOMIZE, USR = (h(x) for x in ("FD", "F4", "EF", "AF", "AA", "F9", "C0"))
        num = self.num
        expected = self.loader(CLEAR + num(32767),
                               POKE + num(23610) + b"," + num(255),
                               LOAD + b'""' + SCREEN + b":" + POKE + num(23739) + b"," + num(111),
                               LOAD + b'""' + CODE,
                               POKE + num(23739) + b"," + num(244) + b":" + RANDOMIZE + USR + num(32768))
        block = Outputs.block
        expected += (block(0, self.head(b"pic", 6912, 0x4000)) + block(0xFF, b"\xAA" * 6912)
                     + block(0, self.head(b"code", 1, 0x8000)) + block(0xFF, h("C9")))
        a = asm(self.SCREEN + " end start\n")
        self.assertEqual(a.warnings, [])
        self.assertEqual(pypasmo.output_bytes(a, "tapbas", "x"), expected)
        self.assertEqual(pypasmo.output_bytes(a, "tzxbas", "x"), pypasmo.tzx(expected))
        self.assertEqual(pypasmo.output_bytes(a, "pzx-wloader-48k", "x"), pypasmo.pzx(expected))

    def test_tapbas_without_entry(self):
        POKE, LOAD, SCREEN = h("F4"), h("EF"), h("AA")
        num = self.num
        out = pypasmo.output_bytes(asm(self.SCREEN), "tapbas", "x")
        # the POKE is undone also without RANDOMIZE USR
        self.assertTrue(out.startswith(self.loader(
            h("FD") + num(32767), POKE + num(23610) + b"," + num(255),
            LOAD + b'""' + SCREEN + b":" + POKE + num(23739) + b"," + num(111),
            LOAD + b'""' + h("AF"), POKE + num(23739) + b"," + num(244))))
        out = pypasmo.output_bytes(asm(" org 8000h\n ret\n tape_block \"a\", 8000h, 1\n"), "tapbas", "x")
        self.assertNotIn(h("F9 C0"), out)

    def test_clear_below_the_lowest_code_block(self):
        src = (" org 9000h\nstart: ret\n org 8000h\n db 1\n org 4000h\n ds 6912\n"
               ' tape_block "a", start, 1\n tape_block "b", 8000h, 1\n tape_block_screen "s"\n')
        out = pypasmo.output_bytes(asm(src), "tapbas", "x")
        self.assertIn(h("FD") + self.num(32767), out)
        # only a screen: no CLEAR (4000h-1 is too low)
        out = pypasmo.output_bytes(asm(' org 4000h\n ds 6912\n tape_block_screen "s"\n'), "tapbas", "x")
        self.assertNotIn(h("FD"), out)

    def test_screen_not_filled_is_a_warning(self):
        a = asm(' org 4000h\n ds 6144, 0FFh\n tape_block_screen "pic"\n')
        self.assertEqual(len(a.warnings), 1)
        self.assertIn("4000h-5AFFh", a.warnings[0])
        with self.assertRaises(pypasmo.AsmError):
            asm(' org 4000h\n ds 6144, 0FFh\n tape_block_screen "pic"\n', werror=True)
        # the screen may be filled after TAPE_BLOCK_SCREEN
        self.assertEqual(asm(' tape_block_screen "pic"\n org 4000h\n ds 6912\n').warnings, [])

    def test_errors(self):
        for bad in (' tape_block "toolongname", 8000h, 1\n',    # 11 characters
                    " tape_block name, 8000h, 1\n",             # not a string
                    ' tape_block "a", 8000h\n',
                    ' tape_block "a", 8000h, 0\n',
                    ' tape_block "a", 0FFFFh, 2\n',              # past FFFFh
                    ' tape_block_screen "a", 4000h\n',
                    " tape_block_screen\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    asm(" org 8000h\n ret\n" + bad)

    def include_asm(self, src, files):
        """Assemble src in a temporary folder with the files {name: bytes}."""
        with tempfile.TemporaryDirectory() as d:
            for name, data in files.items():
                Path(d, name).write_bytes(data)
            return asm(src, name=str(Path(d, "x.asm")))

    def test_tap_include_keeps_the_blocks_in_order(self):
        block = Outputs.block
        loader = block(0, bytes([0]) + b"myloader  " + h("05 00 0A 00 05 00")) + block(0xFF, b"basic")
        udg = block(0, self.head(b"udg", 2, 0xFF58)) + block(0xFF, h("AA 55"))
        src = (' tap_include "loader.tap"\n tape_block_screen "s"\n org 4000h\n ds 6912\n'
               ' org 8000h\nstart: ret\n tape_block "code", start, 1\n tap_include udg.tap\n end start\n')
        a = self.include_asm(src, {"loader.tap": loader, "udg.tap": udg})
        screen = block(0, self.head(b"s", 6912, 0x4000)) + block(0xFF, bytes(6912))
        code_part = block(0, self.head(b"code", 1, 0x8000)) + block(0xFF, h("C9"))
        self.assertEqual(pypasmo.output_bytes(a, "tap", "x"), loader + screen + code_part + udg)
        # --tapbas: the loader before everything, LOAD "" CODE also for the included CODE
        # block (FF58h counts for CLEAR); the included Basic program is the user's business
        POKE, LOAD, num = h("F4"), h("EF"), self.num
        expected = self.loader(h("FD") + num(32767), POKE + num(23610) + b"," + num(255),
                               LOAD + b'""' + h("AA") + b":" + POKE + num(23739) + b"," + num(111),
                               LOAD + b'""' + h("AF"), LOAD + b'""' + h("AF"),
                               POKE + num(23739) + b"," + num(244) + b":" + h("F9 C0") + num(32768))
        self.assertEqual(pypasmo.output_bytes(a, "tapbas", "x"), expected + loader + screen + code_part + udg)
        # .pzx: the same blocks (the included Basic stays a Basic program)
        self.assertEqual(pypasmo.output_bytes(a, "pzx-48k", "x"), pypasmo.pzx(loader + screen + code_part + udg))
        self.assertEqual(pypasmo.output_bytes(a, "pzx-wloader-48k", "x"),
                         pypasmo.pzx(expected + loader + screen + code_part + udg))

    def test_tap_include_screen_and_clear(self):
        block = Outputs.block
        scr = block(0, self.head(b"pic", 6912, 0x4000)) + block(0xFF, bytes(6912))
        code = block(0, self.head(b"c", 1, 0x9000)) + block(0xFF, h("C9"))
        a = self.include_asm(' tap_include "all.tap"\n', {"all.tap": scr + code})
        num = self.num
        # an included CODE 16384,6912 is a screen: LOAD "" SCREEN$, not counted for CLEAR
        self.assertEqual(pypasmo.output_bytes(a, "tapbas", "x"), self.loader(
            h("FD") + num(0x9000 - 1), h("F4") + num(23610) + b"," + num(255),
            h("EF") + b'""' + h("AA") + b":" + h("F4") + num(23739) + b"," + num(111),
            h("EF") + b'""' + h("AF"), h("F4") + num(23739) + b"," + num(244)) + scr + code)

    def test_tap_include_errors(self):
        good = Outputs.block(0xFF, h("01 02"))
        for name, data in (("missing", None), ("empty", b""), ("short", good[:-1]),
                           ("checksum", good[:-1] + b"\x00"), ("zero", h("00 00"))):
            with self.subTest(name):
                files = {} if data is None else {"t.tap": data}
                with self.assertRaises(pypasmo.AsmError):
                    self.include_asm(' tap_include "t.tap"\n', files)
        self.include_asm(' tap_include "t.tap"\n', {"t.tap": good})
        with self.assertRaises(pypasmo.AsmError):
            code(' tap_include "t.tap"\n', pasmo_syntax=True)
        self.assertEqual(code("tap_include: db 1\n ld a,tap_include\n"), h("01 3E 00"))

    def test_tape_block_screen_with_a_file(self):
        pic = bytes(range(256)) * 27                         # 6912 bytes
        src = (' tape_block_screen "pic", "pic.scr"\n org 8000h\nstart: ret\n'
               ' tape_block "code", start, 1\n end start\n')
        a = self.include_asm(src, {"pic.scr": pic})
        self.assertEqual(a.warnings, [])
        self.assertEqual(bytes(a.mem[x] for x in range(0x4000, 0x5B00)), pic)
        self.assertEqual(a.symbols["start"], 0x8000)          # $ does not move
        block = Outputs.block
        self.assertEqual(pypasmo.output_bytes(a, "tap", "x"),
                         block(0, self.head(b"pic", 6912, 0x4000)) + block(0xFF, pic)
                         + block(0, self.head(b"code", 1, 0x8000)) + block(0xFF, h("C9")))
        # $ stays where it was also in the middle of the code
        a = self.include_asm(' org 9000h\n nop\n tape_block_screen "pic", "pic.scr"\n ret\n', {"pic.scr": pic})
        self.assertEqual(a.mem[0x9001], 0xC9)

    def test_tape_block_screen_file_errors(self):
        pic = bytes(6912)
        for name, src, files in (
                ("short", ' tape_block_screen "p", "p.scr"\n', {"p.scr": pic[:-1]}),
                ("long", ' tape_block_screen "p", "p.scr"\n', {"p.scr": pic + b"x"}),
                ("missing", ' tape_block_screen "p", "p.scr"\n', {}),
                ("not a string", ' tape_block_screen "p", 5\n', {}),
                ("code before", ' org 5000h\n nop\n tape_block_screen "p", "p.scr"\n', {"p.scr": pic}),
                ("code after", ' tape_block_screen "p", "p.scr"\n org 5AFFh\n nop\n', {"p.scr": pic})):
            with self.subTest(name):
                with self.assertRaises(pypasmo.AsmError):
                    self.include_asm(src, files)

    def test_tape_block_before_its_labels(self):
        # the TAPE_BLOCK lines may be at the start of the source (values from the last pass)
        a = asm(' tape_block "code", start, last - start\n org 8000h\nstart: nop\n ret\nlast:\n')
        self.assertEqual(a.tape_blocks, [("code", "code", 0x8000, 2)])

    def test_not_with_tap128(self):
        a = asm(" org 8000h\n ret\n tape_block \"a\", 8000h, 1\n")
        for fmt in ("tap128", "tapbas128"):
            with self.subTest(fmt):
                with self.assertRaises(pypasmo.AsmError):
                    pypasmo.output_bytes(a, fmt, "x")

    def test_names_not_reserved_and_pasmo_syntax(self):
        self.assertEqual(code("tape_block: db 1\n ld a,tape_block\ntape_block_screen equ 2\n db tape_block_screen\n"),
                         h("01 3E 00 02"))
        for bad in (' tape_block "a", 0, 1\n', ' tape_block_screen "a"\n'):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad, pasmo_syntax=True)


class MacroExtensions(unittest.TestCase):
    """Default values of macro parameters, IFB / IFNB (pypasmo extension)."""

    def test_default_values(self):
        src = ("fill macro val, n=2, reg=a\n ld reg,val\n ds n,val\n endm\n"
               " fill 5\n fill 7, 1\n fill 9, , b\n fill 1, 3, c\n")
        # ld a,5 / ds 2,5 - ld a,7 / ds 1,7 - ld b,9 / ds 2,9 (empty = default) - ld c,1 / ds 3,1
        self.assertEqual(code(src), h("3E 05 05 05 3E 07 07 06 09 09 09 0E 01 01 01 01"))
        self.assertEqual(code(" macro sum, x=1, y=2\n db x+y\n endm\n sum\n sum 5\n"), h("03 07"))
        # a default with a comma in a string; a comment after the parameters
        self.assertEqual(code('m2 macro t="a,b" ; text\n db t\n endm\n m2\n'), h("61 2C 62"))

    def test_ifb_ifnb(self):
        src = ("chk macro v\n ifb v\n db 0\n else\n db v\n endif\n ifnb <v>\n db 0FFh\n endif\n endm\n"
               " chk\n chk 5\n")
        self.assertEqual(code(src), h("00 05 FF"))
        self.assertEqual(code(" ifb\n db 1\n endif\n ifnb ; a comment is not an argument\n db 2\n endif\n"), h("01"))
        self.assertEqual(code(" ifb <>\n db 1\n endif\n ifb <x>\n db 2\n endif\n"), h("01"))
        # nested in a skipped branch: counted like IF
        self.assertEqual(code(" if 0\n ifb x\n endif\n db 1\n endif\n db 2\n"), h("02"))
        # a parameter with a default is not blank
        self.assertEqual(code("m3 macro v=1\n ifb v\n db 0\n else\n db v\n endif\n endm\n m3\n"), h("01"))

    def test_names_not_reserved_and_pasmo_syntax(self):
        self.assertEqual(code("ifb: db 1\n ld a,ifnb\nifnb equ 2\n"), h("01 3E 02"))
        for bad in (" ifb\n endif\n", "mac macro v=1\n endm\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    code(bad, pasmo_syntax=True)


class BankOf(unittest.TestCase):
    """BANK_OF label (pypasmo extension): the ZX Spectrum 128K RAM bank of a label."""

    def test_bank_of(self):
        src = (" org 8000h\nstart: ld a, bank_of level3\n ld b, BANK_OF(scr2)\n ld c, bank_of start\n"
               " ld d, bank_of low_lbl\n ld e, bank_of top\n ld h, bank_of level3 + 1\n"
               " bank 4\n org 0C000h\nlevel3: db 1\n bank 7\n org 0C000h\nscr2: db 2\n"
               " bank 0\n org 0E000h\ntop: db 3\n org 5000h\nlow_lbl: db 4\n end start\n")
        a = asm(src)
        # labels used before they are defined; BANK n at C000h, 4000h = bank 5, 8000h = bank 2
        self.assertEqual(bytes(a.mem[0x8000 + k] for k in range(12)),
                         h("3E 04 06 07 0E 02 16 05 1E 00 26 05"))

    def test_phase_takes_the_load_address(self):
        a = asm(" org 8000h\n phase 0C000h\nph: nop\n dephase\n ld a, bank_of ph\n")
        self.assertEqual(a.mem[0x8002], 2)

    def test_errors_and_names(self):
        for bad in (" ld a, bank_of x\nx equ 1\n",                 # not a label
                    " org 100h\nl: nop\n ld a, bank_of l\n",        # not in RAM (the ROM)
                    " ld a, bank_of nothing\n"):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    asm(bad)
        self.assertEqual(code("bank_of: db 1\n ld a, bank_of\n"), h("01 3E 00"))
        with self.assertRaises(pypasmo.AsmError):
            asm(" org 8000h\nl: ld a, bank_of l\n", pasmo_syntax=True)


class Display(unittest.TestCase):
    """DISPLAY (pypasmo extension, like sjasmplus): print text and values when assembling."""

    def test_display(self):
        a = asm(' org 8000h\n display "free: ", 0FFFFh-last\n nop\nlast:\n display "x"\n')
        self.assertEqual(a.displays, ["free: 32766 (7FFEh)", "x"])     # labels defined later too
        self.assertEqual(asm(' display "a", 1, 2\n').displays, ["a 1 (0001h) 2 (0002h)"])
        self.assertEqual(asm(' display "a=", 1, ", b=", 2\n').displays, ["a= 1 (0001h), b= 2 (0002h)"])
        self.assertEqual(asm(" rept 2, k\n display \"k=\", k\n endm\n").displays, ["k= 0 (0000h)", "k= 1 (0001h)"])
        self.assertEqual(asm(' if 0\n display "no"\n endif\n').displays, [])

    def test_errors_and_names(self):
        for bad in (" display\n", " display x\n", ' display "a",\n'):
            with self.subTest(bad):
                with self.assertRaises(pypasmo.AsmError):
                    asm(bad)
        self.assertEqual(code("display: db 1\n"), h("01"))
        with self.assertRaises(pypasmo.AsmError):
            asm(' display "x"\n', pasmo_syntax=True)

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text(' org 8000h\n display "end: ", $\n', encoding="utf-8")
            rc, out, err = run_main(str(src), str(Path(d, "p.bin")))
        self.assertEqual(rc, 0, err)
        self.assertIn("end: 32768 (8000h)\n", out)


class Outputs(unittest.TestCase):
    SRC = " org 8000h\nstart: ld a,1\n ret\n end start\n"

    def test_intel_hex(self):
        out = pypasmo.output_bytes(asm(self.SRC), "hex", "")
        # 3 bytes at 8000h: 3E 01 C9, checksum = -(03+80+00+00+3E+01+C9) mod 256 = 75h.
        # The end record holds the entry point from END (Pasmo 0.5.5): -(00+80+00+01) mod 256 = 7Fh.
        self.assertEqual(out.decode(), ":038000003E01C975\r\n:008000017F\r\n")
        out = pypasmo.output_bytes(asm(" org 8000h\n ret\n"), "hex", "")
        self.assertTrue(out.decode().endswith(":00000001FF\r\n"))

    def test_plus3dos(self):
        out = pypasmo.output_bytes(asm(self.SRC), "plus3dos", "")
        head = bytearray(b"PLUS3DOS\x1A\x01\x00")      # signature, issue 1, version 0
        head += (128 + 3).to_bytes(4, "little")         # file size including the header
        head += h("03 03 00 00 80 80 80")               # CODE, length 3, start 8000h, 8080h
        head += bytes(127 - len(head))
        head.append(sum(head) & 0xFF)
        self.assertEqual(out, bytes(head) + h("3E 01 C9") + bytes(125))

    def test_symbol_file(self):
        self.assertEqual(pypasmo.symbol_text(asm(self.SRC)), "start\t\tEQU 08000H\n")

    @staticmethod
    def block(flag, data):
        chk = flag
        for b in data:
            chk ^= b
        return (len(data) + 2).to_bytes(2, "little") + bytes([flag]) + data + bytes([chk])

    def test_tap(self):
        head = bytes([3]) + b"test      " + h("03 00") + h("00 80") + h("00 80")
        expected = self.block(0, head) + self.block(0xFF, h("3E 01 C9"))
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "tap", "test"), expected)
        self.assertEqual(len(expected), 21 + 7)

    def test_tap_name_truncated(self):
        out = pypasmo.output_bytes(asm(self.SRC), "tap", "verylongfilename.tap")
        self.assertEqual(out[4:14], b"verylongfi")

    def test_tapbas(self):
        num = lambda n, txt: txt + h("0E 00 00") + n.to_bytes(2, "little") + h("00")  # noqa: E731
        basic = (h("00 0A 0D 00") + h("FD") + num(32767, b"32767") + h("0D")                 # 10 CLEAR 32767
                 + h("00 14 17 00") + h("F4") + num(23610, b"23610") + b"," + num(255, b"255") + h("0D")
                 + h("00 1E 05 00") + h("EF") + b'""' + h("AF 0D")                            # 30 LOAD "" CODE
                 + h("00 28 0E 00") + h("F9 C0") + num(32768, b"32768") + h("0D"))            # 40 RANDOMIZE USR
        n = len(basic).to_bytes(2, "little")
        head = bytes([0]) + b"loader    " + n + h("0A 00") + n
        code_part = pypasmo.output_bytes(asm(self.SRC), "tap", "test")
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "tapbas", "test"),
                         self.block(0, head) + self.block(0xFF, basic) + code_part)

    def test_tapbas_without_entry_has_no_line_40(self):
        out = pypasmo.output_bytes(asm(" org 8000h\n ret\n"), "tapbas", "x")
        self.assertNotIn(h("F9 C0"), out)

    def test_prl(self):
        src = "start: ld hl,data\n jp start\n ld a,1\ndata: db 12h\n"
        out = pypasmo.output_bytes(asm(src), "prl", "")
        head = bytearray(256)
        head[1] = 9                                     # code length
        code = h("21 08 01 C3 00 01 3E 01 12")         # assembled for 100h
        reloc = h("24 00")                              # bytes 2 and 5 are address high bytes
        self.assertEqual(out, bytes(head) + code + reloc)

    def test_prl_with_absolute_org_fails(self):
        with self.assertRaises(pypasmo.AsmError):
            pypasmo.output_bytes(asm(self.SRC), "prl", "")

    TZX = b"ZXTape!\x1A\x01\x0D"            # signature + version 1.13
    STD = h("10 E8 03")                     # standard speed block, pause 1000 ms

    def test_tzx(self):
        head = bytes([3]) + b"test      " + h("03 00 00 80 00 80")
        expected = self.TZX + self.STD + self.block(0, head) + self.STD + self.block(0xFF, h("3E 01 C9"))
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "tzx", "test"), expected)

    def test_tzxbas_is_tapbas_in_tzx_blocks(self):
        tap = pypasmo.output_bytes(asm(self.SRC), "tapbas", "test")
        tzx = pypasmo.output_bytes(asm(self.SRC), "tzxbas", "test")
        self.assertTrue(tzx.startswith(self.TZX))
        self.assertEqual(tzx.count(self.STD), 4)
        self.assertEqual(tzx.replace(self.STD, b"")[len(self.TZX):], tap)

    PZX = b"PZXT" + h("02 00 00 00 01 00")        # header block, version 1.0, no texts

    @classmethod
    def pzx_block(cls, flag, data):
        """One tap block in PZX blocks, as the PZX specification (pzx_format.txt) shows
        the ROM loading: PULS = the pilot tone (8000h + 8063 pulses for a header, 8000h +
        3223 for data, each 2168 T) and the sync pulses 667 + 735 T; DATA = the bits
        (bit 31 = start high), tail 945 T, 2 pulses for each bit: 0 = 855 + 855 T,
        1 = 1710 + 1710 T, then the bytes (flag, data, checksum); PAUS = 1 s = 3500000 T."""
        body = cls.block(flag, data)[2:]
        pilot = h("7F 9F") if flag < 128 else h("97 8C")
        return (b"PULS" + h("08 00 00 00") + pilot + h("78 08 9B 02 DF 02")
                + b"DATA" + (16 + len(body)).to_bytes(4, "little")
                + (0x80000000 + 8 * len(body)).to_bytes(4, "little")
                + h("B1 03 02 02 57 03 57 03 AE 06 AE 06") + body
                + b"PAUS" + h("04 00 00 00 E0 67 35 00"))

    def test_pzx(self):
        head = bytes([3]) + b"test      " + h("03 00 00 80 00 80")
        expected = self.PZX + self.pzx_block(0, head) + self.pzx_block(0xFF, h("3E 01 C9"))
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "pzx-48k", "test"), expected)

    def test_pzx_wloader_has_the_blocks_of_tapbas(self):
        tap = pypasmo.output_bytes(asm(self.SRC), "tapbas", "test")
        expected, pos = self.PZX, 0
        while pos < len(tap):
            size = int.from_bytes(tap[pos:pos + 2], "little")
            expected += self.pzx_block(tap[pos + 2], tap[pos + 3:pos + 1 + size])
            pos += 2 + size
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "pzx-wloader-48k", "test"), expected)
        self.assertEqual(expected.count(b"PULS"), 4)

    @staticmethod
    def pzx_to_tap(pzx):
        """Back from .pzx to .tap (the bytes of the DATA blocks) and the list of the tags;
        checks the sizes of the blocks on the way."""
        tap, tags, pos = b"", [], 0
        while pos < len(pzx):
            tag, size = pzx[pos:pos + 4], int.from_bytes(pzx[pos + 4:pos + 8], "little")
            body = pzx[pos + 8:pos + 8 + size]
            assert len(body) == size, (tag, size)
            tags.append(tag.decode("ascii"))
            if tag == b"DATA":
                bits = int.from_bytes(body[:4], "little")
                assert bits & 0x80000000 and bits % 8 == 0         # starts high, whole bytes
                data = body[16:]
                assert len(data) * 8 == bits & 0x7FFFFFFF
                tap += len(data).to_bytes(2, "little") + data
            pos += 8 + size
        return tap, tags

    def test_pzx_has_the_blocks_of_the_tap(self):
        # every tape: .pzx = the same blocks as .tap, each as PULS + DATA + PAUS
        for src in (self.SRC, " org 8000h\n", TapBlocks.SCREEN + " end start\n",
                    ' org 8000h\nst: ret\n tape_block "a", st, 1\n tape_block "b", st, 1\n'):
            for tap_fmt, pzx_fmt in (("tap", "pzx-48k"), ("tapbas", "pzx-wloader-48k")):
                with self.subTest(src, fmt=pzx_fmt):
                    tap = pypasmo.output_bytes(asm(src), tap_fmt, "x")
                    back, tags = self.pzx_to_tap(pypasmo.output_bytes(asm(src), pzx_fmt, "x"))
                    self.assertEqual(back, tap)
                    self.assertEqual(tags, ["PZXT"] + ["PULS", "DATA", "PAUS"] * (len(tags) // 3))
                    blocks, pos = 0, 0
                    while pos < len(tap):
                        blocks, pos = blocks + 1, pos + 2 + int.from_bytes(tap[pos:pos + 2], "little")
                    self.assertEqual(len(tags), 1 + 3 * blocks)

    def test_pzx_pilot_tone_by_the_flag(self):
        # the ROM: a flag below 128 is a header (long pilot tone), else data
        for flag, pilot in ((0x00, 8063), (0x7F, 8063), (0x80, 3223), (0xFF, 3223)):
            with self.subTest(flag=flag):
                out = pypasmo.pzx(self.block(flag, h("01 02")))
                self.assertEqual(out[len(self.PZX) + 8:len(self.PZX) + 10], (0x8000 + pilot).to_bytes(2, "little"))
                self.assertEqual(self.pzx_to_tap(out)[0], self.block(flag, h("01 02")))

    def test_pzx_of_no_blocks_is_the_header(self):
        self.assertEqual(pypasmo.pzx(b""), self.PZX)

    def test_pzx_needs_48k_code(self):
        a = asm(" org 8000h\n ret\n bank 1\n org 0C000h\n nop\n")
        for fmt in ("pzx-48k", "pzx-wloader-48k"):
            with self.subTest(fmt):
                with self.assertRaises(pypasmo.AsmError) as e:
                    pypasmo.output_bytes(a, fmt, "x")
                self.assertIn("needs a 128K format", str(e.exception))

    def test_128k_tzx_and_pzx_have_the_blocks_of_tap128(self):
        # --tzx-128k ... = the blocks of --tap-128k / --tap-wloader-128k in .tzx / .pzx
        for src in (ForkExtensions.SRC128, self.SRC, " org 8000h\n"):
            for tap_fmt, tzx_fmt, pzx_fmt in (("tap128", "tzx-128k", "pzx-128k"),
                                              ("tapbas128", "tzx-wloader-128k", "pzx-wloader-128k")):
                with self.subTest(src, fmt=tap_fmt):
                    tap = pypasmo.output_bytes(asm(src), tap_fmt, "x")
                    tzx, pos = self.TZX, 0
                    while pos < len(tap):
                        size = int.from_bytes(tap[pos:pos + 2], "little")
                        tzx += self.STD + tap[pos:pos + 2 + size]
                        pos += 2 + size
                    self.assertEqual(pypasmo.output_bytes(asm(src), tzx_fmt, "x"), tzx)
                    back, tags = self.pzx_to_tap(pypasmo.output_bytes(asm(src), pzx_fmt, "x"))
                    self.assertEqual(back, tap)
                    self.assertEqual(tags, ["PZXT"] + ["PULS", "DATA", "PAUS"] * (len(tags) // 3))

    def test_128k_tzx_and_pzx_messages(self):
        a = asm(" org 5D00h\nst: ret\n bank 1\n org 0C000h\n db 1\n end st\n")
        pypasmo.output_bytes(a, "pzx-wloader-128k", "x")
        self.assertTrue(any(w.startswith("warning: --pzx-wloader-128k: the Basic loader does CLEAR")
                            for w in a.warnings), a.warnings)
        a = asm(" org 100h\n ret\n")
        pypasmo.output_bytes(a, "tzx-128k", "x")
        self.assertIn("warning: --tzx-128k: code at 0000h-3FFFh is in the ROM, LOAD can not put it there",
                      a.warnings)
        for fmt in ("tzx-128k", "tzx-wloader-128k", "pzx-128k", "pzx-wloader-128k"):
            with self.subTest(fmt):
                with self.assertRaises(pypasmo.AsmError) as e:
                    pypasmo.output_bytes(asm(' org 8000h\n ret\n tape_block "a",8000h,1\n'), fmt, "x")
                self.assertIn(f"TAPE_BLOCK is not supported with --{fmt}", str(e.exception))
        with self.assertRaises(pypasmo.AsmError) as e:
            pypasmo.output_bytes(asm(" org 8000h\n ret\n bank 1\n org 0C000h\n nop\n"), "tzx", "x")
        self.assertIn("(--tap-128k, --tap-wloader-128k, --tzx-128k, --tzx-wloader-128k, --pzx-128k, "
                      "--pzx-wloader-128k, --sna-128k, --z80-128k)", str(e.exception))

    def test_msx(self):
        # FEh, start 8000h, end 8002h, execution 8000h (END start)
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "msx", ""),
                         h("FE 00 80 02 80 00 80 3E 01 C9"))
        self.assertEqual(pypasmo.output_bytes(asm(" org 8000h\n ret\n"), "msx", "")[5:7], h("00 00"))

    MSX_HEAD = ' db "AB"\n dw init\n ds 12\ninit: ret\n'

    def test_rom_msx(self):
        # the header from the source (AB, INIT = 4010h, 12 zeros), padded with FFh to 8 KB
        out = pypasmo.output_bytes(asm(" org 4000h\n" + self.MSX_HEAD), "rom-msx", "")
        self.assertEqual(out, b"AB" + h("10 40") + bytes(12) + h("C9") + b"\xFF" * (8192 - 17))
        # the next size: 16 KB, 32 KB (4000h-BFFFh); at 8000h at most 16 KB
        for org, fill, size in (("4000h", 0x2000, 16384), ("4000h", 0x6000, 32768), ("8000h", 0x2000, 16384)):
            with self.subTest(org=org, fill=fill):
                out = pypasmo.output_bytes(asm(f" org {org}\n" + self.MSX_HEAD + f" ds {fill}\n"), "rom-msx", "")
                self.assertEqual(len(out), size)

    def test_rom_msx_errors(self):
        for src in (" org 4000h\n ret\n",                                   # no header
                    " org 0C000h\n" + self.MSX_HEAD,                         # not 4000h / 8000h
                    " org 4000h\n" + self.MSX_HEAD + " ds 8000h\n",          # more than 32 KB
                    " org 8000h\n" + self.MSX_HEAD + " ds 4000h\n"):         # past BFFFh
            with self.subTest(src):
                with self.assertRaises(pypasmo.AsmError):
                    pypasmo.output_bytes(asm(src), "rom-msx", "")

    def test_cas_msx(self):
        # header block: sync header, 10 x D0h (binary), name (6); data block: sync header,
        # start, end, start (END), code; each header at a multiple of 8 (zeros after the data)
        sync = h("1F A6 DE BA CC 13 7D 74")
        out = pypasmo.output_bytes(asm(" org 9000h\nst: ld a,1\n ret\n end st\n"), "cas-msx", "hello.cas")
        self.assertEqual(out, sync + b"\xD0" * 10 + b"hello " + sync + h("00 90 02 90 00 90 3E 01 C9") + bytes(7))
        self.assertEqual(len(out) % 8, 0)
        # the name: up to the first dot, at most 6 characters; without END the start
        out = pypasmo.output_bytes(asm(" org 9000h\n ret\n"), "cas-msx", "verylongname.cas")
        self.assertEqual(out[18:24], b"verylo")
        self.assertEqual(out[32:38], h("00 90 00 90 00 90"))

    def test_mzf(self):
        # 128 byte header: 01h (machine code), name + 0Dh (17 bytes), size, load, start (END), comment
        out = pypasmo.output_bytes(asm(self.SRC), "mzf", "hello.mzf")
        head = h("01") + b"HELLO.MZF\x0D" + b"\x0D" * 7 + h("03 00 00 80 00 80") + bytes(104)
        self.assertEqual(out, head + h("3E 01 C9"))
        # without END: start = load address; the name upper case, at most 16 characters
        out = pypasmo.output_bytes(asm(" org 1200h\n ret\n"), "mzf", "a_very_long_name_x")
        self.assertEqual(out[1:18], b"A_VERY_LONG_NAME\x0D")
        self.assertEqual(out[20:24], h("00 12 00 12"))

    def test_amsdos(self):
        head = bytearray(128)
        head[1:12] = b"test    bin"                 # name 8 + extension 3, user 0
        head[0x12] = 2                              # binary file
        head[0x15:0x17] = h("00 80")                # load address
        head[0x18:0x1A] = h("03 00")                # length
        head[0x1A:0x1C] = h("00 80")                # entry point
        head[0x40:0x43] = h("03 00 00")             # real length (3 bytes)
        head[0x43:0x45] = (sum(head[:0x43])).to_bytes(2, "little")
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "amsdos", "test.bin"),
                         bytes(head) + h("3E 01 C9"))
        out = pypasmo.output_bytes(asm(self.SRC), "amsdos", "longfilename")
        self.assertEqual(out[1:12], b"longfile   ")

    def test_cpc_crc(self):
        import binascii                      # CRC-CCITT (init FFFFh) from the standard library
        for data in (b"", b"\x3E\x01\xC9", bytes(range(256))):
            self.assertEqual(pypasmo.cpc_crc(data),
                             binascii.crc_hqx(data.ljust(256, b"\0"), 0xFFFF) ^ 0xFFFF)

    # TZX turbo block with the CPC timing, followed by a 3 byte data length
    TURBO = h("11 80 03 C0 01 C0 01 C0 01 80 03 00 10 08 70 09")

    def cdt_record(self, sync, data):
        """Independent writer of one record: one 256 byte chunk + CRC (big endian) + FF FF FF FF."""
        chunk = data.ljust(256, b"\0")
        crc = pypasmo.cpc_crc(data)
        return self.TURBO + h("07 01 00") + bytes([sync]) + chunk + crc.to_bytes(2, "big") + b"\xFF" * 4

    def test_cdt(self):
        head = bytearray(64)
        head[0:4] = b"test"
        head[0x10] = 1                              # block 1
        head[0x11] = 0xFF                           # last block
        head[0x12] = 2                              # binary
        head[0x13:0x15] = h("03 00")                # block length
        head[0x15:0x17] = h("00 80")                # load address
        head[0x17] = 0xFF                           # first block
        head[0x18:0x1A] = h("03 00")                # file length
        head[0x1A:0x1C] = h("00 80")                # entry point
        expected = self.TZX + self.cdt_record(0x2C, bytes(head)) + self.cdt_record(0x16, h("3E 01 C9"))
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "cdt", "test"), expected)

    def test_cdt_blocks_of_2k(self):
        out = pypasmo.output_bytes(asm(" org 4000h\n ds 5000, 0AAh\n"), "cdt", "big")
        heads = [k for k in range(len(out)) if out[k:k + 20] == self.TURBO + h("07 01 00 2C")]
        self.assertEqual(len(heads), 3)              # 2048 + 2048 + 904 bytes
        for num, k in enumerate(heads, 1):
            rec = out[k + 20:k + 84]
            self.assertEqual(rec[0x10], num)
            self.assertEqual(rec[0x17], 0xFF if num == 1 else 0)
            self.assertEqual(rec[0x11], 0xFF if num == 3 else 0)
            self.assertEqual(rec[0x13:0x15], (904 if num == 3 else 2048).to_bytes(2, "little"))
            self.assertEqual(rec[0x15:0x17], h("00 40"))     # like Pasmo: load address of the file
        # data record of the 1st block: 8 chunks of 256 bytes + CRC, sync and 4 trailer bytes
        k = heads[0] + 19 + 263
        self.assertEqual(out[k:k + 16], self.TURBO)
        self.assertEqual(int.from_bytes(out[k + 16:k + 19], "little"), 8 * 258 + 5)

    def test_cdtbas(self):
        basic = (h("09 00 0A 00 AA 1C FF 7F 00")                       # 10 MEMORY &7FFF
                 + h("0D 00 14 00 A8") + b'"!",' + h("1C 00 80 00")    # 20 LOAD "!",&8000
                 + h("09 00 1E 00 83 1C 00 80 00")                     # 30 CALL &8000
                 + h("00 00"))
        head = bytearray(64)
        head[0:6] = b"LOADER"
        head[0x10], head[0x11], head[0x17] = 1, 0xFF, 0xFF               # block 1, last, first
        head[0x13:0x15] = head[0x18:0x1A] = len(basic).to_bytes(2, "little")
        code_part = pypasmo.output_bytes(asm(self.SRC), "cdt", "test")[len(self.TZX):]
        self.assertEqual(pypasmo.output_bytes(asm(self.SRC), "cdtbas", "test"),
                         self.TZX + self.cdt_record(0x2C, bytes(head)) + self.cdt_record(0x16, basic)
                         + code_part)


class Snapshot(unittest.TestCase):
    """--sna-48k / --z80-48k. The Basic state comes from tools/devel/make_sna_template.py; programs
    made with it were run in the Z80 simulator of SkoolKit (printing with the ROM, RET gives 0 OK)."""

    @staticmethod
    def word(snap, addr):
        return snap[27 + addr - 0x4000] | snap[28 + addr - 0x4000] << 8

    def test_layout(self):
        snap = pypasmo.output_bytes(asm(" org 8000h\nstart: ret\n end start\n"), "sna-48k", "")
        self.assertEqual(len(snap), 27 + 0xC000)
        sp = snap[23] | snap[24] << 8
        self.assertEqual(sp, 0x8000 - 24 - 2)            # CLEAR 7FFFh, stack, PC pushed
        self.assertEqual(self.word(snap, sp), 0x8000)     # PC
        self.assertEqual(self.word(snap, sp + 2), 0x2D2B)  # USR returns to STACK-BC
        self.assertEqual(snap[13] | snap[14] << 8, 0x8000)  # BC = USR address
        self.assertEqual(self.word(snap, 0x5CB2), 0x7FFF)   # RAMTOP
        self.assertEqual(self.word(snap, 0x5C3D), 0x7FFC)   # ERR_SP ...
        self.assertEqual(self.word(snap, 0x7FFC), 0x1303)   # ... to MAIN-4
        self.assertEqual(snap[27 + 0x7FFF - 0x4000], 0x3E)  # end marker of the GOSUB stack
        self.assertEqual(snap[27 + 0x8000 - 0x4000], 0xC9)  # the code
        self.assertEqual((snap[19], snap[25], snap[0]), (4, 1, 0x3F))   # IFF2, IM 1, I
        basic = snap[27 + 0x5CCB - 0x4000:27 + 0x5CE4 - 0x4000]
        self.assertIn(b'"32767":', basic)
        self.assertIn(b'"32768"', basic)

    def test_entry_and_low_code(self):
        # no END: start of the code; below the lowest CLEAR: RAMTOP stays FF57h
        snap = pypasmo.output_bytes(asm(" org 5D20h\n ret\n"), "sna-48k", "")
        self.assertEqual(self.word(snap, 0x5CB2), 0xFF57)
        self.assertEqual(self.word(snap, snap[23] | snap[24] << 8), 0x5D20)
        self.assertIn(b'"65367"', snap[27 + 0x5CCB - 0x4000:27 + 0x5CE4 - 0x4000])

    def test_errors(self):
        for src in (" org 100h\n ret\n", " org 5D00h\n nop\n org 0FF50h\n nop\n", " bank 1\n org 0C000h\n nop\n"):
            for fmt in ("sna-48k", "z80-48k"):
                with self.subTest(src=src, fmt=fmt):
                    with self.assertRaises(pypasmo.AsmError):
                        pypasmo.output_bytes(asm(src), fmt, "")

    @staticmethod
    def unz80(snap):
        """(header, {page: bytes}) of a version 3 .z80 file, decompressed as the format says."""
        n = 32 + (snap[30] | snap[31] << 8)
        pages, pos = {}, n
        while pos < len(snap):
            size, page = snap[pos] | snap[pos + 1] << 8, snap[pos + 2]
            data, pos = snap[pos + 3:pos + 3 + size], pos + 3 + size
            out, i = bytearray(), 0
            while i < len(data):
                if data[i:i + 2] == b"\xED\xED":
                    out += bytes([data[i + 3]]) * data[i + 2]
                    i += 4
                else:
                    out.append(data[i])
                    i += 1
            pages[page] = bytes(out)
        return snap[:n], pages

    def test_sna_128k(self):
        # the 48K state on a 128K in 48 BASIC (ROM 1) with paging not locked: 7FFDh = 10h
        a = asm(" org 8000h\nstart: ld a,2\n ret\n end start\n")
        sna48, sna = pypasmo.output_bytes(a, "sna-48k", ""), pypasmo.output_bytes(a, "sna-128k", "")
        self.assertEqual(len(sna), 27 + 0xC000 + 4 + 5 * 0x4000)
        self.assertEqual(sna[:23], sna48[:23])
        self.assertEqual(sna[23] | sna[24] << 8, (sna48[23] | sna48[24] << 8) + 2)   # PC is not on the stack
        self.assertEqual(sna[25:27], sna48[25:27])
        ram = 27 + 0xC000
        self.assertEqual(sna[ram:ram + 4], h("00 80 10 00"))                 # PC, 7FFDh, no TR-DOS
        self.assertEqual(sna[27 + 0x5B5C - 0x4000], 0x10)                   # BANKM
        same = bytearray(sna48[27:])
        same[0x5B5C - 0x4000] = 0x10
        self.assertEqual(sna[27:ram], bytes(same))                          # banks 5, 2, 0
        self.assertEqual(sna[ram + 4:], bytes(5 * 0x4000))                  # banks 1, 3, 4, 6, 7

    def test_sna_128k_banks(self):
        src = (" org 8000h\nstart: ret\n org 0C000h\n db 0\n bank 1\n org 0C000h\n db 11h\n"
               " bank 7\n org 0C001h\n db 77h\n end start\n")
        sna = pypasmo.output_bytes(asm(src), "sna-128k", "")
        rest = 27 + 0xC000 + 4                                              # banks 1, 3, 4, 6, 7 follow
        self.assertEqual(sna[rest], 0x11)
        self.assertEqual(sna[rest + 4 * 0x4000 + 1], 0x77)
        self.assertEqual(sna[27 + 0xC000 - 0x4000], 0)                      # bank 0 at C000h
        with self.assertRaises(pypasmo.AsmError):                           # BANK needs a 128K format
            pypasmo.output_bytes(asm(src), "sna-48k", "")

    def test_snapshot_checks(self):
        # snapshots that would not work: an error instead of a broken file
        bad = {
            "start in BANK 1 (bank 0 is at C000h)": (" org 8000h\n ret\n bank 1\n org 0C000h\nst: ret\n end st\n", "128"),
            "code over the system variables / Basic": (" org 5CF0h\n ret\n", "48"),
            "code at BANKM (5B5Ch)": (" org 5B5Ch\n db 0AAh\n org 8000h\n ret\n", "128"),
            "Basic stack in bank 0 with BANK": (" org 5D20h\n ret\n bank 1\n org 0C000h\n db 1\n", "128"),
            # BANK 5 / BANK 2 are also at 4000h / 8000h: the same checks there
            "BANK 5 over the system variables": (" org 8000h\n ret\n bank 5\n org 0DC00h\n db 1,2,3\n", "128"),
            "BANK 5 at BANKM": (" org 8000h\n ret\n bank 5\n org 0DB5Ch\n db 0AAh\n", "128"),
            "BANK 2 over the Basic stack": (" org 9000h\n ret\n bank 2\n org 0CFF0h\n ds 16,0AAh\n", "128"),
        }
        for name, (src, kind) in bad.items():
            fmts = ("sna-128k", "z80-128k") if kind == "128" else ("sna-48k", "z80-48k", "sna-128k", "z80-128k")
            for fmt in fmts:
                with self.subTest(name, fmt=fmt):
                    with self.assertRaises(pypasmo.AsmError):
                        pypasmo.output_bytes(asm(src), fmt, "")
        # still fine: the printer buffer in 48K, a start in bank 0, low code without BANK in 128K
        for src, fmt in ((" org 5B5Ch\n db 0AAh\n org 8000h\n ret\n", "sna-48k"),
                         (" org 8000h\n ret\n org 0C000h\nst: ret\n end st\n", "sna-128k"),
                         (" org 5D20h\n ret\n", "sna-128k")):
            with self.subTest(src, fmt=fmt):
                pypasmo.output_bytes(asm(src), fmt, "")

    def test_snapshot_128k_bank_5_and_2(self):
        # banks 5 and 2 are also at 4000h / 8000h: BANK 5 / BANK 2 code goes into them
        src = (" org 8000h\nstart: ret\n bank 5\n org 0C100h\n db 55h\n bank 2\n org 0C001h\n db 22h\n"
               " end start\n")
        sna = pypasmo.output_bytes(asm(src), "sna-128k", "")
        self.assertEqual((sna[27 + 0x100], sna[27 + 0x4001], sna[27 + 0x4000]), (0x55, 0x22, 0xC9))
        pages = self.unz80(pypasmo.output_bytes(asm(src), "z80-128k", ""))[1]
        self.assertEqual((pages[8][0x100], pages[5][1]), (0x55, 0x22))
        # the same byte twice (8000h and BANK 2 at C000h) is an error
        with self.assertRaises(pypasmo.AsmError):
            pypasmo.output_bytes(asm(" org 8000h\n ret\n bank 2\n org 0C000h\n db 1\n"), "sna-128k", "")

    def test_z80_128k_is_the_state_of_the_sna_128k(self):
        src = (" org 8000h\nstart: ret\n org 0C000h\n db 0Ch\n bank 1\n org 0C000h\n db 11h\n"
               " bank 7\n org 0C001h\n db 77h\n end start\n")
        a = asm(src)
        sna = pypasmo.output_bytes(a, "sna-128k", "")
        head, pages = self.unz80(pypasmo.output_bytes(a, "z80-128k", ""))
        head48 = self.unz80(pypasmo.output_bytes(asm(" org 8000h\nstart: ret\n end start\n"), "z80-48k", ""))[0]
        self.assertEqual((len(head), head[30], head[34], head[35]), (86, 54, 4, 0x10))   # 128K, 7FFDh
        self.assertEqual(head[:30], head48[:30])                          # the same registers
        self.assertEqual(head[32:34], h("00 80"))                         # PC
        self.assertEqual(sorted(pages), list(range(3, 11)))               # page = bank + 3
        k = 0x4000
        banks = {5: sna[27:27 + k], 2: sna[27 + k:27 + 2 * k], 0: sna[27 + 2 * k:27 + 3 * k]}
        rest = 27 + 3 * k + 4
        banks.update({b: sna[rest + i * k:rest + (i + 1) * k] for i, b in enumerate((1, 3, 4, 6, 7))})
        for bank, data in banks.items():
            self.assertEqual(pages[bank + 3], data, bank)
        self.assertEqual((pages[3][0], pages[4][0], pages[10][1]), (0x0C, 0x11, 0x77))

    def test_z80_compression(self):
        c = pypasmo.z80_compress
        self.assertEqual(c(bytes(6) + b"A"), h("ED ED 06 00 41"))        # the example of the format
        self.assertEqual(c(bytes(4)), bytes(4))                           # 4 times: not compressed
        self.assertEqual(c(h("ED ED")), h("ED ED 02 ED"))                 # ED ED always compressed
        self.assertEqual(c(h("ED") + bytes(5)), h("ED 00 00 00 00 00"))   # the byte after one ED as it is
        self.assertEqual(c(bytes(300)), h("ED ED FF 00 ED ED 2D 00"))     # at most 255 at once

    def test_z80_is_the_state_of_the_sna(self):
        a = asm(" org 8000h\nstart: ld a,2\n call 1601h\n ret\n end start\n")
        sna = pypasmo.output_bytes(a, "sna-48k", "")
        head, pages = self.unz80(pypasmo.output_bytes(a, "z80-48k", ""))
        self.assertEqual((len(head), head[30], head[34]), (86, 54, 0))   # version 3, 48K
        self.assertEqual(sorted(pages), [4, 5, 8])
        self.assertEqual(pages[8] + pages[4] + pages[5], sna[27:])        # the same RAM
        w = lambda b, i: b[i] | b[i + 1] << 8  # noqa: E731
        self.assertEqual(w(head, 6), 0)                                   # version 2/3: PC at 32
        self.assertEqual(w(head, 32), 0x8000)                             # PC
        self.assertEqual(w(head, 8), w(sna, 23) + 2)                      # SP (.sna has PC on the stack)
        pairs = [(0, 22), (1, 21), (10, 0), (21, 8), (22, 7)]             # A F I A' F'
        pairs += [(i, j) for k, m in ((2, 13), (4, 9), (13, 11), (15, 5), (17, 3), (19, 1), (23, 15), (25, 17))
                  for i, j in ((k, m), (k + 1, m + 1))]                   # BC HL DE BC' DE' HL' IY IX
        for i, j in pairs:
            self.assertEqual(head[i], sna[j], i)
        self.assertEqual(head[11] | (head[12] & 1) << 7, sna[20])         # R
        self.assertEqual(head[12] >> 1 & 7, sna[26])                      # border
        self.assertEqual((head[27], head[28], head[29] & 3), (1, 1, sna[25]))   # EI, IM 1


class DebugSymbols(unittest.TestCase):
    """--dbgsym-list: list file for DeZog (VS Code), its "revEng" format."""
    SRC = (" org 8000h\nport equ 0FEh\nv defl 1\nstart: ld a,1\n.loop: djnz .loop\n proc\n local l1\n"
           "l1: nop\n endp\ndata: db 1,2,3,4,5,6,7,8\nlast:\n")

    @staticmethod
    def dezog_parse(text):
        """What DeZog reads from the file: ({label: value}, {address: byte count}). The
        regular expressions are those of DeZog src/labels/reverseengineeringlabelparser.ts."""
        labels, sizes, last = {}, {}, ""
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith((";", "//")):
                continue
            m = re.match(r"^\s*([a-z_][\w.]*):\s*EQU\s+([^;]+)", line, re.I)
            if m:
                labels[m.group(1)] = int(m.group(2)) & 0xFFFF
                continue
            m = re.match(r"^(([\da-f]+)(\.(\w+))?\s*)", line, re.I)
            assert m, f"DeZog ignores the line: {line}"
            addr, rest, n = int(m.group(2), 16), line[m.end():], 0
            b = re.match(r"^([\da-f][\da-f]\s)", rest, re.I)
            while b:
                n, rest = n + 1, rest[b.end():]
                b = re.match(r"^([\da-f][\da-f]\s)", rest, re.I)
            m = re.match(r"^\s*(\.?[a-z_][\w.]*):", rest, re.I)
            if m:
                name = m.group(1)
                labels[last + name if name.startswith(".") else name] = addr
                last = last if name.startswith(".") else name
                rest = rest[m.end():]
            if n == 0 and re.match(r"^\s*([a-z]+)", rest, re.I):
                n = 1                                    # DeZog: an instruction is 1 byte at least
            sizes[addr] = sizes.get(addr, 0) + n
        return labels, sizes

    def test_dezog_list(self):
        text = pypasmo.list_dbgsym_text(asm(self.SRC, predefined={"X": 1}))
        labels, sizes = self.dezog_parse(text)
        # labels and EQU; no DEFL, -E symbols or LOCAL / autolocal names
        self.assertEqual(labels, {"port": 0xFE, "start": 0x8000, "start.loop": 0x8002, "data": 0x8005,
                                  "last": 0x800D})
        self.assertEqual(sizes, {0x8000: 2, 0x8002: 2, 0x8004: 1, 0x8005: 6, 0x800B: 2, 0x800D: 0})
        self.assertIn("8000 3E 01  start: ; start: ld a,1\n", text)    # the source line as a comment
        self.assertIn("; org 8000h\n", text)

    def test_source_comments_do_not_break_the_file(self):
        # /* would start a multi-line comment in DeZog
        text = pypasmo.list_dbgsym_text(asm(" org 8000h\n nop ; a /* b\nx: nop\n"))
        self.assertEqual(self.dezog_parse(text)[0], {"x": 0x8001})
        self.assertNotIn("/*", text)

    def test_not_with_bank(self):
        with self.assertRaises(pypasmo.AsmError):
            pypasmo.list_dbgsym_text(asm(" bank 1\n org 0C000h\n nop\n"))

    @staticmethod
    def sld_parse(text, paged=False):
        """What DeZog reads from an SLD file (the fields of sjasmplussldlabelparser.ts):
        (Z data, {address: (file, line)} of T lines, {label: value} of L lines);
        paged: the keys of T lines and the values of labels are (page, address)."""
        lines = text.split("\n")
        assert lines[0].split("|")[1:3] == ["SLD.data.version", "1"], lines[0]
        z, trace, labels = None, {}, {}
        for line in lines[1:]:
            f = line.rstrip().split("|")
            if len(f) < 8 or f[0] == "":
                continue
            if f[6] == "Z":
                z = f[7]
            elif f[6] == "T":
                assert int(f[4]) >= 0                        # DeZog: assert(bank >= 0)
                trace[(int(f[4]), int(f[5])) if paged else int(f[5])] = (f[0], int(f[1]))
            elif f[6] == "L":
                labels[f[7].split(",")[1]] = (int(f[4]), int(f[5])) if paged else int(f[5])
        return z, trace, labels

    def test_sld(self):
        src = (" org 8000h\nport equ 0FEh\nstart: ld a,1\n.loop: djnz .loop\n include \"inc.asm\"\n ret\n"
               "mac macro\n inc hl\n endm\n mac\n")
        with tempfile.TemporaryDirectory() as d:
            Path(d, "p.asm").write_text(src, encoding="utf-8")
            Path(d, "inc.asm").write_text("sub1: nop\n", encoding="utf-8")
            a = pypasmo.Assembler()
            a.assemble(str(Path(d, "p.asm")))
            text = pypasmo.sld_text(a)
        z, trace, labels = self.sld_parse(text)
        # DeZog takes these four values as the ZX48K memory model
        self.assertEqual(z, "pages.size:16384,pages.count:4,slots.count:4,slots.adr:0,16384,32768,49152")
        where = {addr: (Path(f).name, n) for addr, (f, n) in trace.items()}
        self.assertEqual(where, {0x8000: ("p.asm", 3), 0x8002: ("p.asm", 4), 0x8004: ("inc.asm", 1),
                                 0x8005: ("p.asm", 6), 0x8006: ("p.asm", 10)})   # a macro: the call line
        self.assertEqual(labels, {"port": 0xFE, "start": 0x8000, "start.loop": 0x8002, "sub1": 0x8004})
        self.assertIn("||K|KEYWORDS|WPMEM,LOGPOINT,ASSERTION", text)

    def test_sld_128k(self):
        # with BANK: the ZX128K memory model, the page of an address is its RAM bank
        src = (" org 8000h\nstart: call 0C000h\n ret\n org 6000h\nram5: nop\n"
               " bank 1\n org 0C000h\nb1: ld a,1\n ret\n"
               " bank 3\n org 0C000h\nb3: ld a,3\n ret\nn equ 5\n")
        z, trace, labels = self.sld_parse(pypasmo.sld_text(asm(src)), paged=True)
        self.assertEqual(z, "pages.size:16384,pages.count:8,slots.count:4,slots.adr:0,16384,32768,49152")
        self.assertEqual({k: n for k, (f, n) in trace.items()},
                         {(2, 0x8000): 2, (2, 0x8003): 3, (5, 0x6000): 5, (1, 0xC000): 8,
                          (1, 0xC002): 9, (3, 0xC000): 12, (3, 0xC002): 13})
        self.assertEqual(labels, {"start": (2, 0x8000), "ram5": (5, 0x6000), "b1": (1, 0xC000),
                                  "b3": (3, 0xC000), "n": (-1, 5)})

    def test_sld_wpmem_logpoint_assertion(self):
        # comments with the keywords: K lines with the address ($) of the line, the comment
        # from ';' (DeZog takes the text after ';'); other comments are left out
        src = (" org 8000h\nstart: ld a,1 ; ASSERTION A == 1\n ; LOGPOINT [g] A=${A}\n nop\n"
               "buf: defs 2 ; WPMEM\n ret ; just a comment\n")
        k = [line.split("|") for line in pypasmo.sld_text(asm(src)).splitlines()
             if line.split("|")[6:7] == ["K"] and line.split("|")[0]]
        self.assertEqual([(int(f[1]), int(f[4]), int(f[5]), f[7]) for f in k],
                         [(2, 2, 0x8000, "; ASSERTION A == 1"), (3, 2, 0x8002, "; LOGPOINT [g] A=${A}"),
                          (5, 2, 0x8003, "; WPMEM")])

    def test_sld_comment_after_strings(self):
        # the comment starts at the first ';' outside of strings (and AF')
        src = (' org 8000h\n db ";", 1 ; WPMEM\n db "; WPMEM"\n db \'"\', ";" ; WPMEM, 1\n'
               " ex af,af' ; WPMEM\n db \"a\\\";\" ; WPMEM\n")
        k = [line.split("|") for line in pypasmo.sld_text(asm(src)).splitlines()
             if line.split("|")[6:7] == ["K"] and line.split("|")[0]]
        self.assertEqual([(int(f[1]), f[7]) for f in k],
                         [(2, "; WPMEM"), (4, "; WPMEM, 1"), (5, "; WPMEM"), (6, "; WPMEM")])

    def test_sld_option(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text(" org 8000h\nstart: ret\n", encoding="utf-8")
            rc = run_main("--dbgsym-sld", str(Path(d, "p.sld")), str(src), str(Path(d, "p.bin")))[0]
            self.assertEqual(rc, 0)
            z, trace, labels = self.sld_parse(Path(d, "p.sld").read_text(encoding="utf-8"))
            self.assertEqual((list(trace), labels), ([0x8000], {"start": 0x8000}))

    def test_sld_path_not_latin1(self):
        # a folder with a letter outside latin-1: the path in UTF-8 (DeZog reads UTF-8)
        with tempfile.TemporaryDirectory() as d:
            Path(d, "\u010dj").mkdir()
            src = Path(d, "\u010dj", "p.asm")
            src.write_text(" org 8000h\nstart: ret\n", encoding="utf-8")
            rc, _, err = run_main("--dbgsym-sld", str(Path(d, "p.sld")), str(src), str(Path(d, "p.bin")))
            self.assertEqual(rc, 0, err)
            self.assertIn("\u010dj/p.asm|2|".encode("utf-8"), Path(d, "p.sld").read_bytes())

    def test_sld_same_name_in_two_folders(self):
        # main/a.asm includes inc/a.asm: the T lines of the included file point to it
        with tempfile.TemporaryDirectory() as d:
            Path(d, "main").mkdir()
            Path(d, "inc").mkdir()
            Path(d, "main", "a.asm").write_text(' org 8000h\n include "../inc/a.asm"\n ret\n', encoding="utf-8")
            Path(d, "inc", "a.asm").write_text(" nop\n nop\n", encoding="utf-8")
            a = pypasmo.Assembler()
            a.assemble(str(Path(d, "main", "a.asm")))
            _, trace, _ = self.sld_parse(pypasmo.sld_text(a))
        where = {addr: (Path(f).parent.name, n) for addr, (f, n) in trace.items()}
        self.assertEqual(where, {0x8000: ("inc", 1), 0x8001: ("inc", 2), 0x8002: ("main", 3)})

    def test_no_output_file_on_error(self):
        # an error of a symbol file (--dbgsym-list does not support BANK): no file written
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text(" org 8000h\n ret\n bank 1\n org 0C000h\n nop\n", encoding="utf-8")
            rc, _, err = run_main("--sna-128k", str(src), str(Path(d, "p.sna")), str(Path(d, "p.sym")),
                                  "--dbgsym-list", str(Path(d, "p.list")))
            self.assertEqual(rc, 1)
            self.assertIn("--dbgsym-list", err)
            self.assertEqual(sorted(f.name for f in Path(d).iterdir()), ["p.asm"])

    def test_option(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text(" org 8000h\nstart: ret\n", encoding="utf-8")
            rc = run_main("--dbgsym-list", str(Path(d, "p.list")), str(src), str(Path(d, "p.bin")))[0]
            self.assertEqual(rc, 0)
            old = run_main("--dbgsym-dezog", str(Path(d, "q.list")), str(src), str(Path(d, "q.bin")))[0]
            self.assertNotEqual(old, 0)                 # the old name (before 0.2.0 was published)
            self.assertEqual(self.dezog_parse(Path(d, "p.list").read_text(encoding="utf-8")),
                             ({"start": 0x8000}, {0x8000: 1}))


class Listing(unittest.TestCase):
    def test_tstates(self):
        # Zilog Z80 CPU User Manual; all 798 instructions of all.asm and undoc.asm were also
        # checked against the Z80 simulator of SkoolKit
        cases = {"nop": "4", "ld a,b": "4", "ld a,(hl)": "7", "ld (hl),5": "10", "inc (hl)": "11",
                 "ld hl,1234h": "10", "ld hl,(1234h)": "16", "ld a,(1234h)": "13", "add hl,de": "11",
                 "inc de": "6", "jr $": "12", "jr nz,$": "12/7", "djnz $": "13/8", "jp 0": "10",
                 "jp z,0": "10", "call 0": "17", "call c,0": "17/10", "ret": "10", "ret nc": "11/5",
                 "rst 38h": "11", "push bc": "11", "pop af": "10", "ex (sp),hl": "19",
                 "jp (hl)": "4", "ld sp,hl": "6", "out (0FEh),a": "11", "halt": "4",
                 "rlc b": "8", "bit 0,(hl)": "12", "set 7,(hl)": "15",
                 "in a,(c)": "12", "sbc hl,bc": "15", "ld (1234h),de": "20", "neg": "8",
                 "retn": "14", "im 1": "8", "ld a,i": "9", "rld": "18", "ldi": "16", "ldir": "21/16",
                 "ld ix,0": "14", "add ix,bc": "15", "push iy": "15", "jp (ix)": "8", "ex (sp),ix": "23",
                 "ld a,(ix+1)": "19", "ld (iy+2),3": "19", "inc (ix+0)": "23", "add a,(iy-1)": "19",
                 "ld ixh,5": "11", "ld a,ixl": "8", "bit 1,(ix+1)": "20", "rr (iy+4)": "23"}
        for src, t in cases.items():
            with self.subTest(src):
                a = asm(f" {src}\n")
                self.assertEqual([x[2] for x in a.listing if x[1]], [t])

    def test_tstates_comment_at_line_end(self):
        a = asm(" org 8000h\nlbl: ld a,1\n db 2\n jr nz,$ ; loop\n")
        lines = pypasmo.listing_text(a).splitlines()
        self.assertEqual(lines[1], "8000  3E 01               lbl: ld a,1  ;7T")
        self.assertEqual(lines[2], "8002  02                   db 2")    # no T-states for data
        self.assertEqual(lines[3], "8003  20 FE                jr nz,$ ; loop  ;12/7T")

    def test_routine_total(self):
        # a label, instructions without jumps, RET: the sum after the RET line
        src = (" org 8000h\nscr: ld a,b\n and 18h\n or 40h\n ld h,a\n ret\n"     # 4+7+7+4+10 = 32
               "loop: ld a,1\n jr loop\n ret\n"                                  # a jump: no sum
               "data: nop\n db 1\n ret\n"                                        # data: no sum
               "cond: ret z\n ret\n"                                             # RET cc: no sum
               "a1: nop\na2: nop\n ret\n"                                        # from the last label
               "mac macro\n inc hl\n endm\nwm: mac\n mac\n ret\n")               # macros count: 6+6+10
        text = pypasmo.listing_text(asm(src))
        totals = [line.strip() for line in text.splitlines() if "from the label to RET" in line]
        self.assertEqual(totals, ["; scr: 32T from the label to RET", "; a2: 14T from the label to RET",
                                  "; wm: 22T from the label to RET"])
        self.assertIn(" ret  ;10T\n      ; scr: 32T from the label to RET\n", text)


class Examples(unittest.TestCase):
    """The ready files in output_formats/zx_spectrum_results/, made from output_formats/zx_spectrum/
    (tried in a ZX Spectrum emulator). hello_spectrum.tap
    and .tzx are also byte for byte the output of the real Pasmo 0.5.5; --tapbas128 is
    not in Pasmo 0.5.5, so hello_spectrum128.tap only guards against changes."""
    SRC = OUTPUT_FORMATS / "zx_spectrum"
    RESULTS = OUTPUT_FORMATS / "zx_spectrum_results"

    def check(self, src, fmt, name, expected):
        a = pypasmo.Assembler()
        a.assemble(self.SRC / src)
        self.assertEqual(pypasmo.output_bytes(a, fmt, name), (self.RESULTS / expected).read_bytes())

    def test_hello_msx_cas(self):
        # tried by the author in WebMSX: BLOAD "CAS:",R prints the text and returns (Ok)
        a = pypasmo.Assembler()
        a.assemble(OUTPUT_FORMATS / "msx" / "hello_msx.asm")
        self.assertEqual(pypasmo.output_bytes(a, "cas-msx", "hello"),
                         (OUTPUT_FORMATS / "msx_results" / "hello_msx.cas").read_bytes())

    def test_hello_msx_dsk(self):
        a = pypasmo.Assembler()
        a.assemble(OUTPUT_FORMATS / "msx" / "hello_msx.asm")
        self.assertEqual(pypasmo.output_bytes(a, "dsk-msx", "hello"),
                         (OUTPUT_FORMATS / "msx_results" / "hello_msx.dsk").read_bytes())

    def test_hello_msx_rom(self):
        # tried by the author in WebMSX: the text at start-up, a key starts BASIC
        a = pypasmo.Assembler()
        a.assemble(OUTPUT_FORMATS / "msx" / "hello_msx_rom.asm")
        self.assertEqual(pypasmo.output_bytes(a, "rom-msx", ""),
                         (OUTPUT_FORMATS / "msx_results" / "hello_msx_rom.rom").read_bytes())

    def test_hello_other_machines(self):
        # Jupiter Ace and Z 1013: the code checked in the Z80 simulator of SkoolKit (the
        # texts in the video RAM); SMS, KC 85 and Z 1013 tried by the author in an emulator;
        # hello_trs80.cmd is the same as the real Pasmo 0.5.5 makes with --trs
        for src, fmt, name, result in (("hello_ace.asm", "tap-ace", "hello", "hello_ace.tap"),
                                       ("hello_z1013.asm", "z80-z1013", "hello_z1013.z80", "hello_z1013.z80"),
                                       ("hello_kc85.asm", "kcc-kc85", "hello_kc85.kcc", "hello_kc85.kcc"),
                                       ("hello_sms.asm", "rom-sms", "", "hello_sms.sms"),
                                       ("hello_gg.asm", "rom-gg", "", "hello_gg.gg"),
                                       ("hello_trs80.asm", "trs", "", "hello_trs80.cmd"),
                                       ("hello_trs80_tape.asm", "cas-trs", "hello", "hello_trs80.cas"),
                                       ("hello_coleco.asm", "rom-coleco", "", "hello_coleco.col"),
                                       ("hello_pcw.asm", "dsk-pcw", "hello", "hello_pcw.dsk")):
            with self.subTest(src):
                a = pypasmo.Assembler()
                a.assemble(OUTPUT_FORMATS / "other" / src)
                self.assertEqual(pypasmo.output_bytes(a, fmt, name),
                                 (OUTPUT_FORMATS / "other_results" / result).read_bytes())

    def test_hello_cpc(self):
        # Amstrad CPC: an Amsdos file and two tapes (RUN "", with a Basic loader)
        a = pypasmo.Assembler()
        a.assemble(OUTPUT_FORMATS / "cpc" / "hello_cpc.asm")
        for fmt, result in (("amsdos", "hello_cpc.bin"), ("cdt", "hello_cpc.cdt"), ("cdtbas", "hello_cpc_bas.cdt"),
                            ("dsk-cpc", "hello_cpc.dsk"), ("sna-cpc6128", "hello_cpc6128.sna"),
                            ("sna-cpc464", "hello_cpc464.sna")):
            with self.subTest(fmt):
                self.assertEqual(pypasmo.output_bytes(a, fmt, "hello"),
                                 (OUTPUT_FORMATS / "cpc_results" / result).read_bytes())

    def test_hello_zx81(self):
        # the code checked in the Z80 simulator of SkoolKit (the texts in the display file)
        a = pypasmo.Assembler()
        a.assemble(OUTPUT_FORMATS / "zx81" / "hello_zx81.asm")
        self.assertEqual(pypasmo.output_bytes(a, "p-zx81", ""),
                         (OUTPUT_FORMATS / "zx81_results" / "hello_zx81.p").read_bytes())

    def test_hello_spectrum_plus3_disk(self):
        self.check("hello_spectrum.asm", "dsk-plus3", "hello", "hello_spectrum.dsk")

    def test_hello_spectrum(self):
        self.check("hello_spectrum.asm", "tapbas", "hello", "hello_spectrum.tap")
        self.check("hello_spectrum.asm", "tzxbas", "hello", "hello_spectrum.tzx")
        # loaded and run in the SkoolKit simulator (tap2sna)
        self.check("hello_spectrum.asm", "pzx-wloader-48k", "hello", "hello_spectrum.pzx")

    def test_hello_spectrum_pzx_bytes(self):
        pzx = (self.RESULTS / "hello_spectrum.pzx").read_bytes()
        # PZXT 1.0, PULS of a header (8000h + 8063 x 2168 T, 667, 735), DATA of 19 bytes
        # (152 bits + bit 31) with the loader header "loader"
        self.assertEqual(pzx[:42], b"PZXT" + h("02 00 00 00 01 00") + b"PULS" + h("08 00 00 00 7F 9F 78 08 9B 02 DF 02")
                         + b"DATA" + h("23 00 00 00 98 00 00 80 B1 03 02 02"))
        self.assertEqual(pzx[42:50], h("57 03 57 03 AE 06 AE 06"))   # bit 0, bit 1
        self.assertEqual(pzx[50:52], h("00 00"))                     # flag 0, type 0 = Program
        self.assertEqual(pzx[52:58], b"loader")
        # the tap blocks 19 (loader header) + 73 (Basic) + 19 (CODE header) + 140 (code)
        # bytes, each + 52 bytes of PULS, DATA and PAUS headers, + 10 of PZXT
        self.assertEqual(len(pzx), 10 + 19 + 73 + 19 + 140 + 4 * 52)
        tap = (self.RESULTS / "hello_spectrum.tap").read_bytes()
        self.assertEqual(pzx.count(b"PAUS" + h("04 00 00 00 E0 67 35 00")), 4)        # 1 s
        self.assertIn(tap[-140:], pzx)                                  # the code block

    def test_hello_spectrum_sna(self):
        # run in the SkoolKit simulator: prints the text with the ROM, flashes the border
        self.check("hello_spectrum.asm", "sna-48k", "", "hello_spectrum.sna")
        self.check("hello_spectrum.asm", "z80-48k", "", "hello_spectrum.z80")

    def test_hello_spectrum128(self):
        self.check("hello_spectrum128.asm", "tapbas128", "hello_spectrum128.tap", "hello_spectrum128.tap")
        self.check("hello_spectrum128.asm", "tzx-wloader-128k", "hello_spectrum128.tzx", "hello_spectrum128.tzx")
        self.check("hello_spectrum128.asm", "pzx-wloader-128k", "hello_spectrum128.pzx", "hello_spectrum128.pzx")
        # the .tzx / .pzx hold the blocks of the .tap: 1 loader + 2 bank blocks (header + data)
        tap = (self.RESULTS / "hello_spectrum128.tap").read_bytes()
        tzx = (self.RESULTS / "hello_spectrum128.tzx").read_bytes()
        self.assertEqual(tzx[:10], b"ZXTape!\x1A\x01\x0D")
        self.assertEqual(tzx[10:].replace(h("10 E8 03"), b""), tap)
        self.assertEqual(tzx.count(h("10 E8 03")), 2 * (1 + 3))        # loader, banks 1, 2, 3
        back, tags = Outputs.pzx_to_tap((self.RESULTS / "hello_spectrum128.pzx").read_bytes())
        self.assertEqual(back, tap)
        self.assertEqual(tags, ["PZXT"] + ["PULS", "DATA", "PAUS"] * 8)
        self.check("hello_spectrum128.asm", "sna-128k", "", "hello_spectrum128.sna")
        self.check("hello_spectrum128.asm", "z80-128k", "", "hello_spectrum128.z80")


class MultipleErrors(unittest.TestCase):
    """pypasmo reports up to 10 errors of one assembly (Pasmo stops at the first)."""

    def errors(self, src, **opts):
        with self.assertRaises(pypasmo.AsmError) as cm:
            asm(src, **opts)
        return cm.exception.errors

    def test_all_errors_are_reported(self):
        errs = self.errors(" ld a,x1\n nop\n ld q,1\n ld a,(\nok: ld b,x2\n")
        self.assertEqual([e.split(":")[1] for e in errs], ["1", "3", "4", "5"])
        self.assertIn("undefined symbol x1", errs[0])
        self.assertIn("ld b,x2", errs[3])                   # the source line follows the message
        # str() has all of them, one AsmError for the Python API
        with self.assertRaises(pypasmo.AsmError) as cm:
            asm(" ld a,x1\n ld a,x2\n")
        self.assertIn("x1", str(cm.exception))
        self.assertIn("x2", str(cm.exception))

    def test_at_most_10(self):
        errs = self.errors(" ld q,1\n" * 15)
        self.assertEqual(len(errs), 10)
        self.assertIn("stopped after 10 errors", errs[-1])

    def test_errors_after_an_error_do_not_move_the_code(self):
        # the label after the bad lines has the same address in all passes: no new errors
        errs = self.errors(" ld q,1\n jp later\n ld a,(\nlater: ret\n")
        self.assertEqual(len(errs), 2)

    def test_error_in_a_block_line_stops(self):
        # a broken IF / MACRO / ... would only bring follow-up errors
        for src in (" if\n nop\n endif\n ld q,1\n", "mac macro\n ld a,1\n ld q,1\n",   # missing ENDM
                    " rept\n nop\n endm\n ld q,1\n", " endif\n ld q,1\n"):
            with self.subTest(src):
                self.assertEqual(len(self.errors(src)), 1)
        # errors before it are kept
        self.assertEqual(len(self.errors(" ld q,1\n if\n nop\n endif\n ld q,1\n")), 2)

    def test_command_line_prints_each_error(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "e.asm")
            src.write_text(" ld a,x1\n nop\n ld a,x2\n", encoding="utf-8")
            rc, out, err = run_main(str(src), str(Path(d, "e.bin")))
        self.assertEqual(rc, 1)
        self.assertEqual(err.count("ERROR: e.asm:"), 2, err)
        self.assertIn("ERROR: e.asm:3: undefined symbol x2", err)


class CommandLine(unittest.TestCase):
    SRC = " org 8000h\nstart: ld a,1\n ret\n public start\n end start\n"

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text(self.SRC, encoding="utf-8")
            for fmt in pypasmo.FORMATS:
                if fmt in ("prl", "rom-msx", "p-zx81", "rom-sms", "rom-gg", "dsk-msx",   # no ORG, ROM header,
                           "dsk-pcw", "rom-coleco"):            # ORG 16514 / 0, from 8800h, ORG 100h
                    continue
                rc, _, err = run_main(f"--{fmt}", "--name", "p", str(src), str(Path(d, f"p.{fmt}")),
                                      str(Path(d, "p.sym")), str(Path(d, "p.pub")))
                self.assertEqual(rc, 0, err)
            self.assertEqual(run_main("--lst", str(Path(d, "p.lst")), str(src), str(Path(d, "p.bin")))[0], 0)
            self.assertEqual(Path(d, "p.bin").read_bytes(), h("3E 01 C9"))
            self.assertTrue(Path(d, "p.hex").read_text().startswith(":03800000"))
            self.assertEqual(Path(d, "p.tap").read_bytes()[4:14], b"p         ")
            self.assertEqual(len(Path(d, "p.plus3dos").read_bytes()), 256)
            self.assertIn("EQU 08000H", Path(d, "p.sym").read_text())
            self.assertIn("start", Path(d, "p.pub").read_text())
            self.assertIn("ld a,1", Path(d, "p.lst").read_text(encoding="utf-8"))

    def test_public_option(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text("first: nop\nsecond: nop\n public second\n", encoding="utf-8")
            rc, _, _ = run_main("--public", str(src), str(Path(d, "p.bin")), str(Path(d, "p.sym")))
            self.assertEqual(rc, 0)
            self.assertEqual(Path(d, "p.sym").read_text(), "second\t\tEQU 00001H\n")

    def test_version_and_help(self):
        rc, out, _ = run_main("--version")
        self.assertEqual(rc, 0)
        self.assertIn(pypasmo.__version__, out)
        rc, out, _ = run_main("--help")
        self.assertEqual(rc, 0)
        self.assertIn("Usage", out)

    def test_extra_arguments_warning(self):
        # like Pasmo: more than 4 file names (source, output, symbols, publics) is a warning
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text(self.SRC, encoding="utf-8")
            names = [str(Path(d, n)) for n in ("p.bin", "p.sym", "p.pub", "x1", "x2")]
            rc, _, err = run_main(str(src), *names)
            self.assertEqual(rc, 0, err)
            self.assertIn("warning: extra arguments ignored: ", err)
            self.assertFalse(Path(d, "x1").exists())

    def test_spectrum_format_names(self):
        # aliases with the machine in the name; the same file as the Pasmo option
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "p.asm")
            src.write_text(self.SRC, encoding="utf-8")
            for alias, fmt in (("--tap-48k", "--tap"), ("--tzx-48k", "--tzx"),
                               ("--tap-wloader-48k", "--tapbas"), ("--tzx-wloader-48k", "--tzxbas"),
                               ("--tap-128k", "--tap128"), ("--tap-wloader-128k", "--tapbas128"),
                               ("--cdt-wloader", "--cdtbas")):
                with self.subTest(alias):
                    self.assertEqual(run_main(alias, str(src), str(Path(d, "a.out")))[0], 0)
                    self.assertEqual(run_main(fmt, str(src), str(Path(d, "b.out")))[0], 0)
                    self.assertEqual(Path(d, "a.out").read_bytes(), Path(d, "b.out").read_bytes())
            for opt in ("--sna-48k", "--z80-48k", "--pzx-48k", "--pzx-wloader-48k", "--tzx-128k",
                        "--tzx-wloader-128k", "--pzx-128k", "--pzx-wloader-128k"):
                with self.subTest(opt):
                    self.assertEqual(run_main(opt, str(src), str(Path(d, "c.out")))[0], 0)
            # the old name of --sna-48k is gone (pypasmo is not published yet)
            for opt in ("--sna",):
                with self.subTest(opt):
                    self.assertNotEqual(run_main(opt, str(src), str(Path(d, "c.out")))[0], 0)

    def test_err_option(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "e.asm")
            src.write_text(" ld a,\n", encoding="utf-8")
            rc, out, err = run_main(str(src), str(Path(d, "e.bin")))
            self.assertEqual((rc, out), (1, ""))
            self.assertIn("ERROR", err)
            rc, out, err = run_main("--err", str(src), str(Path(d, "e.bin")))
            self.assertEqual((rc, err), (1, ""))
            self.assertIn("ERROR", out)

    def test_equ_option(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "e.asm")
            src.write_text(" db V1, V2\n", encoding="utf-8")
            out = str(Path(d, "e.bin"))
            self.assertEqual(run_main("-E", "V1=12h", "--equ", "V2", str(src), out)[0], 0)
            self.assertEqual(Path(out).read_bytes(), h("12 FF"))
            for bad in ("V1=V2", "V1=1+1", "1V=2", "=5"):      # Pasmo: only NAME or NAME=number
                with self.subTest(bad):
                    rc, _, err = run_main("-E", bad, str(src), out)
                    self.assertEqual(rc, 2)
                    self.assertNotIn("Traceback", err)

    def test_include_after_label_with_the_same_word(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "inc.asm").write_text(" db 1\n", encoding="utf-8")
            Path(d, "data.bin").write_bytes(b"\x02")
            src = Path(d, "m.asm")
            src.write_text(f'my_include: include "{Path(d, "inc.asm").as_posix()}"\n'
                           f'xincbin: incbin "{Path(d, "data.bin").as_posix()}"\n', encoding="utf-8")
            a = pypasmo.Assembler()
            a.assemble(src)
            self.assertEqual(pypasmo.image(a.mem)[1], h("01 02"))

    def test_pzx_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "z.asm")
            src.write_text(" org 5D00h\nst: ret\n end st\n", encoding="utf-8")
            out = Path(d, "z.pzx")
            rc, _, err = run_main("--pzx-wloader-48k", "--name", "zname", str(src), str(out))
            self.assertEqual(rc, 0, err)
            self.assertIn("warning: --pzx-wloader-48k: the Basic loader does CLEAR", err)
            data = out.read_bytes()
            self.assertTrue(data.startswith(b"PZXT"))
            self.assertIn(b"zname     ", data)                           # the CODE header
            self.assertEqual(run_main("--pzx-wloader-48k", "--werror", str(src), str(out))[0], 1)

    def test_werror_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "w.asm")
            src.write_text(" jr $\n", encoding="utf-8")
            self.assertEqual(run_main("--w8080", str(src), str(Path(d, "w.bin")))[0], 0)
            self.assertEqual(run_main("--w8080", "--werror", str(src), str(Path(d, "w.bin")))[0], 1)


if __name__ == "__main__":
    unittest.main()
