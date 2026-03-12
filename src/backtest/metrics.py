from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MetricsConfig:
    annualization_factor: int = 252
    downside_target: float = 0.0


def compute_drawdown(equity: pd.Series) -> pd.Series:
    running_max = equity.cummax()
    return equity / running_max - 1.0


def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b not in (0, 0.0) else np.nan


def compute_performance_metrics(
    backtest_df: pd.DataFrame,
    config: MetricsConfig = MetricsConfig(),
    ticker_pnl_columns: Optional[Dict[str, str]] = None,
) -> Dict[str, float | str | Dict[str, float]]:
    r = backtest_df["returns"].astype(float)
    equity = backtest_df["equity"].astype(float)
    dd = compute_drawdown(equity)

    n = len(r)
    ann = config.annualization_factor
    years = n / ann if ann > 0 else np.nan

    total_return = equity.iloc[-1] / equity.iloc[0] - 1 if len(equity) > 1 else 0.0
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years and years > 0 else np.nan

    vol = r.std(ddof=0) * np.sqrt(ann)
    sharpe = _safe_div(r.mean() * ann, vol)

    downside = r[r < config.downside_target] - config.downside_target
    downside_vol = downside.std(ddof=0) * np.sqrt(ann) if len(downside) else np.nan
    sortino = _safe_div(r.mean() * ann, downside_vol) if not np.isnan(downside_vol) else np.nan

    wins = r[r > 0]
    losses = r[r < 0]
    hit_rate = _safe_div(len(wins), len(wins) + len(losses))

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = _safe_div(gross_profit, gross_loss)

    avg_win = float(wins.mean()) if len(wins) else np.nan
    avg_loss = float(losses.mean()) if len(losses) else np.nan

    turnover = float(backtest_df["turnover"].mean()) if "turnover" in backtest_df else np.nan

    capacity_warning = "unknown"
    if "capacity_clipped_orders" in backtest_df:
        clipped = float(backtest_df["capacity_clipped_orders"].sum())
        capacity_warning = "warning" if clipped > 0 else "ok"

    by_horizon = {
        "1m": float((1 + r.tail(21)).prod() - 1) if len(r) >= 21 else np.nan,
        "3m": float((1 + r.tail(63)).prod() - 1) if len(r) >= 63 else np.nan,
        "12m": float((1 + r.tail(252)).prod() - 1) if len(r) >= 252 else np.nan,
    }

    by_ticker = {}
    if ticker_pnl_columns:
        total_abs = 0.0
        raw = {}
        for ticker, col in ticker_pnl_columns.items():
            if col in backtest_df:
                contrib = float(backtest_df[col].sum())
                raw[ticker] = contrib
                total_abs += abs(contrib)
        if total_abs > 0:
            by_ticker = {k: v / total_abs for k, v in raw.items()}

    return {
        "total_return": float(total_return),
        "cagr": float(cagr) if not np.isnan(cagr) else np.nan,
        "sharpe": float(sharpe) if not np.isnan(sharpe) else np.nan,
        "sortino": float(sortino) if not np.isnan(sortino) else np.nan,
        "max_drawdown": float(dd.min()) if len(dd) else np.nan,
        "hit_rate": float(hit_rate) if not np.isnan(hit_rate) else np.nan,
        "profit_factor": float(profit_factor) if not np.isnan(profit_factor) else np.nan,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "turnover": turnover,
        "capacity_warning": capacity_warning,
        "returns_by_horizon": by_horizon,
        "contribution_by_ticker": by_ticker,
    }


def compare_champion_challenger(
    champion: pd.DataFrame,
    challenger: pd.DataFrame,
    config: MetricsConfig = MetricsConfig(),
) -> pd.DataFrame:
    m1 = compute_performance_metrics(champion, config=config)
    m2 = compute_performance_metrics(challenger, config=config)

    rows = []
    for k in [
        "total_return",
        "cagr",
        "sharpe",
        "sortino",
        "max_drawdown",
        "hit_rate",
        "profit_factor",
        "turnover",
    ]:
        rows.append({"metric": k, "champion": m1.get(k), "challenger": m2.get(k)})
    return pd.DataFrame(rows)
