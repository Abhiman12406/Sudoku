import io
import pandas as pd
import pytest
from src.benchmark.synthetic_generator import (
    generate_synthetic_signals,
    generate_synthetic_dataframe,
    generate_synthetic_excel,
    generate_batch_1k,
    generate_batch_5k,
    generate_batch_10k,
)
from src.domain.models import IOType, Signal
from src.domain.cable import build_cable_blocks


def test_generate_synthetic_signals_counts_and_types():
    signals = generate_synthetic_signals(count=100, seed=42)
    assert len(signals) == 100
    assert all(isinstance(s, Signal) for s in signals)

    # All tags must be unique
    tags = [s.tag for s in signals]
    assert len(tags) == len(set(tags))

    # All IO types must be valid members of IOType
    assert all(isinstance(s.io_type, IOType) for s in signals)
    io_types_present = {s.io_type for s in signals}
    assert len(io_types_present) >= 4  # Mix of AI, AO, DI, DO, RTD, TC


def test_generate_synthetic_signals_cables_and_segregation():
    signals = generate_synthetic_signals(count=200, seed=123)
    
    # Cables should have consistent segregation within the cable
    cable_segs = {}
    for s in signals:
        assert s.cable_id is not None
        if s.cable_id not in cable_segs:
            cable_segs[s.cable_id] = s.segregation
        else:
            assert cable_segs[s.cable_id] == s.segregation, f"Inconsistent segregation for cable {s.cable_id}"

    # Segregations present: Train A, Train B, and None
    all_segs = {s.segregation for s in signals}
    assert "A" in all_segs
    assert "B" in all_segs
    assert None in all_segs

    # Cables should build into CableBlocks cleanly with 0 exceptions
    blocks = build_cable_blocks(signals)
    assert len(blocks) > 0
    # Every block should have valid standard size (2, 6, 12, 24)
    assert all(b.pair_count in (2, 6, 12, 24) for b in blocks)


def test_generate_synthetic_dataframe_and_excel():
    df = generate_synthetic_dataframe(count=50, seed=99)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50
    assert set(["Tag", "IO_Type", "Cable_ID", "Pair_No", "Segregation", "IO_Group", "Description"]).issubset(df.columns)

    excel_bytes = generate_synthetic_excel(count=50, seed=99)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    # Verify readable back from Excel
    df_read = pd.read_excel(io.BytesIO(excel_bytes))
    assert len(df_read) == 50
    assert "Tag" in df_read.columns


def test_generate_preset_batches():
    sigs_1k = generate_batch_1k(seed=42)
    assert len(sigs_1k) == 1000

    sigs_5k = generate_batch_5k(seed=42)
    assert len(sigs_5k) == 5000

    sigs_10k = generate_batch_10k(seed=42)
    assert len(sigs_10k) == 10000

    # 10k batch should span approximately 1,000 cables as specified in the spec
    cables_10k = {s.cable_id for s in sigs_10k}
    assert 800 <= len(cables_10k) <= 1200
