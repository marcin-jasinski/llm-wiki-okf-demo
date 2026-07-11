"""OKF v0.1 conformance checks (spec §9) and the deterministic
wrap-with-frontmatter used when a human files a Query answer (ADR 0006).
"""

from datetime import datetime, timezone
from pathlib import Path

import yaml

RESERVED = {"index.md", "log.md"}
# Exempt from concept-page conformance: the reserved catalog/history files plus
# the wiki-conventions doc (AGENTS.md), which is prose guidance, not a concept.
CONFORMANCE_EXEMPT = RESERVED | {"AGENTS.md"}


def parse_frontmatter(text: str):
    """Return (frontmatter dict or None, body)."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    try:
        fm = yaml.safe_load(text[4:end + 1])
    except yaml.YAMLError:
        return None, text
    return (fm if isinstance(fm, dict) else None), text[end + 5:]


def check_page(text: str) -> list[str]:
    """Problems making a concept document non-conformant (OKF §9)."""
    fm, _ = parse_frontmatter(text)
    if fm is None:
        return ["no parseable YAML frontmatter block"]
    type_ = fm.get("type")
    if not (isinstance(type_, str) and type_.strip()):
        return ["frontmatter has no non-empty 'type' field"]
    return []


def check_pages(pages: dict[str, str]) -> list[str]:
    """Conformance problems across {relpath: text}, as 'path: problem' lines."""
    problems = []
    for rel in sorted(pages):
        if Path(rel).name in CONFORMANCE_EXEMPT:
            continue
        problems += [f"{rel}: {msg}" for msg in check_page(pages[rel])]
    return problems


def check_bundle(root: Path) -> list[str]:
    """Conformance problems across a bundle on disk, as 'path: problem' lines."""
    root = Path(root)
    pages = {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
             for p in root.rglob("*.md")}
    return check_pages(pages)


def wrap_frontmatter(body: str, *, type: str, title: str,
                     description: str = "", tags: list[str] | None = None) -> str:
    """Deterministically wrap a body as a conformant OKF concept document."""
    fm: dict = {"type": type, "title": title}
    if description:
        fm["description"] = description
    if tags:
        fm["tags"] = tags
    fm["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{header}\n---\n\n{body.rstrip()}\n"
