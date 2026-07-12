"""Smoke tests for the five sandboxed file primitives (ticket 08).

Seam: the Primitives class — the exact tool surface every Operation's
inner loop sees, on any Wiki Store (ADR 0011).
"""

import pytest

from wikiagent.primitives import Primitives, SandboxError
from wikiagent.store import LocalStore, make_store


@pytest.fixture
def prims(tmp_path):
    wiki = tmp_path / "wiki"
    sources = tmp_path / "sources"
    wiki.mkdir()
    sources.mkdir()
    (wiki / "index.md").write_text("# Concepts\n", encoding="utf-8")
    (wiki / "tables").mkdir()
    (wiki / "tables" / "orders.md").write_text(
        "---\ntype: Table\n---\nSee [customers](/tables/customers.md).\n",
        encoding="utf-8",
    )
    (sources / "notes.txt").write_text("raw source material", encoding="utf-8")
    return Primitives(LocalStore(wiki), sources)


def test_read_file_from_wiki(prims):
    assert prims.read_file("wiki/index.md") == "# Concepts\n"


def test_read_file_from_sources(prims):
    assert prims.read_file("sources/notes.txt") == "raw source material"


def test_write_file_inside_wiki(prims):
    prims.write_file("wiki/tables/customers.md", "---\ntype: Table\n---\nhi\n")
    assert prims.read_file("wiki/tables/customers.md").endswith("hi\n")


def test_write_file_into_sources_rejected(prims):
    with pytest.raises(SandboxError):
        prims.write_file("sources/notes.txt", "overwrite attempt")


def test_write_file_agents_md_rejected(prims):
    # the wiki-conventions doc is human-owned; the agent must never rewrite it
    with pytest.raises(SandboxError):
        prims.write_file("wiki/AGENTS.md", "sneaky rewrite")


def test_path_traversal_rejected(prims):
    for bad in ("wiki/../escape.md", "sources/../../etc/passwd", "/etc/passwd", "C:/x.md"):
        with pytest.raises(SandboxError):
            prims.read_file(bad)
    with pytest.raises(SandboxError):
        prims.write_file("wiki/../outside.md", "x")


def test_unknown_root_rejected(prims):
    with pytest.raises(SandboxError):
        prims.read_file("elsewhere/file.md")


def test_list_dir(prims):
    top = prims.list_dir("wiki")
    assert "index.md" in top and "tables/" in top
    assert prims.list_dir("wiki/tables") == ["orders.md"]
    assert prims.list_dir("sources") == ["notes.txt"]


def test_grep_wiki(prims):
    hits = prims.grep(r"customers\.md")
    assert len(hits) == 1
    assert hits[0].startswith("wiki/tables/orders.md:")


def test_grep_sources(prims):
    hits = prims.grep("raw source", root="sources")
    assert hits == ["sources/notes.txt:1:raw source material"]


def test_grep_no_match(prims):
    assert prims.grep("zzz-not-there") == []


def test_log_md_append_only_allows_growth(prims):
    prims.write_file("wiki/log.md", "# Log\n\n## 2026-01-01\n\n* **Update**: first.\n")
    prims.write_file(
        "wiki/log.md",
        "# Log\n\n## 2026-01-02\n\n* **Update**: second.\n\n"
        "## 2026-01-01\n\n* **Update**: first.\n",
    )
    assert "first" in prims.read_file("wiki/log.md")
    assert "second" in prims.read_file("wiki/log.md")


def test_log_md_append_only_rejects_dropped_entry(prims):
    prims.write_file(
        "wiki/log.md",
        "# Log\n\n## 2026-01-01\n\n* **Update**: first.\n\n* **Update**: second.\n",
    )
    with pytest.raises(SandboxError):
        prims.write_file("wiki/log.md", "# Log\n\n## 2026-01-01\n\n* **Update**: second.\n")


def test_log_md_append_only_rejects_rewritten_entry(prims):
    prims.write_file(
        "wiki/log.md", "# Log\n\n## 2026-01-01\n\n* **Update**: first version.\n")
    with pytest.raises(SandboxError):
        prims.write_file(
            "wiki/log.md", "# Log\n\n## 2026-01-01\n\n* **Update**: edited version.\n")


def test_make_store_selects_local(tmp_path):
    store = make_store("local", wiki_dir=tmp_path)
    assert isinstance(store, LocalStore)


def test_make_store_unknown_backend(tmp_path):
    with pytest.raises(ValueError):
        make_store("gopher", wiki_dir=tmp_path)
