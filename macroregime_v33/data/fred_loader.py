from __future__ import annotations

from io import StringIO
from typing import Dict

import pandas as pd
import requests

from config.settings import FRED_CACHE_TTL_SECONDS, LIVE_FETCH_ENABLED
from utils.streamlit_compat import st

FRED_SERIES = {
    "INDPRO": "INDPRO",
    "RSAFS": "RSAFS",
    "PAYEMS": "PAYEMS",
    "UNRATE": "UNRATE",
    "ICSA": "ICSA",
    "CPI": "CPIAUCSL",
    "CORECPI": "CPILFESL",
    "DGS2": "DGS2",
    "DGS10": "DGS10",
    "DFII10": "DFII10",
    "T5YIE": "T5YIE",
    "HYOAS": "BAMLH0A0HYM2",
    "ISMNO": "NAPMNOI",
    "HOUST": "HOUST",
    "FEDFUNDS": "FEDFUNDS",
}


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def _empty_meta() -> dict:
    return {
        "requested": len(FRED_SERIES),
        "loaded": 0,
        "missing": len(FRED_SERIES),
        "loaded_keys": [],
        "missing_keys": list(FRED_SERIES.keys()),
        "source": "fred_csv",
    }


def _fetch_series_csv(session: requests.Session, sid: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    resp = session.get(url, timeout=6)
    resp.raise_for_status()
    return pd.read_csv(StringIO(resp.text))


@st.cache_data(ttl=FRED_CACHE_TTL_SECONDS, show_spinner=False)
def load_fred_bundle(*, force_refresh: bool = False) -> dict:
    out: Dict[str, pd.Series] = {}
    meta = _empty_meta()
    if not LIVE_FETCH_ENABLED or not force_refresh:
        return {"series": {k: pd.Series(dtype=float) for k in FRED_SERIES.keys()}, "meta": meta}
    session = _session()

    loaded_keys: list[str] = []
    missing_keys: list[str] = []

    for nice, sid in FRED_SERIES.items():
        try:
            df = _fetch_series_csv(session, sid)
            df.columns = [c.strip() for c in df.columns]
            if "DATE" not in df.columns:
                raise ValueError(f"No DATE column for {sid}")
            df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
            value_cols = [c for c in df.columns if c != "DATE"]
            if not value_cols:
                raise ValueError(f"No value column for {sid}")
            series = pd.to_numeric(df[value_cols[0]], errors="coerce")
            s = pd.Series(series.values, index=df["DATE"], name=nice).dropna()
            out[nice] = s
            if s.empty:
                missing_keys.append(nice)
            else:
                loaded_keys.append(nice)
        except Exception:
            out[nice] = pd.Series(dtype=float)
            missing_keys.append(nice)

    meta.update({
        "requested": len(FRED_SERIES),
        "loaded": len(loaded_keys),
        "missing": len(missing_keys),
        "loaded_keys": loaded_keys,
        "missing_keys": missing_keys,
        "real_share": (len(loaded_keys) / max(len(FRED_SERIES), 1)),
        "source": "fred_csv",
    })
    return {"series": out, "meta": meta}


@st.cache_data(ttl=FRED_CACHE_TTL_SECONDS, show_spinner=False)
def load_fred_series(*, force_refresh: bool = False) -> Dict[str, pd.Series]:
    return load_fred_bundle(force_refresh=force_refresh)["series"]
