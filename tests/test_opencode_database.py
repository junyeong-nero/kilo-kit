"""Opt-in real binary regression: preserve an incompatible DB and initialize the kit DB."""
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("OPENCODE_TEST_BIN"), "Opt-in native database test")
class DatabaseTest(unittest.TestCase):
    def test_incompatible_default_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix="opencode-db-") as temp:
            base = Path(temp).resolve()
            env = {**os.environ, "HOME": str(base), "USERPROFILE": str(base),
                   "OPENCODE_TEST_HOME": str(base), "npm_config_offline": "true",
                   "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_AUTOUPDATE": "1",
                   "OPENCODE_DISABLE_DEFAULT_PLUGINS": "true"}
            for key in ("DATA", "CONFIG", "STATE", "CACHE"):
                env[f"XDG_{key}_HOME"] = str(base / key.lower())
            for key in ("OPENCODE_DB", "OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR", "OPENCODE_CONFIG_CONTENT"):
                env.pop(key, None)
            original = base / "data/opencode/opencode.db"
            original.parent.mkdir(parents=True)
            with sqlite3.connect(original) as db:
                db.execute("CREATE TABLE interrupted_setup (id INTEGER)")
                db.execute("INSERT INTO interrupted_setup VALUES (42)")

            def run():
                return subprocess.run([env["OPENCODE_TEST_BIN"], "session", "list", "--format", "json"],
                                      env=env, cwd=base, capture_output=True, text=True, timeout=60)

            failed = run()
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("database is not empty and has no session table", (failed.stdout + failed.stderr).lower())
            # The failing upstream opener can change journal mode. Compare after that reproduction.
            before = hashlib.sha256(original.read_bytes()).digest()
            launcher = (ROOT / "config/opencode.cmd").read_text()
            self.assertIn('if not defined OPENCODE_DB set "OPENCODE_DB=opencode-kit.db"', launcher)
            env["OPENCODE_DB"] = "opencode-kit.db"
            for _ in range(2):
                result = run()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(hashlib.sha256(original.read_bytes()).digest(), before)
            with sqlite3.connect(original.as_uri() + "?mode=ro", uri=True) as db:
                self.assertEqual(db.execute("SELECT id FROM interrupted_setup").fetchall(), [(42,)])
            kit = original.with_name("opencode-kit.db")
            with sqlite3.connect(kit.as_uri() + "?mode=ro", uri=True) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM session").fetchone(), (0,))
