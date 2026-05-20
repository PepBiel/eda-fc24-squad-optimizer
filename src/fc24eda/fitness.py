from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .sbc_core import build_team_from_indices


PENALTY_PER_UNMET_REQUIREMENT = 0.5

CLUB_THRESHOLDS = [(2, 1), (4, 2), (7, 3)]
LEAGUE_THRESHOLDS = [(3, 1), (5, 2), (8, 3)]
NATIONALITY_THRESHOLDS = [(2, 1), (5, 2), (8, 3)]


@dataclass(frozen=True)
class EvaluationResult:
    fitness: float
    unmet_requirements: int
    team_info: dict[str, Any]
    indices: list[int]

    @property
    def team_price(self) -> int:
        return int(self.team_info["team_price"])

    @property
    def chemistry(self) -> int:
        return int(self.team_info["team_chemistry"])

    @property
    def overall(self) -> float:
        return float(self.team_info["overall"])


def division_score(value: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return abs((value / reference) - 1)


def normalize_team_price(team_price: float, min_price: float, max_price: float) -> float:
    if max_price == min_price:
        return 0.0
    return (team_price - min_price) / (max_price - min_price)


def calculate_team_average_from_info(team_info: dict[str, Any]) -> float:
    total_rating = sum(int(score) * count for score, count in team_info["ratings"].items())
    num_players = sum(team_info["ratings"].values())
    if num_players == 0:
        return 0.0

    average_rating = total_rating / num_players
    excess_sum = sum(
        (int(score) - average_rating) * count
        for score, count in team_info["ratings"].items()
        if int(score) > average_rating
    )
    adjusted_total = total_rating + excess_sum
    return adjusted_total / num_players


def calculate_chemistry_points(count: int, thresholds: list[tuple[int, int]]) -> int:
    points = 0
    for threshold, point in thresholds:
        if count >= threshold:
            points = point
        else:
            break
    return points


def player_positions(player: dict[str, Any]) -> list[str]:
    return [position.strip() for position in str(player.get("position", "")).replace(",", " ").split()]


def is_position_compatible(player: dict[str, Any], assigned_position: str) -> bool:
    return assigned_position in player_positions(player)


def calculate_player_chemistry(
    player: dict[str, Any],
    team_info: dict[str, Any],
    assigned_position: str,
) -> int:
    if not is_position_compatible(player, assigned_position):
        return 0

    version = str(player.get("version", ""))
    if "Icon" in version or "ICON" in version or "Hero" in version:
        return 3

    club = player["club"]
    league = player["league"]
    nationality = player["nacionality"]
    club_points = calculate_chemistry_points(team_info["clubs_chemistry"].get(club, 0), CLUB_THRESHOLDS)
    league_points = calculate_chemistry_points(team_info["leagues_chemistry"].get(league, 0), LEAGUE_THRESHOLDS)
    nationality_points = calculate_chemistry_points(
        team_info["nationalities_chemistry"].get(nationality, 0),
        NATIONALITY_THRESHOLDS,
    )
    return min(club_points + league_points + nationality_points, 3)


def calculate_info(team: list[dict[str, Any]]) -> dict[str, Any]:
    team_info: dict[str, Any] = {
        "ratings": {},
        "nationalities": {},
        "leagues": {},
        "clubs": {},
        "versions": {},
        "nationalities_chemistry": {},
        "leagues_chemistry": {},
        "clubs_chemistry": {},
        "overall": 0.0,
        "overall_rounded": 0,
        "team_price": 0,
        "team_chemistry": 0,
        "players_chemistry": [],
        "players": 0,
    }

    for slot in team:
        player = slot["player"]
        rating = int(player["rating"])
        nationality = player["nacionality"]
        league = player["league"]
        club = player["club"]
        version = player["version"]

        team_info["ratings"][rating] = team_info["ratings"].get(rating, 0) + 1
        team_info["nationalities"][nationality] = team_info["nationalities"].get(nationality, 0) + 1
        team_info["leagues"][league] = team_info["leagues"].get(league, 0) + 1
        team_info["clubs"][club] = team_info["clubs"].get(club, 0) + 1
        team_info["versions"][version] = team_info["versions"].get(version, 0) + 1

        if is_position_compatible(player, slot["assigned_position"]):
            team_info["nationalities_chemistry"][nationality] = (
                team_info["nationalities_chemistry"].get(nationality, 0) + 1
            )
            team_info["leagues_chemistry"][league] = team_info["leagues_chemistry"].get(league, 0) + 1
            team_info["clubs_chemistry"][club] = team_info["clubs_chemistry"].get(club, 0) + 1

        team_info["team_price"] += int(player.get("price") or 0)
        team_info["players"] += 1
        team_info["overall"] = calculate_team_average_from_info(team_info)
        team_info["overall_rounded"] = math.floor(team_info["overall"])

    for slot in team:
        player = slot["player"]
        version = str(player.get("version", ""))
        if "Icon" in version or "ICON" in version:
            if is_position_compatible(player, slot["assigned_position"]):
                nationality = player["nacionality"]
                team_info["nationalities_chemistry"][nationality] = (
                    team_info["nationalities_chemistry"].get(nationality, 0) + 1
                )
                for league in team_info["leagues"]:
                    team_info["leagues_chemistry"][league] = team_info["leagues_chemistry"].get(league, 0) + 1

    for slot in team:
        player = slot["player"]
        version = str(player.get("version", ""))
        if "Hero" in version:
            if is_position_compatible(player, slot["assigned_position"]):
                league = player["league"]
                team_info["leagues_chemistry"][league] = team_info["leagues_chemistry"].get(league, 0) + 1

    team_chemistry = 0
    for slot in team:
        player_chemistry = calculate_player_chemistry(
            slot["player"],
            team_info,
            slot["assigned_position"],
        )
        team_chemistry += player_chemistry
        team_info["players_chemistry"].append(
            {
                "player_name": slot["player"]["name"],
                "chemistry": player_chemistry,
            }
        )

    team_info["team_chemistry"] = team_chemistry
    return team_info


def calculate_fitness(
    team_info: dict[str, Any],
    requirements: dict[str, Any],
    price_bounds: dict[str, Any],
) -> tuple[float, int]:
    requirement_score = 0.0
    unmet_requirements = 0

    average_req = requirements.get("average", {})
    chemistry_req = requirements.get("chemistry", {})
    nationalities_req = requirements.get("nationalities", {})
    clubs_req = requirements.get("clubs", {})
    leagues_req = requirements.get("leagues", {})
    versions_req = requirements.get("versions", {})

    min_avg = average_req.get("min")
    if min_avg is not None:
        requirement_score += division_score(team_info["overall"], min_avg)
        if team_info["overall"] < min_avg:
            unmet_requirements += 1

    chemistry_unmet, chemistry_score = _score_min_max_scalar(
        team_info["team_chemistry"],
        chemistry_req.get("min"),
        chemistry_req.get("max"),
    )
    unmet_requirements += chemistry_unmet
    requirement_score += chemistry_score

    player_min_chem = chemistry_req.get("player_min")
    if player_min_chem is not None:
        failed = False
        for player in team_info["players_chemistry"]:
            if player["chemistry"] < player_min_chem:
                requirement_score += division_score(player["chemistry"], player_min_chem)
                failed = True
        if failed:
            unmet_requirements += 1

    player_max_chem = chemistry_req.get("player_max")
    if player_max_chem is not None:
        failed = False
        for player in team_info["players_chemistry"]:
            if player["chemistry"] > player_max_chem:
                requirement_score += division_score(player["chemistry"], player_max_chem)
                failed = True
        if failed:
            unmet_requirements += 1

    requirement_score, unmet_requirements = _score_group_requirements(
        requirement_score,
        unmet_requirements,
        team_info["nationalities"],
        nationalities_req,
    )
    requirement_score, unmet_requirements = _score_group_requirements(
        requirement_score,
        unmet_requirements,
        team_info["clubs"],
        clubs_req,
    )
    requirement_score, unmet_requirements = _score_group_requirements(
        requirement_score,
        unmet_requirements,
        team_info["leagues"],
        leagues_req,
    )
    requirement_score, unmet_requirements = _score_version_requirements(
        requirement_score,
        unmet_requirements,
        team_info["versions"],
        versions_req,
    )

    normalized_cost = normalize_team_price(
        team_info["team_price"],
        float(price_bounds["min_team_price"]),
        float(price_bounds["max_team_price"]),
    )
    requirement_score += normalized_cost
    requirement_score += unmet_requirements * PENALTY_PER_UNMET_REQUIREMENT
    return requirement_score, unmet_requirements


def _score_min_max_scalar(
    value: float,
    min_value: float | None,
    max_value: float | None,
) -> tuple[int, float]:
    unmet = 0
    score = 0.0
    if min_value is not None and value < min_value:
        unmet += 1
        score += division_score(value, min_value)
    if max_value is not None and value > max_value:
        unmet += 1
        score += division_score(value, max_value)
    return unmet, score


def _score_group_requirements(
    requirement_score: float,
    unmet_requirements: int,
    counts: dict[str, int],
    requirement: dict[str, Any],
) -> tuple[float, int]:
    for item in requirement.get("min") or []:
        name = item["name"]
        number = item["number"]
        if counts.get(name, 0) < number:
            unmet_requirements += 1
            requirement_score += division_score(counts.get(name, 0), number)

    for item in requirement.get("max") or []:
        name = item["name"]
        number = item["number"]
        if counts.get(name, 0) > number:
            unmet_requirements += 1
            requirement_score += division_score(counts.get(name, 0), number)

    exact = requirement.get("exact")
    if exact is not None and len(counts) != exact:
        unmet_requirements += 1
        requirement_score += division_score(len(counts), exact)

    player_min = requirement.get("player_min")
    if player_min is not None:
        failed = False
        for count in counts.values():
            if count < player_min:
                requirement_score += division_score(count, player_min)
                failed = True
        if failed:
            unmet_requirements += 1

    player_max = requirement.get("player_max")
    if player_max is not None:
        failed = False
        for count in counts.values():
            if count > player_max:
                requirement_score += division_score(count, player_max)
                failed = True
        if failed:
            unmet_requirements += 1

    return requirement_score, unmet_requirements


def _score_version_requirements(
    requirement_score: float,
    unmet_requirements: int,
    versions: dict[str, int],
    requirement: dict[str, Any],
) -> tuple[float, int]:
    for item in requirement.get("min") or []:
        name = item["name"]
        number = item["number"]
        count = sum(count for version, count in versions.items() if name in version)
        if count < number:
            unmet_requirements += 1
            requirement_score += division_score(count, number)

    for item in requirement.get("max") or []:
        name = item["name"]
        number = item["number"]
        count = sum(count for version, count in versions.items() if name in version)
        if count > number:
            unmet_requirements += 1
            requirement_score += division_score(count, number)

    return requirement_score, unmet_requirements


def evaluate_solution(
    indices: list[int],
    players: list[dict[str, Any]],
    challenge: dict[str, Any],
    price_bounds: dict[str, Any],
) -> EvaluationResult:
    normalized_indices = [int(i) for i in indices]
    team = build_team_from_indices(normalized_indices, players, challenge["positions"])
    team_info = calculate_info(team)
    fitness, unmet = calculate_fitness(team_info, challenge["requirements"], price_bounds)
    return EvaluationResult(
        fitness=fitness,
        unmet_requirements=unmet,
        team_info=team_info,
        indices=normalized_indices,
    )
