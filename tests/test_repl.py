"""REPL seam: the watcher must always leave a visible prompt behind (grilling
session, .scratch/repl-ux-fixes), and the y/n auto-file flow after a query.
"""

from types import SimpleNamespace

import wikiagent.repl as repl
from wikiagent.repl import PROMPT, SAVE_PROMPT, maybe_prompt_save, report_ingest


def test_report_ingest_reprints_prompt(capsys):
    router = SimpleNamespace(run_ingest=lambda source: "ingested")
    report_ingest(router, "notes.txt")
    out = capsys.readouterr().out
    assert out.endswith(PROMPT)


def test_report_ingest_reprints_whichever_prompt_is_currently_active(monkeypatch, capsys):
    # e.g. the watcher fires while the y/n save prompt (not the main "> ") is
    # the one actually blocked on input() — the reprint must match, not lie.
    monkeypatch.setattr(repl, "_current_prompt", SAVE_PROMPT)
    router = SimpleNamespace(run_ingest=lambda source: "ingested")
    report_ingest(router, "notes.txt")
    assert capsys.readouterr().out.endswith(SAVE_PROMPT)


def test_report_ingest_runs_under_sources_prefix(capsys):
    calls = []
    router = SimpleNamespace(run_ingest=lambda source: calls.append(source) or "ok")
    report_ingest(router, "notes.txt")
    assert calls == ["sources/notes.txt"]


def test_maybe_prompt_save_skips_when_not_awaiting(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: (_ for _ in ()).throw(
        AssertionError("input() should not be called")))
    maybe_prompt_save(SimpleNamespace(awaiting_save=False))


def test_maybe_prompt_save_files_on_yes(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    router = SimpleNamespace(awaiting_save=True, file_last_answer=lambda: "filed at x")
    maybe_prompt_save(router)
    assert "filed at x" in capsys.readouterr().out


def test_maybe_prompt_save_skips_on_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    calls = []
    router = SimpleNamespace(awaiting_save=True, file_last_answer=lambda: calls.append(1))
    maybe_prompt_save(router)
    assert calls == []


def test_maybe_prompt_save_accepts_yes_case_insensitive(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "YES")
    router = SimpleNamespace(awaiting_save=True, file_last_answer=lambda: "filed at x")
    maybe_prompt_save(router)
    assert "filed at x" in capsys.readouterr().out


def test_maybe_prompt_save_marks_save_prompt_active_while_blocked(monkeypatch):
    seen_while_blocked = []

    def fake_input(prompt):
        seen_while_blocked.append(repl._current_prompt)
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)
    router = SimpleNamespace(awaiting_save=True, file_last_answer=lambda: "unused")
    maybe_prompt_save(router)
    assert seen_while_blocked == [SAVE_PROMPT]
    assert repl._current_prompt == PROMPT  # restored once the answer comes back
