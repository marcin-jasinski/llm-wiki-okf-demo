# Grilling: OKF-on-xWiki mapping

Labels: wayfinder:grilling
Status: ready-for-human
Blocked-by: 01-xwiki-mcp-landscape, 03-xwiki-instance
Map: ../MAP.md

## Question

How does an OKF v0.1 bundle map onto xWiki? Concretely: where does YAML frontmatter live (page content as markdown verbatim? xWiki object properties? a fenced block?), how do `index.md`/`log.md` map to pages, how do bundle-relative links (`/tables/orders.md`) translate to xWiki page links and back, and what plays the role of the bundle root (a space?). Conformance target: an export of the xWiki space should be (or trivially convert to) a conformant OKF bundle. Use /domain-modeling; outcome recorded as an ADR.
