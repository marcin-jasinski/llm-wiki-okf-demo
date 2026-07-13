"""Smoke tests for the six sandboxed file primitives (ticket 08).

Seam: the Primitives class — the exact tool surface every Operation's
inner loop sees, on any Wiki Store (ADR 0011).
"""

import re

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


def test_write_file_cleans_stray_frontmatter_whitespace(prims):
    # a model occasionally emits a tab/leading space in the YAML block, which
    # breaks parsing intermittently — write_file must normalize it away
    prims.write_file("wiki/tables/customers.md", "---\n\ttype: Table\n  title: X\n---\nhi\n")
    assert prims.read_file("wiki/tables/customers.md") == \
        "---\ntype: Table\ntitle: X\n---\nhi\n"


def test_write_file_index_first_write_is_free(prims):
    prims.write_file("wiki/index.md", "# Concepts\n\n* [Orders](/tables/orders.md)\n")
    assert "orders.md" in prims.read_file("wiki/index.md")


def test_write_file_index_rejects_dropped_entry(prims):
    prims.write_file("wiki/index.md", "# Concepts\n\n* [Orders](/tables/orders.md)\n")
    with pytest.raises(SandboxError):
        # an ingest that overwrites the catalog with only its own new entry —
        # the reported bug: each ingest deleting everything ingested before it
        prims.write_file("wiki/index.md", "# Concepts\n\n* [Invoices](/tables/invoices.md)\n")


def test_write_file_index_allows_growth_and_rewording(prims):
    prims.write_file("wiki/index.md", "# Concepts\n\n* [Orders](/tables/orders.md)\n")
    prims.write_file(
        "wiki/index.md",
        "# Concepts\n\n## Tables\n* [Orders table](/tables/orders.md)\n"
        "* [Invoices](/tables/invoices.md)\n",
    )
    content = prims.read_file("wiki/index.md")
    assert "orders.md" in content and "invoices.md" in content


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


def test_write_file_log_md_rejected(prims):
    # log.md is append-only — the LLM must go through append_log, never write_file
    with pytest.raises(SandboxError):
        prims.write_file("wiki/log.md", "anything")


def test_append_log_creates_file_with_bracketed_timestamp(prims):
    prims.append_log("Creation: first.")
    content = prims.read_file("wiki/log.md")
    assert re.fullmatch(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] - Creation: first\.\n",
                        content)


def test_append_log_appends_new_line_at_the_bottom(prims):
    prims.append_log("Creation: first.")
    prims.append_log("Update: second.")
    lines = [ln for ln in prims.read_file("wiki/log.md").splitlines() if ln.strip()]
    assert len(lines) == 2
    assert lines[0].endswith("Creation: first.")
    assert lines[1].endswith("Update: second.")


def test_append_log_entries_are_blank_line_separated(prims):
    # a single '\n' is a CommonMark soft break (renders as one line on xWiki) —
    # entries must be separated by a blank line so each renders on its own line
    prims.append_log("Creation: first.")
    prims.append_log("Update: second.")
    assert "\n\n" in prims.read_file("wiki/log.md")


def test_make_store_selects_local(tmp_path):
    store = make_store("local", wiki_dir=tmp_path)
    assert isinstance(store, LocalStore)


def test_make_store_unknown_backend(tmp_path):
    with pytest.raises(ValueError):
        make_store("gopher", wiki_dir=tmp_path)
