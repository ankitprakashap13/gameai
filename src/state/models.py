"""Unified game and vision state models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class HeroMinimapDetection:
    hero_id: str
    x_norm: float
    y_norm: float
    confidence: float


@dataclass
class WardDetection:
    kind: str  # observer | sentry
    x_norm: float
    y_norm: float
    confidence: float


@dataclass
class ItemSlotDetection:
    slot_index: int
    item_id: str | None
    confidence: float


@dataclass
class AbilityCooldownDetection:
    ability_index: int
    on_cooldown: bool
    cooldown_pct: float


@dataclass
class DraftHeroPick:
    """One hero portrait slot on the draft top bar."""

    slot_index: int
    hero_id: str | None
    confidence: float
    team: str  # "radiant" | "dire"


@dataclass
class DraftState:
    """Detected picks during hero selection (vision)."""

    ally_picks: list[DraftHeroPick]
    enemy_picks: list[DraftHeroPick]
    timestamp_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VisionState:
    """Output of the vision pipeline for one frame."""

    timestamp_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    minimap_heroes: list[HeroMinimapDetection] = field(default_factory=list)
    minimap_wards: list[WardDetection] = field(default_factory=list)
    item_slots: list[ItemSlotDetection] = field(default_factory=list)
    health_pct: float | None = None
    mana_pct: float | None = None
    ability_cooldowns: list[AbilityCooldownDetection] = field(default_factory=list)
    frame_width: int = 0
    frame_height: int = 0


@dataclass
class GSIParsedState:
    """Subset of Dota GSI commonly used for coaching."""

    raw: dict[str, Any] = field(default_factory=dict)
    hero_name: str | None = None
    game_time_s: float | None = None
    clock_time_s: float | None = None
    game_state: str | None = None
    player_gold: int | None = None
    player_level: int | None = None
    player_kills: int | None = None
    player_deaths: int | None = None
    player_assists: int | None = None
    player_items: list[str | None] = field(default_factory=list)
    map_name: str | None = None
    radiant_score: int | None = None
    dire_score: int | None = None
    player_team: str | None = None
    win_team: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GameState:
    """Merged GSI + vision snapshot for LLM and history."""

    gsi: GSIParsedState
    vision: VisionState | None = None
    draft: DraftState | None = None
    merged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
