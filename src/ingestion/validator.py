"""Pre-solve validation and formal Technical Query (TQ) generation engine."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from src.domain.cable import VALID_CABLE_SIZES
from src.domain.models import IOType, Severity, Signal, TechnicalQuery
from src.ingestion.mapper import auto_map_columns


def validate_dataframe(
    df: pd.DataFrame,
    col_map: Optional[Dict[str, str]] = None,
    tq_start_index: int = 1,
) -> Tuple[List[Signal], List[TechnicalQuery]]:
    """Validate customer signal data, isolate corrupt/conflicting rows, and emit formal TQs.

    Args:
        df: Input pandas DataFrame of instrument signals.
        col_map: Optional pre-resolved column mapping {standard_name: raw_column_name}.
        tq_start_index: Starting sequential counter for TQ IDs (default: 1).

    Returns:
        Tuple of (list of valid Signal models, list of generated TechnicalQuery records).
    """
    tqs: List[TechnicalQuery] = []
    tq_counter = tq_start_index

    def next_tq_id() -> str:
        nonlocal tq_counter
        tq_id = f"TQ-INST-{tq_counter:03d}"
        tq_counter += 1
        return tq_id

    # Auto-map columns if not provided
    if col_map is None:
        col_map = auto_map_columns(list(df.columns))

    # Check required columns
    if "tag" not in col_map:
        tqs.append(
            TechnicalQuery(
                tq_id=next_tq_id(),
                category="Missing Field",
                impacted_tag="(All Signals)",
                description="Input data is missing a recognized 'Tag' or 'Instrument Tag' column.",
                severity=Severity.CRITICAL,
                recommended_remedy="Ensure the spreadsheet includes a column identifying instrument loop tags.",
            )
        )
        return [], tqs

    if "io_type" not in col_map:
        tqs.append(
            TechnicalQuery(
                tq_id=next_tq_id(),
                category="Missing Field",
                impacted_tag="(All Signals)",
                description="Input data is missing a recognized 'IO Type' or 'Signal Type' column.",
                severity=Severity.CRITICAL,
                recommended_remedy="Ensure the spreadsheet includes a column specifying signal types (AI, AO, DI, DO, RTD, TC).",
            )
        )
        return [], tqs

    tag_col = col_map["tag"]
    io_col = col_map["io_type"]
    cable_col = col_map.get("cable_id")
    pair_col = col_map.get("pair_no")
    desc_col = col_map.get("description")
    grp_col = col_map.get("io_group")
    seg_col = col_map.get("segregation")
    size_col = col_map.get("cable_size")

    # Track row validity
    invalid_row_indices: Set[int] = set()

    # Pre-parse each row and collect basic errors
    row_records: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        excel_row = int(idx) + 2  # Assuming row 1 is header
        raw_tag = row.get(tag_col)
        raw_io = row.get(io_col)

        # 1. Check Missing Tag
        if pd.isna(raw_tag) or str(raw_tag).strip() == "":
            invalid_row_indices.add(idx)
            tqs.append(
                TechnicalQuery(
                    tq_id=next_tq_id(),
                    category="Missing Field",
                    impacted_tag=f"Row {excel_row}",
                    description=f"Row {excel_row}: Missing required instrument tag.",
                    severity=Severity.CRITICAL,
                    recommended_remedy="Provide a unique, non-empty instrument tag per engineering P&ID standards.",
                    rule_code="TQ-VAL-001",
                    row_number=excel_row,
                )
            )
            continue

        tag_str = str(raw_tag).strip()

        # 2. Check Missing IO Type
        if pd.isna(raw_io) or str(raw_io).strip() == "":
            invalid_row_indices.add(idx)
            tqs.append(
                TechnicalQuery(
                    tq_id=next_tq_id(),
                    category="Missing Field",
                    impacted_tag=tag_str,
                    description=f"Row {excel_row}: Tag '{tag_str}' is missing required IO Type.",
                    severity=Severity.CRITICAL,
                    recommended_remedy="Specify an approved DeltaV IO type (AI, AO, DI, DO, RTD, TC).",
                    rule_code="TQ-VAL-001",
                    row_number=excel_row,
                )
            )
            continue

        raw_io_str = str(raw_io).strip().upper().replace("-", "_").replace(" ", "_")
        if raw_io_str in ("RELAY", "DO_RELAY"):
            raw_io_str = "DO_RELAY"

        # 3. Check Unknown IO Type
        try:
            io_type = IOType(raw_io_str)
        except ValueError:
            invalid_row_indices.add(idx)
            tqs.append(
                TechnicalQuery(
                    tq_id=next_tq_id(),
                    category="Unknown IO Type",
                    impacted_tag=tag_str,
                    description=f"Row {excel_row}: Tag '{tag_str}' has unsupported IO Type '{raw_io_str}'.",
                    severity=Severity.CRITICAL,
                    recommended_remedy="Update signal IO type to an approved DeltaV IO type (AI, AO, DI, DO, RTD, TC).",
                    rule_code="TQ-VAL-005",
                    row_number=excel_row,
                )
            )
            continue

        # Extract other fields
        raw_cable = row.get(cable_col) if cable_col else None
        cable_id = str(raw_cable).strip() if pd.notna(raw_cable) and str(raw_cable).strip() != "" else None

        raw_pair = row.get(pair_col) if pair_col else None
        pair_no: Optional[int] = None
        if pd.notna(raw_pair) and str(raw_pair).strip() != "":
            try:
                pair_no = int(float(str(raw_pair).strip()))
            except ValueError:
                invalid_row_indices.add(idx)
                tqs.append(
                    TechnicalQuery(
                        tq_id=next_tq_id(),
                        category="Capacity Overflow",
                        impacted_tag=tag_str,
                        description=f"Row {excel_row}: Tag '{tag_str}' has non-integer pair number '{raw_pair}'.",
                        severity=Severity.CRITICAL,
                        recommended_remedy="Pair numbers must be positive integers (1..N).",
                        row_number=excel_row,
                        cable_id=cable_id,
                    )
                )
                continue

        # Declared cable size if available
        declared_size: Optional[int] = None
        if size_col:
            raw_size = row.get(size_col)
            if pd.notna(raw_size) and str(raw_size).strip() != "":
                try:
                    declared_size = int(float(str(raw_size).strip()))
                except ValueError:
                    pass

        # 4. Check Pair Number Overflows
        max_trunk_cap = max(VALID_CABLE_SIZES)
        if pair_no is not None:
            if pair_no <= 0:
                invalid_row_indices.add(idx)
                tqs.append(
                    TechnicalQuery(
                        tq_id=next_tq_id(),
                        category="Capacity Overflow",
                        impacted_tag=tag_str,
                        description=f"Row {excel_row}: Tag '{tag_str}' has non-positive pair number {pair_no}.",
                        severity=Severity.CRITICAL,
                        recommended_remedy="Pair numbers must be positive integers starting from 1.",
                        row_number=excel_row,
                        cable_id=cable_id,
                    )
                )
                continue

            if pair_no > max_trunk_cap:
                invalid_row_indices.add(idx)
                tqs.append(
                    TechnicalQuery(
                        tq_id=next_tq_id(),
                        category="Capacity Overflow",
                        impacted_tag=tag_str,
                        description=f"Row {excel_row}: Tag '{tag_str}' in cable '{cable_id or 'Unknown'}' declares pair {pair_no}, exceeding maximum cable capacity ({max_trunk_cap} pairs).",
                        severity=Severity.CRITICAL,
                        recommended_remedy=f"Reassign pair number within standard trunk cable capacity ({VALID_CABLE_SIZES} pairs).",
                        row_number=excel_row,
                        cable_id=cable_id,
                    )
                )
                continue

            if declared_size is not None and pair_no > declared_size:
                invalid_row_indices.add(idx)
                tqs.append(
                    TechnicalQuery(
                        tq_id=next_tq_id(),
                        category="Capacity Overflow",
                        impacted_tag=tag_str,
                        description=f"Row {excel_row}: Tag '{tag_str}' declares pair {pair_no}, exceeding declared cable capacity ({declared_size} pairs).",
                        severity=Severity.CRITICAL,
                        recommended_remedy=f"Reassign pair number within declared cable size ({declared_size} pairs) or upsize cable.",
                        row_number=excel_row,
                        cable_id=cable_id,
                    )
                )
                continue

        raw_desc = row.get(desc_col) if desc_col else None
        description = str(raw_desc).strip() if pd.notna(raw_desc) else None

        raw_grp = row.get(grp_col) if grp_col else None
        io_group = str(raw_grp).strip() if pd.notna(raw_grp) else None

        raw_seg = row.get(seg_col) if seg_col else None
        segregation = str(raw_seg).strip().upper() if pd.notna(raw_seg) else None
        if segregation and segregation not in ("A", "B"):
            # If not A or B, treat as general or unassigned
            segregation = None

        row_records.append({
            "idx": idx,
            "excel_row": excel_row,
            "tag": tag_str,
            "io_type": io_type,
            "cable_id": cable_id,
            "pair_no": pair_no,
            "description": description,
            "io_group": io_group,
            "segregation": segregation,
        })

    # 5. Check Duplicate Tags across valid rows
    tags_to_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in row_records:
        if rec["idx"] not in invalid_row_indices:
            tags_to_rows[rec["tag"]].append(rec)

    for tag, records in tags_to_rows.items():
        if len(records) > 1:
            row_numbers = [r["excel_row"] for r in records]
            for r in records:
                invalid_row_indices.add(r["idx"])
            tqs.append(
                TechnicalQuery(
                    tq_id=next_tq_id(),
                    category="Duplicate Tag",
                    impacted_tag=tag,
                    description=f"Duplicate instrument tag '{tag}' detected across rows {row_numbers}.",
                    severity=Severity.CRITICAL,
                    recommended_remedy="Verify instrument loop tagging against engineering P&ID and assign distinct tags.",
                    rule_code="TQ-VAL-002",
                    row_number=row_numbers[0],
                )
            )

    # 6. Check Duplicate Pair Numbers within the same cable
    cable_pairs_to_rows: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    for rec in row_records:
        if rec["idx"] not in invalid_row_indices and rec["cable_id"] and rec["pair_no"] is not None:
            cable_pairs_to_rows[(rec["cable_id"], rec["pair_no"])].append(rec)

    for (cable_id, pair_no), records in cable_pairs_to_rows.items():
        if len(records) > 1:
            impacted_tags = [r["tag"] for r in records]
            row_numbers = [r["excel_row"] for r in records]
            for r in records:
                invalid_row_indices.add(r["idx"])
            tqs.append(
                TechnicalQuery(
                    tq_id=next_tq_id(),
                    category="Duplicate Pair Number",
                    impacted_tag=", ".join(impacted_tags),
                    description=f"Cable '{cable_id}' has conflicting duplicate pair number {pair_no} for tags {impacted_tags} in rows {row_numbers}.",
                    severity=Severity.CRITICAL,
                    recommended_remedy=f"Assign unique pair numbers (1..N) to all field signals sharing cable '{cable_id}'.",
                    rule_code="TQ-VAL-003",
                    row_number=row_numbers[0],
                    cable_id=cable_id,
                )
            )

    # 7. Check Segregation Conflict within the same cable (Train A vs Train B)
    cable_to_seg_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in row_records:
        if rec["idx"] not in invalid_row_indices and rec["cable_id"] and rec["segregation"]:
            cable_to_seg_records[rec["cable_id"]].append(rec)

    for cable_id, records in cable_to_seg_records.items():
        trains = set(r["segregation"] for r in records)
        if "A" in trains and "B" in trains:
            tags_a = [r["tag"] for r in records if r["segregation"] == "A"]
            tags_b = [r["tag"] for r in records if r["segregation"] == "B"]
            for r in records:
                invalid_row_indices.add(r["idx"])
            tqs.append(
                TechnicalQuery(
                    tq_id=next_tq_id(),
                    category="Segregation Conflict",
                    impacted_tag=cable_id,
                    description=f"Cable '{cable_id}' bundles conflicting Train A and Train B signals (Train A: {tags_a} vs Train B: {tags_b}).",
                    severity=Severity.CRITICAL,
                    recommended_remedy="Segregate Train A and Train B field loops into physically separate trunk cables.",
                    rule_code="TQ-VAL-004",
                    cable_id=cable_id,
                )
            )

    # 8. Informational advisory TQs for home-run field connections (non-fatal)
    for rec in row_records:
        if rec["idx"] not in invalid_row_indices and not rec["cable_id"]:
            tqs.append(
                TechnicalQuery(
                    tq_id=next_tq_id(),
                    category="Single-Channel Home Run",
                    impacted_tag=rec["tag"],
                    description=f"Row {rec['excel_row']}: Signal '{rec['tag']}' has no trunk cable assigned; will land as single-pair home-run channel.",
                    severity=Severity.INFO,
                    recommended_remedy="Assign to a trunk cable if loop marshalls through a field junction box.",
                    rule_code="TQ-INFO-001",
                    row_number=rec["excel_row"],
                )
            )

    # Build valid Signal objects for all non-invalid rows
    valid_signals: List[Signal] = []
    for rec in row_records:
        if rec["idx"] not in invalid_row_indices:
            valid_signals.append(
                Signal(
                    tag=rec["tag"],
                    io_type=rec["io_type"],
                    cable_id=rec["cable_id"],
                    pair_no=rec["pair_no"],
                    description=rec["description"],
                    io_group=rec["io_group"],
                    segregation=rec["segregation"],
                )
            )

    return valid_signals, tqs
