"""Fuzzy and regex column auto-mapper for customer signal spreadsheets."""

import re
from typing import Dict, List, Optional, Pattern, Sequence


# Target field regex patterns
FIELD_REGEX_PATTERNS: Dict[str, List[Pattern]] = {
    "tag": [
        re.compile(r"^(instrument[\s_\-]*)?tag([\s_\-]*(no|number|name|id))?$", re.IGNORECASE),
        re.compile(r"^loop[\s_\-]*tag$", re.IGNORECASE),
        re.compile(r"^tag$", re.IGNORECASE),
    ],
    "io_type": [
        re.compile(r"^(i[\s_\-/]*o|signal|channel)[\s_\-]*(type)?$", re.IGNORECASE),
        re.compile(r"^io$", re.IGNORECASE),
        re.compile(r"^type$", re.IGNORECASE),
    ],
    "cable_id": [
        re.compile(r"^(trunk[\s_\-]*)?cable([\s_\-]*(id|no|number))?$", re.IGNORECASE),
        re.compile(r"^multicore([\s_\-]*(id|no|cable|number))?$", re.IGNORECASE),
        re.compile(r"^cable$", re.IGNORECASE),
    ],
    "pair_no": [
        re.compile(r"^(wire[\s_\-]*)?pair([\s_\-]*(no|num|number|id|#))?$", re.IGNORECASE),
        re.compile(r"^pair[\s_\-]*#?$", re.IGNORECASE),
    ],
    "description": [
        re.compile(r"^(tag[\s_\-]*|instrument[\s_\-]*|service[\s_\-]*)?desc(ription)?$", re.IGNORECASE),
        re.compile(r"^service$", re.IGNORECASE),
        re.compile(r"^desc$", re.IGNORECASE),
    ],
    "io_group": [
        re.compile(r"^(i[\s_\-/]*o[\s_\-]*)?group$", re.IGNORECASE),
        re.compile(r"^grp$", re.IGNORECASE),
        re.compile(r"^unit$", re.IGNORECASE),
        re.compile(r"^(plant[\s_\-]*)?area$", re.IGNORECASE),
        re.compile(r"^system$", re.IGNORECASE),
    ],
    "segregation": [
        re.compile(r"^(channel[\s_\-]*)?seg(regation)?$", re.IGNORECASE),
        re.compile(r"^(safety[\s_\-]*)?train$", re.IGNORECASE),
        re.compile(r"^redundancy$", re.IGNORECASE),
    ],
    "cable_size": [
        re.compile(r"^cable[\s_\-]*(size|capacity|pairs)$", re.IGNORECASE),
        re.compile(r"^pair[\s_\-]*count$", re.IGNORECASE),
        re.compile(r"^capacity$", re.IGNORECASE),
    ],
}

# Simplified token synonyms for normalized fallback matching
NORMALIZED_SYNONYMS: Dict[str, List[str]] = {
    "tag": ["tag", "instrumenttag", "tagno", "tagname", "looptag", "tagnumber", "tagid"],
    "io_type": ["iotype", "signaltype", "channeltype", "type", "io", "signaltyp"],
    "cable_id": ["cableid", "cableno", "cable", "trunkcable", "multicore", "cablenumber"],
    "pair_no": ["pairno", "pair", "pairnumber", "wirepair", "pairid", "pairnum"],
    "description": ["description", "desc", "service", "tagdesc", "instrumentdescription"],
    "io_group": ["iogroup", "group", "grp", "unit", "area", "plantarea", "system"],
    "segregation": ["segregation", "seg", "train", "redundancy", "channelseg", "safetytrain"],
    "cable_size": ["cablesize", "cablepairs", "capacity", "cablecapacity", "paircount"],
}


def clean_column_name(col: str) -> str:
    """Normalize a column name by removing non-alphanumeric characters and lowercasing."""
    return re.sub(r"[^a-z0-9]", "", str(col).lower())


def match_field_for_column(col_name: str) -> Optional[str]:
    """Determine which domain field matches the raw column header."""
    raw = str(col_name).strip()
    if not raw:
        return None

    # 1. Regex matching
    for field, patterns in FIELD_REGEX_PATTERNS.items():
        for pat in patterns:
            if pat.match(raw):
                return field

    # 2. Normalized token matching
    cleaned = clean_column_name(raw)
    for field, synonyms in NORMALIZED_SYNONYMS.items():
        if cleaned in synonyms:
            return field

    return None


def auto_map_columns(columns: Sequence[str]) -> Dict[str, str]:
    """Map detected raw columns to standard Signal field names.

    Args:
        columns: Sequence of column names from the customer file.

    Returns:
        Mapping dictionary of {standard_field_name: raw_column_name}.
    """
    mapping: Dict[str, str] = {}
    assigned_raw: set = set()

    for col in columns:
        matched_field = match_field_for_column(col)
        if matched_field and matched_field not in mapping and col not in assigned_raw:
            mapping[matched_field] = col
            assigned_raw.add(col)

    return mapping
