from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class SnapshotState:
    generated_at: str
    structural: Dict[str, Any]
    tactical: Dict[str, Any]
    shock: Dict[str, Any]
    scenarios: Dict[str, Any]
    analogs: Dict[str, Any]
    playbooks: Dict[str, Any]
    outliers: Dict[str, Any]
    translated: Dict[str, Any]
    validation: Dict[str, Any]
