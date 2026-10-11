"""DIN-Rail Baseplate Rack Visualizer Component for Emerson DeltaV Marshalling."""

from collections import defaultdict
from typing import Any, Dict, List, Sequence
import streamlit as st

from src.domain.models import AllocatedSignal

# Distinct aesthetic color palette for trunk cables
PALETTE = [
    "#1E88E5",  # Blue
    "#43A047",  # Green
    "#FB8C00",  # Orange
    "#8E24AA",  # Purple
    "#00ACC1",  # Cyan
    "#E53935",  # Red
    "#3949AB",  # Indigo
    "#D81B60",  # Pink
    "#FDD835",  # Yellow
    "#546E7A",  # Slate
    "#00897B",  # Teal
    "#6D4C41",  # Brown
]


def get_cable_color_map(allocations: Sequence[AllocatedSignal]) -> Dict[str, str]:
    """Map each unique cable_id to a distinct theme color."""
    cables = sorted(list({a.cable_id for a in allocations if a.cable_id}))
    return {cid: PALETTE[idx % len(PALETTE)] for idx, cid in enumerate(cables)}


def build_rack_grid_data(
    allocations: Sequence[AllocatedSignal],
    charms_per_baseplate: int = 12,
) -> Dict[int, Dict[int, List[Dict[str, Any]]]]:
    """Organize allocated signals into a structured (cioc -> baseplate -> slots[12]) grid.

    Returns:
        Dict[cioc_id, Dict[bp_id, List[slot_dict]]]
    """
    grid: Dict[int, Dict[int, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    if not allocations:
        return grid

    # Map allocations by (cioc, baseplate, slot)
    alloc_map: Dict[tuple, AllocatedSignal] = {
        (a.cioc, a.baseplate, a.slot): a for a in allocations
    }

    ciocs = sorted(list({a.cioc for a in allocations}))
    for c in ciocs:
        bps = sorted(list({a.baseplate for a in allocations if a.cioc == c}))
        max_bp = max(bps) if bps else 1
        for bp in range(1, max_bp + 1):
            slots_list: List[Dict[str, Any]] = []
            for s in range(1, charms_per_baseplate + 1):
                key = (c, bp, s)
                if key in alloc_map:
                    alloc = alloc_map[key]
                    slots_list.append(
                        {
                            "slot": s,
                            "tag": alloc.tag,
                            "io_type": alloc.io_type.value if hasattr(alloc.io_type, "value") else str(alloc.io_type),
                            "cable_id": alloc.cable_id,
                            "pair_no": alloc.pair_no,
                            "charm_model": alloc.charm_model,
                            "charm_part_no": alloc.charm_part_no,
                            "terminal_block_type": alloc.terminal_block_type,
                            "terminal_block_part_no": alloc.terminal_block_part_no,
                            "description": alloc.description,
                            "segregation": alloc.segregation,
                            "cabinet": alloc.cabinet,
                            "is_spare": alloc.is_spare,
                            "is_empty": False,
                        }
                    )
                else:
                    slots_list.append(
                        {
                            "slot": s,
                            "tag": None,
                            "io_type": None,
                            "cable_id": None,
                            "pair_no": None,
                            "charm_model": None,
                            "charm_part_no": None,
                            "terminal_block_type": None,
                            "terminal_block_part_no": None,
                            "description": None,
                            "segregation": None,
                            "cabinet": None,
                            "is_spare": False,
                            "is_empty": True,
                        }
                    )
            grid[c][bp] = slots_list

    return grid


def render_din_rail_html(
    allocations: Sequence[AllocatedSignal],
    charms_per_baseplate: int = 12,
) -> str:
    """Render HTML representation of the DIN rail baseplate rack with visually grouped cables."""
    if not allocations:
        return "<p style='color: #666;'>No allocations to render.</p>"

    grid = build_rack_grid_data(allocations, charms_per_baseplate=charms_per_baseplate)
    color_map = get_cable_color_map(allocations)

    html_parts = []
    html_parts.append(
        """
        <style>
        .din-rail-container {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0E1117;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 24px;
        }
        .cioc-banner {
            background: #1E232E;
            color: #E0E0E0;
            padding: 8px 14px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
            margin-top: 14px;
            margin-bottom: 8px;
            border-left: 4px solid #1E88E5;
        }
        .baseplate-row {
            display: flex;
            align-items: stretch;
            background: #161A23;
            border: 1px solid #2B303C;
            border-radius: 6px;
            margin-bottom: 10px;
            padding: 8px;
            overflow-x: auto;
        }
        .baseplate-label {
            min-width: 75px;
            font-size: 11px;
            font-weight: 700;
            color: #8C9BAE;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #202634;
            border-radius: 4px;
            margin-right: 8px;
            text-align: center;
            padding: 4px;
        }
        .slots-grid {
            display: grid;
            grid-template-columns: repeat(12, minmax(76px, 1fr));
            gap: 6px;
            flex-grow: 1;
        }
        .charm-card {
            border-radius: 5px;
            padding: 6px 4px;
            text-align: center;
            font-size: 10px;
            min-height: 84px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            border: 1px solid transparent;
            transition: transform 0.1s ease;
        }
        .charm-card:hover {
            transform: translateY(-2px);
            z-index: 2;
        }
        .charm-card-occupied {
            background: #1C2333;
            color: #FFFFFF;
        }
        .charm-card-spare {
            background: #252830;
            color: #9E9E9E;
            border: 1px dashed #616161 !important;
        }
        .charm-card-empty {
            background: #12151D;
            color: #555E6D;
            border: 1px dashed #282D3A;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .slot-pill {
            font-size: 9px;
            font-weight: 800;
            opacity: 0.85;
            letter-spacing: 0.5px;
        }
        .cable-badge {
            font-size: 9px;
            font-weight: 700;
            padding: 2px 4px;
            border-radius: 3px;
            color: #FFFFFF;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin: 2px 0;
        }
        .tag-label {
            font-size: 10px;
            font-weight: 700;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .type-badge {
            font-size: 9px;
            opacity: 0.85;
        }
        </style>
        <div class="din-rail-container">
        """
    )

    for cioc_id, bp_dict in grid.items():
        cioc_allocs = [a for a in allocations if a.cioc == cioc_id]
        trains = {a.segregation for a in cioc_allocs if a.segregation}
        cab_id = next((a.cabinet for a in cioc_allocs if a.cabinet), (cioc_id - 1) // 4 + 1)

        if "A" in trains and "B" in trains:
            border_color = "#E53935"
            bg_style = "background: linear-gradient(90deg, #2D1418 0%, #1E232E 100%);"
            badge = "<span style='background:#E53935;color:#FFFFFF;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:800;'>🚨 TRAIN MIXED (BREACH)</span>"
        elif "A" in trains:
            border_color = "#1E88E5"
            bg_style = "background: linear-gradient(90deg, #10243E 0%, #1E232E 100%);"
            badge = "<span style='background:#1E88E5;color:#FFFFFF;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:800;'>🛡️ TRAIN A (BLUE)</span>"
        elif "B" in trains:
            border_color = "#FFA000"
            bg_style = "background: linear-gradient(90deg, #332612 0%, #1E232E 100%);"
            badge = "<span style='background:#FFA000;color:#1A1A1A;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:800;'>🛡️ TRAIN B (AMBER)</span>"
        else:
            border_color = "#546E7A"
            bg_style = "background: #1E232E;"
            badge = "<span style='background:#37474F;color:#CFD8DC;padding:3px 8px;border-radius:4px;font-size:11px;font-weight:600;'>COMMON / UNASSIGNED</span>"

        html_parts.append(
            f"<div class='cioc-banner' style='border-left: 5px solid {border_color}; {bg_style} display:flex; justify-content:space-between; align-items:center;'>"
            f"<div>⚡ CIOC CARD {cioc_id:02d} <span style='font-size:12px;opacity:0.75;font-weight:normal;'>(Cabinet {cab_id:02d})</span></div>"
            f"<div>{badge}</div>"
            f"</div>"
        )

        for bp_id, slots in bp_dict.items():
            html_parts.append("<div class='baseplate-row'>")
            html_parts.append(f"<div class='baseplate-label'>BP-{bp_id:02d}<br><span style='font-size:9px;opacity:0.7;'>12 SLOTS</span></div>")
            html_parts.append("<div class='slots-grid'>")

            for slot_info in slots:
                s_num = slot_info["slot"]
                seg_val = slot_info.get("segregation")
                seg_badge = ""
                if seg_val in ("A", "B"):
                    seg_bg = "#1E88E5" if seg_val == "A" else "#FFA000"
                    seg_fg = "#FFFFFF" if seg_val == "A" else "#1A1A1A"
                    seg_badge = f"<span style='font-size:8px;font-weight:800;padding:1px 3px;border-radius:2px;background:{seg_bg};color:{seg_fg};margin-left:3px;'>[{seg_val}]</span>"

                if slot_info["is_empty"]:
                    html_parts.append(
                        f"<div class='charm-card charm-card-empty'>"
                        f"<span style='font-size:9px;'>S{s_num:02d}<br>EMPTY</span>"
                        f"</div>"
                    )
                elif slot_info["is_spare"]:
                    cable_color = color_map.get(slot_info["cable_id"], "#757575")
                    spare_tb = slot_info.get("terminal_block_type") or "Standard"
                    html_parts.append(
                        f"<div class='charm-card charm-card-spare' style='border-top: 3px solid {cable_color};' title='WIRED SPARE\nTB: {spare_tb}'>"
                        f"<div class='slot-pill'>SLOT {s_num:02d}{seg_badge}</div>"
                        f"<div class='cable-badge' style='background: {cable_color};'>P{slot_info['pair_no']:02d}</div>"
                        f"<div class='tag-label' style='color:#B0BEC5;'>WIRED SPARE</div>"
                        f"<div class='type-badge'>{slot_info['cable_id'] or '-'}</div>"
                        f"<div class='type-badge' style='color:#78909C;font-weight:600;'>{spare_tb}</div>"
                        f"</div>"
                    )
                else:
                    cable_color = color_map.get(slot_info["cable_id"], "#1E88E5")
                    hw_title = (
                        f"Tag: {slot_info['tag']}\n"
                        f"CHARM: {slot_info.get('charm_model') or '-'} ({slot_info.get('charm_part_no') or '-'})\n"
                        f"TB: {slot_info.get('terminal_block_type') or '-'} ({slot_info.get('terminal_block_part_no') or '-'})\n"
                        f"Segregation: {seg_val or 'None'}"
                    )
                    tb_type_str = slot_info.get('terminal_block_type') or 'Standard'
                    html_parts.append(
                        f"<div class='charm-card charm-card-occupied' style='border-top: 3px solid {cable_color};' title='{hw_title}'>"
                        f"<div class='slot-pill'>SLOT {s_num:02d}{seg_badge}</div>"
                        f"<div class='cable-badge' style='background: {cable_color};'>P{slot_info['pair_no']:02d}</div>"
                        f"<div class='tag-label' title='{slot_info['tag']}'>{slot_info['tag']}</div>"
                        f"<div class='type-badge'>{slot_info['io_type']} | {slot_info['cable_id']}</div>"
                        f"<div class='type-badge' style='color:#90CAF9;font-weight:600;'>{tb_type_str}</div>"
                        f"</div>"
                    )

            html_parts.append("</div>")  # end slots-grid
            html_parts.append("</div>")  # end baseplate-row

    html_parts.append("</div>")  # end din-rail-container
    return "\n".join(html_parts)


def render_streamlit_rack(
    allocations: Sequence[AllocatedSignal],
    charms_per_baseplate: int = 12,
):
    """Render the full DIN rail visualizer inside Streamlit."""
    if not allocations:
        st.info("No allocations to visualize.")
        return

    # Render Cable legend / summary cards
    cables: Dict[str, List[AllocatedSignal]] = defaultdict(list)
    for a in allocations:
        if a.cable_id:
            cables[a.cable_id].append(a)

    color_map = get_cable_color_map(allocations)

    st.write("#### 🔌 Trunk Cable Blocks & Contiguity Map")
    legend_cols = st.columns(min(max(len(cables), 1), 4))

    for idx, (cid, sigs) in enumerate(cables.items()):
        col = legend_cols[idx % len(legend_cols)]
        active_cnt = sum(1 for s in sigs if not s.is_spare)
        spare_cnt = sum(1 for s in sigs if s.is_spare)
        total_pairs = len(sigs)
        color = color_map.get(cid, "#1E88E5")
        bps = sorted(list({s.baseplate for s in sigs}))
        bp_str = f"BP-{min(bps):02d}" if len(bps) == 1 else f"BP-{min(bps):02d}..{max(bps):02d}"

        with col:
            st.markdown(
                f"""
                <div style="background: #1C2333; border-left: 5px solid {color}; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                    <div style="font-weight: bold; font-size: 13px; color: #FFFFFF;">{cid}</div>
                    <div style="font-size: 11px; color: #B0BEC5;">
                        <b>{total_pairs} Pairs</b> ({active_cnt} active, {spare_cnt} spare)<br>
                        Location: <code>{bp_str}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Render CIOC Redundancy Segregation Status
    ciocs = sorted(list({a.cioc for a in allocations}))
    st.write("#### 🛡️ CIOC Redundancy Segregation Status")
    cioc_cols = st.columns(min(max(len(ciocs), 1), 4))
    for idx, c in enumerate(ciocs):
        col = cioc_cols[idx % len(cioc_cols)]
        c_allocs = [a for a in allocations if a.cioc == c]
        c_trains = {a.segregation for a in c_allocs if a.segregation}
        cab_id = next((a.cabinet for a in c_allocs if a.cabinet), (c - 1) // 4 + 1)
        if "A" in c_trains and "B" in c_trains:
            color = "#E53935"
            label = "🚨 TRAIN MIXED"
            train_desc = "Segregation breach"
        elif "A" in c_trains:
            color = "#1E88E5"
            label = "🛡️ TRAIN A (BLUE)"
            train_desc = f"{sum(1 for a in c_allocs if a.segregation == 'A')} Train A channels"
        elif "B" in c_trains:
            color = "#FFA000"
            label = "🛡️ TRAIN B (AMBER)"
            train_desc = f"{sum(1 for a in c_allocs if a.segregation == 'B')} Train B channels"
        else:
            color = "#546E7A"
            label = "COMMON"
            train_desc = "Unassigned channels"

        with col:
            st.markdown(
                f"""
                <div style="background: #1C2333; border-left: 5px solid {color}; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight: bold; font-size: 13px; color: #FFFFFF;">CIOC-{c:02d}</span>
                        <span style="font-size: 10px; background: {color}; color: {'#1A1A1A' if color=='#FFA000' else '#FFFFFF'}; padding: 2px 6px; border-radius: 3px; font-weight: bold;">{label}</span>
                    </div>
                    <div style="font-size: 11px; color: #B0BEC5; margin-top: 4px;">
                        Cabinet: <code>CAB-{cab_id:02d}</code><br>
                        Channels: <b>{len(c_allocs)}</b> ({train_desc})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Render DIN Rail baseplates
    st.write("#### 🎛️ Physical DIN-Rail Baseplate Rack Visualizer")
    rack_html = render_din_rail_html(allocations, charms_per_baseplate=charms_per_baseplate)
    st.markdown(rack_html, unsafe_allow_html=True)
