"""Router seam (ADR 0008): natural language routed to Operations by the LLM,
plus the human-triggered deterministic filing of a Query answer (ADR 0006).
"""

from types import SimpleNamespace

from wikiagent.okf import check_page
from wikiagent.primitives import Primitives
from wikiagent.repl import new_files
from wikiagent.router import Router
from wikiagent.store import LocalStore

from conftest import FakeClient, msg, tool_call


class StubOps:
    """Records Operation invocations; returns canned results."""

    def __init__(self):
        self.log = []

    def ingest(self, source):
        self.log.append(("ingest", source))
        return "ingested"

    def query(self, question, open_browser=True):
        self.log.append(("query", question))
        return "Alpha joins beta on gamma."

    def lint(self):
        self.log.append(("lint",))
        return "no issues"


def make_router(tmp_path, client, ops=None):
    (tmp_path / "wiki").mkdir(exist_ok=True)
    (tmp_path / "sources").mkdir(exist_ok=True)
    prims = Primitives(LocalStore(tmp_path / "wiki"), tmp_path / "sources")
    return Router(ops or StubOps(), prims, client, model="test-model")


def test_router_routes_to_lint(tmp_path):
    client = FakeClient([
        msg(tool_calls=[tool_call("lint_wiki", {})]),
        msg(content="Wiki is clean."),
    ])
    router = make_router(tmp_path, client)
    assert router.handle("please lint the wiki") == "Wiki is clean."
    assert router.ops.log == [("lint",)]


def test_router_conversation_persists_across_turns(tmp_path):
    client = FakeClient([msg(content="hi"), msg(content="again")])
    router = make_router(tmp_path, client)
    router.handle("hello")
    router.handle("more")
    # second call still sees the first exchange
    contents = [m.get("content") for m in client.calls[1]["messages"]]
    assert "hello" in contents and "hi" in contents


def test_file_answer_writes_conformant_page(tmp_path):
    client = FakeClient([
        msg(tool_calls=[tool_call("query_wiki", {"question": "how join?"})]),
        msg(content="Alpha joins beta on gamma."),
        msg(tool_calls=[tool_call("file_answer", {
            "path": "wiki/answers/joins.md", "title": "How alpha joins beta",
            "description": "Join key answer."})]),
        msg(content="Filed."),
    ])
    router = make_router(tmp_path, client)
    router.handle("how join?")
    router.handle("ingest it")
    page = (tmp_path / "wiki" / "answers" / "joins.md").read_text(encoding="utf-8")
    assert check_page(page) == []
    # ADR 0006: body is the shown answer verbatim
    assert "Alpha joins beta on gamma." in page


def test_file_answer_without_prior_query_errors(tmp_path):
    client = FakeClient([
        msg(tool_calls=[tool_call("file_answer", {"path": "wiki/a.md", "title": "t"})]),
        msg(content="Nothing to file."),
    ])
    router = make_router(tmp_path, client)
    router.handle("ingest it")
    tool_msg = [m for m in client.calls[-1]["messages"] if m["role"] == "tool"][0]
    assert "error" in tool_msg["content"].lower()
    assert not (tmp_path / "wiki" / "a.md").exists()


def test_new_files_detects_only_additions(tmp_path):
    (tmp_path / "old.txt").write_text("x", encoding="utf-8")
    seen = set(new_files(tmp_path, set()))
    assert seen == {"old.txt"}
    (tmp_path / "fresh.txt").write_text("y", encoding="utf-8")
    assert new_files(tmp_path, seen) == ["fresh.txt"]
    assert new_files(tmp_path, seen | {"fresh.txt"}) == []
