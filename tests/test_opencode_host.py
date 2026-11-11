"""Optional real-host smoke test; no inference. Set OPENCODE_TEST_BIN to the pinned native executable.
Windows packaging has its own relocated-bundle check in .github/tools/check-opencode.ps1.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("OPENCODE_TEST_BIN") and sys.platform != "win32", "Opt-in native host smoke test")
class HostTest(unittest.TestCase):
    def test_plugin_registration_and_cp949_edit(self):
        with tempfile.TemporaryDirectory(prefix="opencode-host-") as temp:
            base = Path(temp).resolve()
            runtime = base / "runtime/opencode-tools"
            shutil.copytree(ROOT / "tools/encoding", runtime)
            python = base / "runtime/python/python.exe"
            python.parent.mkdir()
            python.symlink_to(sys.executable)
            config_dir = base / "config/opencode"
            config_dir.mkdir(parents=True)
            for name in ("package.json", "package-lock.json"):
                shutil.copy2(runtime / name, config_dir / name)
            (config_dir / "node_modules").symlink_to(runtime / "node_modules", target_is_directory=True)
            template = json.loads((ROOT / "config/opencode.template.json").read_text())
            template["plugin"] = [(runtime / "index.js").as_uri()]
            template["mcp"] = {}
            template["enabled_providers"] = ["corp"]
            template["model"] = "corp/kit-smoke"
            template["provider"] = {"corp": {"npm": "@ai-sdk/openai-compatible", "options": {"baseURL": "http://127.0.0.1:1/v1"},
                                                  "models": {"kit-smoke": {"limit": {"context": 8192, "output": 1024}}}}}
            (config_dir / "opencode.json").write_text(json.dumps(template))
            project = base / "project"
            project.mkdir()
            target = project / "sample.cpp"
            target.write_bytes("// 한글\r\n".encode("cp949"))
            (project / "encoding-rules.json").write_text(json.dumps({"rules": [{"pattern": "*.cpp", "encoding": "cp949"}]}))
            env = {**os.environ, "HOME": str(base), "USERPROFILE": str(base), "OPENCODE_TEST_HOME": str(base),
                   "OPENCODE_KIT_HOME": str(base), "npm_config_offline": "true",
                   "OPENCODE_DISABLE_DEFAULT_PLUGINS": "true", "OPENCODE_DISABLE_AUTOUPDATE": "1",
                   "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_LSP_DOWNLOAD": "true",
                   "OPENCODE_DISABLE_CLAUDE_CODE": "true", "OTEL_EXPORTER_OTLP_ENDPOINT": ""}
            for key in ("CONFIG", "CACHE", "DATA", "STATE"):
                env[f"XDG_{key}_HOME"] = str(base / key.lower())
            for key in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_CONFIG_DIR", "OPENCODE_PERMISSION"):
                env.pop(key, None)

            def run(*args):
                result = subprocess.run([env["OPENCODE_TEST_BIN"], *args], cwd=project, env=env,
                                        capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                return json.loads(result.stdout)

            config = run("debug", "config")
            self.assertEqual(config["model"], "corp/kit-smoke")
            tools = run("debug", "agent", "build")["tools"]
            for name in ("encoding_read", "encoding_edit", "encoding_write"):
                self.assertTrue(tools[name])
            self.assertFalse(tools.get("apply_patch", False))
            run("debug", "agent", "build", "--tool", "encoding_edit", "--params",
                json.dumps({"filePath": str(target), "oldString": "한글", "newString": "수정"}))
            self.assertEqual(target.read_bytes(), "// 수정\r\n".encode("cp949"))
