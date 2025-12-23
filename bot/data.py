from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from alpaca_trade_api.rest import REST

from .config import (
    BENCHMARKS,
    TIMEFRAME,
    TIMEZONE,
    TOP_TRENDING_LIMIT,
    TRADING_WINDOW_END,
    TRADING_WINDOW_START,
    UNIVERSE_SCAN_LIMIT,
    VOLUME_ACCEL_THRESHOLD,
    MAX_SPREAD_ABS,
    MAX_SPREAD_PCT,
    MIN_BAR_DOLLAR_VOL,
)


def is_market_open(api: REST) -> bool:
    """Use Alpaca clock to avoid local time mistakes."""
    try:
        clock = api.get_clock()
        return bool(clock.is_open)
    except Exception:
        return False


def within_trading_window(now: datetime) -> bool:
    """Restrict trading to the safest intraday window."""
    current_time = now.time()
    return TRADING_WINDOW_START <= current_time <= TRADING_WINDOW_END


def fetch_recent_bars(api: REST, symbol: str, limit: int = 300) -> Optional[pd.DataFrame]:
    """Fetch recent 5-minute bars for a symbol."""
    try:
        bars = api.get_bars(symbol, TIMEFRAME, limit=limit).df
        if bars.empty:
            return None
        # Normalize timezone to Eastern for clear comparisons.
        if bars.index.tz is None:
            bars = bars.tz_localize("UTC")
        return bars.tz_convert(TIMEZONE)
    except Exception as exc:
        print(f"Warning: failed to load bars for {symbol}: {exc}")
        return None


def latest_spread_ok(api: REST, symbol: str) -> bool:
    """Check bid-ask spread against configured thresholds."""
    try:
        q = api.get_latest_quote(symbol)
        bid = float(q.bidprice)
        ask = float(q.askprice)
        if bid <= 0 or ask <= 0 or ask < bid:
            return False
        spread = ask - bid
        pct = spread / bid
        return spread <= MAX_SPREAD_ABS and pct <= MAX_SPREAD_PCT
    except Exception:
        return False


def bar_meets_dollar_volume(bars: pd.DataFrame) -> bool:
    """Ensure the most recent bar has enough dollar volume to avoid illiquidity."""
    if bars is None or bars.empty:
        return False
    last = bars.iloc[-1]
    dollar_vol = float(last["close"] * last["volume"])
    return dollar_vol >= MIN_BAR_DOLLAR_VOL


def _returns_from_bars(bars: pd.DataFrame, bars_back: int) -> Optional[float]:
    if len(bars) < bars_back + 1:
        return None
    now = float(bars["close"].iloc[-1])
    past = float(bars["close"].iloc[-(bars_back + 1)])
    if past <= 0:
        return None
    return (now - past) / past


def compute_intraday_performance(bars: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Calculate 1h, 3h, and day (open-to-now) returns using 5-minute bars only."""
    result: Dict[str, Optional[float]] = {"ret_1h": None, "ret_3h": None, "ret_day": None}
    result["ret_1h"] = _returns_from_bars(bars, 12)   # 12 bars ~ 1 hour
    result["ret_3h"] = _returns_from_bars(bars, 36)   # 36 bars ~ 3 hours
    day_open = float(bars["open"].iloc[0])
    last = float(bars["close"].iloc[-1])
    if day_open > 0:
        result["ret_day"] = (last - day_open) / day_open
    return result


def compute_volume_ratio(bars: pd.DataFrame) -> Optional[float]:
    """Current bar volume vs average of last 20 bars."""
    if len(bars) < 21:
        return None
    current_vol = float(bars["volume"].iloc[-1])
    avg_vol = float(bars["volume"].iloc[-21:-1].mean())
    if avg_vol <= 0:
        return None
    return current_vol / avg_vol


def compute_trend(bars: pd.DataFrame) -> Tuple[bool, float, float]:
    ema21 = bars["close"].ewm(span=21, adjust=False).mean()
    ema50 = bars["close"].ewm(span=50, adjust=False).mean()
    last = len(bars) - 1
    strong_trend = ema21.iloc[last] > ema50.iloc[last] and bars["close"].iloc[last] > ema21.iloc[last]
    return strong_trend, float(ema21.iloc[last]), float(ema50.iloc[last])


def benchmark_performance(api: REST) -> Dict[str, float]:
    """Return intraday performance for benchmarks (SPY, QQQ) using 5-minute bars."""
    perf: Dict[str, float] = {}
    for sym in BENCHMARKS:
        bars = fetch_recent_bars(api, sym, limit=120)
        if bars is None or bars.empty:
            continue
        day_open = float(bars["open"].iloc[0])
        last = float(bars["close"].iloc[-1])
        perf[sym] = (last - day_open) / day_open if day_open > 0 else 0.0
    return perf


def build_trending_universe(api: REST) -> List[Dict]:
    """
    Fetch a universe of tradable symbols and rank by momentum + trend + volume.
    Uses only intraday 5-minute data to avoid timeframe mixing.
    """
    candidates: List[str] = []
    try:
        assets = api.list_assets(status="active", asset_class="us_equity")
        for asset in assets:
            if len(candidates) >= UNIVERSE_SCAN_LIMIT:
                break
            if not asset.tradable or not asset.shortable or not asset.easy_to_borrow:
                continue
            if asset.symbol is None or len(asset.symbol) > 4:
                continue
            candidates.append(asset.symbol)
    except Exception as exc:
        print(f"Warning: could not list assets, using empty universe: {exc}")
        return []

    ranked: List[Dict] = []
    for sym in candidates:
        bars = fetch_recent_bars(api, sym, limit=120)
        if bars is None or len(bars) < 60:
            continue

        perf = compute_intraday_performance(bars)
        vol_ratio = compute_volume_ratio(bars)
        strong_trend, ema21, ema50 = compute_trend(bars)
        if not strong_trend or vol_ratio is None or vol_ratio < VOLUME_ACCEL_THRESHOLD:
            continue

        ret_1h = perf["ret_1h"] or 0
        ret_3h = perf["ret_3h"] or 0
        ret_day = perf["ret_day"] or 0

        # Unified signal strength score: momentum + volume + trend slope
        trend_slope = (ema21 / ema50 - 1) if ema50 else 0
        score = (
            (ret_1h * 100) * 0.4
            + (ret_3h * 100) * 0.35
            + (ret_day * 100) * 0.25
            + (vol_ratio - 1) * 10
            + trend_slope * 200
        )

        ranked.append(
            {
                "symbol": sym,
                "score": score,
                "bars": bars,
                "ret_day": ret_day,
                "ret_1h": perf["ret_1h"],
                "ret_3h": perf["ret_3h"],
                "vol_ratio": vol_ratio,
                "ema21": ema21,
                "ema50": ema50,
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:TOP_TRENDING_LIMIT]

