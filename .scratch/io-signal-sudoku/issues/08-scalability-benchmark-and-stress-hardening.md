# 08: Scalability Benchmark & Stress Hardening (10,000 Signals in <60s)

**What to build:** High-performance guarantee: an automated synthetic generator creating 10,000 signals across 1,000 cables. Confirms end-to-end execution completes in under 60 seconds with 0 rule violations and profiles memory/solver performance for hackathon evaluation.

**Blocked by:** 07: Revision Diff & Perturbation Minimization Engine (Rev A vs Rev B)

**Status:** ready-for-agent

- [ ] Synthetic generator script creating realistic industrial signal batches (1,000, 5,000, and 10,000 signals) with mixed cable sizes, A/B segregation, and IO types.
- [ ] End-to-end performance benchmark script measuring solve time, memory usage, and export generation.
- [ ] Optimization of CP-SAT search strategies, indicator cuts, and pandas operations to guarantee <60s runtime for 10,000 signals.
- [ ] Automated invariant audit proves 0 segregation violations, 100% contiguity, and exact capacity limits on the full 10,000 signal set.
- [ ] Evaluator-ready demo script demonstrating a 1-click test run with live telemetry.
