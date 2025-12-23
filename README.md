# Advanced Alpaca Trading Bot

An intelligent trading bot that automatically finds profitable stocks, manages multiple positions, and implements comprehensive risk management features.

## Features

### 🎯 Stock Selection & Scoring
- **Multi-factor scoring system** (0-100 scale) that evaluates stocks based on:
  - Moving Average Crossovers (Golden Cross detection)
  - EMA Trends
  - RSI Momentum indicators
  - Bollinger Bands position
  - Price momentum
- Automatically scans a watchlist and ranks stocks by potential profitability
- Only trades stocks that meet minimum score threshold

### 🛡️ Risk Management

#### Stop-Loss
- Automatically sets stop-loss orders at configurable percentage below entry price
- Default: 2% below entry price
- Monitors positions in real-time and executes stop-loss when triggered

#### Take-Profit
- Automatically sets take-profit targets at configurable percentage above entry price
- Default: 5% above entry price
- Locks in profits when target is reached

#### Position Sizing
- Calculates position size based on account balance
- Default: Uses 10% of account balance per position
- Maximum position size limit (default: 20% of account)
- Prevents over-leveraging

### 📊 Multiple Stock Trading
- Tracks and trades multiple stocks simultaneously
- Configurable maximum number of positions (default: 5)
- Independent position management for each stock
- Prevents duplicate positions

### ⏰ Trading Hours Validation
- Checks if market is open before executing trades
- Respects market hours (9:30 AM - 4:00 PM ET, weekdays only)
- Prevents after-hours trading mistakes

### 🧪 Backtesting
- Historical strategy testing framework
- Simulates trades on past data
- Calculates:
  - Total return percentage
  - Win/loss ratio
  - Number of trades
  - Performance metrics

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your `.env` file with Alpaca credentials:
```
APCA_API_KEY_ID="your_key_id"
APCA_API_SECRET_KEY="your_secret_key"
APCA_API_BASE_URL="https://paper-api.alpaca.markets"
```

## Configuration

Edit the configuration section in `trading_bot.py`:

```python
# Stock Selection
WATCHLIST = ["AAPL", "MSFT", "GOOGL", ...]  # Stocks to analyze
MAX_POSITIONS = 5  # Maximum simultaneous positions
MIN_SCORE = 60  # Minimum score to trade (0-100)

# Risk Management
STOP_LOSS_PCT = 2.0  # Stop loss percentage
TAKE_PROFIT_PCT = 5.0  # Take profit percentage
POSITION_SIZE_PCT = 10.0  # Position size as % of account
MAX_POSITION_SIZE_PCT = 20.0  # Maximum position size %

# System
CHECK_INTERVAL = 60  # Check interval in seconds
BACKTEST_MODE = False  # Set True for backtesting
```

## Usage

### Live Trading
```bash
python3 trading_bot.py
```

The bot will:
1. Check if market is open
2. Manage existing positions (check stop-loss/take-profit)
3. Scan watchlist for best opportunities
4. Execute buy orders for high-scoring stocks
5. Monitor all positions continuously

### Backtesting
Set `BACKTEST_MODE = True` in the config and modify the backtest function call:

```python
backtest('2024-01-01', '2024-12-31', 100000)
```

## How It Works

### Stock Scoring Algorithm
Each stock receives a score (0-100) based on:
- **30 points**: Golden Cross (short MA crosses above long MA)
- **20 points**: EMA uptrend
- **20 points**: Healthy RSI (30-70 range)
- **15 points**: Bollinger Bands position
- **15 points**: Positive price momentum

### Position Management
- Each position is tracked with entry price, stop-loss, and take-profit levels
- Positions are saved to `positions.json` for persistence
- Real-time monitoring checks prices against stop-loss/take-profit levels
- Automatic order execution when thresholds are hit

### Trading Logic
1. **Entry**: Buy when stock score exceeds minimum threshold and golden cross occurs
2. **Exit**: Sell when:
   - Stop-loss is triggered
   - Take-profit is reached
   - Exit signal (death cross) occurs

## Safety Features

- ✅ Paper trading support (default)
- ✅ Position size limits
- ✅ Stop-loss protection
- ✅ Market hours validation
- ✅ Maximum position limits
- ✅ Error handling and recovery

## Monitoring

The bot provides real-time output:
- Stock analysis and scoring
- Buy/sell signals
- Position status and P&L
- Stop-loss/take-profit triggers
- Error messages

## Files

- `trading_bot.py` - Main bot code
- `positions.json` - Tracks active positions (auto-generated)
- `.env` - API credentials (not in git)
- `requirements.txt` - Python dependencies

## Disclaimer

⚠️ **This bot is for educational purposes only. Trading involves risk. Always test with paper trading first. Past performance does not guarantee future results.**

## License

MIT License

