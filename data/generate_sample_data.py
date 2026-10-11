#!/usr/bin/env python3
"""Generate sample customer IO MDB spreadsheets (1k, 5k, 10k signals) for demo & testing."""

import argparse
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.benchmark.synthetic_generator import generate_synthetic_excel


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate realistic DeltaV customer IO database files")
    parser.add_argument(
        "--count",
        type=int,
        default=10000,
        help="Number of signals to generate (default: 10,000)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/sample_10k_io.xlsx",
        help="Target output Excel file path (default: data/sample_10k_io.xlsx)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )

    args = parser.parse_args()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.count:,} realistic industrial signals -> {out_path} ...")
    generate_synthetic_excel(count=args.count, output_path=out_path, seed=args.seed)
    print(f"Done! File generated: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
