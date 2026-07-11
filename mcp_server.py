"""Entry point: MCP server exposing the three Operations (ADR 0005).
`uv run mcp_server.py` (stdio).
"""

from wikiagent.mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
