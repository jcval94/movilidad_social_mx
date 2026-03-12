from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from .order_models import Fill, Order, OrderSide, OrderStatus, OrderType, Trade, new_id
from .portfolio_state import PortfolioState


@dataclass(frozen=True)
class PaperExecutorConfig:
    paper_trading_enabled: bool = True
    live_trading_enabled: bool = False
    fill_ratio: float = 1.0
    slippage_bps: float = 0.0
    commission_bps: float = 0.0
    sell_fee_bps: float = 0.0

    def validate(self) -> None:
        if not self.paper_trading_enabled:
            raise ValueError("paper_trading_enabled must be True for PaperExecutor")
        if self.live_trading_enabled:
            raise ValueError("live_trading_enabled must be False by default in PaperExecutor")
        if not (0.0 <= self.fill_ratio <= 1.0):
            raise ValueError("fill_ratio must be in [0,1]")
        for k, v in {
            "slippage_bps": self.slippage_bps,
            "commission_bps": self.commission_bps,
            "sell_fee_bps": self.sell_fee_bps,
        }.items():
            if v < 0:
                raise ValueError(f"{k} must be >= 0")


class PaperExecutor:
    def __init__(self, config: PaperExecutorConfig, portfolio_state: PortfolioState):
        config.validate()
        self.config = config
        self.portfolio_state = portfolio_state

        self.order_book: List[Order] = []
        self.fills: List[Fill] = []
        self.trades: List[Trade] = []
        self._executed_cycles: set[str] = set()

    def submit_order(
        self,
        cycle_id: str,
        signal_id: str,
        strategy_id: str,
        ticker: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
    ) -> Order:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        order = Order(
            order_id=new_id("ord"),
            cycle_id=cycle_id,
            signal_id=signal_id,
            strategy_id=strategy_id,
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            status=OrderStatus.SUBMITTED,
        )
        self.order_book.append(order)
        return order

    def execute_cycle(
        self,
        cycle_id: str,
        prices: Dict[str, float],
        timestamp: datetime,
    ) -> List[Fill]:
        if cycle_id in self._executed_cycles:
            raise RuntimeError(f"Cycle {cycle_id} already executed")
        self._executed_cycles.add(cycle_id)

        cycle_fills: List[Fill] = []
        for order in self._orders_for_cycle(cycle_id):
            if order.status in {OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.FILLED}:
                continue

            px = prices.get(order.ticker)
            if px is None or px <= 0:
                order.status = OrderStatus.REJECTED
                order.updated_at = timestamp
                continue

            fill = self._simulate_fill(order, px, timestamp)
            if fill is None:
                continue

            order.filled_quantity += fill.quantity
            if order.filled_quantity >= order.quantity - 1e-12:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
            order.updated_at = timestamp

            self.fills.append(fill)
            cycle_fills.append(fill)
            self.portfolio_state.apply_fill(fill)

            trade = Trade(
                trade_id=new_id("trd"),
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side,
                quantity=fill.quantity,
                avg_price=fill.price,
                gross_notional=fill.quantity * fill.price,
                total_fees=fill.fees,
                executed_at=timestamp,
            )
            self.trades.append(trade)

        self.portfolio_state.mark_to_market(cycle_id=cycle_id, prices=prices, timestamp=timestamp)
        return cycle_fills

    def _orders_for_cycle(self, cycle_id: str) -> Iterable[Order]:
        return [o for o in self.order_book if o.cycle_id == cycle_id]

    def _simulate_fill(self, order: Order, reference_price: float, timestamp: datetime) -> Optional[Fill]:
        qty = order.remaining_quantity * self.config.fill_ratio
        if qty <= 0:
            return None

        slip = self.config.slippage_bps / 10_000.0
        exec_price = reference_price * (1 + slip) if order.side == OrderSide.BUY else reference_price * (1 - slip)

        if order.order_type == OrderType.LIMIT and order.limit_price is not None:
            if order.side == OrderSide.BUY and exec_price > order.limit_price:
                return None
            if order.side == OrderSide.SELL and exec_price < order.limit_price:
                return None

        notional = qty * exec_price
        commission = notional * (self.config.commission_bps / 10_000.0)
        sell_fee = notional * (self.config.sell_fee_bps / 10_000.0) if order.side == OrderSide.SELL else 0.0
        fees = commission + sell_fee

        return Fill(
            fill_id=new_id("fill"),
            order_id=order.order_id,
            cycle_id=order.cycle_id,
            ticker=order.ticker,
            side=order.side,
            quantity=qty,
            price=exec_price,
            fees=fees,
            slippage_bps=self.config.slippage_bps,
            timestamp=timestamp,
        )
