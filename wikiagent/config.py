"""Configuration and composition root: .env → settings → client/store/Operations.

One OpenAI-compatible client serves both LLM backends (ADR 0003); the Wiki
Store is selected by WIKI_BACKEND (ADR 0011).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from wikiagent.agent import Operations
from wikiagent.primitives import Primitives
from wikiagent.store import make_store

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class Settings:
    wiki_dir: Path
    raw_sources_dir: Path
    llm_backend: str
    model_name: str
    openrouter_api_key: str
    lmstudio_base_url: str
    lmstudio_model: str
    wiki_backend: str
    xwiki: dict

    @property
    def model(self) -> str:
        """The model for the active backend (ADR 0003: model rides with the brain)."""
        if self.llm_backend == "lmstudio":
            return self.lmstudio_model or self.model_name
        return self.model_name


def load_settings() -> Settings:
    load_dotenv()
    missing = [k for k in ("WIKI_DIR", "RAW_SOURCES_DIR", "MODEL_NAME") if not os.getenv(k)]
    if missing:
        raise SystemExit(f"missing required .env settings: {', '.join(missing)} "
                         "(copy .env.example to .env and fill it in)")
    wiki_backend = os.getenv("WIKI_BACKEND", "local")
    if wiki_backend == "xwiki":
        missing_x = [k for k in ("XWIKI_BASE_URL", "XWIKI_USER", "XWIKI_PASSWORD",
                                 "XWIKI_SPACE") if not os.getenv(k)]
        if missing_x:
            raise SystemExit(f"WIKI_BACKEND=xwiki needs: {', '.join(missing_x)}")
    return Settings(
        wiki_dir=Path(os.environ["WIKI_DIR"]),
        raw_sources_dir=Path(os.environ["RAW_SOURCES_DIR"]),
        llm_backend=os.getenv("LLM_BACKEND", "openrouter"),
        model_name=os.environ["MODEL_NAME"],
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        lmstudio_base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
        lmstudio_model=os.getenv("LMSTUDIO_MODEL", ""),
        wiki_backend=wiki_backend,
        xwiki={
            "base_url": os.getenv("XWIKI_BASE_URL", ""),
            "user": os.getenv("XWIKI_USER", ""),
            "password": os.getenv("XWIKI_PASSWORD", ""),
            "wiki": os.getenv("XWIKI_WIKI", "xwiki"),
            "space": os.getenv("XWIKI_SPACE", ""),
        },
    )


def make_client(s: Settings) -> OpenAI:
    if s.llm_backend == "openrouter":
        if not s.openrouter_api_key:
            raise SystemExit("LLM_BACKEND=openrouter but OPENROUTER_API_KEY is not set")
        return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=s.openrouter_api_key)
    if s.llm_backend == "lmstudio":
        return OpenAI(base_url=s.lmstudio_base_url, api_key="lm-studio")
    raise SystemExit(f"unknown LLM_BACKEND: {s.llm_backend!r} (expected openrouter|lmstudio)")


def build():
    """Everything an entry point needs: (settings, client, primitives, operations)."""
    s = load_settings()
    client = make_client(s)
    store = make_store(s.wiki_backend, wiki_dir=s.wiki_dir, xwiki=s.xwiki)
    prims = Primitives(store, s.raw_sources_dir)
    ops = Operations(prims, client, model=s.model)
    return s, client, prims, ops
