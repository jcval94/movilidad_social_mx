from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


def _serialize(data: Any) -> Dict[str, Any]:
    if is_dataclass(data) and not isinstance(data, type):
        data = asdict(data)
    if not isinstance(data, dict):
        raise TypeError("snapshot data must be dict or dataclass")

    out: Dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def write_versioned_snapshot(base_dir: str, category: str, session_id: str, ts: datetime, data: Any) -> Tuple[Path, bool]:
    payload = _serialize(data)
    payload["session_id"] = session_id
    payload["timestamp"] = ts.isoformat()

    root = Path(base_dir)
    day = ts.strftime("%Y-%m-%d")
    minute_key = ts.strftime("%Y%m%dT%H%M")

    day_dir = root / category / day
    day_dir.mkdir(parents=True, exist_ok=True)
    file_path = day_dir / f"{category}_{session_id}_{minute_key}.json"

    if file_path.exists():
        existing = json.loads(file_path.read_text(encoding="utf-8"))
        if existing == payload:
            return file_path, False

    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    latest_dir = root / category / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    (latest_dir / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return file_path, True
