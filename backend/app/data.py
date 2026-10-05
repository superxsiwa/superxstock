from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

logger = logging.getLogger(__name__)


class MarketDataProviderError(RuntimeError):
    pass



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


class AlphaVantageProvider:
    def __init__(self, api_key: str | None = None, symbol_suffix: str | None = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
        self.symbol_suffix = (
            os.getenv("ALPHA_VANTAGE_SYMBOL_SUFFIX", ".BKK")
            if symbol_suffix is None
            else symbol_suffix
        )

    def _symbol(self, symbol: str) -> str:
        if symbol.upper().endswith(".BK"):
            return f"{symbol[:-3]}{self.symbol_suffix}"
        return symbol

    def _request(self, params: dict) -> dict:
        if not self.api_key:
            raise MarketDataProviderError("ALPHA_VANTAGE_API_KEY is not configured.")

        params["apikey"] = self.api_key
        request = Request(
            f"https://www.alphavantage.co/query?{urlencode(params)}",
            headers={"User-Agent": "SuperXStock/1.0"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.load(response)
        except HTTPError as error:
            raise MarketDataProviderError(f"Alpha Vantage returned HTTP {error.code}.") from error
        except (URLError, TimeoutError) as error:
            raise MarketDataProviderError("Could not connect to Alpha Vantage.") from error

        provider_message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        if provider_message:
            raise MarketDataProviderError(f"Alpha Vantage request failed: {provider_message}")
        return payload

    def fetch_ohlcv(
        self,
        symbol: str,
        *,
        period: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        payload = self._request({
            "function": "TIME_SERIES_DAILY",
            "symbol": self._symbol(symbol),
            "outputsize": "compact",
        })
        series_key = next((key for key in payload if "Time Series (Daily)" in key), None)
        if series_key is None:
            raise MarketDataProviderError("Alpha Vantage returned no daily time series.")

        data = pd.DataFrame.from_dict(payload[series_key], orient="index")
        data = data.rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "5. volume": "Volume",
        })
        data.index = pd.to_datetime(data.index)
        data = data.astype({"Open": float, "High": float, "Low": float, "Close": float, "Volume": float})
        data = data.sort_index()
        if start is not None:
            data = data[data.index >= pd.Timestamp(start.date())]
        if end is not None:
            data = data[data.index <= pd.Timestamp(end.date())]
        return data

    def get_current_price(self, symbol: str) -> float | None:
        history = self.fetch_ohlcv(symbol, period="1d")
        if history.empty:
            return None
        return float(history["Close"].iloc[-1])


def get_market_data_provider(provider_name: str | None = None) -> MarketDataProvider:
    selected_provider = (provider_name or os.getenv("DATA_PROVIDER", "YAHOO")).strip().upper()
    if selected_provider == "YAHOO":
        return YahooFinanceProvider()
    if selected_provider == "ALPHA_VANTAGE":
        return AlphaVantageProvider()
    raise ValueError(f"Unsupported market data provider: {selected_provider}")


def get_fallback_data_provider(primary_provider: MarketDataProvider) -> MarketDataProvider | None:
    if isinstance(primary_provider, YahooFinanceProvider):
        if not os.getenv("ALPHA_VANTAGE_API_KEY", "").strip():
            return None
        return AlphaVantageProvider()
    return YahooFinanceProvider()


def fetch_ohlcv_with_fallback(
    symbol: str,
    *,
    period: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    primary_provider = get_market_data_provider()
    fallback_provider = get_fallback_data_provider(primary_provider)
    try:
        history = primary_provider.fetch_ohlcv(symbol, period=period, start=start, end=end)
        if history is not None and not history.empty:
            return history
        raise MarketDataProviderError("Primary market data provider returned no data.")
    except Exception as primary_error:
        if fallback_provider is None:
            logger.warning(
                "Primary market data provider failed for %s and Alpha Vantage fallback is disabled: %s",
                symbol,
                primary_error,
            )
            return pd.DataFrame()
        logger.warning(
            "Primary market data provider failed for %s; trying %s: %s",
            symbol,
            type(fallback_provider).__name__,
            primary_error,
        )

    try:
        history = fallback_provider.fetch_ohlcv(symbol, period=period, start=start, end=end)
        if history is None or history.empty:
            raise MarketDataProviderError("Fallback market data provider returned no data.")
        logger.info("Market data for %s recovered with %s", symbol, type(fallback_provider).__name__)
        return history
    except Exception:
        logger.exception("Both market data providers failed for %s", symbol)
        return pd.DataFrame()


def get_current_price_with_fallback(symbol: str) -> float | None:
    primary_provider = get_market_data_provider()
    fallback_provider = get_fallback_data_provider(primary_provider)
    try:
        price = primary_provider.get_current_price(symbol)
        if price is not None:
            return price
        raise MarketDataProviderError("Primary market data provider returned no current price.")
    except Exception as primary_error:
        if fallback_provider is None:
            logger.warning(
                "Primary current-price provider failed for %s and Alpha Vantage fallback is disabled: %s",
                symbol,
                primary_error,
            )
            return None
        logger.warning(
            "Primary current-price provider failed for %s; trying %s: %s",
            symbol,
            type(fallback_provider).__name__,
            primary_error,
        )

    try:
        price = fallback_provider.get_current_price(symbol)
        if price is not None:
            return price
        raise MarketDataProviderError("Fallback provider returned no current price.")
    except Exception:
        logger.exception("Both current-price providers failed for %s", symbol)
        return None


def fetch_real_market_data(symbol: str, days: int = 90) -> list[dict]:
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    df = fetch_ohlcv_with_fallback(symbol, start=start_date, end=end_date)
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
    from app.core.database import SessionLocal
    from app.models.all_models import Stock

    db = SessionLocal()
    try:
        active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
        symbols = [s.symbol for s in active_stocks]
    finally:
        db.close()

    market = {}
    for sym in symbols:
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
