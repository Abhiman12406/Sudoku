"""Domain models for IO Signal Sudoku."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class IOType(str, Enum):
    AI = "AI"
    AO = "AO"
    DI = "DI"
    DO = "DO"
    DO_RELAY = "DO_RELAY"
    RTD = "RTD"
    TC = "TC"
    SPARE = "SPARE"


class Signal(BaseModel):
    tag: str = Field(..., description="Unique instrument loop tag, e.g. 10-FT-101")
    io_type: IOType = Field(..., description="Signal IO type: AI, AO, DI, DO, RTD, TC, SPARE")
    cable_id: Optional[str] = Field(default=None, description="Trunk or multicore cable identifier")
    pair_no: Optional[int] = Field(default=None, description="Pair index inside the cable")
    description: Optional[str] = Field(default=None, description="Instrument loop engineering description")
    io_group: Optional[str] = Field(default=None, description="Functional or plant area unit group")
    segregation: Optional[str] = Field(default=None, description="Train redundancy segregation (A, B, or None)")


class CableBlock(BaseModel):
    cable_id: str = Field(..., description="Unique trunk cable identifier")
    pair_count: int = Field(..., description="Total pairs in cable (2, 6, 12, or 24)")
    signals: list[Signal] = Field(default_factory=list, description="Assigned signals in the cable")
    io_group: Optional[str] = Field(default=None, description="Common IO group")
    segregation: Optional[str] = Field(default=None, description="Segregation (A or B)")

    @property
    def used_pair_count(self) -> int:
        return len(self.signals)

    @property
    def signals_by_pair(self) -> dict[int, Signal]:
        return {s.pair_no: s for s in self.signals if s.pair_no is not None}

    @property
    def spare_pair_numbers(self) -> list[int]:
        used = self.signals_by_pair
        return [p for p in range(1, self.pair_count + 1) if p not in used]


class HardwareAssignment(BaseModel):
    charm_model: str = Field(..., description="Emerson DeltaV CHARM model name")
    charm_part_no: Optional[str] = Field(default=None, description="Emerson DeltaV CHARM part number")
    terminal_block_type: str = Field(..., description="Terminal block type (Standard, CJC, Fused Injected-Power, Relay Form C)")
    terminal_block_part_no: Optional[str] = Field(default=None, description="Terminal block part number")


class AllocatedSignal(BaseModel):
    tag: str
    io_type: IOType
    baseplate: int = Field(..., ge=1, description="Physical baseplate number (1..N)")
    slot: int = Field(..., ge=1, le=12, description="Physical slot number on the baseplate (1..12)")
    cioc: int = Field(default=1, ge=1, description="Physical CIOC index (1..N)")
    cable_id: Optional[str] = None
    pair_no: Optional[int] = None
    description: Optional[str] = None
    charm_model: Optional[str] = None
    charm_part_no: Optional[str] = None
    terminal_block_type: Optional[str] = None
    terminal_block_part_no: Optional[str] = None
    is_spare: bool = Field(default=False, description="Flag indicating if slot is an unallocated wired spare")


class Severity(str, Enum):
    CRITICAL = "Critical"
    WARNING = "Warning"
    INFO = "Info"

    @property
    def badge(self) -> str:
        if self == Severity.CRITICAL:
            return "🔴 Critical"
        elif self == Severity.WARNING:
            return "🟡 Warning"
        return "🔵 Info"


class TechnicalQuery(BaseModel):
    tq_id: str = Field(..., description="Unique technical query identifier, e.g. TQ-INST-001")
    category: str = Field(..., description="Error classification category, e.g. Duplicate Tag")
    impacted_tag: str = Field(..., description="Impacted instrument loop tag or placeholder")
    description: str = Field(..., description="Detailed engineering description of the conflict or error")
    severity: Severity = Field(..., description="Severity level: Critical, Warning, or Info")
    recommended_remedy: str = Field(..., description="Prescriptive engineering remedy or resolution recommendation")
    rule_code: Optional[str] = Field(default=None, description="Standard validation rule code, e.g. TQ-VAL-001")
    row_number: Optional[int] = Field(default=None, description="Source spreadsheet row number if applicable")
    cable_id: Optional[str] = Field(default=None, description="Associated trunk cable identifier if applicable")

    @property
    def recommended_action(self) -> str:
        return self.recommended_remedy



