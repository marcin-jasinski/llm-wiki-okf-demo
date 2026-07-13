"""Smoke tests for the xWiki Wiki Store and backend switching (ticket 09).

The XWikiStore logic (OKF↔page mapping, ADR 0012) is tested against an
in-memory fake PageClient — the injectable seam store.PageClient defines — so
these run with no live xWiki. A separate live test exercises the real MCP
server + REST round-trip and skips when xWiki isn't up.
"""

import pytest

from wikiagent.okf import check_pages, wrap_frontmatter
from wikiagent.primitives import Primitives
from wikiagent.store import LocalStore, XWikiStore, make_store


class FakePageClient:
    """In-memory stand-in for the MCP page client, keyed by (spaces, name)."""

    def __init__(self):
        self.pages: dict[tuple, str] = {}

    def get(self, spaces, name):
        return self.pages.get((tuple(spaces), name))

    def put(self, spaces, name, content):
        self.pages[(tuple(spaces), name)] = content

    def delete(self, spaces, name):
        self.pages.pop((tuple(spaces), name), None)

    def list_all(self, spaces):
        prefix = tuple(spaces)
        return [(list(sp), name) for (sp, name) in self.pages
                if sp[:len(prefix)] == prefix]


@pytest.fixture
def store():
    return XWikiStore(FakePageClient(), space="WikiDemo")


def test_write_maps_path_to_nested_page(store):
    store.write("tables/orders.md", "body")
    # ADR 0012: dirs -> nested spaces under root, filename -> terminal page
    assert store.client.pages == {(("WikiDemo", "tables"), "orders"): "body"}


def test_read_round_trips_verbatim(store):
    # canonical leading-/ link form round-trips byte-identical (ADR 0017): a
    # bare "accounts.md" would too, but always comes back out with a leading /
    page = wrap_frontmatter("See [x](/accounts.md).", type="table", title="Orders")
    store.write("tables/orders.md", page)
    assert store.read("tables/orders.md") == page  # frontmatter + link untouched


def test_frontmatter_fenced_on_the_wire_for_xwiki(store):
    """ADR 0016: raw xWiki content fences frontmatter so CommonMark doesn't
    mangle bare `---` into a <hr>/setext heading; read() reverses it so callers
    still see plain `---` frontmatter (test_read_round_trips_verbatim above)."""
    page = wrap_frontmatter("Body text.", type="Concept", title="X")
    store.write("x.md", page)
    raw = store.client.get(["WikiDemo"], "x")
    assert raw.startswith("```yaml\n") and not raw.startswith("---\n")
    assert store.read("x.md") == page


def test_read_missing_raises(store):
    with pytest.raises(FileNotFoundError):
        store.read("nope.md")


def test_non_markdown_rejected(store):
    with pytest.raises(ValueError):
        store.write("data.json", "{}")


def test_walk_and_list_match_localstore_semantics(store):
    for p in ("index.md", "tables/orders.md", "tables/customers.md", "guides/a.md"):
        store.write(p, "x")
    assert store.walk() == ["guides/a.md", "index.md",
                            "tables/customers.md", "tables/orders.md"]
    assert store.list() == ["guides/", "index.md", "tables/"]
    assert store.list("tables") == ["customers.md", "orders.md"]


def test_list_sort_matches_localstore_on_stem_collision(store, tmp_path):
    """A file and dir sharing a stem must order identically on both backends."""
    for p in ("tables.md", "tables/orders.md"):
        store.write(p, "x")
    local = LocalStore(tmp_path)
    for p in ("tables.md", "tables/orders.md"):
        local.write(p, "x")
    assert store.list() == local.list() == ["tables/", "tables.md"]


def test_export_is_conformant_by_construction(store):
    """ADR 0012: walk+read reproduces a conformant OKF bundle, no reassembly."""
    store.write("concepts/ledger.md",
                wrap_frontmatter("A ledger.", type="concept", title="Ledger"))
    exported = {rel: store.read(rel) for rel in store.walk()}
    assert check_pages(exported) == []


def test_primitives_work_over_xwiki_backend(store):
    """Backend switching: the same six primitives run unchanged on xWiki."""
    prims = Primitives(store, sources_dir=".")
    prims.write_file("wiki/tables/orders.md",
                     "---\ntype: Table\n---\nSee [c](/customers.md).\n")
    assert prims.read_file("wiki/tables/orders.md").endswith("customers.md).\n")
    assert prims.list_dir("wiki") == ["tables/"]
    hits = prims.grep(r"customers\.md")
    assert hits == ["wiki/tables/orders.md:4:See [c](/customers.md)."]


def test_link_rewritten_to_live_url_on_the_wire(store):
    """The reported bug: a stored '.md' cross-link has nothing to resolve
    against once xWiki serves the page (ADR 0017) — it must become the
    target's live view URL on the wire, not stay a bare '.md' href."""
    store = XWikiStore(FakePageClient(), space="WikiDemo", base_url="http://localhost:8080")
    store.write("index.md", "* [Orders](/tables/orders.md)\n")
    raw = store.client.get(["WikiDemo"], "index")
    assert "orders.md" not in raw
    assert "http://localhost:8080/bin/view/WikiDemo/tables/orders" in raw


def test_link_rewrite_reversed_on_read(store):
    store = XWikiStore(FakePageClient(), space="WikiDemo", base_url="http://localhost:8080")
    store.write("index.md", "* [Orders](/tables/orders.md)\n")
    assert store.read("index.md") == "* [Orders](/tables/orders.md)\n"


def test_external_md_link_left_untouched(store):
    page = "* [Readme](https://github.com/x/y/README.md)\n"
    store.write("index.md", page)
    assert store.client.get(["WikiDemo"], "index") == page  # untouched on the wire
    assert store.read("index.md") == page


def test_make_store_selects_xwiki(monkeypatch):
    """make_store wires the real MCP client; stub it so no subprocess spawns."""
    import wikiagent.xwiki_client as xc
    monkeypatch.setattr(xc, "make_page_client", lambda cfg: FakePageClient())
    s = make_store("xwiki", xwiki={"space": "WikiDemo", "base_url": "http://localhost:8080"})
    assert isinstance(s, XWikiStore) and s.space == "WikiDemo"
    assert s.page_url("a.md") == "http://localhost:8080/bin/view/WikiDemo/a"


def test_make_store_still_selects_local(tmp_path):
    assert isinstance(make_store("local", wiki_dir=tmp_path), LocalStore)


def test_local_store_page_url_is_none(tmp_path):
    # LocalStore has no live URL — the answer renderer must render it locally instead.
    assert LocalStore(tmp_path).page_url("a.md") is None


def test_xwiki_store_page_url_maps_path_to_bin_view():
    store = XWikiStore(FakePageClient(), space="WikiDemo", base_url="http://localhost:8080")
    assert store.page_url("tables/orders.md") == \
        "http://localhost:8080/bin/view/WikiDemo/tables/orders"


def test_xwiki_store_page_url_strips_trailing_slash_on_base():
    store = XWikiStore(FakePageClient(), space="WikiDemo", base_url="http://localhost:8080/")
    assert store.page_url("index.md") == "http://localhost:8080/bin/view/WikiDemo/index"
