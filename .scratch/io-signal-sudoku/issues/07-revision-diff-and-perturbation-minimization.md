# 07: Revision Diff & Perturbation Minimization Engine (Rev A vs Rev B)

**What to build:** Automated customer revision handling: uploads Rev A and Rev B simultaneously, identifies changes (`ADDED`, `DELETED`, `MODIFIED`, `UNCHANGED`), freezes unchanged signals, backfills vacated slots, minimizes the weighted movement metric ($\min \Delta$), displays a color-coded delta viewer in the UI, and appends a `Revision_Impact` tab.

**Blocked by:** 04: Safety-Critical A/B Redundancy Segregation & Indicator Cuts, 06: Template-Preserving Overlay & 5-Tab Deliverable Package

**Status:** ready-for-human

- [x] Dual-uploader in Streamlit accepting baseline Rev A and new revision Rev B.
- [x] Tag-based diff classifier categorizing signals into `UNCHANGED`, `MODIFIED`, `DELETED`, and `ADDED`.
- [x] Freezes all `UNCHANGED` signals in their original Rev A physical slots.
- [x] CP-SAT optimization model penalizes physical relocation of modified/new signals using the weighted objective: $\min (10000 \cdot \Delta_{\text{cabinet}} + 1000 \cdot \Delta_{\text{CIOC}} + 100 \cdot \Delta_{\text{baseplate}} + 10 \cdot \Delta_{\text{slot}})$.
- [x] Backfills holes vacated by deleted signals before allocating new hardware.
- [x] Interactive Streamlit revision dashboard showing added (green), deleted (red), and moved (orange) loops.
- [x] Appends `Revision_Impact` summary tab to the Excel deliverable workbook.
- [x] Unit tests verify $\Delta = 0$ moves for unchanged signals and minimal churn for modifications.

## Comments

- Implemented `classify_revision_diff()` in `src/revision/classifier.py` categorizing customer loops into `UNCHANGED`, `MODIFIED`, `DELETED`, and `ADDED` with granular change logs while filtering out internal wired spares.
- Implemented `solve_revision_allocation()` in `src/revision/solver.py` freezing unchanged loops in original physical coordinates ($\Delta = 0$), enforcing CP-SAT weighted movement minimization ($\min 10000 \cdot \Delta_{\text{cabinet}} + 1000 \cdot \Delta_{\text{CIOC}} + 100 \cdot \Delta_{\text{baseplate}} + 10 \cdot \Delta_{\text{slot}}$), backfilling vacated slots before provisioning new hardware, and maintaining strict multi-conductor cable contiguity across both frozen and newly allocated pairs.
- Implemented `populate_revision_impact_sheet()` in `src/revision/excel_tab.py` generating a formatted, styled `Revision_Impact` summary tab with executive KPI metrics and detailed color-coded loop diff log (green for added, red for deleted, orange for moved).
- Extended `export_allocation_to_excel()` in `src/export/excel_export.py` to seamlessly append `Revision_Impact` to deliverable workbooks when revision diff results are present.
- Implemented end-to-end `run_revision_pipeline()` in `src/pipeline.py` supporting baseline spreadsheet parsing, pre-solve validation, revision CP-SAT optimization, independent invariant audit verification, and deliverable workbook generation.
- Enhanced Streamlit dashboard in `src/ui/app.py` with dual-uploader for baseline Rev A and Rev B, downloadable baseline sample spreadsheets, executive revision KPI metric cards, interactive color-coded revision delta viewer with status filters, DIN-rail visualizer, and download button for the Rev B deliverable package with `Revision_Impact`.
- Comprehensive test coverage in `tests/test_revision_diff.py`, `tests/test_revision_solver.py`, `tests/test_revision_export.py`, `tests/test_revision_pipeline.py`, and `tests/test_ui.py` passing with 100% success rate.

