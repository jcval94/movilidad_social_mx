from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from .order_models import Fill, OrderSide, PortfolioSnapshot, new_id


@dataclass
class PositionState:
    quantity: float = 0.0
    avg_cost: float = 0.0


@dataclass
class CashLedgerEntry:
    timestamp: datetime
    cycle_id: str
    amount: float
    reason: str
    balance_after: float


class PortfolioState:
    def __init__(self, initial_cash: float):
        if initial_cash <= 0:
            raise ValueError("initial_cash must be > 0")
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.realized_pnl = 0.0
        self.positions: Dict[str, PositionState] = {}
        self.cash_ledger: List[CashLedgerEntry] = []
        self.snapshots: List[PortfolioSnapshot] = []

    def apply_fill(self, fill: Fill) -> None:
        position = self.positions.setdefault(fill.ticker, PositionState())
        signed_qty = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity

        prev_qty = position.quantity
        prev_avg = position.avg_cost
        new_qty = prev_qty + signed_qty

        cash_change = -(fill.quantity * fill.price) if fill.side == OrderSide.BUY else fill.quantity * fill.price
        cash_change -= fill.fees
        self.cash += cash_change
        self._ledger(fill.cycle_id, cash_change, f"fill:{fill.fill_id}", fill.timestamp)

        closed_qty = 0.0
        if prev_qty != 0 and (prev_qty > 0 > signed_qty or prev_qty < 0 < signed_qty):
            closed_qty = min(abs(prev_qty), abs(signed_qty))

        if closed_qty > 0:
            if prev_qty > 0:
                self.realized_pnl += closed_qty * (fill.price - prev_avg)
            else:
                self.realized_pnl += closed_qty * (prev_avg - fill.price)

        if new_qty == 0:
            position.quantity = 0.0
            position.avg_cost = 0.0
            return

        if prev_qty == 0 or (prev_qty > 0 and signed_qty > 0) or (prev_qty < 0 and signed_qty < 0):
            total_abs = abs(prev_qty) + abs(signed_qty)
            position.avg_cost = (abs(prev_qty) * prev_avg + abs(signed_qty) * fill.price) / total_abs
        elif (prev_qty > 0 > new_qty) or (prev_qty < 0 < new_qty):
            position.avg_cost = fill.price

        position.quantity = new_qty

    def mark_to_market(self, cycle_id: str, prices: Dict[str, float], timestamp: datetime) -> PortfolioSnapshot:
        market_value = 0.0
        unrealized = 0.0
        gross = 0.0
        net = 0.0

        for ticker, pos in self.positions.items():
            px = prices.get(ticker)
            if px is None:
                continue
            mv = pos.quantity * px
            market_value += mv
            gross += abs(mv)
            net += mv
            if pos.quantity > 0:
                unrealized += pos.quantity * (px - pos.avg_cost)
            elif pos.quantity < 0:
                unrealized += abs(pos.quantity) * (pos.avg_cost - px)

        equity = self.cash + market_value
        snap = PortfolioSnapshot(
            snapshot_id=new_id("snap"),
            cycle_id=cycle_id,
            timestamp=timestamp,
            cash=self.cash,
            market_value=market_value,
            equity=equity,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized,
            gross_exposure=gross,
            net_exposure=net,
        )
        self.snapshots.append(snap)
        return snap

    def exposure_report(self, prices: Dict[str, float]) -> Dict[str, float]:
        long_exposure = 0.0
        short_exposure = 0.0
        for ticker, pos in self.positions.items():
            px = prices.get(ticker, 0.0)
            notional = pos.quantity * px
            if notional >= 0:
                long_exposure += notional
            else:
                short_exposure += abs(notional)

        return {
            "long_exposure": long_exposure,
            "short_exposure": short_exposure,
            "gross_exposure": long_exposure + short_exposure,
            "net_exposure": long_exposure - short_exposure,
            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
        }

    def _ledger(self, cycle_id: str, amount: float, reason: str, timestamp: datetime) -> None:
        self.cash_ledger.append(
            CashLedgerEntry(
                timestamp=timestamp,
                cycle_id=cycle_id,
                amount=amount,
                reason=reason,
                balance_after=self.cash,
            )
        )
