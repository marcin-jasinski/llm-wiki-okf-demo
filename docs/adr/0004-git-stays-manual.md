# Git operations stay entirely outside the agent

No `git commit`/`git push` tool is ever exposed to the LLM, and no automatic staging happens after Ingest or Lint. `WIKI_REPO_PATH` just points at a directory the presenter has already cloned; after any write, the presenter reviews `git diff` and commits by hand.

Rejected letting the agent auto-commit: giving a tool-calling loop unsupervised write access to git history (and possibly a remote) is a consequential, hard-to-reverse action with no benefit to what's being demoed — the interesting part is the file edits, not automated git hygiene. Keeping it manual also turns `git diff` into a genuine "here's exactly what the LLM changed" demo moment.
