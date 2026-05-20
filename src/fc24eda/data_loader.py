from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAYERS_PATH = PROJECT_ROOT / "data" / "players" / "jugadores.json"
DEFAULT_CHALLENGES_PATH = PROJECT_ROOT / "data" / "challenges" / "sbc_results.json"
DEFAULT_PRICE_BOUNDS_PATH = PROJECT_ROOT / "config" / "price_bounds.json"


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_players(path: str | Path = DEFAULT_PLAYERS_PATH) -> list[dict[str, Any]]:
    players = load_json(path)
    if not isinstance(players, list):
        raise ValueError(f"Expected a list of players in {path}")
    return players


def load_challenges(path: str | Path = DEFAULT_CHALLENGES_PATH) -> list[dict[str, Any]]:
    data = load_json(path)
    teams = data.get("teams")
    if not isinstance(teams, list):
        raise ValueError(f"Expected a JSON object with a 'teams' list in {path}")
    return teams


def load_price_bounds(path: str | Path = DEFAULT_PRICE_BOUNDS_PATH) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a price bounds object in {path}")
    return data


def select_price_bounds(mode: str, path: str | Path = DEFAULT_PRICE_BOUNDS_PATH) -> dict[str, Any]:
    mode_key = mode.lower()
    bounds = load_price_bounds(path)
    if mode_key not in bounds:
        valid = ", ".join(sorted(bounds))
        raise ValueError(f"Unknown price mode '{mode}'. Valid modes: {valid}")
    return bounds[mode_key]

