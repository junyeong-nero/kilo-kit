"""Run the bundled Windows-MCP with isolated packages and UI-test tools only."""
import os
from pathlib import Path
import site
import sys

BUNDLE = Path(__file__).resolve().parents[2]
PACKAGES = BUNDLE / "runtime" / "windows-mcp"
TOOLS = ("Screenshot", "Snapshot", "DisplayInventory", "App", "Click", "Type",
         "Scroll", "Move", "Shortcut", "Wait", "WaitFor")


def same(path):
    return os.path.normcase(os.path.realpath(path))


def use_windows_packages():
    # Do not mix the build center's MCP packages or the Word server's packages with these.
    shared = {same(BUNDLE / "runtime" / "python" / "Lib" / "site-packages"),
              same(BUNDLE / "mcp" / "build-center"), same(BUNDLE / "mcp" / "word")}
    sys.path[:] = [p for p in sys.path if same(p) not in shared]
    # Executes pywin32.pth so its DLLs can be found by the embedded Python.
    site.addsitedir(str(PACKAGES))


def main():
    os.environ["ANONYMIZED_TELEMETRY"] = "false"
    os.environ["FASTMCP_CHECK_FOR_UPDATES"] = "off"
    os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    use_windows_packages()
    from windows_mcp.__main__ import main as serve
    serve(args=["serve", "--transport", "stdio", "--tools", ",".join(TOOLS)])


if __name__ == "__main__":
    main()
