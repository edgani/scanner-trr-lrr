from __future__ import annotations

import html
import streamlit as st


def render_event_bubble_panel(events) -> None:
    st.subheader('Catalyst Strip')
    if not events:
        st.info('Belum ada event penting.')
        return

    chips = []
    tone_map = {
        'NEWS': ('#ff8a65', 'rgba(255,138,101,.12)'),
        'MACRO': ('#60a5fa', 'rgba(96,165,250,.12)'),
        'PLAYBOOK': ('#c084fc', 'rgba(192,132,252,.12)'),
    }
    impact_border = {'high': 2, 'medium': 1, 'watch': 1}
    for item in events[:12]:
        typ = str(item.get('type', 'WATCH')).upper()
        label = str(item.get('label') or item.get('title') or item).strip()
        if len(label) > 105:
            label = label[:102].rstrip() + '...' 
        if not label:
            continue
        fg, bg = tone_map.get(typ, ('#9fb0c8', 'rgba(159,176,200,.10)'))
        width = impact_border.get(str(item.get('impact', 'watch')).lower(), 1)
        chips.append(
            f"<span style='display:inline-block;margin:0 6px 6px 0;padding:6px 10px;border-radius:999px;"
            f"border:{width}px solid {fg};background:{bg};font-size:.76rem;line-height:1.15;'>"
            f"<b>{html.escape(typ)}</b> · {html.escape(label)}</span>"
        )
    st.markdown("<div style='margin-top:-2px'>" + ''.join(chips) + "</div>", unsafe_allow_html=True)
