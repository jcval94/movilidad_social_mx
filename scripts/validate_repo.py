from __future__ import annotations

import argparse
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.execution.order_models import OrderSide  # noqa: E402
from src.execution.run_paper_trade import (  # noqa: E402
    PaperTradingRuntimeConfig,
    SignalInstruction,
    build_paper_executor,
    run_paper_trading_cycle,
)
from src.storage.export_pages_data import ALLOWED_DATASETS, export_pages_dataset  # noqa: E402
from src.storage.history_writer import write_versioned_snapshot  # noqa: E402

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA) PRIVATE KEY-----"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    re.compile(r"(?i)token\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
]

SCAN_EXTENSIONS = {".py", ".yml", ".yaml", ".md", ".json", ".csv", ".txt"}


def _iter_repo_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        if p.suffix.lower() in SCAN_EXTENSIONS:
            yield p


def _check_secrets(repo_root: Path) -> List[str]:
    findings: List[str] = []
    for path in _iter_repo_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                findings.append(f"possible secret pattern {pat.pattern} in {path}")
    return findings


def _check_permissions(repo_root: Path) -> List[str]:
    findings: List[str] = []
    for path in _iter_repo_files(repo_root):
        mode = path.stat().st_mode
        if mode & stat.S_IWOTH:
            findings.append(f"world-writable file is not allowed: {path}")
    return findings


def _smoke_workflows() -> List[str]:
    findings: List[str] = []
    try:
        executor = build_paper_executor(PaperTradingRuntimeConfig(initial_cash=100_000))
        run_paper_trading_cycle(
            executor=executor,
            cycle_id="smoke-cycle",
            signals=[SignalInstruction("smoke-1", "smoke", "AAA", OrderSide.BUY, 2)],
            prices={"AAA": 10.0},
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )

        with tempfile.TemporaryDirectory() as tmp:
            for dataset in sorted(ALLOWED_DATASETS):
                out = export_pages_dataset(
                    base_dir=tmp,
                    dataset=dataset,
                    records=[{"ticker": "AAA", "value": 1.0, "token": "SECRET"}],
                    ts=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                )
                for key, fpath in out.items():
                    if not Path(fpath).exists():
                        findings.append(f"missing exported file for {dataset}:{key}")

            _, changed_1 = write_versioned_snapshot(
                tmp,
                "model_health",
                "smoke-session",
                datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                {"status": "ok"},
            )
            _, changed_2 = write_versioned_snapshot(
                tmp,
                "model_health",
                "smoke-session",
                datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                {"status": "ok"},
            )
            if not changed_1 or changed_2:
                findings.append("snapshot idempotency check failed")
    except Exception as exc:  # pragma: no cover - smoke diagnostic path
        findings.append(f"smoke test failed: {exc}")

    return findings


def _validate_dataset_contract() -> List[str]:
    required = {
        "dashboard_overview",
        "ticker_detail",
        "model_health",
        "strategy_performance",
        "retrain_history",
        "incident_log",
    }
    if required != ALLOWED_DATASETS:
        return [f"allowed dataset set mismatch. expected={required} got={ALLOWED_DATASETS}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Repository quality validator")
    parser.add_argument("--smoke", action="store_true", help="run end-to-end smoke checks")
    parser.add_argument("--strict", action="store_true", help="run security/schema/permission checks")
    args = parser.parse_args()

    repo_root = Path(os.getcwd())
    findings: List[str] = []

    if args.smoke or args.strict:
        findings.extend(_smoke_workflows())

    if args.strict:
        findings.extend(_validate_dataset_contract())
        findings.extend(_check_secrets(repo_root))
        findings.extend(_check_permissions(repo_root))

    if findings:
        for finding in findings:
            print(f"[FAIL] {finding}")
        return 1

    print("[OK] repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
