# 05: Automated Technical Query (TQ) Engine & Pre-Solve Validation

**What to build:** Robustness against corrupt or contradictory customer data: detects duplicate tags, missing fields, or cable pair overflows, and automatically generates formal `TQ-INST-xxx` records with severity ratings and engineering remedies. Displays an interactive TQ resolution table in Streamlit and writes a dedicated `TQ_Log` sheet in the export.

**Blocked by:** 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**Status:** ready-for-human

- [x] Fuzzy & regex column auto-mapper supporting multiple common customer spreadsheet headers.
- [x] Pre-solve validation detects missing tags, duplicate tags, pair numbers exceeding cable size, and unknown IO types.
- [x] Generate formal Technical Queries (`TQ-INST-001`, `TQ-INST-002`, etc.) with Category, Impacted Tag, Description, Severity, and Recommended Remedy.
- [x] Continue processing valid signals while isolating conflicting rows to TQs without application crash.
- [x] Display interactive TQ review and filter table in Streamlit with severity badges (Critical, Warning, Info).
- [x] Include a dedicated `TQ_Log` tab in the exported Excel workbook.
- [x] Automated tests verify TQ generation on intentionally corrupt sample spreadsheets.

## Comments

- Implemented regex and fuzzy column auto-mapper in `src/ingestion/mapper.py` supporting standard and customer header variants (`Tag`, `Instrument Tag`, `Loop Tag`, `IO Type`, `Signal Type`, `Cable ID`, `Pair No`, `Wire Pair`, etc.).
- Implemented `Severity` enum and `TechnicalQuery` domain model in `src/domain/models.py`.
- Implemented pre-solve validation and fault-tolerant TQ generator in `src/ingestion/validator.py`, isolating missing tags, duplicate tags, capacity overflows, unknown IO types, and cable segregation conflicts into formal `TQ-INST-xxx` records.
- Integrated validation and fault isolation into `src/ingestion/parser.py` via `parse_and_validate_signals()` and `parse_signal_file()`.
- Updated pipeline orchestrator in `src/pipeline.py` with `PipelineResult` container, enabling graceful processing of valid signals while quarantining corrupt rows and preserving backwards compatibility.
- Updated Excel exporter in `src/export/excel_export.py` to write both styled `Allocation` and dedicated `TQ_Log` worksheets.
- Enhanced Streamlit dashboard in `src/ui/app.py` with an interactive TQ resolution table, severity badges (🔴 Critical, 🟡 Warning, 🔵 Info), severity filters, and one-click corrupt sample generator for demonstration.
- Added comprehensive unit and integration tests across `tests/test_mapper.py`, `tests/test_domain_tq.py`, `tests/test_validator.py`, `tests/test_ingestion.py`, `tests/test_export.py`, `tests/test_pipeline.py`, and `tests/test_ui.py`. 100% test pass rate.
