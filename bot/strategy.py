from typing import Dict, Optional, Tuple

import pandas as pd

from .config import EMA_FAST, EMA_SLOW, PULLBACK_TOLERANCE_PCT


def add_trend_columns(bars: pd.DataFrame) -> pd.DataFrame:
    enriched = bars.copy()
    enriched["ema21"] = enriched["close"].ewm(span=EMA_FAST, adjust=False).mean()
    enriched["ema50"] = enriched["close"].ewm(span=EMA_SLOW, adjust=False).mean()
    return enriched


def check_entry_signal(
    bars: Optional[pd.DataFrame],
    benchmark_perf: float,
    recent_metrics: Dict[str, Optional[float]],
    volume_ratio: Optional[float],
) -> Tuple[bool, Optional[float], str]:
    """
    Trend + pullback + break confirmation:
    - Price above EMA(21) and EMA(50)
    - EMA21 > EMA50 (uptrend)
    - Pullback near EMA21
    - Current close > previous candle high (confirmation)
    - Relative strength: stock day return > benchmark (SPY/QQQ)
    - Current volume > recent average (filter choppy moves)
    """
    if bars is None:
        return False, None, "No market data."

    if len(bars) < EMA_SLOW + 2:
        return False, None, "Not enough candles for EMAs."

    enriched = add_trend_columns(bars)
    last = enriched.iloc[-1]
    prev = enriched.iloc[-2]

    if last.ema21 <= last.ema50 or last.close <= last.ema50:
        return False, None, "Trend not strong enough."

    # Pullback check: prior candle low within tolerance of EMA21
    pullback_ok = abs(prev.low - prev.ema21) / prev.ema21 <= PULLBACK_TOLERANCE_PCT
    break_confirmation = last.close > prev.high

    if not (pullback_ok and break_confirmation):
        return False, None, "No pullback + break confirmation."

    if volume_ratio is None or volume_ratio < 1.2:
        return False, None, "Volume not above recent average."

    # Relative strength vs benchmark intraday performance
    day_ret = recent_metrics.get("ret_day") or 0.0
    if day_ret <= benchmark_perf:
        return False, None, "Fails relative strength vs benchmark."

    reason = (
        "Uptrend (21>50), pullback to 21, break above prior high, RS > benchmark, volume confirmed."
    )
    return True, float(last.close), reason

