from __future__ import annotations

from pathlib import Path
from typing import Any

from .data_loader import load_challenges, load_players, select_price_bounds
from .eda_solver import result_to_row, run_umda_for_challenge
from .reporting import RAW_FIELDNAMES, count_requirements, read_csv, write_csv


def run_umda_experiment(
    mode: str,
    seeds: list[int],
    size_gen: int,
    max_iter: int,
    alpha: float,
    challenge_limit: int | None,
    output_path: str | Path,
    resume: bool = False,
) -> list[dict[str, Any]]:
    players = load_players()
    challenges = load_challenges()
    if challenge_limit is not None:
        challenges = challenges[:challenge_limit]
    price_bounds = select_price_bounds(mode)

    output_path = Path(output_path)
    rows: list[dict[str, Any]] = read_csv(output_path) if resume and output_path.exists() else []
    completed = {
        ("umda", row["mode"], int(row["seed"]), row["challenge_name"])
        for row in rows
    }

    for seed in seeds:
        for challenge in challenges:
            key = ("umda", mode, seed, challenge["name"])
            if key in completed:
                continue
            result = run_umda_for_challenge(
                players=players,
                challenge=challenge,
                price_bounds=price_bounds,
                seed=seed,
                mode=mode,
                size_gen=size_gen,
                max_iter=max_iter,
                alpha=alpha,
            )
            rows.append(result_to_row(result, count_requirements(challenge["requirements"])))
            completed.add(key)
            write_csv(output_path, rows, RAW_FIELDNAMES)
    return rows
