"""DeltaV Hardware Catalog and mapping lookup."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from src.domain.models import HardwareAssignment, IOType

DEFAULT_CATALOG: Dict[str, Dict[str, Any]] = {
    "AI": {
        "charm_description": "Analog Input 4-20 mA HART",
        "charm_part_no": "KL3001X1-BA1",
        "terminal_block_type": "Standard",
        "terminal_block_part_no": "KL4001X1-BA1",
    },
    "AO": {
        "charm_description": "Analog Output 4-20 mA HART",
        "charm_part_no": "KL3002X1-BA1",
        "terminal_block_type": "Standard",
        "terminal_block_part_no": "KL4001X1-BA1",
    },
    "DI": {
        "charm_description": "Discrete Input 24 VDC Isolated",
        "charm_part_no": "KL3003X1-BA1",
        "terminal_block_type": "Standard",
        "terminal_block_part_no": "KL4001X1-BA1",
    },
    "DO": {
        "charm_description": "Discrete Output 24 VDC High-Side",
        "charm_part_no": "KL3004X1-BA1",
        "terminal_block_type": "Fused Injected-Power",
        "terminal_block_part_no": "KL4002X1-BA1",
    },
    "DO_RELAY": {
        "charm_description": "Relay Output Form C Isolated",
        "charm_part_no": "KL3005X1-BA1",
        "terminal_block_type": "Relay Form C",
        "terminal_block_part_no": "KL4003X1-BA1",
    },
    "TC": {
        "charm_description": "Thermocouple / mV Input",
        "charm_part_no": "KL3006X1-BA1",
        "terminal_block_type": "CJC",
        "terminal_block_part_no": "KL4004X1-BA1",
    },
    "RTD": {
        "charm_description": "RTD / Resistance Input",
        "charm_part_no": "KL3007X1-BA1",
        "terminal_block_type": "Standard",
        "terminal_block_part_no": "KL4001X1-BA1",
    },
    "SPARE": {
        "charm_description": "Wired Spare",
        "charm_part_no": None,
        "terminal_block_type": "Standard",
        "terminal_block_part_no": "KL4001X1-BA1",
    },
}

RELAY_KEYWORDS = ("relay", "form c", "form_c", "form-c", "dry contact", "dry_contact", "interlock", "rly")
SOLENOID_KEYWORDS = ("solenoid", "sov", "valve", "xv", "shutdown", "blowdown")


def load_hardware_catalog(catalog_path: Optional[Union[str, Path]] = None) -> Dict[str, Dict[str, Any]]:
    """Load hardware catalog from json file if available, otherwise return default."""
    if catalog_path:
        p = Path(catalog_path)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded = data.get("hardware_catalog", data)
                    merged = dict(DEFAULT_CATALOG)
                    merged.update(loaded)
                    return merged
            except Exception:
                return dict(DEFAULT_CATALOG)

    # Default file path check
    repo_catalog = Path("config/deltav_hardware_catalog.json")
    if repo_catalog.exists():
        try:
            with open(repo_catalog, "r", encoding="utf-8") as f:
                data = json.load(f)
                loaded = data.get("hardware_catalog", data)
                merged = dict(DEFAULT_CATALOG)
                merged.update(loaded)
                return merged
        except Exception:
            return dict(DEFAULT_CATALOG)

    return dict(DEFAULT_CATALOG)


def _detect_effective_io_key(
    raw_key: str,
    description: Optional[str] = None,
    tag: Optional[str] = None,
) -> str:
    """Detect whether a DO signal is a Relay Form C or standard Solenoid DO."""
    key = raw_key.strip().upper().replace("-", "_")

    if key in ("DO_RELAY", "RELAY"):
        return "DO_RELAY"

    if key == "DO":
        desc_lower = (description or "").lower()
        tag_lower = (tag or "").lower()
        full_text = f"{desc_lower} {tag_lower}"

        # Check for relay / dry contact heuristics
        if any(kw in full_text for kw in RELAY_KEYWORDS):
            return "DO_RELAY"

        # By default DO maps to DO (Discrete Output 24 VDC High-Side + Fused Injected-Power)
        return "DO"

    return key


def resolve_hardware_assignment(
    io_type: Union[IOType, str],
    description: Optional[str] = None,
    tag: Optional[str] = None,
    catalog: Optional[Dict[str, Any]] = None,
) -> HardwareAssignment:
    """Resolve full HardwareAssignment (CHARM model, part no, terminal block type, part no)
    for a given signal type, taking into account specialized industrial hardware rules
    and engineer overrides.
    """
    cat = catalog or load_hardware_catalog()
    raw_key = io_type.value if hasattr(io_type, "value") else str(io_type)
    effective_key = _detect_effective_io_key(raw_key, description=description, tag=tag)

    if effective_key == "SPARE":
        return HardwareAssignment(
            charm_model="Wired Spare",
            charm_part_no=None,
            terminal_block_type="Standard",
            terminal_block_part_no="KL4001X1-BA1",
        )

    # Lookup in catalog (custom or default)
    entry = cat.get(effective_key)
    if not entry:
        entry = cat.get(raw_key, DEFAULT_CATALOG.get(effective_key, DEFAULT_CATALOG.get("AI", {})))

    charm_model = entry.get("charm_model") or entry.get("charm_description") or "Standard CHARM"
    charm_part_no = entry.get("charm_part_no")
    tb_type = entry.get("terminal_block_type", "Standard")
    tb_part_no = entry.get("terminal_block_part_no")

    return HardwareAssignment(
        charm_model=str(charm_model),
        charm_part_no=str(charm_part_no) if charm_part_no is not None else None,
        terminal_block_type=str(tb_type),
        terminal_block_part_no=str(tb_part_no) if tb_part_no is not None else None,
    )


def resolve_hardware_for_io(
    io_type: IOType,
    catalog: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], str]:
    """Resolve (charm_part_no, terminal_block_type) for a given IOType (backwards-compatible)."""
    hw = resolve_hardware_assignment(io_type, catalog=catalog)
    return hw.charm_part_no, hw.terminal_block_type
