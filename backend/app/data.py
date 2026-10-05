from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from time import monotonic
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


class EODHDProvider:
    _quote_cache: dict[str, tuple[float, float]] = {}
    _quote_cache_ttl_seconds = 15 * 60

    def __init__(self, api_token: str | None = None):
        self.api_token = (
            os.getenv("EODHD_API_TOKEN", "").strip()
            if api_token is None
            else api_token.strip()
        )

    def _request(self, endpoint: str, params: dict) -> object:
        if not self.api_token:
            raise MarketDataProviderError("EODHD_API_TOKEN is not configured.")

        query = {**params, "api_token": self.api_token, "fmt": "json"}
        request = Request(
            f"https://eodhd.com/api/{endpoint}?{urlencode(query)}",
            headers={"User-Agent": "SuperXStock/1.0"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.load(response)
        except HTTPError as error:
            try:
                body = error.read().decode("utf-8")
                error_payload = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_payload = {}
            if isinstance(error_payload, dict):
                message = error_payload.get("message") or error_payload.get("error")
            else:
                message = None
            detail = f": {message}" if message else "."
            raise MarketDataProviderError(f"EODHD returned HTTP {error.code}{detail}") from error
        except (URLError, TimeoutError) as error:
            raise MarketDataProviderError("Could not connect to EODHD.") from error

        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("error")
            if message:
                raise MarketDataProviderError(f"EODHD request failed: {message}")
        return payload

    def fetch_ohlcv(
        self,
        symbol: str,
        *,
        period: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        params = {"period": "d", "order": "a"}
        if start is not None:
            params["from"] = start.strftime("%Y-%m-%d")
        if end is not None:
            params["to"] = end.strftime("%Y-%m-%d")

        payload = self._request(f"eod/{symbol}", params)
        if not isinstance(payload, list) or not payload:
            raise MarketDataProviderError("EODHD returned no daily time series.")

        data = pd.DataFrame(payload)
        if "date" not in data:
            raise MarketDataProviderError("EODHD returned malformed daily time series.")
        data.index = pd.to_datetime(data.pop("date"))
        data = data.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        if not all(column in data.columns for column in required_columns):
            raise MarketDataProviderError("EODHD returned incomplete OHLCV data.")
        data = data[required_columns].apply(pd.to_numeric, errors="coerce")
        data = data.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
        if start is not None:
            data = data[data.index >= pd.Timestamp(start.date())]
        if end is not None:
            data = data[data.index <= pd.Timestamp(end.date())]
        return data

    def get_current_price(self, symbol: str) -> float | None:
        now = monotonic()
        cached_quote = self._quote_cache.get(symbol)
        if cached_quote and now - cached_quote[0] < self._quote_cache_ttl_seconds:
            return cached_quote[1]

        payload = self._request(f"real-time/{symbol}", {})
        if not isinstance(payload, dict):
            raise MarketDataProviderError("EODHD returned malformed live quote data.")
        price = payload.get("close")
        if price is None:
            return None
        price = float(price)
        self._quote_cache[symbol] = (now, price)
        return price


class TwelveDataProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = (
            os.getenv("TWELVE_DATA_API_KEY", "").strip()
            if api_key is None
            else api_key.strip()
        )

    def _request(self, endpoint: str, params: dict) -> dict:
        if not self.api_key:
            raise MarketDataProviderError("TWELVE_DATA_API_KEY is not configured.")

        query = {**params, "apikey": self.api_key}
        request = Request(
            f"https://api.twelvedata.com/{endpoint}?{urlencode(query)}",
            headers={"User-Agent": "SuperXStock/1.0"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.load(response)
        except HTTPError as error:
            try:
                error_payload = json.loads(error.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_payload = {}
            message = error_payload.get("message")
            detail = f": {message}" if message else "."
            raise MarketDataProviderError(
                f"Twelve Data returned HTTP {error.code}{detail}"
            ) from error
        except (URLError, TimeoutError) as error:
            raise MarketDataProviderError("Could not connect to Twelve Data.") from error

        if payload.get("status") == "error" or payload.get("code", 0) >= 400:
            message = payload.get("message", "request failed")
            raise MarketDataProviderError(f"Twelve Data request failed: {message}")
        return payload

    @staticmethod
    def _symbol_params(symbol: str) -> dict:
        if symbol.upper().endswith(".BK"):
            return {"symbol": symbol[:-3], "mic_code": "XBKK"}
        return {"symbol": symbol}

    def fetch_ohlcv(
        self,
        symbol: str,
        *,
        period: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        params = {
            **self._symbol_params(symbol),
            "interval": "1day",
            "outputsize": "5000",
            "order": "ASC",
        }
        if start is not None:
            params["start_date"] = start.strftime("%Y-%m-%d")
        if end is not None:
            params["end_date"] = end.strftime("%Y-%m-%d")
        payload = self._request("time_series", params)
        values = payload.get("values")
        if not values:
            raise MarketDataProviderError("Twelve Data returned no daily time series.")

        data = pd.DataFrame(values)
        if "datetime" not in data:
            raise MarketDataProviderError("Twelve Data returned malformed daily time series.")
        data.index = pd.to_datetime(data.pop("datetime"))
        data = data.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        if not all(column in data.columns for column in required_columns):
            raise MarketDataProviderError("Twelve Data returned incomplete OHLCV data.")
        data = data[required_columns].apply(pd.to_numeric, errors="coerce")
        data = data.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
        if start is not None:
            data = data[data.index >= pd.Timestamp(start.date())]
        if end is not None:
            data = data[data.index <= pd.Timestamp(end.date())]
        return data

    def get_current_price(self, symbol: str) -> float | None:
        payload = self._request("price", self._symbol_params(symbol))
        price = payload.get("price")
        if price is None:
            return None
        return float(price)


class AlphaVantageProvider:
    def __init__(self, api_key: str | None = None, symbol_suffix: str | None = None):
        self.api_key = (
            os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
            if api_key is None
            else api_key.strip()
        )
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
    if selected_provider == "EODHD":
        return EODHDProvider()
    if selected_provider == "TWELVE_DATA":
        return TwelveDataProvider()
    if selected_provider == "ALPHA_VANTAGE":
        return AlphaVantageProvider()
    raise ValueError(f"Unsupported market data provider: {selected_provider}")


def get_fallback_data_provider(primary_provider: MarketDataProvider) -> MarketDataProvider | None:
    if isinstance(primary_provider, YahooFinanceProvider):
        if os.getenv("EODHD_API_TOKEN", "").strip():
            return EODHDProvider()
        if os.getenv("TWELVE_DATA_API_KEY", "").strip():
            return TwelveDataProvider()
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
                "Primary market data provider failed for %s and no fallback provider is configured: %s",
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
                "Primary current-price provider failed for %s and no fallback provider is configured: %s",
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
