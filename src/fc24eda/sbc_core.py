from __future__ import annotations

from typing import Any, Iterable


def player_name(player: dict[str, Any]) -> str:
    return str(player.get("name", ""))


def build_team_from_indices(
    indices: Iterable[int],
    players: list[dict[str, Any]],
    positions: list[str],
) -> list[dict[str, Any]]:
    team = []
    for idx, assigned_position in zip(indices, positions):
        team.append(
            {
                "player": players[int(idx)],
                "assigned_position": assigned_position,
            }
        )
    return team


def build_name_repair_candidate_order(players: list[dict[str, Any]]) -> list[int]:
    return sorted(
        range(len(players)),
        key=lambda idx: (
            int(players[idx].get("price") or 0),
            -int(players[idx].get("rating") or 0),
            player_name(players[idx]),
            idx,
        ),
    )


def repair_duplicate_names_deterministic(
    indices: Iterable[int],
    players: list[dict[str, Any]],
    candidate_order: list[int] | None = None,
) -> list[int]:
    """Apply the GA rule: one player name per squad."""

    if candidate_order is None:
        candidate_order = build_name_repair_candidate_order(players)

    repaired: list[int] = []
    used_names: set[str] = set()

    for raw_idx in indices:
        idx = int(raw_idx)
        valid = 0 <= idx < len(players)
        name = player_name(players[idx]) if valid else ""
        if valid and name not in used_names:
            repaired.append(idx)
            used_names.add(name)
            continue

        replacement = None
        for candidate_idx in candidate_order:
            candidate_name = player_name(players[candidate_idx])
            if candidate_name not in used_names:
                replacement = candidate_idx
                break
        if replacement is None:
            raise ValueError("Not enough unique player names to build a squad")

        repaired.append(replacement)
        used_names.add(player_name(players[replacement]))

    return repaired
