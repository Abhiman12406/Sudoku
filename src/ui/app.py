"""Streamlit Web Application for IO Signal Sudoku Walking Skeleton."""

import io
import pandas as pd
import streamlit as st

from src.pipeline import run_walking_pipeline


def generate_sample_template_bytes() -> bytes:
    """Generate a ready-to-test sample spreadsheet."""
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


def main():
    st.set_page_config(
        page_title="IO Signal Sudoku | Walking Skeleton",
        page_icon="⚡",
        layout="wide",
    )

    st.title("⚡ IO Signal Sudoku")
    st.subheader("DeltaV Electronic Marshalling: Automated CP-SAT Signal Allocation")

    st.markdown(
        """
        **Walking Skeleton Pipeline:** Upload field instrument signals, run deterministic 
        CP-SAT mathematical allocation (enforcing **12 CHARMs per baseplate** capacity and cable pair ordering), 
        inspect slot coordinates, and download the engineering deliverable.
        """
    )

    col_upload, col_sample = st.columns([3, 1])

    with col_sample:
        st.write("##### Sample Input")
        st.write("Need test data? Download this pre-populated signal template:")
        sample_bytes = generate_sample_template_bytes()
        st.download_button(
            label="📥 Download Sample (.xlsx)",
            data=sample_bytes,
            file_name="sample_signals.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
        charms_per_bp = st.slider("CHARMs per Baseplate", min_value=6, max_value=24, value=12, step=2)
        st.caption("Standard Emerson DeltaV DIN-rail baseplates host exactly 12 CHARMs.")

    if uploaded_file is not None:
        try:
            # Preview uploaded file
            preview_bytes = uploaded_file.getvalue()
            if uploaded_file.name.endswith(".csv"):
                df_preview = pd.read_csv(io.BytesIO(preview_bytes))
            else:
                df_preview = pd.read_excel(io.BytesIO(preview_bytes))

            st.write("### 1. Ingested Signals Preview")
            st.dataframe(df_preview, use_container_width=True)

            if st.button("🚀 Run CP-SAT Allocation", type="primary"):
                with st.spinner("Solving constraint satisfaction model with Google OR-Tools CP-SAT..."):
                    allocations, out_excel_bytes = run_walking_pipeline(
                        io.BytesIO(preview_bytes),
                        charms_per_baseplate=charms_per_bp,
                    )

                st.success(f"Successfully allocated {len(allocations)} signals with 0 constraint violations!")

                # Key Metrics
                total_signals = len(allocations)
                baseplates_used = max([a.baseplate for a in allocations]) if allocations else 0
                total_capacity = baseplates_used * charms_per_bp
                spare_slots = total_capacity - total_signals

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Signals", total_signals)
                m2.metric("Baseplates Deployed", baseplates_used)
                m3.metric("Slots Utilized", f"{total_signals} / {total_capacity}")
                m4.metric("Free Spare Slots", spare_slots)

                # Render table
                st.write("### 2. Allocated Baseplate & Slot Coordinates")
                rows = [
                    {
                        "Tag": a.tag,
                        "IO Type": a.io_type.value if hasattr(a.io_type, "value") else str(a.io_type),
                        "Baseplate": f"BP-{a.baseplate:02d}",
                        "Slot": f"SLOT-{a.slot:02d}",
                        "Cable ID": a.cable_id or "-",
                        "Pair No": a.pair_no or "-",
                        "CHARM Part No": a.charm_part_no or "-",
                        "Terminal Block Type": a.terminal_block_type or "-",
                        "Description": a.description or "",
                    }
                    for a in allocations
                ]
                df_allocated = pd.DataFrame(rows)
                st.dataframe(df_allocated, use_container_width=True)

                # Download deliverable
                st.write("### 3. Engineering Deliverable")
                st.download_button(
                    label="💾 Download Populated Excel Allocation (.xlsx)",
                    data=out_excel_bytes,
                    file_name="allocated_signals_walking_skeleton.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        except Exception as e:
            st.error(f"Error processing signal file: {e}")


if __name__ == "__main__":
    main()
