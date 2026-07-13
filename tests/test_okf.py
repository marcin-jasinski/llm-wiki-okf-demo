"""OKF v0.1 conformance seam (ticket 08): the checker used by smoke tests
and Lint, and the deterministic wrap-with-frontmatter save (ADR 0006).
"""

from wikiagent.okf import (
    check_bundle, check_page, check_pages, clean_frontmatter, wrap_frontmatter,
)

GOOD = """---
type: Table
title: Orders
description: One row per order.
---

# Schema

Part of the [sales dataset](/datasets/sales.md).
"""


def test_conformant_page_has_no_problems():
    assert check_page(GOOD) == []


def test_missing_frontmatter_reported():
    assert check_page("# Just a heading\n")


def test_missing_type_reported():
    assert check_page("---\ntitle: No type here\n---\nbody\n")


def test_empty_type_reported():
    assert check_page("---\ntype: ''\n---\nbody\n")


def test_unparseable_yaml_reported():
    assert check_page("---\ntype: [unclosed\n---\nbody\n")


def test_check_bundle(tmp_path):
    (tmp_path / "good.md").write_text(GOOD, encoding="utf-8")
    (tmp_path / "bad.md").write_text("no frontmatter", encoding="utf-8")
    # reserved files are exempt from the frontmatter rule (OKF §3.1, §9)
    (tmp_path / "index.md").write_text("# Concepts\n", encoding="utf-8")
    (tmp_path / "log.md").write_text("# Log\n", encoding="utf-8")
    problems = check_bundle(tmp_path)
    assert any("bad.md" in p for p in problems)
    assert not any("good.md" in p for p in problems)
    assert not any("index.md" in p or "log.md" in p for p in problems)


def test_check_pages_exempts_reserved_and_agents_md():
    pages = {
        "good.md": GOOD,
        "bad.md": "no frontmatter",
        "index.md": "# Concepts\n",
        "log.md": "# Log\n",
        "AGENTS.md": "conventions, not a concept",
    }
    problems = check_pages(pages)
    assert any("bad.md" in p for p in problems)
    assert not any(name in p for p in problems
                   for name in ("good.md", "index.md", "log.md", "AGENTS.md"))


def test_wrap_frontmatter_is_conformant():
    page = wrap_frontmatter(
        "The answer body.", type="Query Answer",
        title="How do orders join customers?",
        description="Answer filed from a query.", tags=["sales"],
    )
    assert check_page(page) == []
    assert page.endswith("The answer body.\n")


def test_wrap_frontmatter_is_deterministic_about_body():
    # ADR 0006: the stored page is the shown answer verbatim, only wrapped
    body = "Line one.\n\n## Detail\nLine two."
    assert body in wrap_frontmatter(body, type="Query Answer", title="t")


def test_clean_frontmatter_strips_leading_whitespace_before_block():
    dirty = "  \n\t---\ntype: Table\n---\nbody\n"
    assert clean_frontmatter(dirty) == "---\ntype: Table\n---\nbody\n"


def test_clean_frontmatter_strips_tabs_and_spaces_inside_block():
    dirty = "---\n\ttype: Table\n  title: Orders\n---\nbody\n"
    cleaned = clean_frontmatter(dirty)
    assert cleaned == "---\ntype: Table\ntitle: Orders\n---\nbody\n"
    assert check_page(cleaned) == []


def test_clean_frontmatter_noop_without_frontmatter():
    assert clean_frontmatter("# Just a heading\n") == "# Just a heading\n"


def test_clean_frontmatter_noop_when_already_clean():
    assert clean_frontmatter(GOOD) == GOOD
