from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .fitness import EvaluationResult, evaluate_solution
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
