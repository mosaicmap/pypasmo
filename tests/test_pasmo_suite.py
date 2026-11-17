"""Tests with the test files of the original Pasmo 0.5.5 (in tests/pasmo_0.5.5_original_tests, GPL v3, see COPYING).

Main tests: all.asm (every Z80 instruction) and allb.asm (the same with [ ] brackets, in
bracket only mode) must give byte for byte the same as all.check, the binary made by the
original Pasmo. For the other files Pasmo's test_cli.sh only checks that they assemble or
fail as expected; some results are additionally checked here by hand.
"""
import contextlib
import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pypasmo  # noqa: E402

PASMO = HERE / "pasmo_0.5.5_original_tests"
RESULTS = HERE / "pasmo_0.5.5_original_test_results"


def build(name, **opts):
    asm = pypasmo.Assembler(**opts)
    asm.assemble(PASMO / name)
    return asm


def word(asm, addr):
    return asm.mem[addr] | asm.mem[addr + 1] << 8


class BinaryMixin:
    def assertBinary(self, actual, expected):
        if actual == expected:
            return
        n = next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), min(len(actual), len(expected)))
        self.fail(f"differs at offset {n:04X}h: {actual[n:n + 8].hex(' ')} instead of {expected[n:n + 8].hex(' ')} "
                  f"(length {len(actual)}, expected {len(expected)})")


class AllInstructions(BinaryMixin, unittest.TestCase):
    def test_all_asm_matches_pasmo_binary(self):
        lo, data = pypasmo.image(build("all.asm").mem)
        self.assertEqual(lo, 0x100)
        self.assertBinary(data, (PASMO / "all.check").read_bytes())

    def test_allb_asm_bracket_mode_matches_pasmo_binary(self):
        lo, data = pypasmo.image(build("allb.asm", bracket=True).mem)
        self.assertBinary(data, (PASMO / "all.check").read_bytes())

    def test_incbin_reproduces_all_check(self):
        lo, data = pypasmo.image(build("incbin_test.asm").mem)
        self.assertBinary(data, (PASMO / "all.check").read_bytes())


class W8080(unittest.TestCase):
    def test_only8080_part_of_all_asm_has_no_warnings(self):
        # all.asm leaves out every Z80-only instruction when ONLY8080 is defined
        self.assertEqual(build("all.asm", predefined={"ONLY8080": 0xFFFF}, w8080=True).warnings, [])

    def test_all_asm_warnings(self):
        # 453 instructions are left out by ONLY8080; one of them, OUT (n),A, is a valid
        # 8080 instruction that is only grouped with OUT (C),r in all.asm.
        self.assertEqual(len(build("all.asm", w8080=True).warnings), 452)

    def test_black_asm_like_pasmo_test_cli(self):
        # test_cli.sh: --w8080 --werror --equ USEHL --equ USEJP --equ CPC --equ LOOP --equ NODELAY
        build("black.asm", w8080=True, werror=True,
              predefined={k: 0xFFFF for k in ("USEHL", "USEJP", "CPC", "LOOP", "NODELAY")})


class Macros(BinaryMixin, unittest.TestCase):
    def test_tmacro_expansion(self):
        # tmacro.asm checked by hand (pushmany with REPT -1/.SHIFT/EXITM, IRP, nested macros)
        call5 = bytes.fromhex("CD 05 00")
        expected = (bytes.fromhex("F5 C5 D5 E5")                 # pushall3: push af,bc,de,hl
                    + bytes.fromhex("11 23 01")                  # ld de, hello
                    + bytes.fromhex("0E 09") + call5             # bdos 9
                    + bytes.fromhex("1E 0D 0E 02") + call5       # lineend
                    + bytes.fromhex("1E 0A 0E 02") + call5
                    + bytes.fromhex("F1 C1 D1 E1")               # popall2 (irp: pop af,bc,de,hl)
                    + bytes.fromhex("0E 00") + call5             # bdos 0
                    + b"Hello, world.$")
        asm = build("tmacro.asm")
        lo, data = pypasmo.image(asm.mem)
        self.assertEqual(lo, 0x100)
        self.assertBinary(data, expected)
        self.assertEqual(asm.entry, 0x100)                       # end start


class Autolocal(BinaryMixin, unittest.TestCase):
    def test_autolocal_test(self):
        expected = bytes.fromhex("C3 07 00 00 C3 03 00 00 C3 07 00 C3 00 00 3E 2A")
        self.assertBinary(pypasmo.image(build("autolocal_test.asm", alocal=True).mem)[1], expected)

    def test_alocal_asm_jump_targets(self):
        asm = build("alocal.asm", alocal=True)
        self.assertEqual(asm.symbols["start"], 0x100)            # label on ORG
        self.assertEqual(word(asm, 0x101), 0x113)    # jp _hola       -> _hola of the start block
        self.assertEqual(word(asm, 0x114), 0x103)    # ld hl, _exit   -> _exit of the start block
        self.assertEqual(word(asm, 0x120), 0x12E)    # jp z, _exit    -> _exit of showtext
        self.assertEqual(word(asm, 0x12C), 0x11C)    # jp _hola       -> _hola of showtext
        self.assertEqual(word(asm, 0x130), 0x138)    # ld hl, _exit   -> _exit after hola


class Misc(unittest.TestCase):
    def test_reserv_asm(self):
        # identifier with $ (add$) and parentheses that are not an indirection
        asm = build("reserv.asm")
        self.assertEqual(pypasmo.image(asm.mem)[1], bytes.fromhex("00 18 FD 06 01 C6 01 C6 00 F6 01"))
        self.assertEqual(sum("non existent instruction" in w for w in asm.warnings), 4)

    def test_limit64_warns(self):
        self.assertTrue(any("64KB" in w for w in build("limit64.asm").warnings))

    def test_public_test(self):
        asm = build("public_test.asm", bracket=True)
        self.assertEqual(pypasmo.symbol_text(asm, asm.publics), "first\t\tEQU 00003H\nsecond\t\tEQU 00004H\n")


class PasmoResults(BinaryMixin, unittest.TestCase):
    """pasmo_0.5.5_original_test_results/NAME.bin: the --bin output of the real Pasmo 0.5.5 (built
    from pasmo_0.5.5_orig/pasmo-0.5.5_src.tar.gz) for each test source it assembles
    without options."""

    def test_same_binary_as_pasmo(self):
        files = sorted(RESULTS.glob("*.bin"))
        self.assertEqual(len(files), 33)
        for expected in files:
            if expected.stem == "limit64":
                continue                     # see test_limit64_differs_as_documented
            with self.subTest(expected.name):
                asm = build(expected.stem + ".asm")
                self.assertBinary(pypasmo.output_bytes(asm, "bin", ""), expected.read_bytes())

    def test_limit64_differs_as_documented(self):
        # 64 KB of code: Pasmo writes an empty file, pypasmo all 65536 bytes (doc/pasmo-differences.md)
        self.assertEqual((RESULTS / "limit64.bin").read_bytes(), b"")
        self.assertEqual(len(pypasmo.output_bytes(build("limit64.asm"), "bin", "")), 0x10000)


class MustAssemble(unittest.TestCase):
    CASES = ["undoc.asm", "local.asm", "rept_test.asm", "defl_test.asm", "if_test.asm",
             "proc_test.asm", "hilo.asm", "defb.asm", "black.asm",
             # sample programs from the Pasmo package
             "callvers.asm", "echovers.asm", "fill8k.asm", "hellocpc.asm", "hellocpm.asm",
             "hellospec.asm", "hola.asm", "indent.asm", "jumptable.asm", "lee.asm", "mas.asm",
             "protector.asm", "showfcb.asm", "showkeys.asm", "showline.asm", "t86.asm", "test.asm"]

    def test_files(self):
        for name in self.CASES:
            with self.subTest(name):
                build(name)

    def test_macro_asm_without_8080_line(self):
        # macro.asm has .8080, which Pasmo 0.5.5 rejects ("8080 mode not supported");
        # the rest of the file must assemble
        text = (PASMO / "macro.asm").read_text(encoding="latin-1")
        self.assertIn("\n.8080\n", text)
        asm = pypasmo.Assembler()
        asm.assemble(PASMO / "macro.asm", text=text.replace("\n.8080\n", "\n"))
        self.assertEqual(len(asm.mem), 96)

    def test_include_with_search_dir(self):
        build("include_test.asm", include_dirs=[PASMO / "testaux"])

    def test_black_variants(self):
        # the --equ combinations used by Pasmo's test_cli.sh
        for equ in ({}, {"CPC": 1, "NODELAY": 1}, {"CPC": 1, "NODELAY": 1, "WITH_PAD": 3000}):
            with self.subTest(equ):
                build("black.asm", predefined=equ)


class MustFail(unittest.TestCase):
    CASES = ["proc_unclosed_test.asm", "rept_unclosed_test.asm", "rept_exitm_unclosed_test.asm",
             "irp_unclosed_test.asm", "irp_exitm_unclosed_test.asm", "macro_unclosed_test.asm",
             "macro_endp_test.asm", "include_notfound_test.asm", "bad.asm",
             "macro.asm"]                     # .8080: "8080 mode not supported" in Pasmo 0.5.5

    def test_files(self):
        for name in self.CASES:
            with self.subTest(name):
                with self.assertRaises(pypasmo.AsmError):
                    build(name)

    def test_unclosed_if_else(self):
        for name in ("if_unclosed_test.asm", "else_unclosed_test.asm"):
            for cond in (0, 1):
                with self.subTest(f"{name} condition={cond}"):
                    with self.assertRaises(pypasmo.AsmError):
                        build(name, predefined={"condition": cond})

    def test_include_with_extra_args(self):
        with self.assertRaises(pypasmo.AsmError):
            build("include_bad_test.asm", include_dirs=[PASMO / "testaux"])

    def test_autolocal_needs_option(self):
        with self.assertRaises(pypasmo.AsmError):        # _label1 is defined twice
            build("autolocal_test.asm")


class CommandLine(unittest.TestCase):
    """Invalid command lines (like in test_cli.sh) must return a non zero exit code."""

    def run_main(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return pypasmo.main(list(argv))

    def test_bad_usage(self):
        for argv in ([], [str(PASMO / "all.asm")], ["--notavalidoption"], ["-I"], ["--equ"]):
            with self.subTest(argv):
                self.assertNotEqual(self.run_main(*argv), 0)


if __name__ == "__main__":
    unittest.main()
