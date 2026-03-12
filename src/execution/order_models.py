from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Literal, Optional
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    order_id: str
    cycle_id: str
    signal_id: str
    strategy_id: str
    ticker: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.CREATED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    filled_quantity: float = 0.0

    @property
    def remaining_quantity(self) -> float:
        return max(self.quantity - self.filled_quantity, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["side"] = self.side.value
        out["order_type"] = self.order_type.value
        out["status"] = self.status.value
        return out


@dataclass
class Fill:
    fill_id: str
    order_id: str
    cycle_id: str
    ticker: str
    side: OrderSide
    quantity: float
    price: float
    fees: float
    slippage_bps: float
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["side"] = self.side.value
        return out


@dataclass
class Trade:
    trade_id: str
    order_id: str
    ticker: str
    side: OrderSide
    quantity: float
    avg_price: float
    gross_notional: float
    total_fees: float
    executed_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["side"] = self.side.value
        return out


@dataclass
class PortfolioSnapshot:
    snapshot_id: str
    cycle_id: str
    timestamp: datetime
    cash: float
    market_value: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    gross_exposure: float
    net_exposure: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Minimal storage schemas for persistence/auditing.
SCHEMA_ORDERS: Dict[str, Literal["str", "float", "datetime"]] = {
    "order_id": "str",
    "cycle_id": "str",
    "signal_id": "str",
    "strategy_id": "str",
    "ticker": "str",
    "side": "str",
    "quantity": "float",
    "order_type": "str",
    "limit_price": "float",
    "status": "str",
    "created_at": "datetime",
    "updated_at": "datetime",
    "filled_quantity": "float",
}

SCHEMA_FILLS: Dict[str, Literal["str", "float", "datetime"]] = {
    "fill_id": "str",
    "order_id": "str",
    "cycle_id": "str",
    "ticker": "str",
    "side": "str",
    "quantity": "float",
    "price": "float",
    "fees": "float",
    "slippage_bps": "float",
    "timestamp": "datetime",
}

SCHEMA_TRADES: Dict[str, Literal["str", "float", "datetime"]] = {
    "trade_id": "str",
    "order_id": "str",
    "ticker": "str",
    "side": "str",
    "quantity": "float",
    "avg_price": "float",
    "gross_notional": "float",
    "total_fees": "float",
    "executed_at": "datetime",
}

SCHEMA_PORTFOLIO_SNAPSHOTS: Dict[str, Literal["str", "float", "datetime"]] = {
    "snapshot_id": "str",
    "cycle_id": "str",
    "timestamp": "datetime",
    "cash": "float",
    "market_value": "float",
    "equity": "float",
    "realized_pnl": "float",
    "unrealized_pnl": "float",
    "gross_exposure": "float",
    "net_exposure": "float",
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"
