# 05: Automated Technical Query (TQ) Engine & Pre-Solve Validation

**What to build:** Robustness against corrupt or contradictory customer data: detects duplicate tags, missing fields, or cable pair overflows, and automatically generates formal `TQ-INST-xxx` records with severity ratings and engineering remedies. Displays an interactive TQ resolution table in Streamlit and writes a dedicated `TQ_Log` sheet in the export.

**Blocked by:** 01: Walking Skeleton: Single-Cable Ingestion to Excel Export via Streamlit

**Status:** ready-for-agent

- [ ] Fuzzy & regex column auto-mapper supporting multiple common customer spreadsheet headers.
- [ ] Pre-solve validation detects missing tags, duplicate tags, pair numbers exceeding cable size, and unknown IO types.
- [ ] Generate formal Technical Queries (`TQ-INST-001`, `TQ-INST-002`, etc.) with Category, Impacted Tag, Description, Severity, and Recommended Remedy.
- [ ] Continue processing valid signals while isolating conflicting rows to TQs without application crash.
- [ ] Display interactive TQ review and filter table in Streamlit with severity badges (Critical, Warning, Info).
- [ ] Include a dedicated `TQ_Log` tab in the exported Excel workbook.
- [ ] Automated tests verify TQ generation on intentionally corrupt sample spreadsheets.
