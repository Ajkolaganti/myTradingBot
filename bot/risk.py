import math
from typing import Optional

from .config import (
    MAX_POSITION_PCT,
    RISK_PER_TRADE_PCT,
    STOP_LOSS_PCT,
    TRAIL_OFFSET_PCT,
    TRAIL_TRIGGER_PCT,
)


def calculate_stop_price(entry_price: float) -> float:
    """Fixed tight stop below entry to cap loss quickly."""
    return round(entry_price * (1 - STOP_LOSS_PCT), 4)


def calculate_position_size(account_equity: float, entry_price: float, aggressive: bool = False) -> int:
    """
    Risk 0.75% (or 1% if aggressive) of equity per trade.
    Position size = (equity * risk%) / stop distance.
    """
    if account_equity <= 0 or entry_price <= 0:
        return 0

    risk_pct = RISK_PER_TRADE_PCT if not aggressive else max(RISK_PER_TRADE_PCT, 0.01)
    risk_capital = account_equity * risk_pct
    stop_distance = entry_price * STOP_LOSS_PCT
    if stop_distance <= 0:
        return 0

    qty = math.floor(risk_capital / stop_distance)
    position_value = qty * entry_price
    max_value = account_equity * MAX_POSITION_PCT
    if position_value > max_value and entry_price > 0:
        qty = math.floor(max_value / entry_price)
    return max(qty, 0)


def trailing_stop_price(entry_price: float, highest_price: float) -> Optional[float]:
    """
    Activate trailing once price is at least 1.0% above entry.
    Then trail 1.5% below the highest price seen since entry.
    """
    if highest_price <= 0 or entry_price <= 0:
        return None

    if highest_price < entry_price * (1 + TRAIL_TRIGGER_PCT):
        return None

    return round(highest_price * (1 - TRAIL_OFFSET_PCT), 4)

