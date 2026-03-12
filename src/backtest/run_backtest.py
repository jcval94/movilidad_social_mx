from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

from .cost_model import CostConfig, CostModel
from .execution_simulator import ExecutionConfig, ExecutionSimulator
from .metrics import MetricsConfig, compare_champion_challenger, compute_performance_metrics
from .portfolio_engine import PortfolioConfig, PortfolioEngine


@dataclass(frozen=True)
class BacktestConfig:
    cost: CostConfig
    execution: ExecutionConfig
    portfolio: PortfolioConfig
    metrics: MetricsConfig = MetricsConfig()


def build_engine(config: BacktestConfig) -> PortfolioEngine:
    cost_model = CostModel(config.cost)
    simulator = ExecutionSimulator(cost_model, config.execution)
    return PortfolioEngine(simulator, config.portfolio)


def run_strategy_backtest(
    price_data: pd.DataFrame,
    target_weights: pd.DataFrame,
    config: BacktestConfig,
    volume_data: Optional[pd.DataFrame] = None,
    strategy_name: str = "strategy",
) -> Dict[str, object]:
    engine = build_engine(config)
    result = engine.run_single_strategy(
        price_data=price_data,
        target_weights=target_weights,
        volume_data=volume_data,
        strategy_name=strategy_name,
    )
    metrics = compute_performance_metrics(result, config.metrics)
    return {"timeseries": result, "metrics": metrics}


def run_portfolio_backtest(
    price_data: pd.DataFrame,
    strategy_weights: Dict[str, pd.DataFrame],
    allocations: Dict[str, float],
    config: BacktestConfig,
    volume_data: Optional[pd.DataFrame] = None,
) -> Dict[str, object]:
    if abs(sum(allocations.values()) - 1.0) > 1e-8:
        raise ValueError("allocations must sum to 1.0")

    engine = build_engine(config)
    outputs = engine.run_multi_strategy_portfolio(
        price_data=price_data,
        strategy_weights=strategy_weights,
        allocations=allocations,
        volume_data=volume_data,
    )

    portfolio_metrics = compute_performance_metrics(outputs["portfolio"], config.metrics)

    contribution_by_strategy = {}
    for name, df in outputs.items():
        if name == "portfolio":
            continue
        contribution_by_strategy[name] = float((df["returns"] * allocations[name]).sum())

    portfolio_metrics["contribution_by_strategy"] = contribution_by_strategy

    ticker_contrib = {}
    for ticker in price_data.columns:
        c = 0.0
        for name, df in outputs.items():
            if name == "portfolio":
                continue
            pos_col = f"position_{ticker}"
            price_col = f"price_{ticker}"
            if pos_col in df and price_col in df:
                pnl = (df[pos_col].shift(1).fillna(0.0) * df[price_col].diff().fillna(0.0)).sum()
                c += float(pnl) * allocations[name]
        ticker_contrib[ticker] = c

    total_abs = sum(abs(v) for v in ticker_contrib.values())
    if total_abs > 0:
        ticker_contrib = {k: v / total_abs for k, v in ticker_contrib.items()}
    portfolio_metrics["contribution_by_ticker"] = ticker_contrib

    return {
        "timeseries": outputs,
        "metrics": portfolio_metrics,
    }


def run_champion_challenger(
    champion_weights: pd.DataFrame,
    challenger_weights: pd.DataFrame,
    price_data: pd.DataFrame,
    config: BacktestConfig,
    volume_data: Optional[pd.DataFrame] = None,
) -> Dict[str, object]:
    ch = run_strategy_backtest(
        price_data=price_data,
        target_weights=champion_weights,
        config=config,
        volume_data=volume_data,
        strategy_name="champion",
    )
    cg = run_strategy_backtest(
        price_data=price_data,
        target_weights=challenger_weights,
        config=config,
        volume_data=volume_data,
        strategy_name="challenger",
    )
    comparison = compare_champion_challenger(
        ch["timeseries"],
        cg["timeseries"],
        config=config.metrics,
    )
    return {
        "champion": ch,
        "challenger": cg,
        "comparison": comparison,
    }
