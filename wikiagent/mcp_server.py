"""MCP server for external hosts (Claude Desktop, Claude Code, …).

Exposes exactly the three Operations and never the file primitives
(ADR 0005) — every entry point runs the same configured LLM backend.
Run: `uv run mcp_server.py` (stdio).
"""

from mcp.server.fastmcp import FastMCP

from wikiagent.config import build

_, _, _, ops = build()
mcp = FastMCP("llm-wiki-okf-demo")


@mcp.tool()
def ingest_source(source: str) -> str:
    """Integrate a raw source (a sources/ file path or a URL) into the wiki."""
    return ops.ingest(source)


@mcp.tool()
def query_wiki(question: str) -> str:
    """Answer a question from the wiki (read-only); also opens the answer in a browser."""
    return ops.query(question)


@mcp.tool()
def lint_wiki() -> str:
    """Self-heal structural wiki issues (orphans, missing links, bad frontmatter)."""
    return ops.lint()


if __name__ == "__main__":
    mcp.run()
