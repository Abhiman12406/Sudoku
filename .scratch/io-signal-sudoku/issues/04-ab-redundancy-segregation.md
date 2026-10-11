# 04: Safety-Critical A/B Redundancy Segregation & Indicator Cuts

**What to build:** Safety compliance for plant redundancy: enforces that Train A and Train B signals never reside on the same CIOC ($U_c^A + U_c^B \le 1$). The Streamlit visualizer badges CIOCs with train colors, and the independent audit pass verifies 0 segregation breaches.

**Blocked by:** 03: Two-Stage Hierarchical Packing & Cable Contiguity (Trunk Cables)

**Status:** ready-for-human

- [x] Support signal segregation attributes ('A', 'B', or None).
- [x] Add linear indicator cuts ($U_c^A + U_c^B \le 1$) in Stage 1 CP-SAT solver ensuring mutual exclusion at CIOC level.
- [x] Support user-configurable segregation policy toggle (CIOC-level vs Cabinet-level) in the rule panel.
- [x] Render color-coded Train A (e.g. Blue) and Train B (e.g. Amber) CIOC status banners in Streamlit.
- [x] Implement independent verification rule failing the audit if any CIOC contains mixed A and B signals.
- [x] Unit tests verify that conflicting A and B cables are strictly placed into separate CIOCs.

## Comments

- Supported signal segregation attributes ('A', 'B', or None) in `Signal`, `CableBlock`, and `AllocatedSignal` with pydantic validation and case normalization in `src/domain/models.py`.
- Added linear indicator cuts ($U_c^A + U_c^B \le 1$) in Stage 1 CP-SAT solver (`src/solver/macro_packer.py`) ensuring mathematical mutual exclusion at CIOC level.
- Implemented Cabinet-level indicator redundancy cuts ($U_{cab}^A + U_{cab}^B \le 1$) with cabinet usage symmetry breaking in Stage 1 solver for strict multi-cabinet segregation.
- Added user-configurable segregation policy toggle (`CIOC-level` vs `Cabinet-level`) in Streamlit sidebar configuration (`src/ui/app.py`) and wired through `run_hierarchical_pipeline()` in `src/pipeline.py`.
- Rendered color-coded Train A (Blue `#1E88E5`) and Train B (Amber `#FFA000`) CIOC status banners, per-slot train badges, and carrier overview cards in `src/ui/components/cabinet_visualizer.py`.
- Added independent post-solve verification rules in `src/solver/audit.py` failing the audit pass if any CIOC contains mixed Train A and Train B signals, or if any Cabinet contains mixed signals when Cabinet policy is active.
- Added comprehensive unit and integration tests in `tests/test_segregation.py` validating 100% mutual exclusion, audit rule enforcement, Excel deliverable export, and visualizer rendering.
