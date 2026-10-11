# 03: Two-Stage Hierarchical Packing & Cable Contiguity (Trunk Cables)

**What to build:** Elimination of cable fragmentation: groups signals into rigid multi-conductor cable blocks (2, 6, 12, 24 pairs). The CP-SAT solver packs whole cables onto baseplates in strict ascending pair order, explicitly labels unused pairs as `WIRED SPARE`, and visually groups cable blocks on the Streamlit DIN-rail view.

**Blocked by:** 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**Status:** resolved

- [x] Construct `CableBlock` bundles grouping signals by cable ID with declared pair sizes (2, 6, 12, 24 pairs).
- [x] Implement Stage 1 macro-packing solver assigning cable blocks to CIOC containers (max 8 baseplates = 96 channels).
- [x] Implement Stage 2 micro-slotting solver assigning cable pairs contiguously in ascending order across baseplates.
- [x] Enforce that 24-pair cables span exactly 2 consecutive baseplates and 12-pair cables span exactly 1 baseplate.
- [x] Explicitly allocate unused cable pairs as `WIRED SPARE` records.
- [x] Render visually grouped cable blocks with pair numbers on the Streamlit DIN-rail rack visualizer.
- [x] Verify 100% contiguity and zero pair shuffling via automated tests.

## Comments

- Implemented `CableBlock` bundles grouping signals by cable ID with declared/inferred standard pair sizes (2, 6, 12, 24 pairs) in `src/domain/cable.py` and `src/domain/models.py`.
- Implemented Stage 1 macro-packing solver (`src/solver/macro_packer.py`) using Google OR-Tools CP-SAT bin packing to assign whole cable blocks to CIOC containers (max 8 baseplates = 96 channels).
- Implemented Stage 2 micro-slotting solver (`src/solver/micro_slotter.py`) assigning cable pairs contiguously in strict ascending order, enforcing 24-pair cables across 2 full consecutive baseplates and 12-pair cables across 1 baseplate.
- Unallocated cable pairs within multi-conductor trunks are explicitly allocated as `WIRED SPARE` records with `io_type=IOType.SPARE` and Standard terminal block mapping.
- Implemented independent post-solve audit pass (`src/solver/audit.py`) with `verify_allocation_invariants()` checking 100% contiguity, zero pair shuffling, slot uniqueness, and baseplate/CIOC boundary constraints.
- Integrated two-stage hierarchical packing engine into `run_hierarchical_pipeline()` in `src/pipeline.py`.
- Created interactive physical DIN-rail rack visualizer in `src/ui/components/cabinet_visualizer.py` and integrated into `src/ui/app.py`, rendering color-coded cable blocks, pair badges (P01..P24), wired spares, and carrier layout.
- Added comprehensive unit and integration test coverage across `tests/test_cable_block.py`, `tests/test_macro_packer.py`, `tests/test_micro_slotter.py`, `tests/test_hierarchical_solver.py`, and `tests/test_visualizer.py`. 100% test pass rate.


