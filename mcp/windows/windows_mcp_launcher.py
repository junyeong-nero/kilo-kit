"""Run the bundled Windows-MCP over stdio with the same tools pi-kit exposes."""
import os

# pi-kit hides PowerShell, FileSystem, Registry, Process, Scrape and Screenshot; Kilo has no per-tool
# exposure setting, so only the remaining tools are registered here.
TOOLS = ("App", "Snapshot", "DisplayInventory", "Click", "Type", "Scroll", "Move", "Shortcut",
         "Wait", "WaitFor", "MultiSelect", "MultiEdit", "Clipboard", "Notification")


def main():
    os.environ["ANONYMIZED_TELEMETRY"] = "false"
    os.environ["FASTMCP_CHECK_FOR_UPDATES"] = "off"
    os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    from windows_mcp.__main__ import main as serve
    serve(args=["serve", "--transport", "stdio", "--tools", ",".join(TOOLS)])


if __name__ == "__main__":
    main()
