"""Abstract LLM provider."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        """Return assistant text (non-streaming)."""
        raise NotImplementedError
