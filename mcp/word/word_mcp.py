"""Start the bundled word-mcp-live server on the bundled Python, limited to documents open in Word.

word-mcp-live needs mcp 2 (through fastmcp 4) while the build center pins mcp 1, so its packages live in
runtime/word-mcp instead of runtime/python/Lib/site-packages. This process sees only that folder.
"""
import os
import asyncio
import json
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


WORD_FILES = (".docx", ".docm", ".doc")


async def word_live_open(path: str) -> str:
    """[Windows only] Open a Word document in Microsoft Word so the word_live_* tools can work on it.
    Starts Word (visible) if it is not running. Does nothing if the document is already open.
    Args: path (str): absolute path of a .docx, .docm or .doc file."""
    if sys.platform != "win32":
        return json.dumps({"error": "Live tools are only available on Windows"})
    full = os.path.abspath(os.path.expandvars(path))
    if not os.path.isfile(full):
        return json.dumps({"error": f"File not found: {full}"})
    if not full.lower().endswith(WORD_FILES):
        return json.dumps({"error": f"Not a Word document ({', '.join(WORD_FILES)}): {full}"})
    import win32com.client
    from word_document_server.core.word_com import get_word_app, find_document
    try:
        app = get_word_app()
    except RuntimeError:
        # Word is not running: start it. The user sees and owns this window like any other.
        app = win32com.client.Dispatch("Word.Application")
    app.Visible = True
    try:
        doc = find_document(app, full)
        opened = False
    except ValueError:
        alerts = app.DisplayAlerts
        app.DisplayAlerts = 0  # wdAlertsNone: a dialog would block the call until the MCP timeout
        try:
            doc = app.Documents.Open(full)
        finally:
            app.DisplayAlerts = alerts
        opened = True
    doc.Activate()
    return json.dumps({"name": doc.Name, "full_path": doc.FullName, "opened": opened,
                       "read_only": bool(doc.ReadOnly)}, ensure_ascii=False)


def keep_open_document_tools(server):
    # The other tools read and write .docx files with python-docx, closed files included. Hide them after registration.
    register = server.register_tools

    def register_open_document_tools():
        register()
        names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
        server.mcp.disable(names={name for name in names if not open_document_tool(name)})
        # word-mcp-live has no tool that opens a file in Word; this one does, so users need not open it by hand.
        from mcp.types import ToolAnnotations
        server.mcp.tool(annotations=ToolAnnotations(title="Word Live Open", readOnlyHint=False))(word_live_open)

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
