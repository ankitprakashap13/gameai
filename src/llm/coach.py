"""Format game state into prompts; generate tips on meaningful events; persist and deduplicate."""

from __future__ import annotations

import asyncio
import logging
import time
from difflib import SequenceMatcher
from typing import Callable

from src.db.store import Database
from src.llm.base import LLMProvider
from src.state.models import DraftHeroPick, GameState

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a concise Dota 2 coach. Give practical, safe-for-gameplay tips.
Respond with ONE short line (max 15 words) of actionable advice. No profanity."""

SYSTEM_PROMPT_DRAFT = """You are a Dota 2 draft coach for Ranked All Pick.
Give ONE pick suggestion with a 1-2 sentence rationale. Be concise. No profanity."""

_MIN_COOLDOWN_S = 5.0


def _hero_label(hero_id: str | None) -> str:
    if not hero_id:
        return "(empty)"
    s = str(hero_id).replace("npc_dota_hero_", "").replace("_", " ").strip()
    return s.title() if s else "(empty)"


def _format_draft_line(label: str, picks: list[DraftHeroPick]) -> str:
    names = [_hero_label(p.hero_id) for p in picks]
    return f"{label}: [{', '.join(names)}]"


def _format_draft_prompt(state: GameState) -> str:
    d = state.draft
    if d is None:
        return _format_user_prompt(state)
    ally = _format_draft_line("Your team", d.ally_picks)
    enemy = _format_draft_line("Enemy team", d.enemy_picks)
    g = state.gsi
    player_side = g.player_team or "unknown"
    lines = [
        "Context: Ranked All Pick draft (vision-detected portraits; may be imperfect).",
        f"Player side (GSI): {player_side}",
        ally,
        enemy,
        "Infer missing roles from picks where possible.",
        "",
        "Suggest ONE hero the player should pick and explain why in 1-2 sentences.",
        "Focus on counter-picks and team synergy.",
    ]
    return "\n".join(lines)


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
        min_cooldown_seconds: float = _MIN_COOLDOWN_S,
        max_tokens: int = 120,
        dedup_threshold: float = 0.6,
        dedup_window: int = 5,
        on_tip: Callable[[str], None] | None = None,
    ) -> None:
        self._provider = provider
        self._db = db
        self._get_match_id = get_match_id
        self._min_cooldown = max(2.0, min_cooldown_seconds)
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

    async def on_event(self, state: GameState, reason: str) -> str | None:
        """Called by the aggregator when a meaningful game event is detected.

        Applies a minimum cooldown to avoid back-to-back LLM calls (e.g. multi-kill
        fires multiple kill events in quick succession), but otherwise trusts
        the caller to only invoke this on real events.
        """
        async with self._lock:
            now = time.monotonic()
            if now - self._last_call < self._min_cooldown:
                log.debug("Event '%s' skipped (cooldown)", reason)
                return None
            self._last_call = now

        log.info("Generating tip for event: %s", reason)
        in_draft = state.draft is not None
        user_prompt = _format_draft_prompt(state) if in_draft else _format_user_prompt(state)
        system = SYSTEM_PROMPT_DRAFT if in_draft else SYSTEM_PROMPT
        match_id = self._get_match_id()

        t0 = time.perf_counter()
        try:
            text = await self._provider.generate(system, user_prompt, self._max_tokens)
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
        """Direct question from the user -- no cooldown, no dedup."""
        in_draft = state.draft is not None
        context = _format_draft_prompt(state) if in_draft else _format_user_prompt(state)
        system = SYSTEM_PROMPT_DRAFT if in_draft else SYSTEM_PROMPT
        full_prompt = f"{context}\n\nThe player asks: {question}\n\nAnswer concisely (1-3 sentences)."
        match_id = self._get_match_id()
        t0 = time.perf_counter()
        try:
            text = await self._provider.generate(system, full_prompt, self._max_tokens * 2)
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
