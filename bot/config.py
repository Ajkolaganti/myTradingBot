import os
from datetime import time as dt_time

import pytz
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
from dotenv import load_dotenv

# Load environment variables early so a beginner does not have to pass flags.
load_dotenv()


def _get_float_env(name: str, default: float) -> float:
    try:
        val = os.getenv(name)
        return float(val) if val is not None else default
    except Exception:
        return default

# WARNING
# This bot is designed for *day trading* on paper trading only.
# Higher profit optimization increases drawdown risk.
# Always paper trade for 30+ days before going live.

# API configuration – paper trading only to keep real money safe.
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
API_BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
# Normalize to avoid accidental double "/v2" paths.
if API_BASE_URL.endswith("/"):
    API_BASE_URL = API_BASE_URL[:-1]
if API_BASE_URL.endswith("/v2"):
    API_BASE_URL = API_BASE_URL[:-3]

if not API_KEY or not API_SECRET:
    raise SystemExit(
        "Alpaca paper credentials are required. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in a .env file."
    )

if "paper-api" not in API_BASE_URL:
    # Hard block live trading endpoints to keep beginners from risking cash.
    raise SystemExit("This bot only supports Alpaca PAPER trading. Use https://paper-api.alpaca.markets.")

# Shared API client – safe because Alpaca SDK is thread-safe for simple use.
API = REST(
    key_id=API_KEY,
    secret_key=API_SECRET,
    base_url=API_BASE_URL,
    api_version="v2",
)

# Trading constants
TIMEFRAME = TimeFrame(5, TimeFrameUnit.Minute)  # Single timeframe by design
EMA_FAST = 21  # Pullback anchor
EMA_SLOW = 50  # Trend filter
UNIVERSE_SCAN_LIMIT = 40  # Max symbols to score per scan to avoid rate limits
VOLUME_ACCEL_THRESHOLD = 1.5  # 150% of recent average
PULLBACK_TOLERANCE_PCT = 0.003  # Price near EMA(21) within 0.3%
BENCHMARKS = ["SPY", "QQQ"]
TOP_TRENDING_LIMIT = 20  # Keep only top symbols each scan to stay performant
MAX_SPREAD_PCT = _get_float_env("MAX_SPREAD_PCT", 0.0015)   # 0.15% max bid-ask spread
MAX_SPREAD_ABS = _get_float_env("MAX_SPREAD_ABS", 0.05)     # or 5 cents max spread
MIN_BAR_DOLLAR_VOL = _get_float_env("MIN_BAR_DOLLAR_VOL", 2_000_000)  # Min $ volume on last bar
SYMBOL_COOLDOWN_MIN = 60        # Cooldown in minutes after a loss per symbol

# Risk controls
STOP_LOSS_PCT = 0.007        # Tighten stop to 0.7% below entry
TRAIL_TRIGGER_PCT = 0.01     # Start trailing after +1.0%
TRAIL_OFFSET_PCT = 0.012     # Trail 1.2% behind the high once active
RISK_PER_TRADE_PCT = 0.0075  # Default: risk 0.75% of equity per trade
AGGRESSIVE_RISK_PCT = 0.01   # Option B: 1.0% risk if user opts in
MAX_POSITION_PCT = 0.1       # Cap any position at 10% of equity
DAILY_LOSS_LIMIT = 0.02      # Stop for the day after -2%
MAX_TRADES_PER_SYMBOL = 1    # Once per symbol per day
INTRADAY_EQUITY_GUARD = 0.015  # Pause trading if drawdown hits -1.5% intraday
MAX_TOTAL_EXPOSURE_PCT = _get_float_env("MAX_TOTAL_EXPOSURE_PCT", 0.5)  # Cap total open exposure (e.g., 50% of equity)

# API server (for UI consumption)
API_HOST = os.getenv("BOT_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("BOT_API_PORT", "8000"))

# Time controls (Eastern Time)
TIMEZONE = pytz.timezone("US/Eastern")
TRADING_WINDOW_START = dt_time(9, 45)  # Avoid first 15 minutes
TRADING_WINDOW_END = dt_time(15, 30)   # Exit 30 minutes before close

# System behavior
CHECK_INTERVAL = 60  # seconds between checks
STATE_FILE = "bot_state.json"

