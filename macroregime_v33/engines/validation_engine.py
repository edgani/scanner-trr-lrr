from __future__ import annotations
from typing import Dict, Tuple, List
import numpy as np
import pandas as pd

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from features.market_features import SECTOR_ETFS


def _series(prices: Dict[str, pd.Series], symbol: str) -> pd.Series:
    s = prices.get(symbol)
    if s is None:
        return pd.Series(dtype=float)
    if isinstance(s, pd.DataFrame) and 'Close' in s.columns:
        return pd.to_numeric(s['Close'], errors='coerce').dropna()
    return pd.to_numeric(s, errors="coerce").dropna()


def _ret_n(s: pd.Series, n: int) -> pd.Series:
    return s / s.shift(n) - 1.0


def _flatten(buckets: dict) -> set[str]:
    out = set()
    for vals in buckets.values():
        out.update(vals)
    return out


US_SET = _flatten(US_BUCKETS)
IHSG_SET = _flatten(IHSG_BUCKETS)
FX_SET = _flatten(FX_BUCKETS)
CMDTY_SET = _flatten(COMMODITY_BUCKETS)
CRYPTO_SET = _flatten(CRYPTO_BUCKETS)


def _market_name(symbol: str) -> str | None:
    if symbol in IHSG_SET or symbol.endswith('.JK'):
        return 'IHSG'
    if symbol in FX_SET or symbol.endswith('=X'):
        return 'FX'
    if symbol in CMDTY_SET or symbol.endswith('=F'):
        return 'Commodities'
    if symbol in CRYPTO_SET or symbol.endswith('-USD'):
        return 'Crypto'
    if symbol in US_SET or symbol.isupper():
        return 'US'
    return None


class ValidationEngine:
    def _history(self, prices: Dict[str, pd.Series]) -> pd.DataFrame:
        spy = _series(prices, 'SPY')
        if spy.empty or len(spy) < 160:
            return pd.DataFrame()
        qqq = _series(prices, 'QQQ').reindex(spy.index).ffill()
        rsp = _series(prices, 'RSP').reindex(spy.index).ffill()
        iwm = _series(prices, 'IWM').reindex(spy.index).ffill()
        uup = _series(prices, 'UUP').reindex(spy.index).ffill()
        tlt = _series(prices, 'TLT').reindex(spy.index).ffill()
        vix = _series(prices, '^VIX').reindex(spy.index).ffill()

        out = pd.DataFrame(index=spy.index)
        out['spy_fwd_21'] = spy.shift(-21) / spy - 1.0
        out['qqq_rel_1m'] = (_ret_n(qqq, 21) - _ret_n(spy, 21)).fillna(0.0)
        out['rsp_rel_1m'] = (_ret_n(rsp, 21) - _ret_n(spy, 21)).fillna(0.0)
        out['rsp_rel_3m'] = (_ret_n(rsp, 63) - _ret_n(spy, 63)).fillna(0.0)
        out['iwm_rel_1m'] = (_ret_n(iwm, 21) - _ret_n(spy, 21)).fillna(0.0)
        out['dxy_1m'] = _ret_n(uup, 21).fillna(0.0)
        out['tlt_1m'] = _ret_n(tlt, 21).fillna(0.0)
        out['vix_1m'] = _ret_n(vix, 21).fillna(0.0)

        sector_rets = []
        for etf in SECTOR_ETFS:
            s = _series(prices, etf)
            if len(s) >= 80:
                sector_rets.append(_ret_n(s.reindex(spy.index).ffill(), 21).rename(etf))
        if sector_rets:
            sec = pd.concat(sector_rets, axis=1)
            out['sector_support_ratio'] = (sec.gt(0).sum(axis=1) / max(sec.shape[1], 1)).astype(float)
        else:
            out['sector_support_ratio'] = 0.45

        out['eqw_health'] = (0.5 * (out['rsp_rel_1m'] / 0.03).clip(0, 1) + 0.5 * (out['rsp_rel_3m'] / 0.05).clip(0, 1)).fillna(0.0)
        out['smallcap_health'] = (out['iwm_rel_1m'] / 0.05).clip(0, 1).fillna(0.0)
        out['narrow_leadership'] = (((out['qqq_rel_1m'] / 0.04).clip(0, 1) + ((-out['rsp_rel_1m']) / 0.03).clip(0, 1) + ((-out['iwm_rel_1m']) / 0.04).clip(0, 1) + (1 - out['sector_support_ratio']).clip(0, 1)) / 4.0).fillna(0.5)
        out = out.dropna(subset=['spy_fwd_21'])
        return out.tail(900)

    def _score(self, hist: pd.DataFrame, weights: Tuple[float, float, float, float], threshold: float) -> float:
        sec, eqw, small, narrow = weights
        mh = (sec * hist['sector_support_ratio'] + eqw * hist['eqw_health'] + small * hist['smallcap_health'] - narrow * hist['narrow_leadership']).clip(0, 1)
        signal = mh > threshold
        if signal.sum() < 6:
            return -1e9
        future = hist['spy_fwd_21']
        hit = (future[signal] > 0).mean()
        avg = future[signal].mean()
        false = (future[signal] < -0.03).mean()
        stability = signal.astype(int).diff().abs().fillna(0).mean()
        return float(1.35 * hit + 4.8 * avg - 1.25 * false - 0.10 * stability)

    def _rolling_windows(self, hist: pd.DataFrame) -> List[tuple[pd.DataFrame, pd.DataFrame]]:
        windows = []
        total = len(hist)
        test_len = 42
        train_candidates = [126, 168, 252, 336]
        for tl in train_candidates:
            start = 0
            while start + tl + test_len <= total:
                train = hist.iloc[start:start+tl]
                test = hist.iloc[start+tl:start+tl+test_len]
                if len(train) >= 100 and len(test) >= 20:
                    windows.append((train, test))
                start += max(21, test_len // 2)
        if not windows and total >= 140:
            split = max(int(total * 0.7), 100)
            windows = [(hist.iloc[:split], hist.iloc[split:])]
        return windows

    def _signal_validation(self, prices: Dict[str, pd.Series], asset_ranges: Dict[str, dict] | None = None) -> Dict[str, dict]:
        asset_ranges = asset_ranges or {}
        grouped: Dict[str, list[str]] = {'US': [], 'IHSG': [], 'FX': [], 'Commodities': [], 'Crypto': []}
        for symbol, rng in asset_ranges.items():
            mkt = _market_name(symbol)
            if mkt in grouped:
                grouped[mkt].append(symbol)
        out: Dict[str, dict] = {}
        for market_name, symbols in grouped.items():
            cont_hits_10 = []
            cont_hits_21 = []
            cont_rets_10 = []
            cont_rets_21 = []
            breakout_false = []
            breakdown_false = []
            reclaim_hits = []
            sample = 0
            for sym in symbols:
                s = _series(prices, sym)
                if len(s) < 90:
                    continue
                rng = asset_ranges.get(sym, {}) or {}
                trade_mid = float(rng.get('trade_mid', np.nan))
                trade_high = float(rng.get('trade_high', np.nan))
                trade_low = float(rng.get('trade_low', np.nan))
                if not np.isfinite(trade_mid) or not np.isfinite(trade_high) or not np.isfinite(trade_low):
                    continue
                df = pd.DataFrame({'px': s.astype(float)})
                df['fwd10'] = df['px'].shift(-10) / df['px'] - 1.0
                df['fwd21'] = df['px'].shift(-21) / df['px'] - 1.0
                # proxy continuation / reclaim / failure tests based on persistent structure
                df['ema10'] = df['px'].ewm(span=10, adjust=False).mean()
                df['ema21'] = df['px'].ewm(span=21, adjust=False).mean()
                df['trade_mid'] = df['ema10'] * 0.65 + df['ema21'] * 0.35
                # approximate local thresholds from current width profile for historical scoring
                trade_width_pct = abs((trade_high - trade_low) / max(trade_mid, 1e-9)) * 0.5
                df['trade_high'] = df['trade_mid'] * (1.0 + trade_width_pct)
                df['trade_low'] = df['trade_mid'] * (1.0 - trade_width_pct)
                breakout_sig = df['px'] > df['trade_high']
                breakdown_sig = df['px'] < df['trade_low']
                reclaim_sig = (df['px'] > df['trade_mid']) & (df['px'].shift(3) <= df['trade_mid'].shift(3))
                continue_sig = (df['px'] > df['trade_mid']) & (df['ema10'] > df['ema21'])
                b = df.loc[breakout_sig & df['fwd10'].notna(), 'fwd10']
                d = df.loc[breakdown_sig & df['fwd10'].notna(), 'fwd10']
                r = df.loc[reclaim_sig & df['fwd10'].notna(), 'fwd10']
                c10 = df.loc[continue_sig & df['fwd10'].notna(), 'fwd10']
                c21 = df.loc[continue_sig & df['fwd21'].notna(), 'fwd21']
                if len(c10):
                    cont_hits_10.append(float((c10 > 0).mean()))
                    cont_rets_10.append(float(c10.mean()))
                if len(c21):
                    cont_hits_21.append(float((c21 > 0).mean()))
                    cont_rets_21.append(float(c21.mean()))
                if len(b):
                    breakout_false.append(float((b < -0.02).mean()))
                if len(d):
                    breakdown_false.append(float((d > 0.02).mean()))
                if len(r):
                    reclaim_hits.append(float((r > 0).mean()))
                sample += int(len(c10) + len(c21) + len(b) + len(d) + len(r))
            if sample == 0:
                out[market_name] = {
                    'continuation_hit_10d': None,
                    'continuation_hit_21d': None,
                    'breakout_false_rate': None,
                    'breakdown_false_rate': None,
                    'reclaim_hit_rate': None,
                    'avg_forward_return_10d': None,
                    'avg_forward_return_21d': None,
                    'sample_size': 0,
                    'confidence': 'low',
                }
            else:
                hit10 = float(np.mean(cont_hits_10)) if cont_hits_10 else 0.0
                hit21 = float(np.mean(cont_hits_21)) if cont_hits_21 else 0.0
                bfalse = float(np.mean(breakout_false)) if breakout_false else 0.0
                dfalse = float(np.mean(breakdown_false)) if breakdown_false else 0.0
                rhit = float(np.mean(reclaim_hits)) if reclaim_hits else 0.0
                avg10 = float(np.mean(cont_rets_10)) if cont_rets_10 else 0.0
                avg21 = float(np.mean(cont_rets_21)) if cont_rets_21 else 0.0
                conf = 'high' if sample >= 200 else 'medium' if sample >= 80 else 'low'
                out[market_name] = {
                    'continuation_hit_10d': hit10,
                    'continuation_hit_21d': hit21,
                    'breakout_false_rate': bfalse,
                    'breakdown_false_rate': dfalse,
                    'reclaim_hit_rate': rhit,
                    'avg_forward_return_10d': avg10,
                    'avg_forward_return_21d': avg21,
                    'sample_size': sample,
                    'confidence': conf,
                }
        return out

    def run(self, prices: Dict[str, pd.Series], price_frames: Dict[str, pd.DataFrame] | None = None, asset_ranges: Dict[str, dict] | None = None, symbols_by_market: Dict[str, list[str]] | None = None) -> Dict[str, object]:
        hist = self._history(prices)
        priors = {'sector': 0.40, 'eqw': 0.25, 'smallcap': 0.20, 'narrow': 0.25}
        signal_validation = self._signal_validation(prices, asset_ranges)
        if hist.empty or len(hist) < 140:
            return {
                'status': 'insufficient_history',
                'calibrated': False,
                'effective_market_health_weights': priors,
                'market_health_threshold': 0.44,
                'summary': 'Walk-forward warming up: histori belum cukup untuk rolling calibration penuh. Pakai prior weights sementara.',
                'method': 'prior_fallback',
                'sample_size': int(len(hist)),
                'windows': 0,
                'last_hit_rate': None,
                'last_avg_next21': None,
                'active_set': 'fallback',
                'signal_validation': signal_validation,
            }
        grid = [
            (0.40, 0.25, 0.20, 0.25),
            (0.45, 0.25, 0.20, 0.20),
            (0.35, 0.30, 0.20, 0.25),
            (0.35, 0.20, 0.25, 0.20),
            (0.30, 0.30, 0.25, 0.20),
            (0.45, 0.20, 0.15, 0.30),
            (0.50, 0.20, 0.15, 0.25),
        ]
        thresholds = [0.38, 0.42, 0.46, 0.50]
        windows = self._rolling_windows(hist)
        agg: dict[tuple[tuple[float,float,float,float], float], List[float]] = {}
        for train, test in windows:
            best_local = None
            best_local_score = -1e9
            for weights in grid:
                for th in thresholds:
                    score = self._score(train, weights, th)
                    if score > best_local_score:
                        best_local_score = score
                        best_local = (weights, th)
            if best_local is None:
                best_local = (grid[0], thresholds[1])
            weights, threshold = best_local
            sec, eqw, small, narrow = weights
            mh_test = (sec * test['sector_support_ratio'] + eqw * test['eqw_health'] + small * test['smallcap_health'] - narrow * test['narrow_leadership']).clip(0, 1)
            signal = mh_test > threshold
            outperf = test['spy_fwd_21'][signal]
            hit = float((outperf > 0).mean()) if len(outperf) else 0.0
            avg = float(outperf.mean()) if len(outperf) else 0.0
            false = float((outperf < -0.03).mean()) if len(outperf) else 0.0
            agg.setdefault((weights, threshold), []).append(1.35 * hit + 4.8 * avg - 1.25 * false)
        if not agg:
            return {
                'status': 'insufficient_history',
                'calibrated': False,
                'effective_market_health_weights': priors,
                'market_health_threshold': 0.44,
                'summary': 'Walk-forward fallback: window scoring belum cukup stabil, pakai prior weights.',
                'method': 'prior_fallback_unstable',
                'sample_size': int(len(hist)),
                'windows': len(windows),
                'last_hit_rate': None,
                'last_avg_next21': None,
                'active_set': 'fallback_unstable',
                'signal_validation': signal_validation,
            }
        best_key = max(agg.items(), key=lambda kv: (np.mean(kv[1]), len(kv[1])))[0]
        weights, threshold = best_key
        sec, eqw, small, narrow = weights
        tail = hist.iloc[-63:]
        mh_tail = (sec * tail['sector_support_ratio'] + eqw * tail['eqw_health'] + small * tail['smallcap_health'] - narrow * tail['narrow_leadership']).clip(0, 1)
        signal = mh_tail > threshold
        outperf = tail['spy_fwd_21'][signal]
        hit = float((outperf > 0).mean()) if len(outperf) else 0.0
        avg = float(outperf.mean()) if len(outperf) else 0.0
        summary = f"Walk-forward aktif · hit {hit:.0%} · avg next-21d {avg:.2%} · threshold {threshold:.2f} · windows {len(windows)}"
        return {
            'status': 'ok',
            'calibrated': True,
            'effective_market_health_weights': {'sector': sec, 'eqw': eqw, 'smallcap': small, 'narrow': narrow},
            'market_health_threshold': threshold,
            'summary': summary,
            'sample_size': int(len(hist)),
            'method': 'rolling_walk_forward',
            'windows': len(windows),
            'last_hit_rate': hit,
            'last_avg_next21': avg,
            'active_set': f'{sec:.2f}/{eqw:.2f}/{small:.2f}/{narrow:.2f}@{threshold:.2f}',
            'signal_validation': signal_validation,
        }
