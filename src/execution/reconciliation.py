from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .order_models import Fill, Order


@dataclass
class ReconciliationResult:
    totals: Dict[str, int]
    missing_order_for_signal: List[str]
    missing_fill_for_order: List[str]


def reconcile_signals_orders_fills(
    signal_ids: Iterable[str],
    orders: Iterable[Order],
    fills: Iterable[Fill],
) -> ReconciliationResult:
    signal_ids = list(signal_ids)
    orders = list(orders)
    fills = list(fills)

    order_by_signal = Counter(o.signal_id for o in orders)
    fill_by_order = Counter(f.order_id for f in fills)

    missing_signal_orders = [sid for sid in signal_ids if order_by_signal[sid] == 0]
    missing_order_fills = [o.order_id for o in orders if fill_by_order[o.order_id] == 0]

    totals = {
        "signals": len(signal_ids),
        "orders": len(orders),
        "fills": len(fills),
        "signals_without_order": len(missing_signal_orders),
        "orders_without_fill": len(missing_order_fills),
    }
    return ReconciliationResult(
        totals=totals,
        missing_order_for_signal=missing_signal_orders,
        missing_fill_for_order=missing_order_fills,
    )
