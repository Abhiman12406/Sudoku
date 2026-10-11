"""Domain models for IO Signal Sudoku."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class IOType(str, Enum):
    AI = "AI"
    AO = "AO"
    DI = "DI"
    DO = "DO"
    RTD = "RTD"
    TC = "TC"


class Signal(BaseModel):
    tag: str = Field(..., description="Unique instrument loop tag, e.g. 10-FT-101")
    io_type: IOType = Field(..., description="Signal IO type: AI, AO, DI, DO, RTD, TC")
    cable_id: Optional[str] = Field(default=None, description="Trunk or multicore cable identifier")
    pair_no: Optional[int] = Field(default=None, description="Pair index inside the cable")
    description: Optional[str] = Field(default=None, description="Instrument loop engineering description")
    io_group: Optional[str] = Field(default=None, description="Functional or plant area unit group")
    segregation: Optional[str] = Field(default=None, description="Train redundancy segregation (A, B, or None)")


class AllocatedSignal(BaseModel):
    tag: str
    io_type: IOType
    baseplate: int = Field(..., ge=1, description="Physical baseplate number (1..N)")
    slot: int = Field(..., ge=1, le=12, description="Physical slot number on the baseplate (1..12)")
    cable_id: Optional[str] = None
    pair_no: Optional[int] = None
    description: Optional[str] = None
    charm_part_no: Optional[str] = None
    terminal_block_type: Optional[str] = None
