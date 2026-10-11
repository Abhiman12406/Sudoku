# 07: Revision Diff & Perturbation Minimization Engine (Rev A vs Rev B)

**What to build:** Automated customer revision handling: uploads Rev A and Rev B simultaneously, identifies changes (`ADDED`, `DELETED`, `MODIFIED`, `UNCHANGED`), freezes unchanged signals, backfills vacated slots, minimizes the weighted movement metric ($\min \Delta$), displays a color-coded delta viewer in the UI, and appends a `Revision_Impact` tab.

**Blocked by:** 04: Safety-Critical A/B Redundancy Segregation & Indicator Cuts, 06: Template-Preserving Overlay & 5-Tab Deliverable Package

**Status:** ready-for-agent

- [ ] Dual-uploader in Streamlit accepting baseline Rev A and new revision Rev B.
- [ ] Tag-based diff classifier categorizing signals into `UNCHANGED`, `MODIFIED`, `DELETED`, and `ADDED`.
- [ ] Freezes all `UNCHANGED` signals in their original Rev A physical slots.
- [ ] CP-SAT optimization model penalizes physical relocation of modified/new signals using the weighted objective: $\min (10000 \cdot \Delta_{\text{cabinet}} + 1000 \cdot \Delta_{\text{CIOC}} + 100 \cdot \Delta_{\text{baseplate}} + 10 \cdot \Delta_{\text{slot}})$.
- [ ] Backfills holes vacated by deleted signals before allocating new hardware.
- [ ] Interactive Streamlit revision dashboard showing added (green), deleted (red), and moved (orange) loops.
- [ ] Appends `Revision_Impact` summary tab to the Excel deliverable workbook.
- [ ] Unit tests verify $\Delta = 0$ moves for unchanged signals and minimal churn for modifications.
