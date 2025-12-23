# Setup Guide - What You Need to Do

## ✅ Step 1: Verify Your Setup

Your dependencies are already installed! ✅
Your `.env` file is configured! ✅

## 📋 Step 2: Review and Customize Configuration

Open `trading_bot.py` and review the configuration section (lines 15-40). Customize these settings:

### Essential Settings to Review:

```python
# Stock Selection
WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "AMD", "INTC"]
MAX_POSITIONS = 5  # How many stocks to trade at once
MIN_SCORE = 60  # Minimum score (0-100) to buy a stock

# Risk Management - ADJUST THESE CAREFULLY!
STOP_LOSS_PCT = 2.0  # Stop loss at 2% below entry (e.g., buy at $100, stop at $98)
TAKE_PROFIT_PCT = 5.0  # Take profit at 5% above entry (e.g., buy at $100, sell at $105)
POSITION_SIZE_PCT = 10.0  # Use 10% of account per position
MAX_POSITION_SIZE_PCT = 20.0  # Never use more than 20% per position

# Trading Hours (already set for US market)
MARKET_OPEN = dt_time(9, 30)  # 9:30 AM ET
MARKET_CLOSE = dt_time(16, 0)  # 4:00 PM ET

# System
CHECK_INTERVAL = 60  # Check every 60 seconds
BACKTEST_MODE = False  # Keep False for live trading
```

### ⚠️ Important Risk Management Notes:

- **Start Conservative**: Lower `POSITION_SIZE_PCT` to 5% when starting
- **Test First**: Always test with paper trading (you're already using paper API)
- **Adjust Stop-Loss**: 2% might be tight for volatile stocks - consider 3-5%
- **Watchlist**: Start with 3-5 stocks you know well, not 10

## 🚀 Step 3: Test Run (Recommended First Steps)

### Option A: Dry Run (Check What It Would Do)
1. Set `MIN_SCORE = 100` (very high, won't buy anything)
2. Run: `python3 trading_bot.py`
3. Watch it analyze stocks without buying
4. See the scoring system in action

### Option B: Start Small
1. Set `MAX_POSITIONS = 1` (trade only 1 stock at a time)
2. Set `POSITION_SIZE_PCT = 5.0` (use only 5% of account)
3. Set `MIN_SCORE = 70` (only buy very strong signals)
4. Run: `python3 trading_bot.py`

## 📊 Step 4: Monitor Your Bot

When running, the bot will show:

```
🔍 Analyzing 10 stocks...
  ✓ AAPL: Score 75.2/100 - Golden Cross, EMA Uptrend, RSI Healthy
  ✓ MSFT: Score 68.5/100 - Above MA, Positive Momentum

💰 BUY Signal: AAPL (Score: 75.2)
   Price: $150.25 | Quantity: 3 | Position Size: $450.75
✅ Order filled: AAPL @ $150.30

📊 Managing 1 existing positions...
  AAPL: $151.20 | Entry: $150.30 | P&L: +0.60%
```

## 🛡️ Step 5: Safety Checklist

Before going live, ensure:

- [ ] ✅ Using **Paper Trading API** (you are - `paper-api.alpaca.markets`)
- [ ] ✅ Tested with small position sizes
- [ ] ✅ Understand stop-loss and take-profit levels
- [ ] ✅ Know which stocks are in your watchlist
- [ ] ✅ Have sufficient account balance (check Alpaca dashboard)
- [ ] ✅ Bot runs during market hours (9:30 AM - 4:00 PM ET, weekdays)

## 🔧 Step 6: Common Customizations

### Change Watchlist
```python
WATCHLIST = ["AAPL", "TSLA"]  # Only trade these 2 stocks
```

### More Conservative (Safer)
```python
MAX_POSITIONS = 2
POSITION_SIZE_PCT = 5.0
MIN_SCORE = 70
STOP_LOSS_PCT = 3.0  # Wider stop-loss
```

### More Aggressive
```python
MAX_POSITIONS = 10
POSITION_SIZE_PCT = 15.0
MIN_SCORE = 50
STOP_LOSS_PCT = 1.5  # Tighter stop-loss
```

## 📱 Step 7: Running the Bot

### Start the Bot:
```bash
python3 trading_bot.py
```

### Stop the Bot:
Press `Ctrl + C` (will safely stop)

### Run in Background (Optional):
```bash
nohup python3 trading_bot.py > bot.log 2>&1 &
```

## 🧪 Step 8: Test Backtesting (Optional)

To test the strategy on historical data:

1. Edit `trading_bot.py`:
   - Set `BACKTEST_MODE = True`
   - Modify the backtest call at the bottom

2. Run:
```bash
python3 trading_bot.py
```

This will simulate trades on past data and show performance metrics.

## ⚠️ Important Reminders

1. **Paper Trading First**: You're already using paper trading - good! Test thoroughly before switching to live.

2. **Market Hours**: Bot only trades during market hours (9:30 AM - 4:00 PM ET, weekdays)

3. **Account Balance**: Make sure your Alpaca paper account has sufficient buying power

4. **Monitor Regularly**: Check the bot output regularly, especially when starting

5. **Start Small**: Begin with 1-2 positions and small position sizes

6. **Understand the Strategy**: The bot uses moving average crossovers - learn how this works

## 🆘 Troubleshooting

### Bot says "Market is closed"
- Normal outside trading hours (9:30 AM - 4:00 PM ET, weekdays)
- Wait for market to open or run during trading hours

### "Insufficient buying power"
- Your account doesn't have enough funds
- Lower `POSITION_SIZE_PCT` or add funds to paper account

### "Not enough data points"
- Stock doesn't have enough historical data
- Remove it from watchlist or wait

### Bot not buying stocks
- Check `MIN_SCORE` - might be too high
- Check if stocks meet scoring criteria
- Verify market is open

## 📞 Next Steps

1. **Review the configuration** in `trading_bot.py`
2. **Start with conservative settings** (1 position, 5% size)
3. **Run the bot** and watch it work
4. **Monitor for a few days** before increasing position sizes
5. **Adjust settings** based on performance

## 🎯 Quick Start Command

```bash
# Make sure you're in the right directory
cd "/Users/aj/Desktop/New Folder With Items/Study Material/PythonAlpacaTradingBot"

# Run the bot
python3 trading_bot.py
```

That's it! The bot is ready to run. Start with conservative settings and adjust as you learn how it performs.

