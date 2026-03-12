from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from .order_models import OrderSide
from .paper_executor import PaperExecutor, PaperExecutorConfig
from .portfolio_state import PortfolioState
from .reconciliation import ReconciliationResult, reconcile_signals_orders_fills


@dataclass(frozen=True)
class SignalInstruction:
    signal_id: str
    strategy_id: str
    ticker: str
    side: OrderSide
    quantity: float


@dataclass(frozen=True)
class PaperTradingRuntimeConfig:
    initial_cash: float = 1_000_000.0
    paper_trading_enabled: bool = True
    live_trading_enabled: bool = False
    fill_ratio: float = 1.0
    slippage_bps: float = 0.0
    commission_bps: float = 0.0
    sell_fee_bps: float = 0.0
    broker_adapter: Optional[str] = None


def build_paper_executor(config: PaperTradingRuntimeConfig) -> PaperExecutor:
    portfolio = PortfolioState(initial_cash=config.initial_cash)
    exec_cfg = PaperExecutorConfig(
        paper_trading_enabled=config.paper_trading_enabled,
        live_trading_enabled=config.live_trading_enabled,
        fill_ratio=config.fill_ratio,
        slippage_bps=config.slippage_bps,
        commission_bps=config.commission_bps,
        sell_fee_bps=config.sell_fee_bps,
    )
    return PaperExecutor(exec_cfg, portfolio)


def run_paper_trading_cycle(
    executor: PaperExecutor,
    cycle_id: str,
    signals: Iterable[SignalInstruction],
    prices: Dict[str, float],
    timestamp: datetime,
) -> Dict[str, object]:
    submitted_orders = []
    signal_ids: List[str] = []
    for signal in signals:
        signal_ids.append(signal.signal_id)
        order = executor.submit_order(
            cycle_id=cycle_id,
            signal_id=signal.signal_id,
            strategy_id=signal.strategy_id,
            ticker=signal.ticker,
            side=signal.side,
            quantity=signal.quantity,
        )
        submitted_orders.append(order)

    cycle_fills = executor.execute_cycle(cycle_id=cycle_id, prices=prices, timestamp=timestamp)

    reconciliation: ReconciliationResult = reconcile_signals_orders_fills(
        signal_ids=signal_ids,
        orders=submitted_orders,
        fills=cycle_fills,
    )

    latest_snapshot = executor.portfolio_state.snapshots[-1]
    return {
        "orders": [o.to_dict() for o in submitted_orders],
        "fills": [f.to_dict() for f in cycle_fills],
        "trades": [t.to_dict() for t in executor.trades if t.order_id in {o.order_id for o in submitted_orders}],
        "portfolio_snapshot": latest_snapshot.to_dict(),
        "cash_ledger": [entry.__dict__ for entry in executor.portfolio_state.cash_ledger],
        "reconciliation": {
            "totals": reconciliation.totals,
            "missing_order_for_signal": reconciliation.missing_order_for_signal,
            "missing_fill_for_order": reconciliation.missing_fill_for_order,
        },
    }
