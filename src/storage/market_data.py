from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

DEFAULT_MARKET_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_bars (
    symbol TEXT NOT NULL,
    ts INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (symbol, ts)
);

CREATE INDEX IF NOT EXISTS idx_market_bars_symbol_ts
ON market_bars(symbol, ts);
"""


def _apply_permissions(path: Path, mode: int) -> None:
    os.chmod(path, mode)


def _apply_ownership(path: Path, *, uid: int | None, gid: int | None) -> None:
    if uid is None and gid is None:
        return
    os.chown(path, uid if uid is not None else -1, gid if gid is not None else -1)


def ensure_permissions_for_workflow(
    db_path: str | Path,
    *,
    directory_mode: int = 0o770,
    file_mode: int = 0o660,
    workflow_uid: int | None = None,
    workflow_gid: int | None = None,
) -> None:
    """Apply read/write permissions for the process that runs workflows."""
    db_path = Path(db_path)
    parent = db_path.parent

    uid = workflow_uid
    gid = workflow_gid

    if uid is None and os.getenv("WORKFLOW_UID"):
        uid = int(os.environ["WORKFLOW_UID"])
    if gid is None and os.getenv("WORKFLOW_GID"):
        gid = int(os.environ["WORKFLOW_GID"])

    _apply_permissions(parent, directory_mode)
    _apply_permissions(db_path, file_mode)
    _apply_ownership(parent, uid=uid, gid=gid)
    _apply_ownership(db_path, uid=uid, gid=gid)


def ensure_market_data_db(
    db_path: str | Path = "data/market/market_data.sqlite",
    *,
    schema_sql: str = DEFAULT_MARKET_SCHEMA,
    directory_mode: int = 0o770,
    file_mode: int = 0o660,
    workflow_uid: int | None = None,
    workflow_gid: int | None = None,
) -> Path:
    """Idempotently create directory, DB file and schema for market data."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.touch(exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()

    ensure_permissions_for_workflow(
        db_path,
        directory_mode=directory_mode,
        file_mode=file_mode,
        workflow_uid=workflow_uid,
        workflow_gid=workflow_gid,
    )
    return db_path


def validate_sufficient_history(
    conn: sqlite3.Connection,
    symbols: Iterable[str],
    *,
    min_bars: int = 200,
    table_name: str = "market_bars",
) -> dict[str, int]:
    """Ensure each symbol has enough bars before training/inference."""
    symbols = [s for s in symbols]
    if not symbols:
        raise ValueError("Se requiere al menos un símbolo para validar historial.")

    placeholders = ", ".join("?" for _ in symbols)
    query = (
        f"SELECT symbol, COUNT(*) AS n FROM {table_name} "
        f"WHERE symbol IN ({placeholders}) GROUP BY symbol"
    )

    counts = {symbol: 0 for symbol in symbols}
    for symbol, n_bars in conn.execute(query, symbols):
        counts[str(symbol)] = int(n_bars)

    missing = {symbol: n for symbol, n in counts.items() if n < min_bars}
    if missing:
        details = ", ".join(f"{symbol}={n}/{min_bars}" for symbol, n in sorted(missing.items()))
        raise ValueError(
            "Historial insuficiente para entrenamiento/inferencia: "
            f"{details}."
        )

    return counts
