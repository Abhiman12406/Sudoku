"""Unit tests for Seam 1: Revision Diff Classifier."""

import pytest
from src.domain.models import IOType, Signal
from src.revision.classifier import DiffStatus, SignalDiffItem, classify_revision_diff


def test_classify_signals_into_four_categories():
    # Rev A signals
    rev_a = [
        Signal(tag="FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1, description="Flow"),
        Signal(tag="PT-102", io_type=IOType.AI, cable_id="CBL-01", pair_no=2, description="Pressure"),
        Signal(tag="XV-103", io_type=IOType.DO, cable_id="CBL-02", pair_no=1, description="Valve"),
    ]

    # Rev B signals:
    # FT-101: unchanged
    # PT-102: modified (IOType changed from AI to RTD)
    # XV-103: deleted (not in Rev B)
    # LT-104: added (new in Rev B)
    rev_b = [
        Signal(tag="FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1, description="Flow"),
        Signal(tag="PT-102", io_type=IOType.RTD, cable_id="CBL-01", pair_no=2, description="Pressure"),
        Signal(tag="LT-104", io_type=IOType.AI, cable_id="CBL-03", pair_no=1, description="Level"),
    ]

    diff_result = classify_revision_diff(rev_a, rev_b)

    assert diff_result.total_rev_a == 3
    assert diff_result.total_rev_b == 3

    assert len(diff_result.unchanged) == 1
    assert diff_result.unchanged[0].tag == "FT-101"
    assert diff_result.unchanged[0].status == DiffStatus.UNCHANGED

    assert len(diff_result.modified) == 1
    assert diff_result.modified[0].tag == "PT-102"
    assert diff_result.modified[0].status == DiffStatus.MODIFIED
    assert any("io_type" in c.lower() for c in diff_result.modified[0].changes)

    assert len(diff_result.deleted) == 1
    assert diff_result.deleted[0].tag == "XV-103"
    assert diff_result.deleted[0].status == DiffStatus.DELETED

    assert len(diff_result.added) == 1
    assert diff_result.added[0].tag == "LT-104"
    assert diff_result.added[0].status == DiffStatus.ADDED


def test_classify_accepts_allocated_signals_for_rev_a():
    from src.domain.models import AllocatedSignal

    rev_a_allocated = [
        AllocatedSignal(
            tag="FT-101",
            io_type=IOType.AI,
            baseplate=1,
            slot=1,
            cioc=1,
            cabinet=1,
            cable_id="CBL-01",
            pair_no=1,
        )
    ]
    rev_b = [
        Signal(tag="FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1)
    ]

    diff_result = classify_revision_diff(rev_a_allocated, rev_b)
    assert len(diff_result.unchanged) == 1
    assert diff_result.unchanged[0].tag == "FT-101"
    assert diff_result.unchanged[0].status == DiffStatus.UNCHANGED


def test_classify_ignores_wired_spares():
    from src.domain.models import AllocatedSignal

    rev_a = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=1,
        ),
        AllocatedSignal(
            tag="WIRED SPARE",
            io_type=IOType.SPARE,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=2,
            is_spare=True,
        ),
        AllocatedSignal(
            tag="CBL-01-SPARE-03",
            io_type=IOType.SPARE,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=3,
            is_spare=True,
        ),
    ]

    rev_b = [
        Signal(tag="10-FT-101", io_type=IOType.AI),
    ]

    diff_result = classify_revision_diff(rev_a, rev_b)
    assert len(diff_result.unchanged) == 1
    assert diff_result.unchanged[0].tag == "10-FT-101"
    # Neither WIRED SPARE nor CBL-01-SPARE-03 should be classified as deleted customer loops
    assert len(diff_result.deleted) == 0

