from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .fitness import EvaluationResult, evaluate_solution, is_position_compatible
from .sbc_core import build_name_repair_candidate_order, repair_duplicate_names_deterministic


@dataclass(frozen=True)
class SolverResult:
    algorithm: str
    mode: str
    seed: int
    challenge_name: str
    solution: list[int]
    evaluation: EvaluationResult
    runtime_seconds: float


def run_umda_for_challenge(
    players: list[dict[str, Any]],
    challenge: dict[str, Any],
    price_bounds: dict[str, Any],
    seed: int,
    mode: str,
    size_gen: int = 200,
    max_iter: int = 800,
    alpha: float = 0.5,
) -> SolverResult:
    umda_cls = _load_umda_cat()
    np.random.seed(seed)

    n_variables = len(challenge["positions"])
    player_ids = np.arange(len(players), dtype=np.int64)
    possible_values = np.tile(player_ids, (n_variables, 1))
    frequency = np.full(
        (n_variables, len(players)),
        1.0 / len(players),
        dtype=np.float64,
    )
    repair_order = build_name_repair_candidate_order(players)

    def cost_function(solution: Any) -> float:
        raw = [int(value) for value in np.asarray(solution).tolist()]
        repaired = repair_duplicate_names_deterministic(raw, players, repair_order)
        return evaluate_solution(repaired, players, challenge, price_bounds).fitness

    eda = umda_cls(
        size_gen=size_gen,
        max_iter=max_iter,
        dead_iter=max_iter,
        n_variables=n_variables,
        alpha=alpha,
        frequency=frequency,
        possible_values=possible_values,
        disp=False,
    )
    # UMDAcat 1.1.4 sets w_noise=-1, which becomes "" and breaks integer generations.
    eda.w_noise = 0

    started_at = time.perf_counter()
    raw_result = eda.minimize(cost_function, output_runtime=False)
    runtime_seconds = time.perf_counter() - started_at

    best_solution = _extract_best_solution(raw_result, eda)
    repaired_solution = repair_duplicate_names_deterministic(best_solution, players, repair_order)
    evaluation = evaluate_solution(repaired_solution, players, challenge, price_bounds)

    return SolverResult(
        algorithm="umda",
        mode=mode,
        seed=seed,
        challenge_name=challenge["name"],
        solution=repaired_solution,
        evaluation=evaluation,
        runtime_seconds=runtime_seconds,
    )


def run_structured_umda_for_challenge(
    players: list[dict[str, Any]],
    challenge: dict[str, Any],
    price_bounds: dict[str, Any],
    seed: int,
    mode: str,
    size_gen: int = 200,
    max_iter: int = 800,
    alpha: float = 0.5,
    domain_size: int = 250,
) -> SolverResult:
    umda_cls = _load_umda_cat()
    np.random.seed(seed)

    n_variables = len(challenge["positions"])
    slot_domains = build_structured_slot_domains(players, challenge, domain_size)
    local_domain_size = len(slot_domains[0])
    local_ids = np.arange(local_domain_size, dtype=np.int64)
    possible_values = np.tile(local_ids, (n_variables, 1))
    frequency = _rank_biased_frequency(n_variables, local_domain_size)
    repair_order = build_name_repair_candidate_order(players)

    def cost_function(solution: Any) -> float:
        local_solution = [int(value) for value in np.asarray(solution).tolist()]
        mapped = _map_local_solution(local_solution, slot_domains)
        repaired = _repair_duplicate_names_with_slot_domains(mapped, players, slot_domains, repair_order)
        return evaluate_solution(repaired, players, challenge, price_bounds).fitness

    eda = umda_cls(
        size_gen=size_gen,
        max_iter=max_iter,
        dead_iter=max_iter,
        n_variables=n_variables,
        alpha=alpha,
        frequency=frequency,
        possible_values=possible_values,
        disp=False,
    )
    eda.w_noise = 0

    started_at = time.perf_counter()
    raw_result = eda.minimize(cost_function, output_runtime=False)
    runtime_seconds = time.perf_counter() - started_at

    best_local_solution = _extract_best_solution(raw_result, eda)
    mapped_solution = _map_local_solution(best_local_solution, slot_domains)
    repaired_solution = _repair_duplicate_names_with_slot_domains(
        mapped_solution,
        players,
        slot_domains,
        repair_order,
    )
    evaluation = evaluate_solution(repaired_solution, players, challenge, price_bounds)

    return SolverResult(
        algorithm="umda_structured",
        mode=mode,
        seed=seed,
        challenge_name=challenge["name"],
        solution=repaired_solution,
        evaluation=evaluation,
        runtime_seconds=runtime_seconds,
    )


def build_structured_slot_domains(
    players: list[dict[str, Any]],
    challenge: dict[str, Any],
    domain_size: int,
) -> list[list[int]]:
    if domain_size < 11:
        raise ValueError("domain_size must be at least 11")

    actual_size = min(domain_size, len(players))
    domains = []
    for position in challenge["positions"]:
        compatible = [
            idx for idx, player in enumerate(players)
            if is_position_compatible(player, position)
        ]
        off_position = [
            idx for idx, player in enumerate(players)
            if not is_position_compatible(player, position)
        ]
        compatible.sort(key=lambda idx: _structured_candidate_score(players[idx], challenge, position))
        off_position.sort(key=lambda idx: _structured_candidate_score(players[idx], challenge, position))

        compatible_quota = max(1, int(actual_size * 0.85))
        selected = compatible[:compatible_quota]
        selected.extend(off_position[: actual_size - len(selected)])

        if len(selected) < actual_size:
            selected_names = set(selected)
            fallback = sorted(
                (idx for idx in range(len(players)) if idx not in selected_names),
                key=lambda idx: _structured_candidate_score(players[idx], challenge, position),
            )
            selected.extend(fallback[: actual_size - len(selected)])

        domains.append(selected[:actual_size])
    return domains


def _structured_candidate_score(
    player: dict[str, Any],
    challenge: dict[str, Any],
    assigned_position: str,
) -> tuple[float, int, int, str]:
    requirements = challenge["requirements"]
    position_penalty = 0 if is_position_compatible(player, assigned_position) else 1
    requirement_penalty = _player_requirement_penalty(player, requirements)
    min_average = (requirements.get("average") or {}).get("min") or 0
    rating = int(player.get("rating") or 0)
    rating_shortfall = max(0, int(min_average) - rating)
    price = int(player.get("price") or 0)
    # Cheap players just above the target average are preferred over expensive overkill.
    score = (
        requirement_penalty * 1000
        + position_penalty * 100
        + rating_shortfall * 10
        + max(0, rating - int(min_average)) * 0.1
        + price / 100000
    )
    return (score, price, -rating, str(player.get("name", "")))


def _player_requirement_penalty(player: dict[str, Any], requirements: dict[str, Any]) -> int:
    penalty = 0
    checks = [
        ("nationalities", "nacionality"),
        ("clubs", "club"),
        ("leagues", "league"),
    ]
    for requirement_key, player_key in checks:
        required_values = {
            item["name"]
            for item in (requirements.get(requirement_key, {}).get("min") or [])
        }
        if required_values and player.get(player_key) not in required_values:
            penalty += 1

    version_minimums = requirements.get("versions", {}).get("min") or []
    if version_minimums:
        version = str(player.get("version", ""))
        if not any(item["name"] in version for item in version_minimums):
            penalty += 1

    return penalty


def _rank_biased_frequency(n_variables: int, domain_size: int) -> np.ndarray:
    weights = np.linspace(1.0, 0.05, domain_size, dtype=np.float64)
    weights = weights / weights.sum()
    return np.tile(weights, (n_variables, 1))


def _map_local_solution(local_solution: list[int], slot_domains: list[list[int]]) -> list[int]:
    mapped = []
    for slot_idx, raw_value in enumerate(local_solution):
        domain = slot_domains[slot_idx]
        mapped.append(domain[int(raw_value) % len(domain)])
    return mapped


def _repair_duplicate_names_with_slot_domains(
    indices: list[int],
    players: list[dict[str, Any]],
    slot_domains: list[list[int]],
    fallback_order: list[int],
) -> list[int]:
    repaired: list[int] = []
    used_names: set[str] = set()

    for slot_idx, raw_idx in enumerate(indices):
        idx = int(raw_idx)
        name = str(players[idx].get("name", "")) if 0 <= idx < len(players) else ""
        if 0 <= idx < len(players) and name not in used_names:
            repaired.append(idx)
            used_names.add(name)
            continue

        replacement = None
        for candidate_idx in slot_domains[slot_idx]:
            candidate_name = str(players[candidate_idx].get("name", ""))
            if candidate_name not in used_names:
                replacement = candidate_idx
                break
        if replacement is None:
            for candidate_idx in fallback_order:
                candidate_name = str(players[candidate_idx].get("name", ""))
                if candidate_name not in used_names:
                    replacement = candidate_idx
                    break
        if replacement is None:
            raise ValueError("Not enough unique player names to build a squad")

        repaired.append(replacement)
        used_names.add(str(players[replacement].get("name", "")))

    return repaired


def _load_umda_cat() -> type:
    try:
        import torch  # noqa: F401
        from EDAspy.optimization import UMDAcat

        return UMDAcat
    except ImportError as first_error:
        try:
            import torch  # noqa: F401
            from EDAspy.optimization.univariate import UMDAcat

            return UMDAcat
        except ImportError:
            raise RuntimeError(
                "EDAspy is not installed or UMDAcat could not be imported. "
                "Install dependencies with: pip install -r requirements.txt"
            ) from first_error


def _extract_best_solution(raw_result: Any, eda: Any) -> list[int]:
    candidates = [
        getattr(raw_result, "best_ind", None),
        getattr(raw_result, "best_individual", None),
        getattr(raw_result, "best_solution", None),
        getattr(eda, "best_ind", None),
        getattr(eda, "best_individual", None),
        getattr(eda, "best_solution", None),
    ]

    if isinstance(raw_result, tuple) and raw_result:
        for item in reversed(raw_result):
            candidates.insert(0, item)
    if isinstance(raw_result, list) and raw_result and not isinstance(raw_result[0], (int, np.integer)):
        candidates.insert(0, raw_result[0])
    elif isinstance(raw_result, list):
        candidates.insert(0, raw_result)

    for candidate in candidates:
        if candidate is None:
            continue
        array = np.asarray(candidate)
        if array.ndim == 0:
            continue
        values = array.astype(int).tolist()
        if values and isinstance(values[0], list):
            values = values[0]
        if values:
            return [int(value) for value in values]

    raise RuntimeError(
        "Could not extract the best solution from EDAspy result. "
        f"Result type: {type(raw_result)!r}"
    )


def result_to_row(result: SolverResult, total_requirements: int) -> dict[str, Any]:
    unmet = result.evaluation.unmet_requirements
    return {
        "algorithm": result.algorithm,
        "mode": result.mode,
        "seed": result.seed,
        "challenge_name": result.challenge_name,
        "total_requirements": total_requirements,
        "unmet_requirements": unmet,
        "met_requirements": total_requirements - unmet,
        "fitness": result.evaluation.fitness,
        "team_price": result.evaluation.team_price,
        "overall": result.evaluation.overall,
        "chemistry": result.evaluation.chemistry,
        "runtime_seconds": result.runtime_seconds,
        "solution": " ".join(str(index) for index in result.solution),
    }


SolverFn = Callable[
    [list[dict[str, Any]], dict[str, Any], dict[str, Any], int, str, int, int, float],
    SolverResult,
]
