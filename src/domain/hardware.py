"""DeltaV Hardware Catalog and mapping lookup."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.domain.models import IOType

DEFAULT_CATALOG: Dict[str, Dict[str, str]] = {
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
}


def load_hardware_catalog(catalog_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Load hardware catalog from json file if available, otherwise return default."""
    if catalog_path and catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("hardware_catalog", DEFAULT_CATALOG)
        except Exception:
            return DEFAULT_CATALOG

    # Default file path check
    repo_catalog = Path("config/deltav_hardware_catalog.json")
    if repo_catalog.exists():
        try:
            with open(repo_catalog, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("hardware_catalog", DEFAULT_CATALOG)
        except Exception:
            return DEFAULT_CATALOG

    return DEFAULT_CATALOG


def resolve_hardware_for_io(io_type: IOType, catalog: Optional[Dict[str, Dict[str, str]]] = None) -> Tuple[str, str]:
    """Resolve (charm_part_no, terminal_block_type) for a given IOType."""
    cat = catalog or load_hardware_catalog()
    key = io_type.value if hasattr(io_type, "value") else str(io_type)
    entry = cat.get(key, DEFAULT_CATALOG.get("AI", {}))
    return entry.get("charm_part_no", "KL3001X1-BA1"), entry.get("terminal_block_type", "Standard")
