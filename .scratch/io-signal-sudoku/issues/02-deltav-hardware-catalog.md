# 02: DeltaV Hardware Catalog & CHARM/Terminal-Block Auto-Selection

**What to build:** Full hardware engineering intelligence: given signal types (AI, AO, DI, DO, TC, RTD, Solenoids), the system automatically selects exact Emerson DeltaV CHARM models and Terminal Blocks (Standard, CJC, Fused Injected-Power, Relay Form C), displays them in the Streamlit rack view, and writes part numbers to the Excel export with editable rule overrides.

**Blocked by:** 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**Status:** ready-for-human

- [x] Load the Emerson DeltaV hardware catalog mapping signal types to CHARM part numbers and terminal block types.
- [x] Support specialized hardware rules: TC -> CJC terminal blocks, Solenoid Valves -> Fused Injected-Power blocks, Relay DO -> Form C Relay blocks.
- [x] Provide an interactive Streamlit hardware editor allowing engineers to customize hardware mappings.
- [x] Display resolved CHARM and Terminal Block names in the UI table and slot details.
- [x] Include CHARM Model and Terminal Block Type columns in the exported Excel file.
- [x] Unit tests verify correct hardware selection for all supported industrial signal types.

## Comments

- Loaded the Emerson DeltaV hardware catalog in `src/domain/hardware.py` supporting standard signal types (AI, AO, DI, DO, DO_RELAY, TC, RTD, SPARE) with default part numbers and descriptions.
- Implemented specialized hardware rules:
  - Thermocouple (`TC`) automatically selects CJC terminal blocks (`KL4004X1-BA1`) and Thermocouple CHARMs (`KL3006X1-BA1`).
  - Solenoid Valves and high-side discrete outputs (`DO`, `SOV`, `XV`) select Fused Injected-Power terminal blocks (`KL4002X1-BA1`) and 24 VDC High-Side CHARMs (`KL3004X1-BA1`).
  - Relay DO signals (via `IOType.DO_RELAY` or keyword heuristic detection for dry contacts / interlocks / Form C) select Relay Form C terminal blocks (`KL4003X1-BA1`) and Form C Relay CHARMs (`KL3005X1-BA1`).
  - RTD, AI, AO, and DI signals select Standard terminal blocks (`KL4001X1-BA1`).
  - Wired Spares map to Standard terminal blocks with no CHARM module (`None`).
- Added `HardwareAssignment` domain model and enhanced `AllocatedSignal` with `charm_model` and `terminal_block_part_no`.
- Built interactive Streamlit Hardware Catalog Editor in `src/ui/app.py` with `catalog_to_dataframe` and `dataframe_to_catalog`, allowing engineers to customize part numbers and terminal block types in real-time.
- Extended Excel export columns in `src/export/excel_export.py` to write `CHARM Model`, `CHARM Part No`, `Terminal Block Type`, and `Terminal Block Part No`.
- Displayed resolved CHARM Model and Terminal Block Type in the Streamlit allocation table, physical rack visualizer cards (`src/ui/components/cabinet_visualizer.py`), and dedicated Slot Details & Hardware Inspector.
- Added comprehensive unit tests in `tests/test_hardware.py`, `tests/test_ui.py`, and updated `tests/test_pipeline.py`, `tests/test_solver.py`. 100% test pass rate across the full suite (62 passing tests).
