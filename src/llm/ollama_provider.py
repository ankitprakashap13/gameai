from __future__ import annotations

import httpx

from src.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._base = base_url.rstrip("/")
        self._model = model

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        url = f"{self._base}/api/chat"
        payload = {
            "model": self._model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        msg = data.get("message") or {}
        return str(msg.get("content", "")).strip()
