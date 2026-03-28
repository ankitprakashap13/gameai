from __future__ import annotations

import os

import anthropic

from src.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        self._client = anthropic.AsyncAnthropic()

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = []
        for block in msg.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts).strip()
