"""Operation tool-loop seam (ticket 08), against a scripted fake LLM client.

Behavior under test: the inner loop executes the LLM's tool calls through
the primitives and returns the final answer; Query is read-only (ADR 0006);
AGENTS.md is folded into the system prompt when present.
"""

import json
from types import SimpleNamespace

import pytest

from wikiagent.agent import Operations
from wikiagent.primitives import Primitives
from wikiagent.store import LocalStore


def msg(content=None, tool_calls=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content=content, tool_calls=tool_calls))]
    )


def tool_call(name, args, id="call_1"):
    return SimpleNamespace(
        id=id, function=SimpleNamespace(name=name, arguments=json.dumps(args))
    )


class FakeClient:
    """Plays back scripted responses; records every create() kwargs."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


@pytest.fixture
def wiki(tmp_path):
    (tmp_path / "wiki").mkdir()
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "a.txt").write_text("alpha beta", encoding="utf-8")
    return tmp_path


def make_ops(wiki, client):
    prims = Primitives(LocalStore(wiki / "wiki"), wiki / "sources")
    return Operations(prims, client, model="test-model")


def test_ingest_executes_tool_calls_and_returns_summary(wiki):
    client = FakeClient([
        msg(tool_calls=[tool_call("read_file", {"path": "sources/a.txt"})]),
        msg(tool_calls=[tool_call("write_file", {
            "path": "wiki/concepts/alpha.md",
            "content": "---\ntype: Concept\n---\nalpha\n"})]),
        msg(content="Ingested a.txt into 1 page."),
    ])
    result = make_ops(wiki, client).ingest("sources/a.txt")
    assert result == "Ingested a.txt into 1 page."
    assert (wiki / "wiki" / "concepts" / "alpha.md").exists()
    # tool results were fed back to the LLM
    roles = [m["role"] for m in client.calls[-1]["messages"]]
    assert roles.count("tool") == 2


def test_query_has_no_write_tool(wiki):
    client = FakeClient([msg(content="The answer.")])
    answer = make_ops(wiki, client).query("what is alpha?", open_browser=False)
    assert answer == "The answer."
    names = [t["function"]["name"] for t in client.calls[0]["tools"]]
    assert "write_file" not in names
    assert "read_file" in names and "grep" in names


def test_lint_has_write_tool(wiki):
    client = FakeClient([msg(content="No issues.")])
    make_ops(wiki, client).lint()
    names = [t["function"]["name"] for t in client.calls[0]["tools"]]
    assert "write_file" in names


def test_bad_tool_call_reports_error_to_llm_not_crash(wiki):
    client = FakeClient([
        msg(tool_calls=[tool_call("write_file", {"path": "sources/a.txt", "content": "x"})]),
        msg(content="Understood, cannot write there."),
    ])
    result = make_ops(wiki, client).lint()
    assert result == "Understood, cannot write there."
    tool_msg = [m for m in client.calls[-1]["messages"] if m["role"] == "tool"][0]
    assert "error" in tool_msg["content"].lower()


def test_agents_md_folded_into_system_prompt(wiki):
    (wiki / "wiki" / "AGENTS.md").write_text("Prefer type: Recipe.", encoding="utf-8")
    client = FakeClient([msg(content="ok")])
    make_ops(wiki, client).query("q", open_browser=False)
    system = client.calls[0]["messages"][0]
    assert system["role"] == "system"
    assert "Prefer type: Recipe." in system["content"]


def test_loop_stops_at_max_iterations(wiki):
    endless = [msg(tool_calls=[tool_call("list_dir", {"path": "wiki"})])] * 50
    client = FakeClient(endless)
    result = make_ops(wiki, client).lint()
    assert "iteration limit" in result
