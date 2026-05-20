from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fc24eda.experiments import run_umda_experiment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FC24 SBC optimization experiments.")
    parser.add_argument("--algorithm", choices=["umda"], required=True)
    parser.add_argument("--mode", choices=["club", "bd"], required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--max-iter", type=int, default=800)
    parser.add_argument("--size-gen", type=int, default=200)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--challenge-limit", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output
    if output is None:
        suffix = "sample" if args.challenge_limit else "full"
        output = PROJECT_ROOT / "results" / "raw" / f"{args.algorithm}_{args.mode}_{suffix}.csv"

    if args.algorithm == "umda":
        rows = run_umda_experiment(
            mode=args.mode,
            seeds=args.seeds,
            size_gen=args.size_gen,
            max_iter=args.max_iter,
            alpha=args.alpha,
            challenge_limit=args.challenge_limit,
            output_path=output,
            resume=args.resume,
        )
    else:
        raise ValueError(f"Unsupported algorithm: {args.algorithm}")

    print(f"Wrote {len(rows)} rows to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
