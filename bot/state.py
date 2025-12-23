import copy
import json
import os
from datetime import date, datetime, time as dt_time
from typing import Dict, Optional

from .config import STATE_FILE, TIMEZONE

# Minimal persisted state so the bot survives restarts without tracking positions locally.
DEFAULT_STATE: Dict[str, object] = {
    "trading_day": None,       # ISO date string
    "start_equity": None,      # Equity at the start of the trading day
    "trades_executed": 0,      # Count of completed trades today (all symbols)
    "trading_halted": False,   # Set when daily loss limit is breached
    "traded_symbols": {},      # {symbol: True} once traded today
    "metrics": {               # Rolling intraday metrics
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "pnl_by_symbol": {},   # symbol -> cumulative pnl $
        "max_equity": None,
        "max_drawdown": 0.0,
    },
}


class BotState:
    """Lightweight day-level state (no position storage)."""

    def __init__(self) -> None:
        self.state = DEFAULT_STATE.copy()
        self.load()

    def load(self) -> None:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                for key in DEFAULT_STATE:
                    if key in stored:
                        self.state[key] = stored[key]
            except Exception:
                # Corrupt or unreadable state gets reset for safety.
                self.state = DEFAULT_STATE.copy()
        self.save()

    def save(self) -> None:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def reset_for_day(self, today: date, start_equity: float) -> None:
        """Reset counters when a new trading day starts."""
        today_str = today.isoformat()
        if self.state["trading_day"] != today_str:
            self.state["trading_day"] = today_str
            self.state["start_equity"] = start_equity
            self.state["trades_executed"] = 0
            self.state["trading_halted"] = False
            self.state["traded_symbols"] = {}
            self.state["metrics"] = copy.deepcopy(DEFAULT_STATE["metrics"])
            self.save()

    def record_trade(self) -> None:
        self.state["trades_executed"] += 1
        self.save()

    def record_symbol_trade(self, symbol: str) -> None:
        traded = self.state.get("traded_symbols", {})
        traded[symbol] = True
        self.state["traded_symbols"] = traded
        self.save()

    def has_traded_symbol(self, symbol: str) -> bool:
        return bool(self.state.get("traded_symbols", {}).get(symbol, False))

    def halt_trading(self) -> None:
        self.state["trading_halted"] = True
        self.save()

    def trading_day_start(self) -> Optional[datetime]:
        """Return the start-of-day timestamp in Eastern time."""
        day = self.state.get("trading_day")
        if not day:
            return None
        return datetime.combine(date.fromisoformat(day), dt_time(0, 0, tzinfo=TIMEZONE))

    @property
    def start_equity(self) -> Optional[float]:
        val = self.state.get("start_equity")
        return float(val) if val is not None else None

    @property
    def trades_executed(self) -> int:
        return int(self.state.get("trades_executed", 0))

    @property
    def trading_halted(self) -> bool:
        return bool(self.state.get("trading_halted", False))

    def update_metrics(self, symbol: str, pnl_dollars: float, entry: float, exit: float) -> None:
        m = self.state["metrics"]
        m["total_trades"] += 1
        if pnl_dollars >= 0:
            m["wins"] += 1
            m["gross_profit"] += pnl_dollars
        else:
            m["losses"] += 1
            m["gross_loss"] += pnl_dollars
        by_symbol = m.get("pnl_by_symbol", {})
        by_symbol[symbol] = by_symbol.get(symbol, 0.0) + pnl_dollars
        m["pnl_by_symbol"] = by_symbol
        self.state["metrics"] = m
        self.save()

        # Track last loss time for cooldowns
        if pnl_dollars < 0:
            traded = self.state.get("traded_symbols", {})
            traded[symbol] = {"last_loss_at": datetime.now(TIMEZONE).isoformat()}
            self.state["traded_symbols"] = traded
            self.save()

    def update_drawdown(self, equity: float) -> None:
        m = self.state["metrics"]
        if m.get("max_equity") is None or equity > m["max_equity"]:
            m["max_equity"] = equity
        if m["max_equity"]:
            dd = (equity - m["max_equity"]) / m["max_equity"]
            m["max_drawdown"] = min(m.get("max_drawdown", 0.0), dd)
        self.state["metrics"] = m
        self.save()

    def symbol_in_cooldown(self, symbol: str, cooldown_minutes: int) -> bool:
        traded = self.state.get("traded_symbols", {})
        info = traded.get(symbol)
        if not info or "last_loss_at" not in info:
            return False
        try:
            ts = datetime.fromisoformat(info["last_loss_at"]).astimezone(TIMEZONE)
        except Exception:
            return False
        delta = datetime.now(TIMEZONE) - ts
        return delta.total_seconds() < cooldown_minutes * 60

