# 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**What to build:** An end-to-end verifiable pipeline on Day 1: upload a basic signal spreadsheet, run a minimal single-cable CP-SAT slot assignment (12 CHARMs per baseplate), view the resulting allocation in a Streamlit table, and download a populated Excel spreadsheet.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [x] Upload an Excel file containing basic instrument signals (AI, AO, DI, DO) via a Streamlit web interface.
- [x] Parse and validate input rows using Pydantic domain models.
- [x] Solve valid slot assignment using Google OR-Tools CP-SAT enforcing 12 CHARMs per baseplate capacity.
- [x] Render the allocated signals in an interactive Streamlit data table with baseplate/slot coordinates.
- [x] Export and download the allocation as an Excel workbook (.xlsx).
- [x] Unit tests cover parsing, solving, and export end-to-end.

## Comments

- Implemented pure domain models `Signal`, `IOType`, and `AllocatedSignal` in `src/domain/models.py`.
- Implemented hardware resolution against DeltaV hardware catalog in `src/domain/hardware.py`.
- Implemented robust spreadsheet ingestion with column synonym mapping in `src/ingestion/parser.py`.
- Implemented mathematical CP-SAT slot assignment solver enforcing 12 CHARMs per baseplate capacity and contiguous ascending pair order in `src/solver/walking_solver.py`.
- Implemented styled Excel workbook generator in `src/export/excel_export.py`.
- Implemented end-to-end orchestrator in `src/pipeline.py`.
- Implemented Streamlit web interface with file uploader, sample template generator, interactive allocation preview, and excel download in `src/ui/app.py`.
- Added comprehensive unit and integration tests in `tests/test_ingestion.py`, `tests/test_solver.py`, `tests/test_export.py`, and `tests/test_pipeline.py`. 100% passing.
