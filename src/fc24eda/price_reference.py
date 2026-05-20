from __future__ import annotations

from typing import Any


def max_team_price(players: list[dict[str, Any]]) -> int:
    prices = sorted((int(player.get("price") or 0) for player in players), reverse=True)
    return sum(prices[:11])


def min_team_price(players: list[dict[str, Any]]) -> int:
    prices = sorted(int(player.get("price") or 0) for player in players)
    return sum(prices[:11])

