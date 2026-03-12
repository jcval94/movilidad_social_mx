from datetime import datetime, timezone

import pytest

from src.execution.order_models import (
    OrderSide,
    SCHEMA_FILLS,
    SCHEMA_ORDERS,
    SCHEMA_PORTFOLIO_SNAPSHOTS,
    SCHEMA_TRADES,
)
from src.execution.run_paper_trade import (
    PaperTradingRuntimeConfig,
    SignalInstruction,
    build_paper_executor,
    run_paper_trading_cycle,
)


def test_minimum_schemas_exist():
    assert {"order_id", "cycle_id", "signal_id", "ticker", "status"}.issubset(SCHEMA_ORDERS)
    assert {"fill_id", "order_id", "ticker", "price", "fees"}.issubset(SCHEMA_FILLS)
    assert {"trade_id", "order_id", "ticker", "avg_price"}.issubset(SCHEMA_TRADES)
    assert {"snapshot_id", "cycle_id", "cash", "equity"}.issubset(SCHEMA_PORTFOLIO_SNAPSHOTS)


def test_run_paper_cycle_generates_auditable_artifacts():
    executor = build_paper_executor(
        PaperTradingRuntimeConfig(
            initial_cash=100_000,
            paper_trading_enabled=True,
            live_trading_enabled=False,
            fill_ratio=1.0,
            slippage_bps=5,
            commission_bps=10,
            sell_fee_bps=2,
        )
    )

    signals = [
        SignalInstruction("sig1", "stratA", "AAA", OrderSide.BUY, 10),
        SignalInstruction("sig2", "stratA", "BBB", OrderSide.BUY, 5),
    ]

    output = run_paper_trading_cycle(
        executor=executor,
        cycle_id="c1",
        signals=signals,
        prices={"AAA": 100.0, "BBB": 200.0},
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    assert len(output["orders"]) == 2
    assert len(output["fills"]) == 2
    assert len(output["trades"]) == 2
    assert output["portfolio_snapshot"]["equity"] > 0
    assert len(output["cash_ledger"]) == 2

    rec = output["reconciliation"]
    assert rec["totals"]["signals_without_order"] == 0
    assert rec["totals"]["orders_without_fill"] == 0


def test_double_execution_protection_same_cycle():
    executor = build_paper_executor(PaperTradingRuntimeConfig(initial_cash=50_000))
    run_paper_trading_cycle(
        executor=executor,
        cycle_id="dup",
        signals=[SignalInstruction("sigx", "s", "AAA", OrderSide.BUY, 1)],
        prices={"AAA": 10.0},
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(RuntimeError):
        executor.execute_cycle(
            cycle_id="dup",
            prices={"AAA": 10.5},
            timestamp=datetime(2025, 1, 1, 0, 1, tzinfo=timezone.utc),
        )


def test_realized_and_unrealized_pnl_and_exposure_report():
    executor = build_paper_executor(PaperTradingRuntimeConfig(initial_cash=100_000))

    run_paper_trading_cycle(
        executor=executor,
        cycle_id="buy",
        signals=[SignalInstruction("s1", "st", "AAA", OrderSide.BUY, 10)],
        prices={"AAA": 100.0},
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    out2 = run_paper_trading_cycle(
        executor=executor,
        cycle_id="sell",
        signals=[SignalInstruction("s2", "st", "AAA", OrderSide.SELL, 4)],
        prices={"AAA": 110.0},
        timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    snap = out2["portfolio_snapshot"]
    assert snap["realized_pnl"] > 0
    assert snap["unrealized_pnl"] >= 0

    exposure = executor.portfolio_state.exposure_report({"AAA": 110.0})
    assert exposure["gross_exposure"] > 0
    assert exposure["long_exposure"] >= 0
    assert exposure["realized_pnl"] > 0
