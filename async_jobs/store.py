import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path("data/job_results.sqlite")


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_store() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_results (
                idempotency_key TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result_json TEXT,
                error_message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def get_cached_result(idempotency_key: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT status, result_json, error_message, updated_at FROM job_results WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()

    if not row:
        return None

    status, result_json, error_message, updated_at = row
    payload = {
        "status": status,
        "error_message": error_message,
        "updated_at": updated_at,
    }
    if result_json:
        payload["result"] = json.loads(result_json)
    return payload


def upsert_result(idempotency_key: str, status: str, result: dict[str, Any] | None = None, error_message: str = "") -> None:
    encoded = json.dumps(result, ensure_ascii=False) if result is not None else None
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO job_results (idempotency_key, status, result_json, error_message, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(idempotency_key) DO UPDATE SET
                status=excluded.status,
                result_json=excluded.result_json,
                error_message=excluded.error_message,
                updated_at=CURRENT_TIMESTAMP
            """,
            (idempotency_key, status, encoded, error_message),
        )
