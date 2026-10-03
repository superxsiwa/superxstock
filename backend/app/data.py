from __future__ import annotations
from datetime import datetime, timedelta
import yfinance as yf

THAI_SYMBOLS = ["AOT.BK", "ADVANC.BK", "BDMS.BK", "CPALL.BK", "DELTA.BK", "KBANK.BK", "PTT.BK", "PTTEP.BK", "SCB.BK", "TRUE.BK"]

def fetch_real_market_data(symbol: str, days: int = 90):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    
    if df.empty:
        return []

    points = []
    for index, row in df.iterrows():
        points.append({
            "date": index.strftime("%Y-%m-%d"),
            "open": round(row['Open'], 2),
            "high": round(row['High'], 2),
            "low": round(row['Low'], 2),
            "close": round(row['Close'], 2),
            "volume": int(row['Volume']),
        })
        
    return points

def get_market_data():
    market = {}
    for sym in THAI_SYMBOLS:
        history = fetch_real_market_data(sym)
        if not history:
            continue
            
        market[sym.replace(".BK", "")] = {
            "name": sym.replace(".BK", ""),
            "history": history,
            "current_price": history[-1]["close"],
            "change_pct": round(((history[-1]["close"] - history[-2]["close"]) / history[-2]["close"]) * 100, 2) if len(history) > 1 else 0,
            "volume": history[-1]["volume"],
        }
    return market
