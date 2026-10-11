"""Streamlit Web Application for IO Signal Sudoku with Automated TQ Engine."""

import io
from typing import List
import pandas as pd
import streamlit as st

from src.domain.hardware import DEFAULT_CATALOG, load_hardware_catalog
from src.domain.models import TechnicalQuery
from src.pipeline import run_hierarchical_pipeline, run_walking_pipeline
from src.ui.components.cabinet_visualizer import render_streamlit_rack


def generate_sample_template_bytes() -> bytes:
    """Generate a ready-to-test clean sample spreadsheet."""
    sample_data = {
        "Tag": [
            "10-FT-101",
            "10-FV-101",
            "10-PT-102",
            "10-PV-102",
            "10-TT-103",
            "10-LT-104",
            "10-PSH-105",
            "10-PSL-105",
            "10-XV-106",
            "10-SOV-107",
            "10-TT-108",
            "10-ZT-109",
            "20-FT-201",
            "20-FV-201",
        ],
        "IO Type": [
            "AI",
            "AO",
            "AI",
            "AO",
            "RTD",
            "AI",
            "DI",
            "DI",
            "DO",
            "DO",
            "TC",
            "AI",
            "AI",
            "AO",
        ],
        "Cable ID": [
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-02",
            "CBL-TRUNK-02",
        ],
        "Pair No": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2],
        "Description": [
            "Inlet Flow Transmitter",
            "Inlet Control Valve",
            "Separator Pressure Transmitter",
            "Separator Pressure Control Valve",
            "Reboiler Temperature Element",
            "Flash Drum Level Transmitter",
            "Feed Line High Pressure Switch",
            "Feed Line Low Pressure Switch",
            "Emergency Shutdown Valve",
            "Blowdown Solenoid Valve",
            "Furnace Pyrometer Thermocouple",
            "Compressor Shaft Position Transmitter",
            "Condensate Return Flow Transmitter",
            "Condensate Control Valve",
        ],
    }
    df = pd.DataFrame(sample_data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Signal_Schedule")
    return buf.getvalue()


def generate_corrupt_sample_template_bytes() -> bytes:
    """Generate a sample spreadsheet with intentionally corrupted rows to demonstrate TQ Engine."""
    corrupt_data = {
        "Tag": [
            "10-FT-101",
            "10-FT-101",        # Duplicate tag
            None,               # Missing tag
            "10-BAD-001",       # Unknown IO type
            "10-OVF-002",       # Pair overflow (pair 28 on 24-pair max)
            "20-PT-201",        # Valid Train A
            "20-TT-202",        # Valid Train A
            "30-FT-301",        # Valid
            "30-FV-301",        # Valid
        ],
        "IO Type": [
            "AI",
            "AI",
            "AI",
            "XYZ_CORRUPT",
            "AI",
            "AI",
            "RTD",
            "AI",
            "AO",
        ],
        "Cable ID": [
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-01",
            "CBL-TRUNK-02",
            "CBL-TRUNK-02",
            "CBL-TRUNK-03",
            "CBL-TRUNK-03",
        ],
        "Pair No": [1, 1, 3, 4, 28, 1, 2, 1, 2],
        "Description": [
            "Clean Flow Loop",
            "Duplicate Tag Conflict",
            "Missing Tag Row",
            "Corrupt Signal Type",
            "Exceeds 24 Pairs",
            "Compressor Suction Pressure",
            "Compressor Discharge Temperature",
            "Feed Water Flow Transmitter",
            "Feed Water Control Valve",
        ],
    }
    df = pd.DataFrame(corrupt_data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Corrupt_Schedule")
    return buf.getvalue()


def format_severity_badge(severity: str) -> str:
    """Return formatted emoji badge for a given severity rating."""
    sev = str(severity).strip().capitalize()
    if sev == "Critical":
        return "🔴 Critical"
    elif sev == "Warning":
        return "🟡 Warning"
    elif sev == "Info":
        return "🔵 Info"
    return sev


def catalog_to_dataframe(catalog: dict) -> pd.DataFrame:
    """Convert hardware catalog dictionary to editable DataFrame."""
    rows = []
    for sig_key in ["AI", "AO", "DI", "DO", "DO_RELAY", "TC", "RTD", "SPARE"]:
        entry = catalog.get(sig_key, {})
        rows.append({
            "Signal Type": sig_key,
            "CHARM Model": entry.get("charm_description") or entry.get("charm_model", ""),
            "CHARM Part No": entry.get("charm_part_no", ""),
            "Terminal Block Type": entry.get("terminal_block_type", "Standard"),
            "Terminal Block Part No": entry.get("terminal_block_part_no", ""),
        })
    return pd.DataFrame(rows)


def dataframe_to_catalog(df: pd.DataFrame) -> dict:
    """Convert edited DataFrame back into hardware catalog dictionary."""
    custom_catalog = {}
    for _, r in df.iterrows():
        custom_catalog[str(r["Signal Type"])] = {
            "charm_description": str(r["CHARM Model"]),
            "charm_part_no": str(r["CHARM Part No"]),
            "terminal_block_type": str(r["Terminal Block Type"]),
            "terminal_block_part_no": str(r["Terminal Block Part No"]),
        }
    return custom_catalog


def main():
    st.set_page_config(
        page_title="IO Signal Sudoku | Automated TQ Engine",
        page_icon="⚡",
        layout="wide",
    )

    st.title("⚡ IO Signal Sudoku")
    st.subheader("DeltaV Electronic Marshalling: Automated CP-SAT Allocation & TQ Engine")

    st.markdown(
        """
        **Automated Technical Query (TQ) Engine:** Automatically validates incoming customer spreadsheets, 
        flags duplicate tags, unknown IO types, and cable pair overflows into formal `TQ-INST-xxx` records, 
        and safely processes valid signals without crashing.
        """
    )

    col_upload, col_sample = st.columns([3, 1])

    with col_sample:
        st.write("##### Sample Files")
        clean_bytes = generate_sample_template_bytes()
        st.download_button(
            label="📥 Download Clean Sample (.xlsx)",
            data=clean_bytes,
            file_name="clean_signals.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        corrupt_bytes = generate_corrupt_sample_template_bytes()
        st.download_button(
            label="⚠️ Download Corrupt Sample (.xlsx)",
            data=corrupt_bytes,
            file_name="corrupt_signals_for_tq_test.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Contains duplicate tags, missing fields, unknown IO types, and pair overflows to test TQ generation.",
        )

    with col_upload:
        st.write("##### Ingestion")
        uploaded_file = st.file_uploader(
            "Upload Signal Database (.xlsx or .csv)",
            type=["xlsx", "xls", "csv"],
            help="Excel workbook containing Tag, IO Type, Cable ID, Pair No, and Description.",
        )

    with st.sidebar:
        st.header("⚙️ Configuration")
        solver_mode = st.radio(
            "Solver Algorithm",
            options=["Two-Stage Hierarchical (Trunk Cables & Spares)", "Walking Skeleton (Flat)"],
            index=0,
            help="Hierarchical mode groups signals into rigid multi-conductor cable blocks (2, 6, 12, 24 pairs), preserves ascending pair contiguity, and creates WIRED SPARE records.",
        )
        charms_per_bp = st.slider("CHARMs per Baseplate", min_value=6, max_value=24, value=12, step=2)
        baseplates_per_cioc = st.slider("Baseplates per CIOC", min_value=4, max_value=12, value=8, step=1)
        st.caption("Standard Emerson DeltaV DIN-rail baseplates host 12 CHARMs; CIOC carriers host up to 8 baseplates.")

        st.subheader("🛠️ Hardware Catalog Editor")
        with st.expander("Customize CHARMs & Terminal Blocks", expanded=False):
            st.caption("Edit CHARM models and terminal block mappings for each signal type:")
            default_cat = load_hardware_catalog()
            df_cat_init = catalog_to_dataframe(default_cat)
            edited_cat_df = st.data_editor(
                df_cat_init,
                num_rows="fixed",
                use_container_width=True,
                key="hardware_catalog_editor",
            )

        custom_catalog = dataframe_to_catalog(edited_cat_df)

    if uploaded_file is not None:
        try:
            preview_bytes = uploaded_file.getvalue()
            if uploaded_file.name.endswith(".csv"):
                df_preview = pd.read_csv(io.BytesIO(preview_bytes))
            else:
                df_preview = pd.read_excel(io.BytesIO(preview_bytes))

            st.write("### 1. Ingested Signals Preview")
            st.dataframe(df_preview, use_container_width=True)

            if st.button("🚀 Run Pre-Solve Validation & Allocation", type="primary"):
                with st.spinner("Validating data & solving CP-SAT allocation..."):
                    if solver_mode.startswith("Two-Stage"):
                        result = run_hierarchical_pipeline(
                            io.BytesIO(preview_bytes),
                            charms_per_baseplate=charms_per_bp,
                            baseplates_per_cioc=baseplates_per_cioc,
                            catalog=custom_catalog,
                        )
                    else:
                        result = run_walking_pipeline(
                            io.BytesIO(preview_bytes),
                            charms_per_baseplate=charms_per_bp,
                            catalog=custom_catalog,
                        )
                    allocations = result.allocations
                    out_excel_bytes = result.excel_bytes
                    tqs: List[TechnicalQuery] = result.tqs

                # --- 2. Technical Query Review Table ---
                st.write("### 2. Pre-Solve Validation & Technical Query (TQ) Log")

                if tqs:
                    crit_count = sum(1 for t in tqs if t.severity.value == "Critical")
                    warn_count = sum(1 for t in tqs if t.severity.value == "Warning")
                    info_count = sum(1 for t in tqs if t.severity.value == "Info")

                    st.warning(
                        f"⚠️ **{len(tqs)} Technical Queries Generated:** {crit_count} Critical, "
                        f"{warn_count} Warning, {info_count} Info. "
                        f"Conflicting rows isolated; {len(allocations)} valid signals allocated successfully."
                    )

                    tq_c1, tq_c2, tq_c3, tq_c4 = st.columns(4)
                    tq_c1.metric("Total TQs", len(tqs))
                    tq_c2.metric("Critical (Isolated)", crit_count)
                    tq_c3.metric("Warnings", warn_count)
                    tq_c4.metric("Informational", info_count)

                    # Interactive Filter
                    severity_filter = st.radio(
                        "Filter by Severity",
                        options=["All", "Critical", "Warning", "Info"],
                        horizontal=True,
                    )

                    filtered_tqs = [
                        t for t in tqs
                        if severity_filter == "All" or t.severity.value == severity_filter
                    ]

                    tq_rows = [
                        {
                            "TQ ID": t.tq_id,
                            "Severity": t.severity.badge,
                            "Category": t.category,
                            "Impacted Tag": t.impacted_tag,
                            "Description": t.description,
                            "Recommended Remedy": t.recommended_remedy,
                            "Row": t.row_number if t.row_number else "-",
                        }
                        for t in filtered_tqs
                    ]
                    df_tq_display = pd.DataFrame(tq_rows)
                    st.dataframe(df_tq_display, use_container_width=True)
                else:
                    st.success("✅ **Zero Technical Queries:** 100% of input rows passed pre-solve validation clean!")

                # --- 3. DIN-Rail Physical Visualizer ---
                st.write("### 3. Physical DIN-Rail Rack & Cable Contiguity Visualizer")
                if allocations:
                    render_streamlit_rack(allocations, charms_per_baseplate=charms_per_bp)

                # --- 4. Allocated Coordinates & Metrics ---
                st.write("### 4. Allocated Baseplate & Slot Coordinates")

                if allocations:
                    active_signals = sum(1 for a in allocations if not a.is_spare)
                    spare_signals = sum(1 for a in allocations if a.is_spare)
                    total_allocated = len(allocations)
                    ciocs_used = len({a.cioc for a in allocations})
                    baseplates_used = len({(a.cioc, a.baseplate) for a in allocations})
                    total_capacity = baseplates_used * charms_per_bp

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Active Signals", active_signals)
                    m2.metric("Wired Spares", spare_signals)
                    m3.metric("CIOCs / Baseplates", f"{ciocs_used} CIOC / {baseplates_used} BP")
                    m4.metric("Total Cable Slots", f"{total_allocated} / {total_capacity}")

                    rows = [
                        {
                            "Tag": a.tag,
                            "IO Type": a.io_type.value if hasattr(a.io_type, "value") else str(a.io_type),
                            "CIOC": f"CIOC-{a.cioc:02d}",
                            "Baseplate": f"BP-{a.baseplate:02d}",
                            "Slot": f"SLOT-{a.slot:02d}",
                            "Cable ID": a.cable_id or "-",
                            "Pair No": a.pair_no or "-",
                            "CHARM Model": a.charm_model or "-",
                            "CHARM Part No": a.charm_part_no or "-",
                            "Terminal Block Type": a.terminal_block_type or "-",
                            "Terminal Block Part No": a.terminal_block_part_no or "-",
                            "Description": a.description or "",
                            "Type": "WIRED SPARE" if a.is_spare else "Active Loop",
                        }
                        for a in allocations
                    ]
                    df_allocated = pd.DataFrame(rows)
                    st.dataframe(df_allocated, use_container_width=True)

                    with st.expander("🔍 Slot Details & Hardware Inspector", expanded=False):
                        st.caption("Detailed engineering hardware specifications resolved per physical slot:")
                        slot_details = [
                            {
                                "Location": f"CIOC-{a.cioc:02d} / BP-{a.baseplate:02d} / SLOT-{a.slot:02d}",
                                "Tag": a.tag,
                                "IO Type": a.io_type.value if hasattr(a.io_type, "value") else str(a.io_type),
                                "CHARM Model": a.charm_model or "-",
                                "CHARM Part No": a.charm_part_no or "-",
                                "Terminal Block Type": a.terminal_block_type or "-",
                                "Terminal Block Part No": a.terminal_block_part_no or "-",
                                "Cable & Pair": f"{a.cable_id or '-'} (Pair {a.pair_no or '-'})",
                                "Description": a.description or "-",
                            }
                            for a in allocations
                        ]
                        st.dataframe(pd.DataFrame(slot_details), use_container_width=True)
                else:
                    st.info("No valid signals to allocate after quarantining corrupt rows.")

                # --- 5. Deliverable Download ---
                st.write("### 5. Engineering Deliverables")
                st.download_button(
                    label="💾 Download Populated Excel Workbook with TQ_Log (.xlsx)",
                    data=out_excel_bytes,
                    file_name="allocated_signals_with_tq_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        except Exception as e:
            st.error(f"Error processing signal file: {e}")



if __name__ == "__main__":
    main()
