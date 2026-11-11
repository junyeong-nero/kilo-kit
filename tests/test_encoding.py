"""Encoding MCP file logic: byte-exact round trips and refusals that leave files untouched."""
import codecs
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("encoding_mcp", Path(__file__).resolve().parents[1] / "mcp/encoding/encoding_mcp.py")
enc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enc)


class EncodingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.file = self.root / "src" / "sample.cpp"
        self.file.parent.mkdir()

    def rules(self, encoding, pattern="**/*.cpp"):
        (self.root / enc.RULE_FILE).write_text(json.dumps({"rules": [{"pattern": pattern, "encoding": encoding}]}))

    def test_round_trip_keeps_encoding_bom_and_crlf(self):
        cases = [("utf-8", b"", None), ("utf-8", codecs.BOM_UTF8, None), ("cp949", b"", None),
                 ("euc_kr", b"", "euc-kr"), ("utf-16-le", codecs.BOM_UTF16_LE, None),
                 ("utf-16-be", codecs.BOM_UTF16_BE, None), ("utf-16-le", b"", "utf-16-le")]
        for encoding, bom, rule in cases:
            with self.subTest(encoding=encoding, bom=bom):
                (self.root / enc.RULE_FILE).unlink(missing_ok=True)
                if rule:
                    self.rules(rule)
                self.file.write_bytes(bom + "// 한글 주석\r\nint value = 1;\r\n".encode(encoding))
                self.assertIn("1: // 한글 주석", enc.read_file(self.root, "src/sample.cpp"))
                enc.edit_file(self.root, str(self.file), "한글 주석\nint value = 1;", "수정\nint value = 2;")
                self.assertEqual(self.file.read_bytes(), bom + "// 수정\r\nint value = 2;\r\n".encode(encoding))

    def test_short_cp949_file_without_rule(self):
        # Short Korean CP949 text is where generic detectors misfire; it is never valid UTF-8.
        self.file.write_bytes("확인".encode("cp949"))
        self.assertIn("(cp949)", enc.read_file(self.root, "src/sample.cpp"))
        enc.write_file(self.root, "src/sample.cpp", "똠방각하")
        self.assertEqual(self.file.read_bytes(), "똠방각하".encode("cp949"))

    def test_refusals_leave_bytes_unchanged(self):
        self.file.write_bytes("한글 one one\n".encode("cp949"))
        before = self.file.read_bytes()
        for old, new in [("한글", "😀"), ("one", "two"), ("missing", "x"), ("", "x")]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                enc.edit_file(self.root, "src/sample.cpp", old, new)
        with self.assertRaises(ValueError):
            enc.read_file(self.root, str(self.root.parent / "outside.txt"))
        self.assertEqual(self.file.read_bytes(), before)
        enc.edit_file(self.root, "src/sample.cpp", "one", "two", replace_all=True)
        self.assertEqual(self.file.read_bytes(), "한글 two two\n".encode("cp949"))

    def test_undecodable_and_new_files(self):
        self.file.write_bytes(b"\xff\xff\xfe")
        with self.assertRaisesRegex(ValueError, enc.RULE_FILE):
            enc.read_file(self.root, "src/sample.cpp")
        self.rules("cp949", "src/new/**")
        enc.write_file(self.root, "src/new/a.h", "// 새 파일\n")
        self.assertEqual((self.root / "src/new/a.h").read_bytes(), "// 새 파일\n".encode("cp949"))
        enc.write_file(self.root, "b.txt", "새 파일\n")
        self.assertEqual((self.root / "b.txt").read_bytes(), "새 파일\n".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
