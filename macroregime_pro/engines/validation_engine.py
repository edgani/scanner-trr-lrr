from __future__ import annotations
from typing import Dict, Tuple, List
import numpy as np
import pandas as pd

from features.market_features import SECTOR_ETFS


def _series(prices: Dict[str, pd.Series], symbol: str) -> pd.Series:
    s = prices.get(symbol)
    if s is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(s, errors="coerce").dropna()


def _ret_n(s: pd.Series, n: int) -> pd.Series:
    return s / s.shift(n) - 1.0


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

    def run(self, prices: Dict[str, pd.Series]) -> Dict[str, object]:
        hist = self._history(prices)
        priors = {'sector': 0.40, 'eqw': 0.25, 'smallcap': 0.20, 'narrow': 0.25}
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
            weights, threshold = best_local
            sec, eqw, small, narrow = weights
            mh_test = (sec * test['sector_support_ratio'] + eqw * test['eqw_health'] + small * test['smallcap_health'] - narrow * test['narrow_leadership']).clip(0, 1)
            signal = mh_test > threshold
            outperf = test['spy_fwd_21'][signal]
            hit = float((outperf > 0).mean()) if len(outperf) else 0.0
            avg = float(outperf.mean()) if len(outperf) else 0.0
            false = float((outperf < -0.03).mean()) if len(outperf) else 0.0
            agg.setdefault((weights, threshold), []).append(1.35 * hit + 4.8 * avg - 1.25 * false)
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
        }
