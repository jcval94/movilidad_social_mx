from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .execution_simulator import ExecutionSimulator


@dataclass(frozen=True)
class PortfolioConfig:
    initial_cash: float = 1_000_000.0
    max_gross_exposure: float = 1.0
    allow_short: bool = False

    def validate(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be > 0")
        if self.max_gross_exposure <= 0:
            raise ValueError("max_gross_exposure must be > 0")


class PortfolioEngine:
    """Simple but robust portfolio backtesting engine.

    price_data columns are tickers and index is datetime-like.
    target_weights uses same shape/index and represents end-of-day desired weights.
    """

    def __init__(
        self,
        execution_simulator: ExecutionSimulator,
        config: PortfolioConfig,
    ):
        self.execution_simulator = execution_simulator
        self.config = config
        self.config.validate()

    def run_single_strategy(
        self,
        price_data: pd.DataFrame,
        target_weights: pd.DataFrame,
        volume_data: Optional[pd.DataFrame] = None,
        strategy_name: str = "strategy",
    ) -> pd.DataFrame:
        if not price_data.index.equals(target_weights.index):
            raise ValueError("price_data and target_weights index must match")
        if set(price_data.columns) != set(target_weights.columns):
            raise ValueError("price_data and target_weights columns must match")

        tickers = list(price_data.columns)
        dates = price_data.index
        positions = pd.Series(0.0, index=tickers)
        avg_cost = pd.Series(0.0, index=tickers)
        cash = self.config.initial_cash

        rows = []

        for dt in dates:
            prices = price_data.loc[dt].astype(float)
            weights = target_weights.loc[dt].fillna(0.0).astype(float)

            if not self.config.allow_short and (weights < 0).any():
                raise ValueError("Short weights provided but allow_short=False")

            market_value = float((positions * prices).sum())
            equity_before = cash + market_value

            weights = self._clip_weights_by_exposure(weights)
            desired_notional = weights * equity_before
            current_notional = positions * prices
            delta_notional = desired_notional - current_notional
            order_qty = delta_notional / prices.replace(0, np.nan)
            order_qty = order_qty.replace([np.inf, -np.inf], np.nan).fillna(0.0)

            realized_pnl = 0.0
            unrealized_pnl = 0.0
            turnover_notional = 0.0
            clipped_count = 0
            gross_traded_notional = 0.0

            for ticker in tickers:
                qty = float(order_qty[ticker])
                if qty == 0:
                    continue

                daily_volume = None
                if volume_data is not None and ticker in volume_data.columns:
                    daily_volume = float(volume_data.loc[dt, ticker])

                fill = self.execution_simulator.simulate_fill(
                    order_quantity=qty,
                    reference_price=float(prices[ticker]),
                    daily_volume=daily_volume,
                )
                fq = fill.filled_quantity
                if fq == 0:
                    continue

                fill_notional = abs(fq * fill.execution_price)
                turnover_notional += fill_notional
                gross_traded_notional += fill_notional
                if fill.was_clipped_by_capacity:
                    clipped_count += 1

                prev_pos = float(positions[ticker])
                prev_avg = float(avg_cost[ticker])
                new_pos = prev_pos + fq

                # cash impact
                cash -= fq * fill.execution_price
                cash -= fill.transaction_cost

                # realized PnL when reducing or flipping position
                if prev_pos != 0 and np.sign(prev_pos) != np.sign(new_pos):
                    closed_qty = abs(prev_pos)
                elif prev_pos != 0 and np.sign(prev_pos) != np.sign(fq):
                    closed_qty = min(abs(prev_pos), abs(fq))
                else:
                    closed_qty = 0.0

                if closed_qty > 0:
                    if prev_pos > 0:
                        realized_pnl += closed_qty * (fill.execution_price - prev_avg)
                    else:
                        realized_pnl += closed_qty * (prev_avg - fill.execution_price)

                # average cost update
                if new_pos == 0:
                    avg_cost[ticker] = 0.0
                elif prev_pos == 0 or np.sign(prev_pos) == np.sign(fq):
                    total_qty = abs(prev_pos) + abs(fq)
                    weighted = abs(prev_pos) * prev_avg + abs(fq) * fill.execution_price
                    avg_cost[ticker] = weighted / total_qty
                elif np.sign(prev_pos) != np.sign(new_pos):
                    avg_cost[ticker] = fill.execution_price

                positions[ticker] = new_pos

            market_value_after = float((positions * prices).sum())
            equity_after = cash + market_value_after

            for ticker in tickers:
                pos = float(positions[ticker])
                if pos == 0:
                    continue
                px = float(prices[ticker])
                ac = float(avg_cost[ticker])
                if pos > 0:
                    unrealized_pnl += pos * (px - ac)
                else:
                    unrealized_pnl += abs(pos) * (ac - px)

            gross_exposure = float((positions.abs() * prices).sum()) / max(equity_after, 1e-12)
            turnover = turnover_notional / max(equity_before, 1e-12)

            row = {
                "date": dt,
                "strategy": strategy_name,
                "cash": cash,
                "equity": equity_after,
                "market_value": market_value_after,
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "turnover": turnover,
                "gross_exposure": gross_exposure,
                "capacity_clipped_orders": clipped_count,
                "gross_traded_notional": gross_traded_notional,
            }
            for ticker in tickers:
                row[f"position_{ticker}"] = float(positions[ticker])
                row[f"price_{ticker}"] = float(prices[ticker])
            rows.append(row)

        result = pd.DataFrame(rows).set_index("date")
        result["returns"] = result["equity"].pct_change().fillna(0.0)
        return result

    def run_multi_strategy_portfolio(
        self,
        price_data: pd.DataFrame,
        strategy_weights: Dict[str, pd.DataFrame],
        allocations: Dict[str, float],
        volume_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, pd.DataFrame]:
        if set(strategy_weights) != set(allocations):
            raise ValueError("strategy_weights and allocations keys must match")

        per_strategy = {}
        weighted_returns: Optional[pd.Series] = None
        for name, w in strategy_weights.items():
            out = self.run_single_strategy(
                price_data=price_data,
                target_weights=w,
                volume_data=volume_data,
                strategy_name=name,
            )
            per_strategy[name] = out
            contrib = out["returns"] * allocations[name]
            weighted_returns = contrib if weighted_returns is None else weighted_returns.add(contrib, fill_value=0.0)

        total = pd.DataFrame(index=price_data.index)
        total["returns"] = weighted_returns.fillna(0.0) if weighted_returns is not None else 0.0
        total["equity"] = self.config.initial_cash * (1 + total["returns"]).cumprod()
        total["strategy"] = "portfolio"
        per_strategy["portfolio"] = total
        return per_strategy

    def _clip_weights_by_exposure(self, weights: pd.Series) -> pd.Series:
        gross = float(weights.abs().sum())
        if gross <= self.config.max_gross_exposure:
            return weights
        scale = self.config.max_gross_exposure / gross
        return weights * scale
