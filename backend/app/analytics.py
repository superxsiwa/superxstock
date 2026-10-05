from datetime import datetime
from zoneinfo import ZoneInfo


def calculate_signal_performance(signal_history, latest_prices):
    open_positions = {}
    closed_trades = []
    equity_curve = []
    realized_pnl = 0.0
    peak_pnl = 0.0
    max_drawdown = 0.0

    for signal in signal_history:
        symbol = signal["symbol"]
        recommendation = signal["recommendation"]
        if recommendation == "BUY":
            open_positions.setdefault(symbol, signal)
        elif recommendation == "SELL" and symbol in open_positions:
            buy_signal = open_positions.pop(symbol)
            pnl = round(signal["price"] - buy_signal["price"], 2)
            realized_pnl = round(realized_pnl + pnl, 2)
            peak_pnl = max(peak_pnl, realized_pnl)
            max_drawdown = max(max_drawdown, peak_pnl - realized_pnl)
            closed_trades.append({
                "symbol": symbol,
                "buy_date": buy_signal["signal_date"],
                "buy_price": buy_signal["price"],
                "sell_date": signal["signal_date"],
                "sell_price": signal["price"],
                "pnl_thb": pnl,
                "return_pct": round(pnl / buy_signal["price"] * 100, 2),
            })
            equity_curve.append({"date": signal["signal_date"], "pnl_thb": realized_pnl})

    open_trades = []
    unrealized_pnl = 0.0
    for symbol, buy_signal in open_positions.items():
        current_price = latest_prices.get(symbol, buy_signal["price"])
        pnl = round(current_price - buy_signal["price"], 2)
        unrealized_pnl = round(unrealized_pnl + pnl, 2)
        open_trades.append({
            "symbol": symbol,
            "buy_date": buy_signal["signal_date"],
            "buy_price": buy_signal["price"],
            "current_price": current_price,
            "pnl_thb": pnl,
            "return_pct": round(pnl / buy_signal["price"] * 100, 2),
        })

    total_pnl = round(realized_pnl + unrealized_pnl, 2)
    max_drawdown = round(max(max_drawdown, peak_pnl - total_pnl), 2)
    if open_trades:
        today = datetime.now(ZoneInfo("Asia/Bangkok")).date().isoformat()
        equity_curve.append({"date": today, "pnl_thb": total_pnl})

    closed_count = len(closed_trades)
    wins = sum(trade["pnl_thb"] > 0 for trade in closed_trades)
    return {
        "summary": {
            "total_signals": len(signal_history),
            "closed_trades": closed_count,
            "open_positions": len(open_trades),
            "win_rate_pct": round(wins / closed_count * 100, 2) if closed_count else 0.0,
            "realized_pnl_thb": realized_pnl,
            "unrealized_pnl_thb": unrealized_pnl,
            "total_pnl_thb": total_pnl,
            "max_drawdown_thb": max_drawdown,
        },
        "closed_trades": closed_trades,
        "open_trades": open_trades,
        "equity_curve": equity_curve,
    }