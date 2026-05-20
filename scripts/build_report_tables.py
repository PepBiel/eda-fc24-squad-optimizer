from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fc24eda.data_loader import load_challenges
from fc24eda.reporting import (
    parse_original_ga_txt,
    read_csv,
    summarize_rows,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build summary CSV files for report tables.")
    parser.add_argument("--include-raw", nargs="*", type=Path, default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    total_requirements_per_iteration = sum(
        _count_requirements(challenge["requirements"]) for challenge in load_challenges()
    )
    historical_total = total_requirements_per_iteration * 5

    original_rows = []
    original_rows.extend(
        parse_original_ga_txt(
            PROJECT_ROOT / "results" / "original_ga" / "Resultados_normal_1.txt",
            algorithm="ga",
            mode="club",
        )
    )
    original_rows.extend(
        parse_original_ga_txt(
            PROJECT_ROOT / "results" / "original_ga" / "Resultados_bd_1.txt",
            algorithm="ga",
            mode="bd",
        )
    )

    summary_rows = [
        summarize_rows(
            [row for row in original_rows if row["mode"] == "club"],
            historical_total,
        ),
        summarize_rows(
            [row for row in original_rows if row["mode"] == "bd"],
            historical_total,
        ),
    ]

    for raw_path in args.include_raw:
        rows = read_csv(raw_path)
        if not rows:
            continue
        total = sum(int(row["total_requirements"]) for row in rows)
        summary_rows.append(summarize_rows(rows, total))

    write_csv(PROJECT_ROOT / "results" / "summary" / "comparison_summary.csv", summary_rows)
    print("Wrote results/summary/comparison_summary.csv")
    return 0


def _count_requirements(requirements):
    from fc24eda.reporting import count_requirements

    return count_requirements(requirements)


if __name__ == "__main__":
    raise SystemExit(main())

