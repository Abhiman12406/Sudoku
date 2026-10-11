import pytest
from src.domain.models import IOType, Signal, CableBlock
from src.domain.cable import build_cable_blocks, VALID_CABLE_SIZES


def test_cable_block_creation():
    sig1 = Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1)
    sig2 = Signal(tag="10-FT-102", io_type=IOType.AI, cable_id="CBL-01", pair_no=2)

    block = CableBlock(
        cable_id="CBL-01",
        pair_count=6,
        signals=[sig1, sig2],
    )
    assert block.cable_id == "CBL-01"
    assert block.pair_count == 6
    assert block.used_pair_count == 2
    assert block.spare_pair_numbers == [3, 4, 5, 6]


def test_build_cable_blocks_auto_size():
    # 22 signals on a cable without explicit size -> should resolve to 24 pairs
    signals_24 = [
        Signal(tag=f"10-TT-{i:02d}", io_type=IOType.AI, cable_id="CBL-24", pair_no=i)
        for i in range(1, 23)
    ]
    # 4 signals on a cable -> should resolve to 6 pairs
    signals_6 = [
        Signal(tag=f"10-PT-{i:02d}", io_type=IOType.AI, cable_id="CBL-06", pair_no=i)
        for i in range(1, 5)
    ]

    blocks = build_cable_blocks(signals_24 + signals_6)

    block_map = {b.cable_id: b for b in blocks}
    assert "CBL-24" in block_map
    assert block_map["CBL-24"].pair_count == 24
    assert len(block_map["CBL-24"].signals) == 22
    assert block_map["CBL-24"].spare_pair_numbers == [23, 24]

    assert "CBL-06" in block_map
    assert block_map["CBL-06"].pair_count == 6
    assert len(block_map["CBL-06"].signals) == 4
    assert block_map["CBL-06"].spare_pair_numbers == [5, 6]


def test_build_cable_blocks_explicit_size():
    signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-EXPLICIT", pair_no=1),
        Signal(tag="10-FT-102", io_type=IOType.AI, cable_id="CBL-EXPLICIT", pair_no=2),
    ]
    declared = {"CBL-EXPLICIT": 12}
    blocks = build_cable_blocks(signals, declared_sizes=declared)
    assert len(blocks) == 1
    assert blocks[0].pair_count == 12
    assert blocks[0].spare_pair_numbers == list(range(3, 13))


def test_build_cable_blocks_duplicate_pair_raises():
    signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1),
        Signal(tag="10-FT-102", io_type=IOType.AI, cable_id="CBL-01", pair_no=1),
    ]
    with pytest.raises(ValueError, match="Duplicate pair"):
        build_cable_blocks(signals)


def test_build_cable_blocks_exceeding_capacity_raises():
    signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=25),
    ]
    with pytest.raises(ValueError, match="exceeds maximum"):
        build_cable_blocks(signals)
