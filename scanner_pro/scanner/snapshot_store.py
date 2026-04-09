from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from pandas.errors import EmptyDataError
from config.settings import SCANS_DIR, SIMPLE_TABLE_COLUMNS

def snapshot_csv_path(market: str) -> Path:
    SCANS_DIR.mkdir(parents=True, exist_ok=True)
    return SCANS_DIR / f'{market}_scanner_snapshot.csv'

def manifest_path(market: str) -> Path:
    SCANS_DIR.mkdir(parents=True, exist_ok=True)
    return SCANS_DIR / f'{market}_scanner_manifest.json'

def save_snapshot(market: str, df: pd.DataFrame, manifest: dict) -> None:
    snapshot_csv_path(market).parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if out.empty:
        for col in SIMPLE_TABLE_COLUMNS:
            if col not in out.columns:
                out[col] = pd.Series(dtype='object')
    out.to_csv(snapshot_csv_path(market), index=False)
    manifest_path(market).write_text(json.dumps(manifest, indent=2), encoding='utf-8')

def load_snapshot(market: str) -> tuple[pd.DataFrame | None, dict]:
    csv_path = snapshot_csv_path(market)
    man_path = manifest_path(market)
    manifest = json.loads(man_path.read_text()) if man_path.exists() else {}
    df = None
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
        except EmptyDataError:
            cols = manifest.get('required_columns', SIMPLE_TABLE_COLUMNS)
            df = pd.DataFrame(columns=cols)
    return df, manifest
