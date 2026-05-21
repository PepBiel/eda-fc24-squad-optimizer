from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fc24eda.data_loader import load_challenges, load_players
from fc24eda.fitness import evaluate_solution, explain_unmet_requirements
from fc24eda.reporting import read_csv


FIELDNAMES = [
    "algorithm",
    "mode",
    "challenge_name",
    "attempts",
    "total_requirements",
    "best_unmet_requirements",
    "best_met_requirements",
    "best_reliability_percent",
    "found_feasible_solution",
    "best_team_price",
    "best_overall",
    "best_chemistry",
    "best_seed",
    "best_unmet_details",
    "persistent_unmet_details",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a per-challenge feasibility report from raw experiment CSV files.",
    )
    parser.add_argument("--include-raw", nargs="+", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "summary" / "feasibility_report.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    players = load_players()
    challenges = {challenge["name"]: challenge for challenge in load_challenges()}

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for raw_path in args.include_raw:
        for row in read_csv(raw_path):
            key = (row["algorithm"], row["mode"], row["challenge_name"])
            groups.setdefault(key, []).append(row)

    report_rows = []
    zero_price_bounds = {"min_team_price": 0, "max_team_price": 0}
    for (algorithm, mode, challenge_name), rows in sorted(groups.items()):
        challenge = challenges[challenge_name]
        evaluated_rows = []
        for row in rows:
            solution = [int(value) for value in row["solution"].split()]
            evaluation = evaluate_solution(solution, players, challenge, zero_price_bounds)
            unmet_details = explain_unmet_requirements(evaluation.team_info, challenge["requirements"])
            evaluated_rows.append((row, evaluation, unmet_details))

        best_row, best_evaluation, best_details = min(
            evaluated_rows,
            key=lambda item: (
                item[1].unmet_requirements,
                item[1].fitness,
                item[1].team_price,
            ),
        )
        all_detail_sets = [set(details) for _, _, details in evaluated_rows]
        persistent_details = set.intersection(*all_detail_sets) if all_detail_sets else set()
        total_requirements = int(rows[0]["total_requirements"])
        best_unmet = best_evaluation.unmet_requirements
        best_met = total_requirements - best_unmet
        report_rows.append(
            {
                "algorithm": algorithm,
                "mode": mode,
                "challenge_name": challenge_name,
                "attempts": len(rows),
                "total_requirements": total_requirements,
                "best_unmet_requirements": best_unmet,
                "best_met_requirements": best_met,
                "best_reliability_percent": (best_met / total_requirements) * 100 if total_requirements else 0,
                "found_feasible_solution": best_unmet == 0,
                "best_team_price": best_evaluation.team_price,
                "best_overall": best_evaluation.overall,
                "best_chemistry": best_evaluation.chemistry,
                "best_seed": best_row["seed"],
                "best_unmet_details": ";".join(best_details),
                "persistent_unmet_details": ";".join(sorted(persistent_details)),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
