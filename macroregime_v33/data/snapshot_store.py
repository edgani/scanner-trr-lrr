from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from config.settings import CACHE_BASE_DIR, SNAPSHOT_FILENAME, SNAPSHOT_MANIFEST_FILENAME
from data.cache_store import write_json, read_json


def snapshot_path(base_dir: str | None = None) -> Path:
    return Path(base_dir or CACHE_BASE_DIR) / SNAPSHOT_FILENAME


def snapshot_manifest_path(base_dir: str | None = None) -> Path:
    return Path(base_dir or CACHE_BASE_DIR) / SNAPSHOT_MANIFEST_FILENAME


def save_snapshot(payload: Any, base_dir: str | None = None) -> None:
    write_json(snapshot_path(base_dir), payload)
    meta = payload.get('meta', {}) if isinstance(payload, dict) else {}
    manifest = {
        'generated_at': meta.get('generated_at'),
        'schema': meta.get('schema'),
        'runtime_mode': meta.get('runtime_mode'),
        'loader_meta': meta.get('loader_meta', {}),
        'history_meta': meta.get('history_meta', {}),
        'snapshot_status': meta.get('snapshot_status', {}),
    }
    write_json(snapshot_manifest_path(base_dir), manifest)


def load_snapshot(base_dir: str | None = None) -> Optional[Any]:
    return read_json(snapshot_path(base_dir))


def load_snapshot_manifest(base_dir: str | None = None) -> Optional[Any]:
    return read_json(snapshot_manifest_path(base_dir))
