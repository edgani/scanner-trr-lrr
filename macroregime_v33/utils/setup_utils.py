from __future__ import annotations

import math
from typing import Any


def _fnum(x: Any) -> str:
    try:
        x = float(x)
    except Exception:
        return '-'
    if not math.isfinite(x):
        return '-'
    ax = abs(x)
    if ax >= 1000:
        return f"{x:,.0f}"
    if ax >= 100:
        return f"{x:,.1f}"
    if ax >= 1:
        return f"{x:,.2f}"
    if ax >= 0.01:
        return f"{x:,.4f}"
    return f"{x:,.6f}"


def _pct(x: Any) -> str:
    try:
        x = float(x)
    except Exception:
        return '-'
    if not math.isfinite(x):
        return '-'
    return f"{100.0 * x:.1f}%"


def _range_has(row: dict, *keys: str) -> bool:
    for k in keys:
        v = row.get(k)
        if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            return False
    return True


def signal_quality_label(row: dict) -> str:
    conf = float(row.get('signal_confidence', 0.5) or 0.5)
    vol = float(row.get('volume_confirm', 0.5) or 0.5)
    stretch = str(row.get('stretch_state', 'neutral'))
    brk = str(row.get('break_state', 'unknown'))
    q = 0.60 * conf + 0.40 * vol
    if stretch in {'extended', 'overbought'}:
        q -= 0.08
    if brk in {'upside_escape', 'trade_breakout', 'downside_break', 'trade_breakdown'}:
        q += 0.05
    if q >= 0.78:
        return 'High'
    if q >= 0.62:
        return 'Medium-High'
    if q >= 0.48:
        return 'Medium'
    return 'Low'


def risk_label(row: dict, side: str, high_vol: float = 0.05) -> str:
    vol = float(row.get('vol21', 0.0) or 0.0)
    exh = float(row.get('exhaustion', 0.0) or 0.0)
    conf = float(row.get('signal_confidence', 0.5) or 0.5)
    brk = str(row.get('break_state', 'unknown'))
    stretch = str(row.get('stretch_state', 'neutral'))
    score = 0.0
    score += 1.0 if vol >= high_vol else 0.0
    score += 1.0 if exh >= 0.55 else 0.0
    score += 0.8 if conf < 0.45 else (0.3 if conf < 0.58 else 0.0)
    score += 0.4 if brk in {'upside_escape', 'downside_break'} else 0.0
    score += 0.5 if stretch in {'extended', 'overbought'} and side == 'long' else 0.0
    score += 0.5 if stretch == 'oversold' and side == 'short' else 0.0
    if score >= 2.2:
        return 'High'
    if score >= 1.2:
        return 'Medium-High'
    return 'Medium'


def action_from_row(row: dict, side: str, fallback: str) -> str:
    side = (side or 'long').lower()
    brk = str(row.get('break_state', 'unknown'))
    stretch = str(row.get('stretch_state', 'neutral'))
    conf = float(row.get('signal_confidence', 0.5) or 0.5)
    score = float(row.get('score', 0.0) or 0.0)
    if side == 'long':
        if brk == 'upside_escape' and conf >= 0.62 and stretch not in {'extended', 'overbought'}:
            return 'Breakout Hold / Add Carefully'
        if stretch == 'reset_zone' and conf >= 0.52 and score >= 0.08:
            return 'Long on Reset'
        if brk == 'trade_breakout' and stretch in {'extended', 'overbought'}:
            return "Wait Retest / Don't Chase"
        return fallback
    if brk == 'downside_break' and conf >= 0.62 and stretch != 'oversold':
        return 'Breakdown Hold / Add Carefully'
    if stretch == 'neutral' and score <= -0.08:
        return 'Short on Bounce'
    if brk == 'trade_breakdown' and stretch == 'oversold':
        return 'Wait Failed Bounce'
    return fallback


def entry_zone_from_row(row: dict, side: str, is_radar: bool = False) -> str:
    side = (side or 'long').lower()
    brk = str(row.get('break_state', 'unknown'))
    action = str(row.get('action', row.get('radar_type', ''))).lower()
    if side == 'long':
        if _range_has(row, 'trade_low', 'trade_mid'):
            if is_radar:
                return f"wait reclaim {_fnum(row['trade_mid'])}; best pullback {_fnum(row['trade_low'])}-{_fnum(row['trade_mid'])}"
            if 'breakout' in action or brk in {'trade_breakout', 'upside_escape'}:
                if _range_has(row, 'trade_high'):
                    return f"hold/retest above {_fnum(row['trade_high'])}"
            return f"buy reset {_fnum(row['trade_low'])}-{_fnum(row['trade_mid'])}"
        return 'pullback / reset zone near support'
    if _range_has(row, 'trade_mid', 'trade_high'):
        if is_radar:
            return f"wait failure below {_fnum(row['trade_mid'])}; best short bounce {_fnum(row['trade_mid'])}-{_fnum(row['trade_high'])}"
        if 'breakdown' in action or brk in {'trade_breakdown', 'downside_break'}:
            if _range_has(row, 'trade_low'):
                return f"stay below / failed retest under {_fnum(row['trade_low'])}"
        return f"short bounce {_fnum(row['trade_mid'])}-{_fnum(row['trade_high'])}"
    return 'failed bounce / continuation zone'


def invalidation_from_row(row: dict, side: str, fallback: str) -> str:
    side = (side or 'long').lower()
    if side == 'long':
        if _range_has(row, 'trade_low'):
            msg = f"daily close back under {_fnum(row['trade_low'])}"
            if _range_has(row, 'trend_low'):
                msg += f"; hard fail under {_fnum(row['trend_low'])}"
            return msg
        return fallback
    if _range_has(row, 'trade_high'):
        msg = f"close back above {_fnum(row['trade_high'])}"
        if _range_has(row, 'trend_high'):
            msg += f"; squeeze risk above {_fnum(row['trend_high'])}"
        return msg
    return fallback


def target_ladder_from_row(row: dict, side: str, is_radar: bool = False) -> tuple[str, str]:
    side = (side or 'long').lower()
    if side == 'long':
        t1 = _fnum(row.get('trade_high')) if _range_has(row, 'trade_high') else '-'
        t2 = _fnum(row.get('trend_high')) if _range_has(row, 'trend_high') else (_fnum(row.get('tail_ceiling')) if _range_has(row, 'tail_ceiling') else '-')
    else:
        t1 = _fnum(row.get('trade_low')) if _range_has(row, 'trade_low') else '-'
        t2 = _fnum(row.get('trend_low')) if _range_has(row, 'trend_low') else (_fnum(row.get('tail_floor')) if _range_has(row, 'tail_floor') else '-')
    if is_radar:
        return (f"T1 {t1} after trigger", f"T2 {t2} if follow-through")
    return (f"T1 {t1}", f"T2 {t2}")


def target_summary_from_row(row: dict, side: str, is_radar: bool = False) -> str:
    t1, t2 = target_ladder_from_row(row, side, is_radar=is_radar)
    return f"{t1} · {t2}"


def why_now_from_row(row: dict, side: str) -> str:
    parts = [
        f"r21 {_pct(row.get('r21'))}",
        f"r63 {_pct(row.get('r63'))}",
        f"trend {row.get('trend_state', row.get('trend', '-'))}",
        f"break {row.get('break_state', '-')}",
        f"conf {float(row.get('signal_confidence', 0.5) or 0.5):.2f}",
    ]
    if row.get('structural_flag'):
        parts.append(f"struct {row.get('structural_flag')}")
    return ' · '.join(parts)


def why_radar_from_row(row: dict, side: str) -> str:
    parts = [
        f"trend {row.get('trend_state', row.get('trend', '-'))}",
        f"range {row.get('range_state', '-')}",
        f"break {row.get('break_state', '-')}",
        f"conf {float(row.get('signal_confidence', 0.5) or 0.5):.2f}",
    ]
    if row.get('structural_flag'):
        parts.append(f"struct {row.get('structural_flag')}")
    return ' · '.join(parts)


def not_ready_from_row(row: dict, side: str) -> str:
    side = (side or 'long').lower()
    stretch = str(row.get('stretch_state', 'neutral'))
    brk = str(row.get('break_state', 'unknown'))
    if side == 'long':
        if brk in {'inside_trade_range', 'inside_trend_range'}:
            return 'belum reclaim / breakout jelas'
        if stretch in {'extended', 'overbought'}:
            return 'terlalu extended; tunggu reset'
        return 'butuh follow-through + breadth confirm'
    if brk in {'inside_trade_range', 'inside_trend_range'}:
        return 'belum ada breakdown / failed bounce jelas'
    if stretch == 'oversold':
        return 'terlalu dekat oversold; tunggu bounce gagal'
    return 'butuh breakdown lanjut + no squeeze'


def trigger_from_row(row: dict, side: str) -> str:
    side = (side or 'long').lower()
    if side == 'long':
        if _range_has(row, 'trade_mid', 'trade_high'):
            return f"hold above {_fnum(row['trade_mid'])}, confirm above {_fnum(row['trade_high'])}"
        return 'reclaim support + breadth confirm'
    if _range_has(row, 'trade_low', 'trade_mid'):
        return f"stay below {_fnum(row['trade_mid'])}, breakdown under {_fnum(row['trade_low'])}"
    return 'failed bounce + breakdown confirm'
