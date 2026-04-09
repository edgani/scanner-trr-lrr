from __future__ import annotations

import html
import streamlit as st


def render_flow_state_strip(items: list[dict], title: str = "Flow State") -> None:
    if not items:
        return
    tone_map = {
        "structural": ("#2fa36b", "rgba(47,163,107,.12)"),
        "monthly": ("#b98a2f", "rgba(185,138,47,.14)"),
        "resolved": ("#b14a63", "rgba(177,74,99,.14)"),
        "next": ("#5a78b5", "rgba(90,120,181,.14)"),
    }
    blocks = []
    for idx, item in enumerate(items):
        key = str(item.get("tone", "resolved"))
        border, bg = tone_map.get(key, tone_map["resolved"])
        label = html.escape(str(item.get("label", "Step")))
        value = html.escape(str(item.get("value", "-")))
        note = html.escape(str(item.get("note", "")))
        card = (
            f"<div style='display:flex;align-items:center;gap:8px;min-width:155px;flex:1 1 155px'>"
            f"<div style='flex:1;border:1px solid {border};background:{bg};border-radius:999px;padding:6px 10px;'>"
            f"<div style='font-size:.63rem;color:#9fb0c8;font-weight:800;text-transform:uppercase;letter-spacing:.05em'>{label}</div>"
            f"<div style='font-size:.82rem;font-weight:900;line-height:1.05'>{value}</div>"
            f"<div style='font-size:.68rem;color:#9fb0c8;line-height:1.08'>{note}</div>"
            f"</div>"
        )
        if idx < len(items) - 1:
            card += "<div style='font-size:1rem;color:#7aa2ff;font-weight:900'>→</div>"
        card += "</div>"
        blocks.append(card)
    st.markdown(f"<div style='margin:2px 0 6px 0'><div style='font-size:.76rem;font-weight:800;margin-bottom:4px'>{html.escape(title)}</div><div style='display:flex;flex-wrap:wrap;gap:6px'>{''.join(blocks)}</div></div>", unsafe_allow_html=True)
