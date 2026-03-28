from __future__ import annotations

import os

from openai import AsyncOpenAI

from src.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._client = AsyncOpenAI()

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.6,
        )
        choice = resp.choices[0]
        return (choice.message.content or "").strip()
