from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .cost_model import CostModel


@dataclass(frozen=True)
class ExecutionConfig:
    """Execution assumptions; all must be explicit.

    fill_ratio controls partial fills (0..1).
    max_participation_rate constrains traded quantity by market volume when
    daily_volume is provided. If volume is not provided, no capacity clipping is
    applied and this is explicitly reported in metrics.
    """

    fill_ratio: float = 1.0
    max_participation_rate: float = 1.0
    min_trade_notional: float = 0.0

    def validate(self) -> None:
        if not (0.0 <= self.fill_ratio <= 1.0):
            raise ValueError("fill_ratio must be in [0, 1]")
        if not (0.0 < self.max_participation_rate <= 1.0):
            raise ValueError("max_participation_rate must be in (0, 1]")
        if self.min_trade_notional < 0:
            raise ValueError("min_trade_notional must be >= 0")


@dataclass
class FillResult:
    filled_quantity: float
    execution_price: float
    transaction_cost: float
    was_clipped_by_capacity: bool


class ExecutionSimulator:
    def __init__(self, cost_model: CostModel, config: ExecutionConfig):
        self.cost_model = cost_model
        self.config = config
        self.config.validate()

    def simulate_fill(
        self,
        order_quantity: float,
        reference_price: float,
        daily_volume: Optional[float] = None,
    ) -> FillResult:
        if reference_price <= 0:
            raise ValueError(f"reference_price must be > 0, got {reference_price}")

        desired = order_quantity * self.config.fill_ratio
        clipped = False

        if daily_volume is not None:
            max_qty = abs(daily_volume) * self.config.max_participation_rate
            if abs(desired) > max_qty:
                desired = max_qty if desired > 0 else -max_qty
                clipped = True

        if abs(desired) * reference_price < self.config.min_trade_notional:
            desired = 0.0

        if desired == 0:
            return FillResult(0.0, reference_price, 0.0, clipped)

        side = 1 if desired > 0 else -1
        execution_price = reference_price * self.cost_model.slippage_multiplier(side)
        costs = self.cost_model.transaction_cost(desired, execution_price)

        return FillResult(
            filled_quantity=desired,
            execution_price=execution_price,
            transaction_cost=costs,
            was_clipped_by_capacity=clipped,
        )
