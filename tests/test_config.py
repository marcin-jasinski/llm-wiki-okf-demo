"""The one branch worth guarding in config: model rides with the active
backend (ADR 0003 — "same agent, different brain")."""

from wikiagent.config import Settings


def _settings(**over):
    base = dict(wiki_dir=".", raw_sources_dir=".", llm_backend="openrouter",
                model_name="or/model", openrouter_api_key="", lmstudio_base_url="",
                lmstudio_model="lm/model", wiki_backend="local", xwiki={})
    return Settings(**{**base, **over})


def test_openrouter_uses_model_name():
    assert _settings(llm_backend="openrouter").model == "or/model"


def test_lmstudio_uses_its_own_model():
    assert _settings(llm_backend="lmstudio").model == "lm/model"


def test_lmstudio_falls_back_to_model_name_when_unset():
    assert _settings(llm_backend="lmstudio", lmstudio_model="").model == "or/model"
