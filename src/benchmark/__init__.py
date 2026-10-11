"""Scalability benchmark, stress testing, and synthetic data generation package."""

from src.benchmark.runner import (
    BenchmarkMetrics,
    run_single_benchmark,
    run_scalability_benchmark,
)
from src.benchmark.synthetic_generator import (
    generate_synthetic_signals,
    generate_synthetic_dataframe,
    generate_synthetic_excel,
    generate_batch_1k,
    generate_batch_5k,
    generate_batch_10k,
)

__all__ = [
    "BenchmarkMetrics",
    "run_single_benchmark",
    "run_scalability_benchmark",
    "generate_synthetic_signals",
    "generate_synthetic_dataframe",
    "generate_synthetic_excel",
    "generate_batch_1k",
    "generate_batch_5k",
    "generate_batch_10k",
]
