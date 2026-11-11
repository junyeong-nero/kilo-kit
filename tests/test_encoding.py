import codecs
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "tools/encoding/file_io.py"
spec = importlib.util.spec_from_file_location("file_io", MODULE)
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)


class EncodingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.file = self.root / "sample.cpp"

    def rules(self, encoding, pattern="**/*.cpp"):
        (self.root / io.RULE_FILE).write_text(json.dumps({"rules": [{"pattern": pattern, "encoding": encoding}]}))

    def prepare(self, operation="edit", **args):
        return io.prepare({"root": str(self.root), "filePath": str(self.file), "operation": operation, **args})

    def test_roundtrip_encodings_bom_crlf(self):
        for encoding, bom, explicit in [
            ("utf-8", b"", False), ("utf-8", codecs.BOM_UTF8, False),
            ("cp949", b"", True), ("euc_kr", b"", True),
            ("utf-16-le", codecs.BOM_UTF16_LE, False),
            ("utf-16-be", codecs.BOM_UTF16_BE, False), ("utf-16-le", b"", True),
        ]:
            with self.subTest(encoding=encoding, bom=bom):
                (self.root / io.RULE_FILE).unlink(missing_ok=True)
                if explicit:
                    self.rules(encoding)
                old = "// 한글\r\nint value = 1;\r\n"
                self.file.write_bytes(bom + old.encode(encoding))
                original = self.file.read_bytes()
                result = self.prepare("read")
                self.assertIn("한글", result["output"])
                plan = self.prepare(oldString="한글\nint value = 1;", newString="수정\nint value = 2;")
                self.assertEqual(self.file.read_bytes(), original, "prepare must not write")
                io.commit(plan)
                self.assertEqual(self.file.read_bytes(), bom + "// 수정\r\nint value = 2;\r\n".encode(encoding))

    def test_unknown_legacy_rejected(self):
        self.file.write_bytes("한글".encode("cp949"))
        before = self.file.read_bytes()
        for operation, args in [("read", {}), ("edit", {"oldString": "한글", "newString": "수정"}),
                                ("write", {"content": "new"})]:
            with self.assertRaisesRegex(ValueError, "explicit rule"):
                self.prepare(operation, **args)
            self.assertEqual(self.file.read_bytes(), before)

    def test_unrepresentable_character_and_cp949_extension(self):
        self.rules("cp949")
        self.file.write_bytes("똠방각하".encode("cp949"))
        self.assertIn("똠", self.prepare("read")["output"])
        with self.assertRaisesRegex(ValueError, "not representable"):
            self.prepare(oldString="똠", newString="😀")
        self.rules("euc-kr")
        with self.assertRaises(ValueError):
            self.prepare("read")

    def test_ambiguous_and_no_match_rejected(self):
        self.file.write_bytes(b"one one\r\n")
        for old in ["one", "missing", ""]:
            with self.assertRaises(ValueError):
                self.prepare(oldString=old, newString="two")
        io.commit(self.prepare(oldString="one", newString="two", replaceAll=True))
        self.assertEqual(self.file.read_bytes(), b"two two\r\n")

    def test_new_file_and_rewrite(self):
        self.rules("cp949")
        io.commit(self.prepare("write", content="새 파일\r\n"))
        self.assertEqual(self.file.read_bytes(), "새 파일\r\n".encode("cp949"))
        io.commit(self.prepare("write", content="수정\n"))
        self.assertEqual(self.file.read_bytes(), "수정\r\n".encode("cp949"))

    def test_bom_conflict_and_binary_and_mixed_endings(self):
        self.rules("cp949")
        self.file.write_bytes(codecs.BOM_UTF8 + b"hello")
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.prepare("read")
        (self.root / io.RULE_FILE).unlink()
        self.file.write_bytes(b"hello\x00world")
        with self.assertRaisesRegex(ValueError, "NUL"):
            self.prepare("read")
        self.file.write_bytes(b"a\r\nb\nc")
        with self.assertRaisesRegex(ValueError, "Mixed"):
            self.prepare("write", content="x\ny")
        io.commit(self.prepare(oldString="b", newString="d"))
        self.assertEqual(self.file.read_bytes(), b"a\r\nd\nc")

    def test_changed_file_not_overwritten(self):
        self.file.write_bytes(b"before")
        plan = self.prepare(oldString="before", newString="after")
        self.file.write_bytes(b"external")
        with self.assertRaisesRegex(ValueError, "changed"):
            io.commit(plan)
        self.assertEqual(self.file.read_bytes(), b"external")
        self.assertFalse(self.file.with_name(self.file.name + ".opencode-kit.lock").exists())

    def test_failed_replace_preserves_original_and_cleans_temp(self):
        self.file.write_bytes(b"before")
        plan = self.prepare(oldString="before", newString="after")
        with patch.object(io.os, "replace", side_effect=OSError("simulated failure")):
            with self.assertRaises(OSError):
                io.commit(plan)
        self.assertEqual(self.file.read_bytes(), b"before")
        self.assertEqual(list(self.root.iterdir()), [self.file])

    def test_new_file_created_during_approval(self):
        plan = self.prepare("write", content="mine")
        self.file.write_bytes(b"theirs")
        with self.assertRaisesRegex(ValueError, "changed"):
            io.commit(plan)
        self.assertEqual(self.file.read_bytes(), b"theirs")

    def test_lock_and_read_only(self):
        self.file.write_bytes(b"before")
        plan = self.prepare(oldString="before", newString="after")
        lock = self.file.with_name(self.file.name + ".opencode-kit.lock")
        lock.touch()
        with self.assertRaises(FileExistsError):
            io.commit(plan)
        self.assertTrue(lock.exists())
        lock.unlink()
        self.file.chmod(stat.S_IRUSR)
        try:
            with self.assertRaisesRegex(ValueError, "read-only"):
                io.commit(plan)
        finally:
            self.file.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_rules_last_wins_and_globs(self):
        self.assertTrue(io.glob_match("legacy/**/*.cpp", "legacy/a.cpp"))
        self.assertTrue(io.glob_match("legacy/**/*.cpp", "legacy/sub/a.cpp"))
        self.assertFalse(io.glob_match("*.cpp", "sub/a.cpp"))
        (self.root / io.RULE_FILE).write_text(json.dumps({"rules": [
            {"pattern": "**/*.cpp", "encoding": "cp949"},
            {"pattern": "sample.cpp", "encoding": "utf-8"},
        ]}))
        self.file.write_text("한글", encoding="utf-8")
        self.assertEqual(self.prepare("read")["encoding"], "utf-8")

    def test_symlink_rejected(self):
        target = self.root / "target.cpp"
        target.write_bytes(b"before")
        try:
            self.file.symlink_to(target)
        except OSError:
            self.skipTest("Symlink privilege unavailable")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.prepare(oldString="before", newString="after")
        self.assertEqual(target.read_bytes(), b"before")


if __name__ == "__main__":
    unittest.main()
