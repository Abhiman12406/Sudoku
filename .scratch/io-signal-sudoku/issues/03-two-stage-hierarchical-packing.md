# 03: Two-Stage Hierarchical Packing & Cable Contiguity (Trunk Cables)

**What to build:** Elimination of cable fragmentation: groups signals into rigid multi-conductor cable blocks (2, 6, 12, 24 pairs). The CP-SAT solver packs whole cables onto baseplates in strict ascending pair order, explicitly labels unused pairs as `WIRED SPARE`, and visually groups cable blocks on the Streamlit DIN-rail view.

**Blocked by:** 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**Status:** ready-for-agent

- [ ] Construct `CableBlock` bundles grouping signals by cable ID with declared pair sizes (2, 6, 12, 24 pairs).
- [ ] Implement Stage 1 macro-packing solver assigning cable blocks to CIOC containers (max 8 baseplates = 96 channels).
- [ ] Implement Stage 2 micro-slotting solver assigning cable pairs contiguously in ascending order across baseplates.
- [ ] Enforce that 24-pair cables span exactly 2 consecutive baseplates and 12-pair cables span exactly 1 baseplate.
- [ ] Explicitly allocate unused cable pairs as `WIRED SPARE` records.
- [ ] Render visually grouped cable blocks with pair numbers on the Streamlit DIN-rail rack visualizer.
- [ ] Verify 100% contiguity and zero pair shuffling via automated tests.
