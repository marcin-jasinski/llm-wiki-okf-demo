"""Router seam (ADR 0008): natural language routed to Operations by the LLM,
plus the human-triggered deterministic filing of a Query answer (ADR 0006).
"""

from types import SimpleNamespace

from wikiagent.okf import check_page
from wikiagent.primitives import Primitives
from wikiagent.repl import new_files
from wikiagent.router import ROUTER_TOOLS, Router
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


def test_query_sets_awaiting_save_and_last_question(tmp_path):
    client = FakeClient([msg(tool_calls=[tool_call("query_wiki", {"question": "how join?"})]),
                        msg(content="Alpha joins beta on gamma.")])
    router = make_router(tmp_path, client)
    router.handle("how join?")
    assert router.awaiting_save is True
    assert router.last_question == "how join?"
    assert router.last_answer == "Alpha joins beta on gamma."


def test_awaiting_save_resets_on_next_non_query_turn(tmp_path):
    client = FakeClient([
        msg(tool_calls=[tool_call("query_wiki", {"question": "how join?"})]),
        msg(content="Alpha joins beta on gamma."),
        msg(content="hi"),
    ])
    router = make_router(tmp_path, client)
    router.handle("how join?")
    router.handle("hello")
    assert router.awaiting_save is False


def test_file_last_answer_writes_conformant_page(tmp_path):
    client = FakeClient([msg(tool_calls=[tool_call("query_wiki", {"question": "How does alpha join beta?"})]),
                        msg(content="Alpha joins beta on gamma.")])
    router = make_router(tmp_path, client)
    router.handle("How does alpha join beta?")
    result = router.file_last_answer()
    assert result == "filed the answer at wiki/query-answers/how-does-alpha-join-beta.md"
    page = (tmp_path / "wiki" / "query-answers" / "how-does-alpha-join-beta.md").read_text(encoding="utf-8")
    assert check_page(page) == []
    # ADR 0006/0014: body is the shown answer verbatim
    assert "Alpha joins beta on gamma." in page
    assert router.awaiting_save is False


def test_file_last_answer_adds_index_entry(tmp_path):
    client = FakeClient([msg(tool_calls=[tool_call("query_wiki", {"question": "How does alpha join beta?"})]),
                        msg(content="Alpha joins beta on gamma.")])
    router = make_router(tmp_path, client)
    (tmp_path / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    router.handle("How does alpha join beta?")
    router.file_last_answer()
    index = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "query-answers/how-does-alpha-join-beta.md" in index


def test_file_last_answer_without_prior_query_errors(tmp_path):
    router = make_router(tmp_path, FakeClient([]))
    result = router.file_last_answer()
    assert "error" in result.lower()
    assert router.prims.store.walk() == []


def test_file_answer_tool_no_longer_offered():
    names = [t["function"]["name"] for t in ROUTER_TOOLS]
    assert "file_answer" not in names


def test_new_files_detects_only_additions(tmp_path):
    (tmp_path / "old.txt").write_text("x", encoding="utf-8")
    seen = set(new_files(tmp_path, set()))
    assert seen == {"old.txt"}
    (tmp_path / "fresh.txt").write_text("y", encoding="utf-8")
    assert new_files(tmp_path, seen) == ["fresh.txt"]
    assert new_files(tmp_path, seen | {"fresh.txt"}) == []
