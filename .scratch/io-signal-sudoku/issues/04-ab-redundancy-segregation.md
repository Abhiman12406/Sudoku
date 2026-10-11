# 04: Safety-Critical A/B Redundancy Segregation & Indicator Cuts

**What to build:** Safety compliance for plant redundancy: enforces that Train A and Train B signals never reside on the same CIOC ($U_c^A + U_c^B \le 1$). The Streamlit visualizer badges CIOCs with train colors, and the independent audit pass verifies 0 segregation breaches.

**Blocked by:** 03: Two-Stage Hierarchical Packing & Cable Contiguity (Trunk Cables)

**Status:** ready-for-agent

- [ ] Support signal segregation attributes ('A', 'B', or None).
- [ ] Add linear indicator cuts ($U_c^A + U_c^B \le 1$) in Stage 1 CP-SAT solver ensuring mutual exclusion at CIOC level.
- [ ] Support user-configurable segregation policy toggle (CIOC-level vs Cabinet-level) in the rule panel.
- [ ] Render color-coded Train A (e.g. Blue) and Train B (e.g. Amber) CIOC status banners in Streamlit.
- [ ] Implement independent verification rule failing the audit if any CIOC contains mixed A and B signals.
- [ ] Unit tests verify that conflicting A and B cables are strictly placed into separate CIOCs.
