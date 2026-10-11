# 06: Template-Preserving Overlay & 5-Tab Deliverable Package

**What to build:** Zero-rework customer deliverables: takes the customer's blank formatted Excel template and injects allocation data via `openpyxl` preserving all existing formatting, fonts, and formulas, while appending `Allocation`, `TQ_Log`, `Cabinet_Summary`, and `Rule_Compliance` sheets.

**Blocked by:** 02: DeltaV Hardware Catalog & CHARM/Terminal-Block Auto-Selection, 04: Safety-Critical A/B Redundancy Segregation & Indicator Cuts, 05: Automated Technical Query (TQ) Engine & Pre-Solve Validation

**Status:** ready-for-agent

- [ ] Template overlay cloner preserves all cell styles, fonts, borders, headers, and formulas of customer Excel templates.
- [ ] Inject allocated loop records into exact column coordinates starting at data row 2.
- [ ] Generate `Cabinet_Summary` tab with channel counts, wired spares, free spares, and utilization percentages per cabinet.
- [ ] Generate `Rule_Compliance` tab listing the independent audit checklist with pass/fail counts.
- [ ] Provide a download button in Streamlit delivering the complete multi-tab `.xlsx` workbook.
- [ ] End-to-end tests verify workbook opens in Microsoft Excel without corruption or repair warnings.
