"""The Router: the top-level tool-calling loop behind the REPL (ADR 0008).

Its LLM-facing tools are the three Operations. Filing a Query answer into the
wiki stays human-gated but is now a deterministic REPL-level y/n prompt, not
an LLM-decided tool call (ADR 0006, amended by ADR 0014).
"""

import re
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
Relay each tool's result back to the user concisely. If the request matches no tool, just
answer conversationally and mention what you can do."""

ROUTER_TOOLS = [
    tool_spec("ingest_source", "Integrate a sources/ file or URL into the wiki.",
              {"source": STR}, ["source"]),
    tool_spec("query_wiki", "Answer a question from the wiki (read-only).",
              {"question": STR}, ["question"]),
    tool_spec("lint_wiki", "Self-heal structural wiki issues.", {}, []),
]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "answer"


class Router:
    def __init__(self, ops, prims, client, model: str):
        self.ops = ops
        self.prims = prims
        self.client = client
        self.model = model
        self.lock = threading.Lock()  # serializes Operations with the watcher (ADR 0008)
        self.last_answer = None
        self.last_question = None
        self.awaiting_save = False  # a fresh query_wiki answer is offerable to file (ADR 0014)
        self.messages = [{"role": "system", "content": ROUTER_PROMPT}]

    def handle(self, text: str) -> str:
        self.awaiting_save = False
        self.messages.append({"role": "user", "content": text})
        return run_tool_loop(self.client, self.model, self.messages,
                             ROUTER_TOOLS, self._dispatch)

    def run_ingest(self, source: str) -> str:
        """Ingest under the shared lock — used by both the Router and the watcher."""
        with self.lock:
            return self.ops.ingest(source)

    def file_last_answer(self) -> str:
        """Deterministically file the last query answer (ADR 0006, amended by ADR 0014).

        Triggered by the REPL's y/n prompt, never by the LLM — the write is a
        plain wrap-with-frontmatter, not a second judgment call.
        """
        if not self.last_answer:
            return "error: no query answer to file — run a query first"
        path = f"wiki/query-answers/{_slugify(self.last_question or 'answer')}.md"
        page = wrap_frontmatter(self.last_answer, type="Query Answer",
                                title=(self.last_question or "Query answer").strip())
        try:
            self.prims.write_file(path, page)
        except SandboxError as e:
            return f"error: {e}"
        self.awaiting_save = False
        return f"filed the answer at {path}"

    def _dispatch(self, name: str, args: dict) -> str:
        if name == "ingest_source":
            return self.run_ingest(args["source"])
        if name == "query_wiki":
            with self.lock:
                answer = self.ops.query(args["question"])
                self.last_answer = answer
                self.last_question = args["question"]
                self.awaiting_save = True
            return answer
        if name == "lint_wiki":
            with self.lock:
                return self.ops.lint()
        return f"error: unknown tool {name}"
