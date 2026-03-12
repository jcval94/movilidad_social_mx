import numpy as np
import pandas as pd

from src.backtest.cost_model import CostConfig
from src.backtest.execution_simulator import ExecutionConfig
from src.backtest.metrics import compute_drawdown
from src.backtest.portfolio_engine import PortfolioConfig
from src.backtest.run_backtest import (
    BacktestConfig,
    run_champion_challenger,
    run_portfolio_backtest,
    run_strategy_backtest,
)


def _sample_data():
    dates = pd.date_range("2024-01-01", periods=80, freq="B")
    prices = pd.DataFrame(
        {
            "AAA": np.linspace(100, 120, len(dates)),
            "BBB": np.linspace(80, 76, len(dates)),
        },
        index=dates,
    )
    volume = pd.DataFrame({"AAA": 10_000, "BBB": 10_000}, index=dates)
    return prices, volume


def test_single_strategy_backtest_outputs_required_fields():
    prices, volume = _sample_data()
    weights = pd.DataFrame({"AAA": 0.6, "BBB": 0.2}, index=prices.index)

    cfg = BacktestConfig(
        cost=CostConfig(commission_bps=5, slippage_bps=2, sell_fee_bps=3),
        execution=ExecutionConfig(fill_ratio=1.0, max_participation_rate=0.2),
        portfolio=PortfolioConfig(initial_cash=1_000_000, max_gross_exposure=1.0),
    )

    out = run_strategy_backtest(prices, weights, cfg, volume_data=volume)
    ts = out["timeseries"]
    metrics = out["metrics"]

    assert "equity" in ts.columns
    assert "realized_pnl" in ts.columns
    assert "unrealized_pnl" in ts.columns
    assert "turnover" in ts.columns
    assert "gross_exposure" in ts.columns

    for required in [
        "cagr",
        "sharpe",
        "sortino",
        "max_drawdown",
        "hit_rate",
        "profit_factor",
        "avg_win",
        "avg_loss",
        "turnover",
        "capacity_warning",
        "returns_by_horizon",
    ]:
        assert required in metrics


def test_multi_strategy_portfolio_and_contributions():
    prices, volume = _sample_data()
    momentum = pd.DataFrame({"AAA": 0.7, "BBB": 0.0}, index=prices.index)
    defensive = pd.DataFrame({"AAA": 0.1, "BBB": 0.4}, index=prices.index)

    cfg = BacktestConfig(
        cost=CostConfig(commission_bps=1, slippage_bps=1),
        execution=ExecutionConfig(fill_ratio=1.0, max_participation_rate=0.5),
        portfolio=PortfolioConfig(initial_cash=500_000, max_gross_exposure=1.0),
    )

    out = run_portfolio_backtest(
        prices,
        strategy_weights={"momentum": momentum, "defensive": defensive},
        allocations={"momentum": 0.6, "defensive": 0.4},
        config=cfg,
        volume_data=volume,
    )
    metrics = out["metrics"]

    assert "contribution_by_strategy" in metrics
    assert set(metrics["contribution_by_strategy"].keys()) == {"momentum", "defensive"}
    assert "contribution_by_ticker" in metrics
    assert set(metrics["contribution_by_ticker"].keys()) == {"AAA", "BBB"}


def test_champion_challenger_comparison():
    prices, volume = _sample_data()
    champion = pd.DataFrame({"AAA": 0.7, "BBB": 0.1}, index=prices.index)
    challenger = pd.DataFrame({"AAA": 0.2, "BBB": 0.6}, index=prices.index)

    cfg = BacktestConfig(
        cost=CostConfig(commission_bps=2, slippage_bps=1, sell_fee_bps=1),
        execution=ExecutionConfig(fill_ratio=0.9, max_participation_rate=0.1),
        portfolio=PortfolioConfig(initial_cash=750_000, max_gross_exposure=1.0),
    )

    out = run_champion_challenger(champion, challenger, prices, cfg, volume_data=volume)
    comparison = out["comparison"]

    assert {"metric", "champion", "challenger"}.issubset(comparison.columns)
    assert len(comparison) >= 6


def test_drawdown_is_non_positive():
    equity = pd.Series([100, 110, 105, 120, 90, 95])
    dd = compute_drawdown(equity)
    assert (dd <= 1e-12).all()
    assert dd.min() < 0
