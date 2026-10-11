import subprocess
import sys
from pathlib import Path
import pytest


def test_benchmark_cli_quick_run(tmp_path):
    out_dir = tmp_path / "bench_out"
    cmd = [
        sys.executable,
        "scripts/run_10k_benchmark.py",
        "--signals", "300",
        "--output-dir", str(out_dir),
        "--no-export",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI failed with error:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "PASSED (0 Violations)" in res.stdout or "STATUS: PASS" in res.stdout
    assert "300 Signals" in res.stdout or "300 signals" in res.stdout


def test_benchmark_cli_suite_run(tmp_path):
    out_dir = tmp_path / "suite_out"
    cmd = [
        sys.executable,
        "scripts/run_10k_benchmark.py",
        "--suite",
        "--counts", "100", "200",
        "--output-dir", str(out_dir),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Suite CLI failed with error:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "SCALABILITY BENCHMARK SUITE SUMMARY" in res.stdout or "Benchmark Results" in res.stdout
    # Check that summary JSON was generated
    assert (out_dir / "benchmark_summary.json").exists()
