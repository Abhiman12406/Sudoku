import pytest
from pydantic import ValidationError
from src.domain.models import IOType, Signal, AllocatedSignal, SegregationPolicy


def test_signal_segregation_attributes():
    # Valid Train A
    sig_a = Signal(tag="10-FT-101", io_type=IOType.AI, segregation="A")
    assert sig_a.segregation == "A"

    # Valid Train B
    sig_b = Signal(tag="10-FT-102", io_type=IOType.AI, segregation="B")
    assert sig_b.segregation == "B"

    # None / unassigned
    sig_none = Signal(tag="10-FT-103", io_type=IOType.AI, segregation=None)
    assert sig_none.segregation is None

    # Normalization of lowercase and empty string
    sig_lower_a = Signal(tag="10-FT-104", io_type=IOType.AI, segregation="a")
    assert sig_lower_a.segregation == "A"

    sig_lower_b = Signal(tag="10-FT-105", io_type=IOType.AI, segregation="b")
    assert sig_lower_b.segregation == "B"

    sig_empty = Signal(tag="10-FT-106", io_type=IOType.AI, segregation="   ")
    assert sig_empty.segregation is None

    # Invalid segregation should fail validation
    with pytest.raises(ValidationError):
        Signal(tag="10-FT-107", io_type=IOType.AI, segregation="C")


def test_allocated_signal_has_segregation_and_cabinet():
    alloc = AllocatedSignal(
        tag="10-FT-101",
        io_type=IOType.AI,
        cioc=1,
        baseplate=1,
        slot=1,
        cabinet=1,
        segregation="A",
    )
    assert alloc.segregation == "A"
    assert alloc.cabinet == 1

    alloc_default = AllocatedSignal(
        tag="10-FT-102",
        io_type=IOType.AI,
        baseplate=1,
        slot=2,
    )
    assert alloc_default.segregation is None
    assert alloc_default.cabinet == 1


def test_segregation_policy_enum():
    assert SegregationPolicy.CIOC.value == "CIOC"
    assert SegregationPolicy.CABINET.value == "CABINET"
    assert SegregationPolicy.from_str("cioc") == SegregationPolicy.CIOC
    assert SegregationPolicy.from_str("Cabinet-level") == SegregationPolicy.CABINET


def test_macro_packing_cioc_segregation():
    from src.domain.models import CableBlock
    from src.solver.macro_packer import solve_macro_packing

    # Two 12-pair cables: one Train A, one Train B.
    # Total 24 slots <= 96, but segregation forbids sharing CIOC.
    blocks = [
        CableBlock(cable_id="CBL-A-01", pair_count=12, segregation="A", signals=[]),
        CableBlock(cable_id="CBL-B-01", pair_count=12, segregation="B", signals=[]),
    ]

    result = solve_macro_packing(blocks, slots_per_cioc=96, segregation_policy="CIOC")

    assert result.num_ciocs == 2
    # Verify the two blocks are assigned to different CIOCs
    ciocs_a = [c for c, blist in result.cioc_assignments.items() if any(b.segregation == "A" for b in blist)]
    ciocs_b = [c for c, blist in result.cioc_assignments.items() if any(b.segregation == "B" for b in blist)]

    assert len(ciocs_a) == 1
    assert len(ciocs_b) == 1
    assert ciocs_a[0] != ciocs_b[0]

    # Verify each CIOC contains only its respective train
    for c in ciocs_a:
        for b in result.cioc_assignments[c]:
            assert b.segregation != "B"
    for c in ciocs_b:
        for b in result.cioc_assignments[c]:
            assert b.segregation != "A"

    # Verify result exposes cioc_trains metadata
    assert result.cioc_trains[ciocs_a[0]] == "A"
    assert result.cioc_trains[ciocs_b[0]] == "B"


def test_macro_packing_cabinet_segregation():
    from src.domain.models import CableBlock
    from src.solver.macro_packer import solve_macro_packing

    blocks = [
        CableBlock(cable_id="CBL-A-01", pair_count=12, segregation="A", signals=[]),
        CableBlock(cable_id="CBL-B-01", pair_count=12, segregation="B", signals=[]),
    ]

    # With 4 CIOCs per cabinet, Cabinet 1 = CIOCs 1..4, Cabinet 2 = CIOCs 5..8
    result = solve_macro_packing(
        blocks,
        slots_per_cioc=96,
        segregation_policy="CABINET",
        ciocs_per_cabinet=4,
    )

    cioc_a = [c for c, blist in result.cioc_assignments.items() if any(b.segregation == "A" for b in blist)][0]
    cioc_b = [c for c, blist in result.cioc_assignments.items() if any(b.segregation == "B" for b in blist)][0]

    cab_a = (cioc_a - 1) // 4 + 1
    cab_b = (cioc_b - 1) // 4 + 1

    assert cab_a != cab_b, f"Train A (CIOC {cioc_a}, CAB {cab_a}) and Train B (CIOC {cioc_b}, CAB {cab_b}) must be in separate cabinets"


def test_macro_packing_unassigned_cables_share_cioc_freely():
    from src.domain.models import CableBlock
    from src.solver.macro_packer import solve_macro_packing

    blocks = [
        CableBlock(cable_id="CBL-A-01", pair_count=12, segregation="A", signals=[]),
        CableBlock(cable_id="CBL-COMMON-01", pair_count=12, segregation=None, signals=[]),
    ]

    result = solve_macro_packing(blocks, slots_per_cioc=96, segregation_policy="CIOC")
    # Both should fit comfortably on 1 CIOC (24 slots <= 96)
    assert result.num_ciocs == 1
    assert 1 in result.cioc_assignments
    assert len(result.cioc_assignments[1]) == 2


def test_hierarchical_packing_cioc_segregation():
    from src.solver.hierarchical_solver import solve_hierarchical_packing

    sig_a = Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-A-01", pair_no=1, segregation="A")
    sig_b = Signal(tag="20-FT-201", io_type=IOType.AI, cable_id="CBL-B-01", pair_no=1, segregation="B")

    allocations = solve_hierarchical_packing([sig_a, sig_b], segregation_policy="CIOC")

    alloc_a = [a for a in allocations if a.tag == "10-FT-101"][0]
    alloc_b = [a for a in allocations if a.tag == "20-FT-201"][0]

    assert alloc_a.segregation == "A"
    assert alloc_b.segregation == "B"
    assert alloc_a.cioc != alloc_b.cioc, f"Train A CIOC {alloc_a.cioc} must not equal Train B CIOC {alloc_b.cioc}"

    # Verify wired spares in CBL-A-01 also inherit segregation A
    spares_a = [a for a in allocations if a.cable_id == "CBL-A-01" and a.is_spare]
    for s in spares_a:
        assert s.segregation == "A"


def test_hierarchical_packing_cabinet_segregation():
    from src.solver.hierarchical_solver import solve_hierarchical_packing

    sig_a = Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-A-01", pair_no=1, segregation="A")
    sig_b = Signal(tag="20-FT-201", io_type=IOType.AI, cable_id="CBL-B-01", pair_no=1, segregation="B")

    allocations = solve_hierarchical_packing(
        [sig_a, sig_b],
        segregation_policy="CABINET",
        ciocs_per_cabinet=4,
    )

    alloc_a = [a for a in allocations if a.tag == "10-FT-101"][0]
    alloc_b = [a for a in allocations if a.tag == "20-FT-201"][0]

    assert alloc_a.cabinet != alloc_b.cabinet, f"Train A CAB {alloc_a.cabinet} must not equal Train B CAB {alloc_b.cabinet}"


def test_audit_passes_valid_segregated_allocations():
    from src.solver.audit import verify_allocation_invariants

    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
            cabinet=1,
            segregation="A",
        ),
        AllocatedSignal(
            tag="20-FT-201",
            io_type=IOType.AI,
            cioc=2,
            baseplate=1,
            slot=1,
            cabinet=1,
            segregation="B",
        ),
    ]

    valid, errors = verify_allocation_invariants(allocations, segregation_policy="CIOC")
    assert valid is True
    assert errors == []


def test_audit_fails_when_cioc_has_mixed_a_and_b():
    from src.solver.audit import verify_allocation_invariants

    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
            cabinet=1,
            segregation="A",
        ),
        AllocatedSignal(
            tag="20-FT-201",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=2,
            cabinet=1,
            segregation="B",
        ),
    ]

    valid, errors = verify_allocation_invariants(allocations, segregation_policy="CIOC")
    assert valid is False
    assert any("Segregation breach" in e and "CIOC 1" in e for e in errors)


def test_audit_cabinet_policy_enforcement():
    from src.solver.audit import verify_allocation_invariants

    # CIOC 1 and CIOC 2 both belong to Cabinet 1 (with ciocs_per_cabinet=4)
    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
            cabinet=1,
            segregation="A",
        ),
        AllocatedSignal(
            tag="20-FT-201",
            io_type=IOType.AI,
            cioc=2,
            baseplate=1,
            slot=1,
            cabinet=1,
            segregation="B",
        ),
    ]

    # CIOC policy allows separate CIOCs in the same cabinet
    valid_cioc, errors_cioc = verify_allocation_invariants(allocations, segregation_policy="CIOC")
    assert valid_cioc is True

    # Cabinet policy forbids Train A and Train B in the same cabinet
    valid_cab, errors_cab = verify_allocation_invariants(
        allocations,
        segregation_policy="CABINET",
        ciocs_per_cabinet=4,
    )
    assert valid_cab is False
    assert any("Segregation breach" in e and "Cabinet 1" in e for e in errors_cab)


def test_hierarchical_pipeline_e2e_segregation():
    import io
    import pandas as pd
    from src.pipeline import run_hierarchical_pipeline

    data = {
        "Tag": ["10-FT-101", "10-FV-101", "20-FT-201", "20-FV-201"],
        "IO Type": ["AI", "AO", "AI", "AO"],
        "Cable ID": ["CBL-A-01", "CBL-A-01", "CBL-B-01", "CBL-B-01"],
        "Pair No": [1, 2, 1, 2],
        "Segregation": ["A", "A", "B", "B"],
        "Description": ["Train A Flow", "Train A Valve", "Train B Flow", "Train B Valve"],
    }
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    in_bytes = buf.getvalue()

    result = run_hierarchical_pipeline(in_bytes, segregation_policy="CIOC")
    allocations = result.allocations

    ciocs_a = {a.cioc for a in allocations if a.segregation == "A"}
    ciocs_b = {a.cioc for a in allocations if a.segregation == "B"}

    assert ciocs_a.isdisjoint(ciocs_b), f"Train A CIOCs {ciocs_a} and Train B CIOCs {ciocs_b} must be disjoint"
    assert len(result.tqs) == 0

    # Verify Excel deliverable
    df_out = pd.read_excel(io.BytesIO(result.excel_bytes), sheet_name="Allocation")
    assert "Segregation" in df_out.columns
    assert set(df_out["Segregation"].dropna().unique()) == {"A", "B"}


def test_visualizer_renders_train_a_and_train_b_status_banners():
    from src.ui.components.cabinet_visualizer import render_din_rail_html

    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
            cable_id="CBL-A-01",
            pair_no=1,
            segregation="A",
        ),
        AllocatedSignal(
            tag="20-FT-201",
            io_type=IOType.AI,
            cioc=2,
            baseplate=1,
            slot=1,
            cable_id="CBL-B-01",
            pair_no=1,
            segregation="B",
        ),
    ]

    html = render_din_rail_html(allocations)
    # Verify Train A badge / banner styling
    assert "TRAIN A" in html
    # Verify Train B badge / banner styling
    assert "TRAIN B" in html


def test_allocated_signal_segregation_validation():
    # Valid values
    s_a = AllocatedSignal(tag="FT-101", io_type=IOType.AI, cioc=1, baseplate=1, slot=1, segregation=" a ")
    assert s_a.segregation == "A"

    s_none = AllocatedSignal(tag="FT-102", io_type=IOType.AI, cioc=1, baseplate=1, slot=2, segregation="")
    assert s_none.segregation is None

    # Invalid value raises ValueError
    with pytest.raises(ValueError, match="Segregation must be 'A', 'B', or None"):
        AllocatedSignal(tag="FT-103", io_type=IOType.AI, cioc=1, baseplate=1, slot=3, segregation="C")


def test_audit_report_rule_safe_01_evaluates_cabinet_policy():
    from src.export.audit_report import generate_rule_compliance_audit

    # Train A in CIOC 1, Train B in CIOC 2 (both in Cabinet 1)
    allocs = [
        AllocatedSignal(tag="FT-A", io_type=IOType.AI, cioc=1, baseplate=1, slot=1, cabinet=1, segregation="A"),
        AllocatedSignal(tag="FT-B", io_type=IOType.AI, cioc=2, baseplate=1, slot=1, cabinet=1, segregation="B"),
    ]

    # Under CIOC policy: PASS (different CIOCs)
    items_cioc, _ = generate_rule_compliance_audit(allocs, segregation_policy=SegregationPolicy.CIOC)
    rule_cioc = next(it for it in items_cioc if it.rule_id == "RULE-SAFE-01")
    assert rule_cioc.status == "PASS"
    assert rule_cioc.violations == 0

    # Under CABINET policy: FAIL (same Cabinet 1)
    items_cab, _ = generate_rule_compliance_audit(allocs, segregation_policy=SegregationPolicy.CABINET)
    rule_cab = next(it for it in items_cab if it.rule_id == "RULE-SAFE-01")
    assert rule_cab.status == "FAIL"
    assert rule_cab.violations == 1
    assert "Cabinet" in rule_cab.requirement






