from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Protocol

import pandas as pd

THAI_SYMBOLS = ["AOT.BK", "ADVANC.BK", "BDMS.BK", "CPALL.BK", "DELTA.BK", "KBANK.BK", "PTT.BK", "PTTEP.BK", "SCB.BK", "TRUE.BK"]


class MarketDataProvider(Protocol):
    def fetch_ohlcv(
        self,
        symbol: str,
        *,
        period: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame: ...

    def get_current_price(self, symbol: str) -> float | None: ...


class YahooFinanceProvider:
    def fetch_ohlcv(
        self,
        symbol: str,
        *,
        period: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        if period is not None:
            return ticker.history(period=period)
        return ticker.history(start=start, end=end)

    def get_current_price(self, symbol: str) -> float | None:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        try:
            price = ticker.fast_info.get("last_price")
        except Exception:
            price = None

        if price is not None and pd.notna(price):
            return float(price)

        history = ticker.history(period="1d")
        if history.empty:
            return None
        return float(history["Close"].iloc[-1])


def get_market_data_provider(provider_name: str | None = None) -> MarketDataProvider:
    selected_provider = (provider_name or os.getenv("DATA_PROVIDER", "YAHOO")).strip().upper()
    if selected_provider == "YAHOO":
        return YahooFinanceProvider()
    raise ValueError(f"Unsupported market data provider: {selected_provider}")


def fetch_real_market_data(symbol: str, days: int = 90) -> list[dict]:
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    df = get_market_data_provider().fetch_ohlcv(symbol, start=start_date, end=end_date)
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
