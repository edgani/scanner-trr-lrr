from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from utils.streamlit_utils import render_pills


def _parse_dt(item: dict) -> datetime | None:
    raw = item.get('event_dt') or item.get('datetime')
    if raw:
        try:
            dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    date_part = str(item.get('date', '')).strip()
    time_part = str(item.get('time', '')).replace('UTC', '').strip()
    if not date_part:
        return None
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            raw2 = f"{date_part} {time_part}".strip()
            dt = datetime.strptime(raw2, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _countdown(dt: datetime | None) -> str:
    if not dt:
        return '-'
    now = datetime.now(timezone.utc)
    secs = int((dt - now).total_seconds())
    if secs <= 0:
        return 'Released'
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days > 0:
        return f"T-{days}d {hours}h"
    if hours > 0:
        return f"T-{hours}h {mins}m"
    return f"T-{mins}m"


def _tone(impact: str) -> str:
    impact = str(impact).lower()
    return 'bad' if impact == 'high' else ('warn' if impact == 'medium' else 'blue')


def render_next_macro_panel(events: list[dict], summary: dict | None = None, title: str = 'Next Macro Catalyst', columns: int = 1) -> None:
    st.subheader(title)
    summary = summary or {}
    if summary.get('headline'):
        st.markdown(f"**{summary.get('headline')}**")
    pills = []
    if summary.get('countdown') and summary.get('countdown') != '-':
        pills.append((str(summary.get('countdown')), 'bad'))
    if summary.get('family') and summary.get('family') != '-':
        pills.append((f"{summary.get('family')}", 'blue'))
    if pills:
        render_pills(pills)
    events = events[:4]
    if not events:
        st.caption('No upcoming macro event')
        return
    for item in events:
        dt = _parse_dt(item)
        render_pills([(str(item.get('impact', 'watch')).upper(), _tone(item.get('impact', 'watch'))), (_countdown(dt), 'blue')])
        st.markdown(f"**{item.get('title', '-')}**")
        st.caption(f"{item.get('family', '-')} · {str(item.get('date', '')).strip()} {str(item.get('time', '')).strip()}")
