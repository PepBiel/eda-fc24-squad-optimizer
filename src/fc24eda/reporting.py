from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path
from typing import Any


RAW_FIELDNAMES = [
    "algorithm",
    "mode",
    "seed",
    "challenge_name",
    "total_requirements",
    "unmet_requirements",
    "met_requirements",
    "fitness",
    "team_price",
    "overall",
    "chemistry",
    "runtime_seconds",
    "solution",
]


def count_requirements(requirements: dict[str, Any]) -> int:
    total = 0
    for value in requirements.values():
        if isinstance(value, dict):
            for nested in value.values():
                if nested is None:
                    continue
                if isinstance(nested, list):
                    total += len(nested)
                else:
                    total += 1
        elif value is not None:
            total += 1
    return total


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else RAW_FIELDNAMES
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parse_original_ga_txt(path: str | Path, algorithm: str, mode: str) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    json_blocks = re.findall(r"\[\s*\{.*?\}\s*\]", text, flags=re.DOTALL)
    rows: list[dict[str, Any]] = []
    for iteration, block in enumerate(json_blocks, start=1):
        try:
            entries = json.loads(block)
        except json.JSONDecodeError:
            continue
        for entry in entries:
            rows.append(
                {
                    "algorithm": algorithm,
                    "mode": mode,
                    "seed": iteration - 1,
                    "iteration": iteration,
                    "challenge_name": entry["challenge_name"],
                    "unmet_requirements": int(entry["unmet_requirements"]),
                    "team_price": int(entry["team_price"]),
                }
            )
    return rows


def summarize_rows(rows: list[dict[str, Any]], total_requirements: int) -> dict[str, Any]:
    if not rows:
        raise ValueError("Cannot summarize empty rows")
    unmet = [int(row["unmet_requirements"]) for row in rows]
    prices = [float(row["team_price"]) for row in rows]
    unmet_sum = sum(unmet)
    met = total_requirements - unmet_sum
    return {
        "algorithm": rows[0]["algorithm"],
        "mode": rows[0]["mode"],
        "runs": len(rows),
        "total_requirements": total_requirements,
        "met_requirements": met,
        "unmet_requirements": unmet_sum,
        "reliability_percent": (met / total_requirements) * 100 if total_requirements else 0,
        "mean_price": statistics.mean(prices),
        "median_price": statistics.median(prices),
        "max_price": max(prices),
        "min_price": min(prices),
        "mean_runtime_seconds": _mean_optional(rows, "runtime_seconds"),
        "mean_fitness": _mean_optional(rows, "fitness"),
    }


def _mean_optional(rows: list[dict[str, Any]], key: str) -> float | str:
    values = []
    for row in rows:
        value = row.get(key)
        if value in (None, "", "None"):
            continue
        values.append(float(value))
    return statistics.mean(values) if values else ""

