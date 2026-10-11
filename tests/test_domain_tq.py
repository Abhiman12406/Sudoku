import pytest
from pydantic import ValidationError

from src.domain.models import Severity, TechnicalQuery


def test_technical_query_creation_and_attributes():
    tq = TechnicalQuery(
        tq_id="TQ-INST-001",
        category="Duplicate Tag",
        impacted_tag="10-FT-101",
        description="Duplicate instrument tag found in row 5.",
        severity=Severity.CRITICAL,
        recommended_remedy="Clarify tag nomenclature with P&ID and rename duplicate tag.",
        row_number=5,
    )

    assert tq.tq_id == "TQ-INST-001"
    assert tq.category == "Duplicate Tag"
    assert tq.impacted_tag == "10-FT-101"
    assert tq.severity == Severity.CRITICAL
    assert tq.severity.value == "Critical"
    assert tq.recommended_remedy == "Clarify tag nomenclature with P&ID and rename duplicate tag."
    assert tq.recommended_action == tq.recommended_remedy
    assert tq.row_number == 5


def test_technical_query_validation():
    with pytest.raises(ValidationError):
        # Missing required fields like category, severity, description
        TechnicalQuery(tq_id="TQ-INST-002")


def test_severity_values():
    assert Severity.CRITICAL.value == "Critical"
    assert Severity.WARNING.value == "Warning"
    assert Severity.INFO.value == "Info"
