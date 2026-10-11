# 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**What to build:** An end-to-end verifiable pipeline on Day 1: upload a basic signal spreadsheet, run a minimal single-cable CP-SAT slot assignment (12 CHARMs per baseplate), view the resulting allocation in a Streamlit table, and download a populated Excel spreadsheet.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Upload an Excel file containing basic instrument signals (AI, AO, DI, DO) via a Streamlit web interface.
- [ ] Parse and validate input rows using Pydantic domain models.
- [ ] Solve valid slot assignment using Google OR-Tools CP-SAT enforcing 12 CHARMs per baseplate capacity.
- [ ] Render the allocated signals in an interactive Streamlit data table with baseplate/slot coordinates.
- [ ] Export and download the allocation as an Excel workbook (.xlsx).
- [ ] Unit tests cover parsing, solving, and export end-to-end.
