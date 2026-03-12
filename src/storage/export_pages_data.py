from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


ALLOWED_DATASETS = {
    "dashboard_overview",
    "ticker_detail",
    "model_health",
    "strategy_performance",
    "retrain_history",
    "incident_log",
}
SENSITIVE_KEYS = {"api_key", "token", "secret", "password", "internal_notes", "raw_features"}


def _sanitize(record: Dict[str, object]) -> Dict[str, object]:
    return {k: v for k, v in record.items() if k not in SENSITIVE_KEYS}


def export_pages_dataset(base_dir: str, dataset: str, records: List[Dict[str, object]], ts: datetime) -> Dict[str, str]:
    if dataset not in ALLOWED_DATASETS:
        raise ValueError(f"dataset {dataset} not allowed")

    cleaned = [_sanitize(r) for r in records]
    root = Path(base_dir) / dataset
    latest = root / "latest"
    historical = root / "historical" / ts.strftime("%Y-%m-%d")
    latest.mkdir(parents=True, exist_ok=True)
    historical.mkdir(parents=True, exist_ok=True)

    stamp = ts.strftime("%Y%m%dT%H%M")
    json_hist = historical / f"{dataset}_{stamp}.json"
    csv_hist = historical / f"{dataset}_{stamp}.csv"

    json_latest = latest / "latest.json"
    csv_latest = latest / "latest.csv"

    json_payload = json.dumps(cleaned, ensure_ascii=False, indent=2, sort_keys=True)
    for path in [json_hist, json_latest]:
        path.write_text(json_payload, encoding="utf-8")

    keys = sorted({k for row in cleaned for k in row.keys()})
    for path in [csv_hist, csv_latest]:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in cleaned:
                writer.writerow(row)

    return {
        "json_latest": str(json_latest),
        "csv_latest": str(csv_latest),
        "json_historical": str(json_hist),
        "csv_historical": str(csv_hist),
    }
