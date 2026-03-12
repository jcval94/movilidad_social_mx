from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostConfig:
    """Explicit trading cost configuration.

    All costs default to zero by design, and each parameter is explicit to avoid
    hidden assumptions in simulations.

    Attributes
    ----------
    commission_bps:
        Commission in basis points applied on notional traded (buy and sell).
    slippage_bps:
        Slippage in basis points applied through execution price impact.
    sell_fee_bps:
        Extra fee in basis points applied only on sell notional.
    fixed_commission:
        Fixed cash fee charged per non-zero fill.
    """

    commission_bps: float = 0.0
    slippage_bps: float = 0.0
    sell_fee_bps: float = 0.0
    fixed_commission: float = 0.0

    def validate(self) -> None:
        for field_name, value in self.__dict__.items():
            if value < 0:
                raise ValueError(f"{field_name} must be >= 0, got {value}")


class CostModel:
    """Computes explicit transaction costs for a fill."""

    def __init__(self, config: CostConfig):
        self.config = config
        self.config.validate()

    @staticmethod
    def _bps_to_fraction(bps: float) -> float:
        return bps / 10_000.0

    def slippage_multiplier(self, side: int) -> float:
        """Returns price multiplier including slippage impact.

        side: +1 for buy, -1 for sell
        """
        if side not in (-1, 1):
            raise ValueError(f"Invalid side {side}, expected +/-1")
        slip = self._bps_to_fraction(self.config.slippage_bps)
        return 1.0 + side * slip

    def transaction_cost(self, quantity: float, price: float) -> float:
        """Total cash cost charged for the fill (always >= 0)."""
        if quantity == 0:
            return 0.0

        side = 1 if quantity > 0 else -1
        notional = abs(quantity) * price
        commission = notional * self._bps_to_fraction(self.config.commission_bps)
        sell_fee = (
            notional * self._bps_to_fraction(self.config.sell_fee_bps) if side < 0 else 0.0
        )
        fixed = self.config.fixed_commission
        return commission + sell_fee + fixed
