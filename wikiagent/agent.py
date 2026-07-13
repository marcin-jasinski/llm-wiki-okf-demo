"""The three Operations (Ingest, Query, Lint) and their inner tool-calling
loop over the five file primitives (ADR 0002, README).
"""

import json
import re
import sys
import tempfile
import webbrowser
from datetime import date
from pathlib import Path


def parse_loose_json(s: str):
    """Parse JSON that may have extra trailing characters (e.g. from LLM tool calls).

    Some models emit JSON like '{"key": "value"}}}' or '{"key": "value"}extra'.
    This function finds the first valid JSON object and ignores trailing garbage.
    """
    s = s.strip()
    # Quick path: valid JSON
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Fallback: find the end of the first valid JSON object by bracket counting
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(s):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # Found the end of the first top-level object
                    return json.loads(s[: i + 1])

    # If we get here, no balanced object was found
    raise json.JSONDecodeError("No valid JSON object found", s, 0)


import markdown

from wikiagent import okf
from wikiagent.primitives import SandboxError

# Full-wiki Lint reads every page before it writes fixes, so it needs more
# headroom than a single Ingest; ceiling stays low enough to stop a runaway loop.
MAX_ITERATIONS = 40

STR = {"type": "string"}


def tool_spec(name, description, params, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required,
            },
        },
    }


TOOL_SPECS = {
    "read_file": tool_spec(
        "read_file",
        "Read a file. Paths start with wiki/ (the wiki) or sources/ (read-only raw sources).",
        {"path": STR},
        ["path"],
    ),
    "write_file": tool_spec(
        "write_file",
        "Create or overwrite a file. Only wiki/ paths are writable.",
        {"path": STR, "content": STR},
        ["path", "content"],
    ),
    "list_dir": tool_spec(
        "list_dir",
        "List one directory level under wiki/ or sources/. Subdirectories end with '/'.",
        {"path": STR},
        ["path"],
    ),
    "grep": tool_spec(
        "grep",
        "Regex-search file contents. Returns path:line:text hits.",
        {"pattern": STR, "root": {"type": "string", "enum": ["wiki", "sources"]}},
        ["pattern"],
    ),
    "fetch_url": tool_spec(
        "fetch_url", "Fetch a URL and return its body as text.", {"url": STR}, ["url"]
    ),
}

OKF_CONVENTIONS = """\
You maintain a wiki that is an OKF v0.1 knowledge bundle. Rules for every page you write:
- Every concept page starts with YAML frontmatter delimited by --- lines, containing at \
minimum a non-empty `type:` (e.g. Concept, Person, Playbook, Source Summary, Query Answer), \
plus `title:`, `description:` (one line), optional `tags:` and `timestamp:` (ISO 8601).
- The body is structural markdown (headings, lists, tables). Cite external sources under a \
final `# Citations` heading, numbered.
- Cross-link related concepts with bundle-relative markdown links: [title](/path/page.md). \
Links to not-yet-written pages are allowed.
- `wiki/index.md` is the catalog: sections of `* [Title](path) - one-line description` \
entries. Keep it current on every ingest. It has no frontmatter.
- `wiki/log.md` is the append-only history, newest first, grouped under `## YYYY-MM-DD` \
headings with `* **Update**: ...` / `* **Creation**: ...` entries. No frontmatter.
- File paths: lowercase, hyphenated, `.md`, organized into subdirectories by kind when \
useful. `index.md` and `log.md` are reserved names — never use them for concepts.
Explore before writing: read wiki/index.md (and grep) to find existing pages to update and \
link, rather than duplicating them."""

INGEST_PROMPT = """\
Operation: Ingest. Integrate the given source into the wiki:
1. Read the source (read_file for sources/ paths, fetch_url for URLs).
2. Read wiki/index.md and any related existing pages.
3. Write or update concept pages capturing the source's key knowledge, cross-linked both ways.
4. Write a source summary page for the source itself, citing it.
5. Update wiki/index.md and append to wiki/log.md.
Finish with a short plain-text report of what you created and updated."""

QUERY_PROMPT = """\
Operation: Query (read-only — you have no write tool). Answer the question from the wiki:
read wiki/index.md, grep for relevant terms, read the relevant pages, then answer.
Your final message is the answer itself, in markdown, citing wiki pages you drew from as \
bundle-relative links. If the wiki cannot answer, say what is missing."""

LINT_PROMPT = """\
Operation: Lint. Self-heal STRUCTURAL issues only (ADR 0007):
- orphan pages (no inbound links): link them from index.md or a related page;
- pages missing from wiki/index.md: add entries;
- concepts mentioned across pages but with no cross-reference link: add the links;
- non-conformant pages (missing/empty frontmatter `type`): fix the frontmatter.
`wiki/AGENTS.md` is the wiki-conventions doc: it is exempt from these rules and must
never be rewritten.
Do NOT rewrite content, resolve contradictions, or judge staleness — report those instead.
Append a lint entry to wiki/log.md. Finish with a plain-text report of fixes and of any \
content-level issues you saw but deliberately left alone."""

HTML_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>Wiki answer</title>
<style>
body {{ font: 17px/1.6 Georgia, serif; max-width: 46em; margin: 3em auto; padding: 0 1em;
       color: #222; }}
h1, h2, h3 {{ font-family: Helvetica, Arial, sans-serif; }}
code {{ background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }}
pre code {{ display: block; padding: 1em; overflow-x: auto; }}
table {{ border-collapse: collapse; }} td, th {{ border: 1px solid #ccc; padding: 4px 10px; }}
blockquote {{ border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; color: #555; }}
</style>
{body}
"""


def run_tool_loop(client, model: str, messages: list, tools: list, dispatch) -> str:
    """Run one tool-calling exchange to completion (ADR 0002).

    Mutates `messages` in place so callers (the Router REPL) can keep a
    running conversation. `dispatch(name, args) -> str` executes a tool.
    """
    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=model, messages=messages, tools=tools
        )
        if not response.choices or response.choices[0] is None:
            error_msg = (
                f"error: LLM returned empty response (no choices). Response: {response}"
            )
            messages.append({"role": "assistant", "content": error_msg})
            return error_msg
        m = response.choices[0].message
        if not m.tool_calls:
            messages.append({"role": "assistant", "content": m.content})
            return m.content or ""
        messages.append(
            {
                "role": "assistant",
                "content": m.content,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {
                            "name": c.function.name,
                            "arguments": c.function.arguments,
                        },
                    }
                    for c in m.tool_calls
                ],
            }
        )
        for c in m.tool_calls:
            # stderr: stdout belongs to the MCP stdio transport in mcp_server.py
            print(
                f"  [{c.function.name}] {c.function.arguments[:120]}", file=sys.stderr
            )
            result = dispatch(c.function.name, parse_loose_json(c.function.arguments))
            messages.append({"role": "tool", "tool_call_id": c.id, "content": result})
    # Leave `messages` ending on an assistant turn, not a tool result, so the
    # Router's persistent history stays a valid conversation.
    stopped = "stopped: iteration limit reached without a final answer"
    messages.append({"role": "assistant", "content": stopped})
    return stopped


# Matches the OKF cross-link convention (bundle-relative, optionally leading-/):
# [title](/path/page.md) or [title](path/page.md). Also matches an external
# https://.../x.md link syntactically — _rewrite_links leaves those alone since
# they never appear in `known` (the store's own bundle-relative paths).
WIKI_LINK_RE = re.compile(r"\]\(/?([^)\s]+\.md)\)")


def _rewrite_links(text: str, store, known: set[str], mirror_dir: Path) -> str:
    """Point each cross-link at something clickable (ADR 0015): the page's live
    URL if the store has one (xWiki), else its rendered sibling under mirror_dir.
    Links to pages the store doesn't have (not-yet-written concepts, allowed by
    the OKF convention) keep their original bundle-relative href — still an inert
    link once rendered, same as before this change; there's nothing to point at yet.
    """
    def repl(m: re.Match) -> str:
        rel = m.group(1)
        if rel not in known:
            return m.group(0)
        url = store.page_url(rel) or (mirror_dir / (rel[:-3] + ".html")).as_uri()
        return f"]({url})"
    return WIKI_LINK_RE.sub(repl, text)


def _render_page(md_text: str, store, known: set[str], mirror_dir: Path, out_path: Path) -> None:
    body = markdown.markdown(_rewrite_links(md_text, store, known, mirror_dir),
                             extensions=["tables", "fenced_code"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(HTML_TEMPLATE.format(body=body), encoding="utf-8")


def render_answer_html(answer_md: str, store) -> Path:
    """Render a markdown answer to a styled HTML file, with wiki-page links
    rewritten so they actually work when opened (ADR 0015): the local backend
    renders the whole wiki bundle alongside the answer so multi-hop links stay
    clickable; the xWiki backend rewrites links to the page's live view URL and
    renders nothing locally.
    """
    mirror_dir = Path(tempfile.mkdtemp(prefix="wiki-answer-"))
    known = {p for p in store.walk() if p.endswith(".md")}
    # ponytail: re-renders the whole local bundle on every query (ADR 0015) — O(pages)
    # markdown renders per query. Fine at demo scale; cache by store write-version if a
    # real bundle ever makes this slow.
    for rel in known:
        if store.page_url(rel) is not None:
            continue  # xWiki backend: the page opens live, nothing to render
        _render_page(store.read(rel), store, known, mirror_dir, mirror_dir / (rel[:-3] + ".html"))
    answer_path = mirror_dir / "answer.html"
    _render_page(answer_md, store, known, mirror_dir, answer_path)
    return answer_path


class Operations:
    """The agent's three high-level capabilities, uniform across entry points."""

    def __init__(self, prims, client, model: str):
        self.prims = prims
        self.client = client
        self.model = model

    def _system_prompt(self, operation_prompt: str) -> str:
        parts = [
            OKF_CONVENTIONS,
            f"Today's date is {date.today().isoformat()}. Use it for "
            "frontmatter `timestamp:` and log.md date headings — never invent or reuse "
            "a date from an existing page.",
        ]
        try:
            conventions = self.prims.read_file("wiki/AGENTS.md")
            parts.append(
                "Additional wiki-specific conventions (AGENTS.md):\n" + conventions
            )
        except (FileNotFoundError, OSError):
            pass
        parts.append(operation_prompt)
        return "\n\n".join(parts)

    def _dispatch(self, name: str, args: dict) -> str:
        try:
            fn = getattr(self.prims, name)
            result = fn(**args)
            return json.dumps(result) if isinstance(result, list) else str(result)
        except SandboxError as e:
            return f"error: {e}"
        except Exception as e:
            return f"error: {type(e).__name__}: {e}"

    def _loop(self, operation_prompt: str, user_msg: str, tool_names: list[str]) -> str:
        messages = [
            {"role": "system", "content": self._system_prompt(operation_prompt)},
            {"role": "user", "content": user_msg},
        ]
        return run_tool_loop(
            self.client,
            self.model,
            messages,
            [TOOL_SPECS[n] for n in tool_names],
            self._dispatch,
        )

    def ingest(self, source: str) -> str:
        """Integrate a sources/ file or a URL into the wiki."""
        return self._loop(
            INGEST_PROMPT,
            f"Ingest this source: {source}",
            ["read_file", "write_file", "list_dir", "grep", "fetch_url"],
        )

    def query(self, question: str, open_browser: bool = True) -> str:
        """Answer a question from the wiki. Read-only (ADR 0006)."""
        answer = self._loop(QUERY_PROMPT, question, ["read_file", "list_dir", "grep"])
        if open_browser and answer:
            webbrowser.open(render_answer_html(answer, self.prims.store).as_uri())
        return answer

    def _conformance_problems(self) -> list[str]:
        """Mechanical OKF conformance scan over the wiki, backend-agnostic."""
        pages = {
            p: self.prims.store.read(p)
            for p in self.prims.store.walk()
            if p.endswith(".md")
        }
        return okf.check_pages(pages)

    def lint(self) -> str:
        """Self-heal structural issues (ADR 0007)."""
        user_msg = "Lint the wiki now."
        problems = self._conformance_problems()
        if problems:
            user_msg += (
                "\n\nA mechanical conformance scan already found these "
                "non-conformant pages — fix each one:\n" + "\n".join(problems)
            )
        return self._loop(
            LINT_PROMPT, user_msg, ["read_file", "write_file", "list_dir", "grep"]
        )
