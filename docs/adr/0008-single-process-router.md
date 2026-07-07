# Single no-argument entry point: Router REPL + background watcher in one process

There is exactly one way to start the agent for interactive use: a no-argument entry point that runs a background file watcher (over `raw/`) and a foreground REPL concurrently in one process. The REPL is itself a tool-calling loop — the Router — whose only tools are the three Operations, so natural-language input like "lint the database" is routed to the right Operation by the LLM itself, not by CLI subcommands or argparse flags.

This superseded an earlier design of three separate one-shot CLI subcommands (`ingest`/`query`/`lint`); changed because the agent should be conversed with continuously, not invoked with startup arguments.

The MCP server remains a separate process/entry point — MCP hosts (e.g. Claude Desktop) must spawn their own server subprocess by design (STDIO transport), so this isn't a consistency compromise, it's inherent to MCP.

**Consequences**: the watcher and the Router share one Wiki Repo, so their Operations are serialized with a lock to avoid interleaved writes; a watcher-triggered Ingest prints into the same terminal even mid-conversation.
