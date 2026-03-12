from datetime import datetime, timezone

import pytest

from src.execution.order_models import OrderSide
from src.execution.run_paper_trade import (
    PaperTradingRuntimeConfig,
    SignalInstruction,
    build_paper_executor,
    run_paper_trading_cycle,
)
from src.storage.history_writer import write_versioned_snapshot


def test_session_gating_prevents_double_cycle_execution():
    executor = build_paper_executor(PaperTradingRuntimeConfig(initial_cash=100_000))
    run_paper_trading_cycle(
        executor=executor,
        cycle_id="session-A",
        signals=[SignalInstruction("s1", "st", "AAA", OrderSide.BUY, 1)],
        prices={"AAA": 10.0},
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(RuntimeError):
        run_paper_trading_cycle(
            executor=executor,
            cycle_id="session-A",
            signals=[SignalInstruction("s2", "st", "AAA", OrderSide.BUY, 1)],
            prices={"AAA": 10.0},
            timestamp=datetime(2025, 1, 1, 0, 1, tzinfo=timezone.utc),
        )


def test_snapshot_writer_is_idempotent_for_same_session_and_payload(tmp_path):
    ts = datetime(2025, 1, 1, 9, 30, tzinfo=timezone.utc)
    payload = {"metric": 1.23, "status": "ok"}

    _, changed_1 = write_versioned_snapshot(str(tmp_path), "model_health", "session-A", ts, payload)
    _, changed_2 = write_versioned_snapshot(str(tmp_path), "model_health", "session-A", ts, payload)

    assert changed_1 is True
    assert changed_2 is False
