"""The Router: the top-level tool-calling loop behind the REPL (ADR 0008).

Its only LLM-facing tools are the three Operations plus `file_answer`, the
human-triggered, deterministic filing of the last Query answer (ADR 0006).
"""

import threading

from wikiagent.agent import tool_spec, STR, run_tool_loop
from wikiagent.okf import wrap_frontmatter
from wikiagent.primitives import SandboxError

ROUTER_PROMPT = """\
You are the router for a wiki-maintaining agent. Interpret the user's request and call the
right tool; you never read or write wiki files yourself:
- ingest_source: integrate a new source into the wiki. Sources are files under sources/
  (e.g. "sources/notes.md") or URLs.
- query_wiki: answer a question from the wiki (read-only).
- lint_wiki: self-heal structural wiki issues.
- file_answer: save the previous query_wiki answer into the wiki, verbatim. Only call this
  when the user explicitly asks to keep/file/ingest the answer. Pick a sensible new
  wiki/... path and a short title/description.
Relay each tool's result back to the user concisely. If the request matches no tool, just
answer conversationally and mention what you can do."""

ROUTER_TOOLS = [
    tool_spec("ingest_source", "Integrate a sources/ file or URL into the wiki.",
              {"source": STR}, ["source"]),
    tool_spec("query_wiki", "Answer a question from the wiki (read-only).",
              {"question": STR}, ["question"]),
    tool_spec("lint_wiki", "Self-heal structural wiki issues.", {}, []),
    tool_spec("file_answer",
              "Save the last query answer to the wiki verbatim (human-approved).",
              {"path": STR, "title": STR, "description": STR,
               "tags": {"type": "array", "items": STR}},
              ["path", "title"]),
]


class Router:
    def __init__(self, ops, prims, client, model: str):
        self.ops = ops
        self.prims = prims
        self.client = client
        self.model = model
        self.lock = threading.Lock()  # serializes Operations with the watcher (ADR 0008)
        self.last_answer = None
        self.messages = [{"role": "system", "content": ROUTER_PROMPT}]

    def handle(self, text: str) -> str:
        self.messages.append({"role": "user", "content": text})
        return run_tool_loop(self.client, self.model, self.messages,
                             ROUTER_TOOLS, self._dispatch)

    def run_ingest(self, source: str) -> str:
        """Ingest under the shared lock — used by both the Router and the watcher."""
        with self.lock:
            return self.ops.ingest(source)

    def _file_answer(self, path: str, title: str, description: str = "",
                     tags: list | None = None) -> str:
        if not self.last_answer:
            return "error: no query answer to file — run a query first"
        page = wrap_frontmatter(self.last_answer, type="Query Answer",
                                title=title, description=description, tags=tags)
        try:
            self.prims.write_file(path, page)
        except SandboxError as e:
            return f"error: {e}"
        return f"filed the answer at {path}"

    def _dispatch(self, name: str, args: dict) -> str:
        if name == "ingest_source":
            return self.run_ingest(args["source"])
        if name == "query_wiki":
            with self.lock:
                answer = self.ops.query(args["question"])
                self.last_answer = answer
            return answer
        if name == "lint_wiki":
            with self.lock:
                return self.ops.lint()
        if name == "file_answer":
            with self.lock:
                return self._file_answer(**args)
        return f"error: unknown tool {name}"
