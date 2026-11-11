"""Synthetic packaging test. This does not execute Windows binaries or claim a deployable build."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("offline_builder", ROOT / ".github/tools/build.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class PackagingTests(unittest.TestCase):
    def test_bundle_layout_and_private_file_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in ("bin", "runtime/python", "runtime/word-mcp", "runtime/windows-mcp",
                           "runtime/opencode-tools", "mcp", "config", "scripts", "docs", "third_party"):
                (root / folder).mkdir(parents=True, exist_ok=True)
                (root / folder / "fixture.txt").write_text("fixture")
            for filename in ("setup.ps1", "README.md", "bin/opencode.cmd", "runtime/opencode-tools/index.js"):
                (root / filename).write_text("fixture")
            for filename in ("config/models.json", "config/owners.json", "config/server_IP_mappings.json", "config/settings.bak"):
                (root / filename).write_text("DO NOT SHIP")
            cache = root / ".cache"
            cache.mkdir()
            output = root / "dist/opencode-kit-win-x64.zip"
            with patch.object(builder, "ROOT", root), patch.object(builder, "CACHE", cache):
                builder.package({"platform": "win-x64", "artifacts": {}}, output)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertIn("opencode-kit/bin/opencode.cmd", names)
                self.assertIn("opencode-kit/runtime/opencode-tools/index.js", names)
                for forbidden in ("models.json", "owners.json", "server_IP_mappings.json", "settings.bak"):
                    self.assertFalse(any(name.endswith(forbidden) for name in names))
                manifest = json.loads(archive.read("opencode-kit/manifest.json"))
                for name, digest in manifest["files"].items():
                    self.assertEqual(hashlib.sha256(archive.read("opencode-kit/" + name)).hexdigest(), digest)

    def test_source_and_config_contracts(self):
        ast.parse((ROOT / ".github/tools/build.py").read_text())
        self.assertTrue((ROOT / "scripts/setup.ps1").read_text().isascii())
        config = json.loads((ROOT / "config/opencode.template.json").read_text())
        self.assertEqual(set(config["mcp"]), {"build_center", "word", "windows"})
        self.assertEqual(config["permission"]["windows_*"], "ask")
        lock = json.loads((ROOT / "config/offline-artifacts.lock.json").read_text())
        package = json.loads((ROOT / "tools/encoding/package.json").read_text())
        self.assertEqual(lock["artifacts"]["opencode"]["version"], package["dependencies"]["@opencode-ai/plugin"])
        self.assertNotIn("kilo", lock["artifacts"])
