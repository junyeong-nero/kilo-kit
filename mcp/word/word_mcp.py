"""Start the bundled word-mcp-live server on the bundled Python, limited to documents open in Word.

word-mcp-live needs mcp 2 (through fastmcp 4) while the build center pins mcp 1, so its packages live in
runtime/word-mcp instead of runtime/python/Lib/site-packages. This process sees only that folder.
"""
import os
import asyncio
from pathlib import Path
import site
import sys

BUNDLE = Path(__file__).resolve().parents[2]
PACKAGES = BUNDLE / "runtime" / "word-mcp"


def same(path):
    return os.path.normcase(os.path.realpath(path))


def use_word_packages():
    # python313._pth lists the build center's packages and code for every process; drop them here.
    shared = {same(BUNDLE / "runtime" / "python" / "Lib" / "site-packages"), same(BUNDLE / "mcp" / "build-center")}
    sys.path[:] = [p for p in sys.path if same(p) not in shared]
    # addsitedir also runs pywin32.pth, which registers pywin32's DLL folder.
    site.addsitedir(str(PACKAGES))


def open_document_tool(name):
    # word_live_* and the screen capture attach to the running Word through COM and accept only open documents.
    return name.startswith("word_live_") or name == "word_screen_capture"


def keep_open_document_tools(server):
    # The other tools read and write .docx files with python-docx, closed files included. Hide them after registration.
    register = server.register_tools

    def register_open_document_tools():
        register()
        names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
        server.mcp.disable(names={name for name in names if not open_document_tool(name)})

    server.register_tools = register_open_document_tools


def main():
    # Fixed here so a .env in the user's project cannot switch the transport or turn on network checks.
    os.environ["MCP_TRANSPORT"] = "stdio"
    os.environ["FASTMCP_CHECK_FOR_UPDATES"] = "off"
    os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    # Author of tracked changes and comments.
    os.environ.setdefault("MCP_AUTHOR", os.environ.get("USERNAME") or "Author")
    use_word_packages()
    from word_document_server import main as server
    keep_open_document_tools(server)
    server.run_server()


if __name__ == "__main__":
    main()
