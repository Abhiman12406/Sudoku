# 02: DeltaV Hardware Catalog & CHARM/Terminal-Block Auto-Selection

**What to build:** Full hardware engineering intelligence: given signal types (AI, AO, DI, DO, TC, RTD, Solenoids), the system automatically selects exact Emerson DeltaV CHARM models and Terminal Blocks (Standard, CJC, Fused Injected-Power, Relay Form C), displays them in the Streamlit rack view, and writes part numbers to the Excel export with editable rule overrides.

**Blocked by:** 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**Status:** ready-for-agent

- [ ] Load the Emerson DeltaV hardware catalog mapping signal types to CHARM part numbers and terminal block types.
- [ ] Support specialized hardware rules: TC -> CJC terminal blocks, Solenoid Valves -> Fused Injected-Power blocks, Relay DO -> Form C Relay blocks.
- [ ] Provide an interactive Streamlit hardware editor allowing engineers to customize hardware mappings.
- [ ] Display resolved CHARM and Terminal Block names in the UI table and slot details.
- [ ] Include CHARM Model and Terminal Block Type columns in the exported Excel file.
- [ ] Unit tests verify correct hardware selection for all supported industrial signal types.
