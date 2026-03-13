import sqlite3
from pathlib import Path

import pytest

from src.storage.market_data import ensure_market_data_db, validate_sufficient_history


def test_ensure_market_data_db_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "data" / "market" / "market_data.sqlite"

    first = ensure_market_data_db(db_path)
    second = ensure_market_data_db(db_path)

    assert first == db_path
    assert second == db_path
    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO market_bars(symbol, ts, open, high, low, close, volume) "
            "VALUES('AAPL', 1, 1, 1, 1, 1, 10)"
        )
        conn.commit()

    ensure_market_data_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM market_bars WHERE symbol='AAPL'").fetchone()
    assert rows is not None
    assert rows[0] == 1


def test_validate_sufficient_history_ok(tmp_path: Path):
    db_path = ensure_market_data_db(tmp_path / "market_data.sqlite")
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO market_bars(symbol, ts, open, high, low, close, volume) VALUES (?, ?, 1, 1, 1, 1, 1)",
            [("AAPL", i) for i in range(5)] + [("MSFT", i) for i in range(5)],
        )
        conn.commit()
        counts = validate_sufficient_history(conn, ["AAPL", "MSFT"], min_bars=5)

    assert counts == {"AAPL": 5, "MSFT": 5}


def test_validate_sufficient_history_raises_when_missing(tmp_path: Path):
    db_path = ensure_market_data_db(tmp_path / "market_data.sqlite")
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO market_bars(symbol, ts, open, high, low, close, volume) VALUES (?, ?, 1, 1, 1, 1, 1)",
            [("AAPL", i) for i in range(3)],
        )
        conn.commit()

        with pytest.raises(ValueError, match="Historial insuficiente"):
            validate_sufficient_history(conn, ["AAPL", "MSFT"], min_bars=4)
