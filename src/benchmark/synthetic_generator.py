"""Automated synthetic industrial instrumentation signal generator for scalability stress benchmarks."""

import io
from pathlib import Path
import random
from typing import Dict, List, Optional, Sequence, Tuple, Union
import pandas as pd

from src.domain.models import IOType, Signal

# Standard industrial cable capacities
VALID_CABLE_SIZES = (2, 6, 12, 24)

# Realistic industrial tagging patterns
INSTRUMENT_PATTERNS = {
    IOType.AI: [
        ("FT", "Flow Transmitter (4-20mA HART)"),
        ("PT", "Pressure Transmitter (4-20mA HART)"),
        ("LT", "Level Transmitter (4-20mA HART)"),
        ("AT", "Gas Analyzer Transmitter (4-20mA)"),
    ],
    IOType.AO: [
        ("FCV", "Flow Control Valve Actuator (4-20mA)"),
        ("PCV", "Pressure Control Valve Actuator (4-20mA)"),
        ("LCV", "Level Control Valve Positioner (4-20mA)"),
    ],
    IOType.DI: [
        ("ZSO", "Valve Open Limit Switch (Dry Contact)"),
        ("ZSC", "Valve Closed Limit Switch (Dry Contact)"),
        ("PSH", "High Pressure Alarm Switch"),
        ("LSL", "Low Level Alarm Switch"),
    ],
    IOType.DO: [
        ("XV", "Emergency Shutdown Solenoid Valve (24VDC 1.0A)"),
        ("SOV", "Process Vent Solenoid Valve (24VDC)"),
        ("PMP", "Pump Motor Run Command (Relay Form C)"),
        ("ALM", "High-Decibel Audio-Visual Beacon"),
    ],
    IOType.RTD: [
        ("TE_RTD", "Bearing Temperature Sensor (Pt100 RTD)"),
        ("TT_RTD", "Compressor Casing RTD Sensor"),
    ],
    IOType.TC: [
        ("TE_TC", "Furnace Core Thermocouple (Type K)"),
        ("TT_TC", "Reactor Bed Temperature Thermocouple"),
    ],
}


def generate_synthetic_signals(
    count: int,
    cable_count: Optional[int] = None,
    seed: int = 42,
    segregation_ratio: Tuple[float, float, float] = (0.4, 0.4, 0.2),
) -> List[Signal]:
    """Generate a realistic industrial instrumentation signal batch.

    Args:
        count: Exact target number of signals to generate.
        cable_count: Approximate number of multi-conductor trunk cables to distribute across.
        seed: Random seed for reproducible dataset generation.
        segregation_ratio: Proportions of (Train A, Train B, Unsegregated None).

    Returns:
        List of Signal domain objects with consistent cable grouping and pair ordering.
    """
    if count <= 0:
        return []

    rng = random.Random(seed)

    # Estimate cable count if not provided
    # Standard mix: average cable has ~10 active pairs
    if cable_count is None:
        target_cables = max(1, round(count / 10.0))
    else:
        target_cables = max(1, cable_count)

    # Distribute signals into cables
    # Cable sizes weighted by typical refinery / offshore distributions:
    # 24-pair: 30%, 12-pair: 40%, 6-pair: 20%, 2-pair: 10%
    size_choices = [24, 12, 6, 2]
    size_weights = [0.30, 0.40, 0.20, 0.10]

    train_choices = ["A", "B", None]
    norm_ratio = sum(segregation_ratio)
    train_weights = [r / norm_ratio for r in segregation_ratio]

    io_types = list(INSTRUMENT_PATTERNS.keys())
    # Weighted by typical industrial DCS I/O ratios: AI 35%, DI 30%, DO 20%, AO 10%, RTD 3%, TC 2%
    io_weights = [0.35, 0.10, 0.30, 0.20, 0.03, 0.02]

    units = [f"AREA-{u:02d}" for u in range(1, 11)]

    signals: List[Signal] = []
    generated_count = 0
    cable_idx = 1
    tag_counter = 1000

    while generated_count < count:
        c_size = rng.choices(size_choices, weights=size_weights, k=1)[0]
        c_seg = rng.choices(train_choices, weights=train_weights, k=1)[0]
        c_unit = rng.choice(units)
        
        # Cable ID prefix reflecting segregation and area
        seg_tag = f"-TR{c_seg}" if c_seg else "-GEN"
        cable_id = f"CBL-{c_unit[5:]}{seg_tag}-{cable_idx:04d}"
        cable_idx += 1

        # How many active pairs in this cable?
        # Typically between 60% and 100% of cable capacity (leaving a few wired spares)
        max_possible_pairs = min(c_size, count - generated_count)
        if max_possible_pairs <= 0:
            break

        min_fill = max(1, int(c_size * 0.6))
        desired_pairs = rng.randint(min_fill, c_size)
        actual_pairs = min(desired_pairs, max_possible_pairs)

        # Distribute pairs strictly in ascending order 1..actual_pairs
        for pair_no in range(1, actual_pairs + 1):
            io_type = rng.choices(io_types, weights=io_weights, k=1)[0]
            prefix, desc_template = rng.choice(INSTRUMENT_PATTERNS[io_type])
            
            tag_counter += 1
            suffix = f"-{c_seg}" if c_seg else ""
            tag = f"{c_unit[5:]}-{prefix}-{tag_counter:04d}{suffix}"

            signals.append(
                Signal(
                    tag=tag,
                    io_type=io_type,
                    cable_id=cable_id,
                    pair_no=pair_no,
                    segregation=c_seg,
                    io_group=c_unit,
                    description=f"{desc_template} [Cable {cable_id} Pair {pair_no}]",
                )
            )
            generated_count += 1
            if generated_count >= count:
                break

    return signals


def generate_synthetic_dataframe(
    count: int,
    cable_count: Optional[int] = None,
    seed: int = 42,
    segregation_ratio: Tuple[float, float, float] = (0.4, 0.4, 0.2),
) -> pd.DataFrame:
    """Generate synthetic signals as a pandas DataFrame."""
    signals = generate_synthetic_signals(
        count=count,
        cable_count=cable_count,
        seed=seed,
        segregation_ratio=segregation_ratio,
    )
    records = [
        {
            "Tag": s.tag,
            "IO_Type": s.io_type.value,
            "Cable_ID": s.cable_id,
            "Pair_No": s.pair_no,
            "Segregation": s.segregation,
            "IO_Group": s.io_group,
            "Description": s.description,
        }
        for s in signals
    ]
    return pd.DataFrame(records)


def generate_synthetic_excel(
    count: int,
    output_path: Optional[Union[str, Path]] = None,
    cable_count: Optional[int] = None,
    seed: int = 42,
    segregation_ratio: Tuple[float, float, float] = (0.4, 0.4, 0.2),
) -> bytes:
    """Generate synthetic signals and export directly to Excel bytes or file."""
    df = generate_synthetic_dataframe(
        count=count,
        cable_count=cable_count,
        seed=seed,
        segregation_ratio=segregation_ratio,
    )
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="IO_Database", index=False)

    data = out_buf.getvalue()
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    return data


def generate_batch_1k(seed: int = 42) -> List[Signal]:
    """Generate 1,000 synthetic industrial signals (~100 cables)."""
    return generate_synthetic_signals(count=1000, cable_count=100, seed=seed)


def generate_batch_5k(seed: int = 42) -> List[Signal]:
    """Generate 5,000 synthetic industrial signals (~500 cables)."""
    return generate_synthetic_signals(count=5000, cable_count=500, seed=seed)


def generate_batch_10k(seed: int = 42) -> List[Signal]:
    """Generate 10,000 synthetic industrial signals (~1,000 cables)."""
    return generate_synthetic_signals(count=10000, cable_count=1000, seed=seed)
