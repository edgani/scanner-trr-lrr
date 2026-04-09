from __future__ import annotations

import html
from typing import Iterable

import streamlit as st


def metric_card(title: str, value: str, subtitle: str = "") -> None:
    st.markdown(
        f'''
        <div style="background:linear-gradient(180deg, rgba(14,32,62,0.95), rgba(8,20,39,0.95));
                    border:1px solid #203552;border-radius:13px;padding:7px 9px;min-height:62px;">
            <div style="font-size:.70rem;color:#9fb0c8;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">{html.escape(title)}</div>
            <div style="font-size:1.18rem;font-weight:900;line-height:1.02;margin-top:2px;">{html.escape(str(value))}</div>
            <div style="font-size:.71rem;color:#9fb0c8;margin-top:3px;line-height:1.15;">{html.escape(subtitle)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def info_card(title: str, lines: Iterable[str], accent: str = "#203552") -> None:
    body = "".join(f"<li style='margin:0 0 1px 0'>{html.escape(str(line))}</li>" for line in lines if str(line).strip())
    st.markdown(
        f'''
        <div style="background:linear-gradient(180deg, rgba(16,24,41,0.98), rgba(10,17,30,0.98));
                    border:1px solid {accent};border-radius:13px;padding:7px 9px;">
            <div style="font-size:.82rem;font-weight:800;margin-bottom:4px;">{html.escape(title)}</div>
            <ul style="margin:0;padding-left:14px;color:#9fb0c8;font-size:.76rem;line-height:1.16;">{body}</ul>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def pill(text: str, tone: str = "neutral") -> str:
    colors = {
        "good": ("#39d98a", "rgba(57,217,138,.12)"),
        "bad": ("#ff6b6b", "rgba(255,107,107,.12)"),
        "warn": ("#f6c85f", "rgba(246,200,95,.12)"),
        "blue": ("#60a5fa", "rgba(96,165,250,.12)"),
        "neutral": ("#9fb0c8", "rgba(159,176,200,.10)"),
    }
    fg, bg = colors.get(tone, colors["neutral"])
    return (
        f"<span style='display:inline-block;padding:2px 7px;border-radius:999px;"
        f"border:1px solid {fg};background:{bg};color:{fg};font-size:.66rem;font-weight:800;"
        f"margin:0 4px 4px 0'>{html.escape(str(text))}</span>"
    )


def render_pills(items: Iterable[tuple[str, str]]) -> None:
    st.markdown("".join(pill(text, tone) for text, tone in items), unsafe_allow_html=True)
