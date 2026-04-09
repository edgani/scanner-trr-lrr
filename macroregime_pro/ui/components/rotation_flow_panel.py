from __future__ import annotations

import html

import streamlit as st


def _tone_border(tone: str) -> str:
    return {
        'good': '#2fa36b',
        'warn': '#b98a2f',
        'bad': '#9b3a3a',
        'blue': '#2b6cb0',
    }.get(tone, '#2a3d56')


def _ticker_pills(items: list[str]) -> str:
    if not items:
        return ''
    out = []
    for item in items[:6]:
        safe = html.escape(str(item))
        out.append(
            "<span style='display:inline-block;margin:5px 6px 0 0;padding:3px 8px;border-radius:999px;"
            "border:1px solid #375784;background:rgba(55,87,132,.16);color:#d9e7ff;font-size:.69rem;font-weight:800'>"
            f"{safe}</span>"
        )
    return ''.join(out)


def _meta_pill(text: str, border: str, bg: str = 'rgba(55,87,132,.16)') -> str:
    safe = html.escape(str(text))
    return (
        "<span style='display:inline-block;margin:0 6px 6px 0;padding:3px 8px;border-radius:999px;"
        f"border:1px solid {border};background:{bg};color:#d9e7ff;font-size:.69rem;font-weight:800'>"
        f"{safe}</span>"
    )


def render_rotation_flow_panel(flows: list[dict], title: str = 'Rotation / Flow Map') -> None:
    st.subheader(title)
    if not flows:
        st.info('Belum ada flow map yang siap ditampilkan.')
        return

    blocks: list[str] = []
    for flow in flows:
        label = html.escape(str(flow.get('label', 'Flow utama')))
        summary = html.escape(str(flow.get('summary', '')))
        tone = _tone_border(str(flow.get('tone', 'blue')))
        stage_now = str(flow.get('stage_now', '') or '').strip()
        stage_remaining = str(flow.get('stage_remaining', '') or '').strip()
        stage_note = html.escape(str(flow.get('stage_note', '') or '').strip())
        meta_html = ''
        if stage_now or stage_remaining:
            pills = []
            if stage_now:
                pills.append(_meta_pill(stage_now, tone, 'rgba(43,108,176,.18)'))
            if stage_remaining:
                pills.append(_meta_pill(stage_remaining, '#556b8a', 'rgba(33,46,66,.35)'))
            meta_html = f"<div style='margin:2px 0 6px 0'>{''.join(pills)}</div>"
        note_html = f"<div style='font-size:.73rem;color:#9fb0c8;line-height:1.16;margin:-1px 0 8px 0'>{stage_note}</div>" if stage_note else ''
        steps_html: list[str] = []
        steps = flow.get('steps', []) or []
        for idx, step in enumerate(steps):
            title_txt = html.escape(str(step.get('title', '-')))
            note_txt = html.escape(str(step.get('note', '')))
            step_tone = _tone_border(str(step.get('tone', 'blue')))
            tickers = [str(x) for x in (step.get('tickers', []) or []) if str(x).strip()]
            rank = html.escape(str(step.get('rank', '')))
            rank_html = (
                f"<div style='font-size:.66rem;color:#9fb0c8;font-weight:800;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px'>{rank}</div>"
                if rank else ''
            )
            ticker_html = _ticker_pills(tickers)
            steps_html.append(
                f"<div style='display:flex;align-items:center;gap:8px;flex:1 1 180px;min-width:180px'>"
                f"<div style='flex:1;background:linear-gradient(180deg, rgba(18,31,54,.98), rgba(9,17,29,.98));border:1px solid {step_tone};border-radius:14px;padding:9px 10px;min-height:88px'>"
                f"{rank_html}"
                f"<div style='font-size:.84rem;font-weight:800;line-height:1.16'>{title_txt}</div>"
                f"<div style='font-size:.74rem;color:#9fb0c8;line-height:1.18;margin-top:4px'>{note_txt}</div>"
                f"<div style='margin-top:3px'>{ticker_html}</div>"
                f"</div>"
                + ("<div style='font-size:1rem;color:#6fa3ff;font-weight:900'>→</div></div>" if idx < len(steps)-1 else "</div>")
            )
        blocks.append(
            f"<div style='background:linear-gradient(180deg, rgba(13,22,38,.98), rgba(9,16,28,.98));border:1px solid {tone};border-radius:16px;padding:10px 11px;margin:0 0 10px 0'>"
            f"<div style='font-size:.92rem;font-weight:900;margin-bottom:3px'>{label}</div>"
            f"{meta_html}"
            f"{note_html}"
            f"<div style='font-size:.77rem;color:#9fb0c8;line-height:1.18;margin-bottom:9px'>{summary}</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:8px'>{''.join(steps_html)}</div>"
            f"</div>"
        )
    st.markdown(''.join(blocks), unsafe_allow_html=True)
