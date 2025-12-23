import threading
import time
from datetime import datetime

from . import data, execution, risk, strategy
from .api import run_api
from .config import (
    API,
    CHECK_INTERVAL,
    DAILY_LOSS_LIMIT,
    INTRADAY_EQUITY_GUARD,
    MAX_TOTAL_EXPOSURE_PCT,
    SYMBOL_COOLDOWN_MIN,
    TIMEZONE,
    TRADING_WINDOW_END,
)
from .shared import LOG_BUFFER, SNAPSHOTS
from .state import BotState


def log_status(message: str) -> None:
    ts = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    LOG_BUFFER.add("INFO", line)


def display_dashboard(state: BotState, equity: float) -> None:
    m = state.state["metrics"]
    total = m["total_trades"]
    wins = m["wins"]
    losses = m["losses"]
    win_rate = (wins / total * 100) if total else 0.0
    avg_win = (m["gross_profit"] / wins) if wins else 0.0
    avg_loss = (m["gross_loss"] / losses) if losses else 0.0
    loss_rate = (losses / total) if total else 0.0
    expectancy = (win_rate / 100) * avg_win + loss_rate * avg_loss
    profit_factor = (m["gross_profit"] / abs(m["gross_loss"])) if m["gross_loss"] else float("inf") if wins else 0.0
    dd_pct = m["max_drawdown"] * 100 if m.get("max_drawdown") else 0.0

    print("=" * 60)
    print("PERFORMANCE DASHBOARD")
    print(f"Equity: ${equity:,.2f}")
    print(f"Trades: {total} | Wins: {wins} | Losses: {losses} | Win rate: {win_rate:.1f}%")
    print(f"Avg win: ${avg_win:.2f} | Avg loss: ${avg_loss:.2f} | Expectancy: ${expectancy:.2f}")
    print(f"Profit factor: {profit_factor:.2f} | Max drawdown: {dd_pct:.2f}%")
    if m.get("pnl_by_symbol"):
        print("P/L by symbol:")
        for sym, pnl in m["pnl_by_symbol"].items():
            print(f"  {sym}: ${pnl:.2f}")
    print("=" * 60)

    SNAPSHOTS.update(
        metrics={
            "equity": equity,
            "trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expectancy": expectancy,
            "profit_factor": profit_factor,
            "max_drawdown_pct": dd_pct,
            "pnl_by_symbol": m.get("pnl_by_symbol", {}),
        }
    )


def trading_loop() -> None:
    state = BotState()

    while True:
        now = datetime.now(TIMEZONE)
        try:
            account = API.get_account()
            equity = float(account.equity)
        except Exception as exc:
            log_status(f"Could not reach Alpaca API: {exc}")
            time.sleep(CHECK_INTERVAL)
            continue

        state.update_drawdown(equity)
        state.reset_for_day(now.date(), equity)
        day_start = state.trading_day_start()

        # Halt if daily loss exceeds limit or intraday guard trips.
        if state.start_equity:
            daily_change = (equity - state.start_equity) / state.start_equity
            if daily_change <= -INTRADAY_EQUITY_GUARD and not state.trading_halted:
                log_status(f"Equity guard {-INTRADAY_EQUITY_GUARD*100:.2f}% hit. Pausing entries.")
                state.halt_trading()
            if daily_change <= -DAILY_LOSS_LIMIT:
                if not state.trading_halted:
                    log_status(f"Daily loss {daily_change * 100:.2f}% hit. Halting for the day.")
                    state.halt_trading()
                execution.close_all_positions(API, reason="Daily loss limit reached")

        # Always exit before the cutoff.
        if now.time() >= TRADING_WINDOW_END:
            execution.close_all_positions(API, reason="End of trading window")
            state.halt_trading()
            time.sleep(CHECK_INTERVAL)
            continue

        if not data.is_market_open(API):
            log_status("Market closed. Waiting...")
            time.sleep(CHECK_INTERVAL)
            continue

        if not data.within_trading_window(now):
            log_status("Outside trading window. Waiting...")
            time.sleep(CHECK_INTERVAL)
            continue

        # Manage existing positions first.
        try:
            positions = API.list_positions()
        except Exception as exc:
            log_status(f"Could not list positions: {exc}")
            time.sleep(CHECK_INTERVAL)
            continue

        for pos in positions:
            bars = data.fetch_recent_bars(API, pos.symbol, limit=150)
            if bars is None:
                continue
            exit_info = execution.manage_open_position(API, pos.symbol, bars, day_start)
            if exit_info:
                reason, entry_px, exit_px, qty = exit_info
                pnl = (exit_px - entry_px) * qty
                state.update_metrics(pos.symbol, pnl, entry_px, exit_px)
                log_status(f"Exited {pos.symbol} via {reason} | Entry: {entry_px:.2f} Exit: {exit_px:.2f} PnL: ${pnl:.2f}")

        # If trading is halted, skip entries.
        if state.trading_halted:
            log_status("Trading halted for safety. Standing by.")
            display_dashboard(state, equity)
            time.sleep(CHECK_INTERVAL)
            continue

        # Build trending universe.
        benchmarks = data.benchmark_performance(API)
        benchmark_perf = max(benchmarks.values()) if benchmarks else 0.0
        universe = data.build_trending_universe(API)
        SNAPSHOTS.update(
            status={
                "timestamp": datetime.now(TIMEZONE).isoformat(),
                "trading_halted": state.trading_halted,
                "benchmark_perf": benchmark_perf,
            },
            candidates=[
                {
                    "symbol": c["symbol"],
                    "score": c["score"],
                    "ret_day": c.get("ret_day"),
                    "ret_1h": c.get("ret_1h"),
                    "ret_3h": c.get("ret_3h"),
                    "vol_ratio": c.get("vol_ratio"),
                }
                for c in universe
            ],
        )

        if not universe:
            log_status("No trending symbols found this cycle.")
            time.sleep(CHECK_INTERVAL)
            continue

        for candidate in universe:
            symbol = candidate["symbol"]
            if state.has_traded_symbol(symbol):
                continue

            # Skip if already holding the symbol.
            if execution.get_position(API, symbol):
                continue

            if state.symbol_in_cooldown(symbol, SYMBOL_COOLDOWN_MIN):
                log_status(f"{symbol}: in cooldown after loss; skipping.")
                continue

            bars = candidate["bars"]
            metrics = {
                "ret_day": candidate.get("ret_day"),
                "ret_1h": candidate.get("ret_1h"),
                "ret_3h": candidate.get("ret_3h"),
            }

            signal, entry_price, reason = strategy.check_entry_signal(
                bars, benchmark_perf, metrics, candidate.get("vol_ratio")
            )
            if not signal or entry_price is None:
                continue

            # Liquidity and spread guards
            if not data.bar_meets_dollar_volume(bars):
                log_status(f"{symbol}: skipped, low dollar volume on last bar.")
                continue
            if not data.latest_spread_ok(API, symbol):
                log_status(f"{symbol}: skipped, spread too wide.")
                continue

            if execution.has_open_order(API, symbol):
                log_status(f"{symbol}: open order exists; skipping new order.")
                continue

            # Exposure cap: do not exceed total open exposure limit.
            try:
                positions = API.list_positions()
            except Exception:
                positions = []
            current_exposure = sum(float(p.market_value) for p in positions)
            prospective_value = qty * entry_price
            if (current_exposure + prospective_value) > (equity * MAX_TOTAL_EXPOSURE_PCT):
                log_status(f"{symbol}: skipping, exposure cap reached ({MAX_TOTAL_EXPOSURE_PCT*100:.0f}% of equity).")
                continue

            qty = risk.calculate_position_size(equity, entry_price)
            if qty <= 0:
                log_status(f"{symbol}: position size zero (risk cap).")
                continue

            stop_price = risk.calculate_stop_price(entry_price)
            log_status(
                f"BUY {symbol} | Qty: {qty} | Entry: {entry_price:.2f} | Stop: {stop_price:.2f} | "
                f"Score: {candidate['score']:.2f} | Reason: {reason}"
            )

            try:
                execution.submit_market_buy(API, symbol, qty)
                state.record_trade()
                state.record_symbol_trade(symbol)
            except Exception as exc:
                log_status(f"{symbol}: order placement failed: {exc}")
                continue

        display_dashboard(state, equity)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    log_status("Trend pullback bot started (paper only, intraday).")
    log_status(
        "Rules: 5-min bars, trend (21>50), pullback to 21, break prior high, RS > SPY/QQQ; "
        "0.8% stop, 1.5% trail after +1.0%; risk 0.75% per trade; intraday only."
    )
    log_status("Warning: profits are NOT guaranteed. Higher profit focus increases drawdown risk.")
    # Run API server in background thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    trading_loop()

