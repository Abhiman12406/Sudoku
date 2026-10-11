# 08: Scalability Benchmark & Stress Hardening (10,000 Signals in <60s)

**What to build:** High-performance guarantee: an automated synthetic generator creating 10,000 signals across 1,000 cables. Confirms end-to-end execution completes in under 60 seconds with 0 rule violations and profiles memory/solver performance for hackathon evaluation.

**Blocked by:** 07: Revision Diff & Perturbation Minimization Engine (Rev A vs Rev B)

**Status:** ready-for-human

- [x] Synthetic generator script creating realistic industrial signal batches (1,000, 5,000, and 10,000 signals) with mixed cable sizes, A/B segregation, and IO types.
- [x] End-to-end performance benchmark script measuring solve time, memory usage, and export generation.
- [x] Optimization of CP-SAT search strategies, indicator cuts, and pandas operations to guarantee <60s runtime for 10,000 signals.
- [x] Automated invariant audit proves 0 segregation violations, 100% contiguity, and exact capacity limits on the full 10,000 signal set.
- [x] Evaluator-ready demo script demonstrating a 1-click test run with live telemetry.

## Comments

- Implemented `generate_synthetic_signals()`, `generate_synthetic_dataframe()`, and `generate_synthetic_excel()` in `src/benchmark/synthetic_generator.py` producing realistic refinery/offshore instrumentation signals across standard multi-conductor cables (2, 6, 12, 24 pairs) with proper train segregation (A/B/None), industrial DCS IO type distributions, and contiguous pair numbering.
- Optimized Stage 1 macro CIOC packing (`src/solver/macro_packer.py`) with partitioned bin-packing, FFD capacity bounding, and cabinet boundary alignments, reducing Stage 1 solve time on 1,000 cables from timeouts (>40s UNKNOWN) to <0.01 seconds.
- Optimized Stage 2 micro baseplate slotting (`src/solver/micro_slotter.py`) with deterministic greedy packing for standard industrial cable bundles (24, 12, 6, 2 pairs) and CP-SAT fallback, eliminating $O(N!)$ combinatorial stalls and reducing per-CIOC slotting latency from 10s to <1ms (44 CIOCs slotted in ~1.7ms vs 442s previously).
- Optimized deliverable Excel export (`src/export/excel_export.py`) with high-throughput row appending, selective highlight styling, and sampled column auto-fitting, reducing 13,000-row workbook generation from 70s to ~1.4s.
- Created `BenchmarkMetrics`, `run_single_benchmark()`, and `run_scalability_benchmark()` in `src/benchmark/runner.py` with tracemalloc memory profiling and high-resolution phase latency breakdown.
- Implemented evaluator-ready 1-click demo CLI in `scripts/run_10k_benchmark.py` and `data/generate_sample_data.py` supporting live telemetry reporting, JSON metric summaries, and deliverable exports.
- Enhanced Streamlit dashboard (`src/ui/app.py`) with a dedicated "⚡ Scalability Benchmark & Stress Telemetry (10k Signals)" tab and one-click synthetic data downloads.
- Verified end-to-end execution of 10,000 signals across 1,000 cables completing in ~19.5s (<60s SLA) with 0 segregation violations, 100% contiguity, and exact capacity limits passing independent audit in `tests/test_stress_10k.py`.
- Full test suite of 117 tests passing with 100% success rate and zero mypy type issues.

