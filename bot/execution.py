from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
from alpaca_trade_api.rest import REST

from .config import TIMEZONE
from .risk import calculate_stop_price, trailing_stop_price
from .shared import LOG_BUFFER


def get_position(api: REST, symbol: str):
    """Return the open position if it exists."""
    try:
        return api.get_position(symbol)
    except Exception:
        return None


def submit_market_buy(api: REST, symbol: str, qty: int):
    return api.submit_order(
        symbol=symbol,
        qty=qty,
        side="buy",
        type="market",
        time_in_force="day",
    )


def submit_market_sell(api: REST, symbol: str, qty: int, reason: str = ""):
    order = api.submit_order(
        symbol=symbol,
        qty=qty,
        side="sell",
        type="market",
        time_in_force="day",
    )
    if reason:
        LOG_BUFFER.add("INFO", f"{symbol} exit: {reason}")
    return order


def has_open_order(api: REST, symbol: str) -> bool:
    """Avoid duplicate orders; check for open orders on the symbol."""
    try:
        orders = api.list_orders(status="open", limit=50)
    except Exception:
        return False
    return any(o.symbol == symbol for o in orders)


def close_symbol(api: REST, symbol: str, reason: str) -> None:
    pos = get_position(api, symbol)
    if pos:
        qty = abs(int(float(pos.qty)))
        submit_market_sell(api, symbol, qty, reason=reason)
        print(f"Closed {qty} shares of {symbol}: {reason}")


def close_all_positions(api: REST, reason: str) -> None:
    try:
        positions = api.list_positions()
    except Exception:
        return
    for pos in positions:
        close_symbol(api, pos.symbol, reason=reason)


def latest_buy_fill(api: REST, symbol: str, day_start: Optional[datetime]) -> Tuple[Optional[float], Optional[datetime]]:
    """
    Find the most recent filled BUY for symbol for the current day.
    Used to anchor trailing-stop calculations after restarts.
    """
    after = day_start.isoformat() if day_start else None
    try:
        orders = api.list_orders(
            status="all",
            limit=50,
            direction="desc",
            after=after,
        )
    except Exception:
        return None, None

    for order in orders:
        if order.symbol != symbol or order.side != "buy":
            continue
        if not order.filled_at:
            continue
        filled_at = pd.to_datetime(order.filled_at).tz_convert(TIMEZONE)
        if after and filled_at < pd.to_datetime(after):
            continue
        price = None
        if order.filled_avg_price:
            price = float(order.filled_avg_price)
        elif order.limit_price:
            price = float(order.limit_price)
        elif order.stop_price:
            price = float(order.stop_price)
        return price, filled_at

    return None, None


def manage_open_position(api: REST, symbol: str, bars: pd.DataFrame, day_start: Optional[datetime]) -> Optional[Tuple[str, float, float]]:
    """
    Check exits:
    - Hard stop below entry.
    - Trailing stop below high after activation.
    - Trend flip: EMA21 crosses below EMA50.
    """
    position = get_position(api, symbol)
    if not position:
        return None

    entry_price = float(position.avg_entry_price)
    last_price = float(bars["close"].iloc[-1])

    # Determine entry time/price from fills to stay restart-safe.
    filled_price, filled_at = latest_buy_fill(api, symbol, day_start)
    anchor_price = filled_price or entry_price
    entry_time = filled_at or bars.index[0]

    recent = bars[bars.index >= entry_time]
    if recent.empty:
        recent = bars
    highest_since_entry = float(recent["high"].max())

    stop_price = calculate_stop_price(anchor_price)
    trailing_price = trailing_stop_price(anchor_price, highest_since_entry)

    if last_price <= stop_price:
        qty = abs(int(float(position.qty)))
        submit_market_sell(api, symbol, qty, reason=f"Fixed stop hit at {last_price:.2f}")
        return ("stop", anchor_price, last_price, qty)

    if trailing_price and last_price <= trailing_price:
        qty = abs(int(float(position.qty)))
        submit_market_sell(api, symbol, qty, reason=f"Trailing stop hit at {last_price:.2f}")
        return ("trail", anchor_price, last_price, qty)

    # Trend flip: EMA21 below EMA50
    ema21 = bars["close"].ewm(span=21, adjust=False).mean().iloc[-1]
    ema50 = bars["close"].ewm(span=50, adjust=False).mean().iloc[-1]
    if ema21 < ema50:
        qty = abs(int(float(position.qty)))
        submit_market_sell(api, symbol, qty, reason="Trend flipped (21 below 50)")
        return ("trend_flip", anchor_price, last_price, qty)

    return None

