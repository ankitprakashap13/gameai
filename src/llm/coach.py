"""Format game state into prompts; throttle LLM calls; persist and deduplicate tips."""

from __future__ import annotations

import asyncio
import logging
import time
from difflib import SequenceMatcher
from typing import Callable

from src.db.store import Database
from src.llm.base import LLMProvider
from src.state.models import GameState

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a concise Dota 2 coach. Give practical, safe-for-gameplay tips.
Respond with ONE short line (max 15 words) of actionable advice. No profanity."""


def _format_user_prompt(state: GameState) -> str:
    g = state.gsi
    lines = [
        f"Hero: {g.hero_name or 'unknown'}",
        f"Game time (s): {g.game_time_s}",
        f"Gold: {g.player_gold}, Level: {g.player_level}",
        f"K/D/A: {g.player_kills}/{g.player_deaths}/{g.player_assists}",
        f"GSI items: {g.player_items}",
        f"Score radiant-dire: {g.radiant_score}-{g.dire_score}",
    ]
    v = state.vision
    if v:
        heroes = ", ".join(f"{h.hero_id}@({h.x_norm:.2f},{h.y_norm:.2f})" for h in v.minimap_heroes[:12])
        lines.append(f"Vision minimap heroes: {heroes or 'none'}")
        wards = ", ".join(f"{w.kind}" for w in v.minimap_wards[:8])
        lines.append(f"Wards: {wards or 'none'}")
        items = [s.item_id for s in v.item_slots if s.item_id]
        lines.append(f"Vision item slots: {items}")
        if v.health_pct is not None:
            lines.append(f"Health est: {v.health_pct*100:.0f}%")
        if v.mana_pct is not None:
            lines.append(f"Mana est: {v.mana_pct*100:.0f}%")
        cds = [str(a.ability_index) for a in v.ability_cooldowns if a.on_cooldown]
        lines.append(f"Abilities on cooldown (indices): {','.join(cds) or 'none'}")
    return "\n".join(lines) + "\n\nGive ONE coaching tip now."


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class CoachService:
    def __init__(
        self,
        provider: LLMProvider,
        db: Database,
        get_match_id: Callable[[], int | None],
        throttle_seconds: float = 10.0,
        max_tokens: int = 120,
        dedup_threshold: float = 0.6,
        dedup_window: int = 5,
        on_tip: Callable[[str], None] | None = None,
    ) -> None:
        self._provider = provider
        self._db = db
        self._get_match_id = get_match_id
        self._throttle = max(3.0, throttle_seconds)
        self._max_tokens = max_tokens
        self._dedup_threshold = dedup_threshold
        self._dedup_window = dedup_window
        self._on_tip = on_tip
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    def _is_duplicate(self, tip: str, match_id: int | None) -> bool:
        recent = self._db.get_recent_tips(match_id, limit=self._dedup_window)
        for row in recent:
            if _similarity(tip, str(row.get("tip_text", ""))) >= self._dedup_threshold:
                return True
        return False

    async def maybe_generate_tip(self, state: GameState) -> str | None:
        async with self._lock:
            now = time.monotonic()
            if now - self._last_call < self._throttle:
                return None
            self._last_call = now

        user_prompt = _format_user_prompt(state)
        match_id = self._get_match_id()

        t0 = time.perf_counter()
        try:
            text = await self._provider.generate(SYSTEM_PROMPT, user_prompt, self._max_tokens)
        except Exception:
            log.exception("LLM generation failed")
            return None
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if not text:
            return None

        if self._is_duplicate(text, match_id):
            log.debug("Tip deduplicated: %s", text[:60])
            return None

        self._db.save_coaching_tip(
            match_id=match_id,
            game_time=state.gsi.game_time_s,
            tip_text=text,
            prompt_snapshot=user_prompt,
            latency_ms=latency_ms,
        )

        if self._on_tip:
            self._on_tip(text)
        return text

    async def answer_user_question(self, question: str, state: GameState) -> str | None:
        """Direct question from the user -- no throttle, no dedup."""
        context = _format_user_prompt(state)
        full_prompt = f"{context}\n\nThe player asks: {question}\n\nAnswer concisely (1-3 sentences)."
        match_id = self._get_match_id()
        t0 = time.perf_counter()
        try:
            text = await self._provider.generate(SYSTEM_PROMPT, full_prompt, self._max_tokens * 2)
        except Exception:
            log.exception("LLM chat answer failed")
            return None
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if text:
            self._db.save_coaching_tip(
                match_id=match_id,
                game_time=state.gsi.game_time_s,
                tip_text=text,
                category="chat",
                prompt_snapshot=full_prompt,
                latency_ms=latency_ms,
            )
        return text
