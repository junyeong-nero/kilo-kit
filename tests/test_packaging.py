"""Small synthetic ZIP regression: preserve runtime modules, exclude private settings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build", ROOT / ".github/tools/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class PackagingTests(unittest.TestCase):
    def test_kilo_bundle_and_runtime_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("bin", "runtime/python", "runtime/word-mcp", "runtime/windows-mcp", "mcp", "config", "scripts", "docs", "third_party"):
                (root / name).mkdir(parents=True)
                (root / name / "fixture.txt").write_text("fixture")
            for name in ("setup.ps1", "README.md"):
                (root / name).write_text("fixture")
            module = "runtime/windows-mcp/beartype/_util/cache/__init__.py"
            for name in ("bin/kilo/kilo.exe", module, "config/redis/cache/private.json", "config/models.json", "config/redis/owners.json", "config/redis/server_IP_mappings.json", "config/models.json.bak"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            cache = root / "build-cache"
            cache.mkdir()
            output = root / "dist/kilo-kit-win-x64.zip"
            with patch.object(build, "ROOT", root), patch.object(build, "CACHE", cache):
                build.package({"platform": "win-x64", "artifacts": {}}, output)
            with zipfile.ZipFile(output) as archive:
                manifest = json.loads(archive.read("kilo-kit/manifest.json"))
                self.assertIn("bin/kilo/kilo.exe", manifest["files"])
                self.assertIn(module, manifest["files"])
                for name in ("config/models.json", "config/redis/owners.json", "config/redis/server_IP_mappings.json", "config/models.json.bak", "config/redis/cache/private.json"):
                    self.assertNotIn(name, manifest["files"])
                for name, digest in manifest["files"].items():
                    self.assertEqual(build.digest(root / name), digest)

    def test_kilo_only_contract(self):
        lock = json.loads((ROOT / "config/offline-artifacts.lock.json").read_text())
        self.assertIn("kilo", lock["artifacts"])
        self.assertNotIn("opencode", lock["artifacts"])
        template = json.loads((ROOT / "config/kilo.template.json").read_text())
        self.assertEqual(set(template["mcp"]), {"build_center", "word", "windows"})
        self.assertNotIn("plugin", template)
        self.assertFalse((ROOT / "config/opencode.cmd").exists())
        self.assertFalse((ROOT / "tools/encoding/package.json").exists())
