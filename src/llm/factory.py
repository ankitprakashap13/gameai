"""Build LLMProvider from config dict and environment."""

from __future__ import annotations

import os
from typing import Any

from src.llm.anthropic_provider import AnthropicProvider
from src.llm.base import LLMProvider
from src.llm.ollama_provider import OllamaProvider
from src.llm.openai_provider import OpenAIProvider


def build_llm_provider(cfg: dict[str, Any]) -> LLMProvider:
    llm = cfg.get("llm") or {}
    provider = (os.environ.get("COACH_LLM_PROVIDER") or llm.get("provider") or "openai").lower()

    if provider == "anthropic":
        return AnthropicProvider(model=llm.get("anthropic_model"))

    if provider == "ollama":
        base = os.environ.get("OLLAMA_HOST") or llm.get("ollama_base_url") or "http://localhost:11434"
        model = os.environ.get("OLLAMA_MODEL") or llm.get("ollama_model") or "llama3.2"
        return OllamaProvider(base_url=base, model=model)

    return OpenAIProvider(model=llm.get("openai_model"))
