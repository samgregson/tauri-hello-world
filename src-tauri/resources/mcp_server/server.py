"""
MCP Server for structural engineering desktop automation.

Transport:  stdio (JSON-RPC 2.0) — invoked via --mcp-server flag on the Tauri binary
Protocol:   Model Context Protocol via FastMCP
COM tools:  Real on Windows; mock stubs returned on Linux/macOS for dev/testing
"""
import sys
import platform

from fastmcp import FastMCP

# ── Platform guard ────────────────────────────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"

# ── Create the MCP server ────────────────────────────────────────────────────
mcp = FastMCP(
    name="Engineering Tools MCP",
    instructions=(
        "Provides COM automation tools for structural engineering applications "
        "(Excel, Word, SAP2000, ETABS, Tekla Structural Designer). "
        "On non-Windows platforms, tools return mock data for development/testing."
    ),
)

# ── Register tool modules ────────────────────────────────────────────────────
# Each module registers its tools against the shared `mcp` instance.
from tools import excel, word, sap2000, etabs, tekla_sd  # noqa: E402

excel.register(mcp, IS_WINDOWS)
word.register(mcp, IS_WINDOWS)
sap2000.register(mcp, IS_WINDOWS)
etabs.register(mcp, IS_WINDOWS)
tekla_sd.register(mcp, IS_WINDOWS)


if __name__ == "__main__":
    mcp.run(transport="stdio")
