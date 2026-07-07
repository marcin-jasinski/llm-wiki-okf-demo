# One OpenAI-compatible client for both LLM backends

Both supported backends (OpenRouter, local LM Studio) are accessed through a single OpenAI-compatible client (the `openai` Python SDK), switching only `base_url`/`api_key` based on `LLM_BACKEND` in `.env`. Rejected writing separate client code per backend since both already speak the same Chat Completions + function-calling API — one code path handles both, and swapping backends becomes a one-line `.env` edit, which doubles as a demo beat ("same agent, different brain").
