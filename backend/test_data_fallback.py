import unittest
from datetime import datetime
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import Mock, patch

import pandas as pd

from app import data


class MarketDataFallbackTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame(
            {
                "Open": [10.0],
                "High": [12.0],
                "Low": [9.0],
                "Close": [11.0],
                "Volume": [1000.0],
            },
            index=pd.to_datetime(["2026-10-01"]),
        )

    def test_falls_back_when_primary_raises(self):
        primary = Mock()
        primary.fetch_ohlcv.side_effect = TimeoutError("Yahoo timed out")
        fallback = Mock()
        fallback.fetch_ohlcv.return_value = self.history

        with (
            patch.object(data, "get_market_data_provider", return_value=primary),
            patch.object(data, "get_fallback_data_provider", return_value=fallback),
        ):
            result = data.fetch_ohlcv_with_fallback("AOT.BK", start=datetime(2026, 9, 1))

        self.assertEqual(result["Close"].tolist(), [11.0])
        fallback.fetch_ohlcv.assert_called_once()

    def test_falls_back_when_primary_returns_empty_data(self):
        primary = Mock()
        primary.fetch_ohlcv.return_value = pd.DataFrame()
        fallback = Mock()
        fallback.fetch_ohlcv.return_value = self.history

        with (
            patch.object(data, "get_market_data_provider", return_value=primary),
            patch.object(data, "get_fallback_data_provider", return_value=fallback),
        ):
            result = data.fetch_ohlcv_with_fallback("AOT.BK")

        self.assertEqual(result["Close"].tolist(), [11.0])
        fallback.fetch_ohlcv.assert_called_once()

    def test_uses_fallback_for_current_price(self):
        primary = Mock()
        primary.get_current_price.return_value = None
        fallback = Mock()
        fallback.get_current_price.return_value = 11.0

        with (
            patch.object(data, "get_market_data_provider", return_value=primary),
            patch.object(data, "get_fallback_data_provider", return_value=fallback),
        ):
            price = data.get_current_price_with_fallback("AOT.BK")

        self.assertEqual(price, 11.0)
        fallback.get_current_price.assert_called_once_with("AOT.BK")

    def test_alpha_vantage_parses_ohlcv_and_maps_bangkok_suffix(self):
        provider = data.AlphaVantageProvider(api_key="test-key", symbol_suffix=".BKK")
        response = {
            "Time Series (Daily)": {
                "2026-10-02": {
                    "1. open": "10.00",
                    "2. high": "12.00",
                    "3. low": "9.00",
                    "4. close": "11.00",
                    "5. volume": "1000",
                },
                "2026-10-01": {
                    "1. open": "9.00",
                    "2. high": "11.00",
                    "3. low": "8.00",
                    "4. close": "10.00",
                    "5. volume": "900",
                },
            }
        }

        with patch.object(provider, "_request", return_value=response) as request:
            result = provider.fetch_ohlcv("AOT.BK")

        self.assertEqual(result.index.strftime("%Y-%m-%d").tolist(), ["2026-10-01", "2026-10-02"])
        self.assertEqual(result["Close"].tolist(), [10.0, 11.0])
        self.assertEqual(provider._symbol("AOT.BK"), "AOT.BKK")
        self.assertEqual(request.call_args.args[0]["symbol"], "AOT.BKK")

    def test_alpha_vantage_missing_key_fails_explicitly(self):
        provider = data.AlphaVantageProvider(api_key="", symbol_suffix=".BKK")
        with self.assertRaisesRegex(data.MarketDataProviderError, "not configured"):
            provider.fetch_ohlcv("AOT.BK")

    def test_eodhd_parses_ohlcv_and_maps_date_range(self):
        provider = data.EODHDProvider(api_token="test-token")
        response = [
            {
                "date": "2026-10-02",
                "open": 10.0,
                "high": 12.0,
                "low": 9.0,
                "close": 11.0,
                "volume": 1000,
            },
            {
                "date": "2026-10-01",
                "open": 9.0,
                "high": 11.0,
                "low": 8.0,
                "close": 10.0,
                "volume": 900,
            },
        ]

        with patch.object(provider, "_request", return_value=response) as request:
            result = provider.fetch_ohlcv(
                "AOT.BK",
                start=datetime(2026, 10, 1),
                end=datetime(2026, 10, 2),
            )

        self.assertEqual(result.index.strftime("%Y-%m-%d").tolist(), ["2026-10-01", "2026-10-02"])
        self.assertEqual(result["Close"].tolist(), [10.0, 11.0])
        self.assertEqual(
            request.call_args.args,
            (
                "eod/AOT.BK",
                {
                    "period": "d",
                    "order": "a",
                    "from": "2026-10-01",
                    "to": "2026-10-02",
                },
            ),
        )

    def test_eodhd_current_price_uses_delayed_quote_close(self):
        provider = data.EODHDProvider(api_token="test-token")
        with patch.object(provider, "_request", return_value={"close": 59.5}) as request:
            price = provider.get_current_price("AOT.BK")

        self.assertEqual(price, 59.5)
        self.assertEqual(request.call_args.args, ("real-time/AOT.BK", {}))

    def test_eodhd_caches_delayed_quote_across_stream_polls(self):
        data.EODHDProvider._quote_cache.clear()
        self.addCleanup(data.EODHDProvider._quote_cache.clear)
        provider = data.EODHDProvider(api_token="test-token")

        with (
            patch("app.data.monotonic", side_effect=[1000.0, 1001.0]),
            patch.object(provider, "_request", return_value={"close": 59.5}) as request,
        ):
            first_price = provider.get_current_price("AOT.BK")
            second_price = provider.get_current_price("AOT.BK")

        self.assertEqual((first_price, second_price), (59.5, 59.5))
        request.assert_called_once_with("real-time/AOT.BK", {})

    def test_eodhd_fallback_is_preferred_when_configured(self):
        primary = data.YahooFinanceProvider()
        with patch.dict(
            "os.environ",
            {
                "DATA_PROVIDER": "YAHOO",
                "EODHD_API_TOKEN": "test-token",
                "TWELVE_DATA_API_KEY": "test-key",
                "ALPHA_VANTAGE_API_KEY": "alpha-key",
            },
        ):
            fallback = data.get_fallback_data_provider(primary)

        self.assertIsInstance(fallback, data.EODHDProvider)

    def test_eodhd_missing_token_fails_explicitly(self):
        provider = data.EODHDProvider(api_token="")
        with self.assertRaisesRegex(data.MarketDataProviderError, "not configured"):
            provider.fetch_ohlcv("AOT.BK")

    def test_twelve_data_parses_ohlcv_and_maps_set_symbol(self):
        provider = data.TwelveDataProvider(api_key="test-key")
        response = {
            "values": [
                {
                    "datetime": "2026-10-02",
                    "open": "10.00",
                    "high": "12.00",
                    "low": "9.00",
                    "close": "11.00",
                    "volume": "1000",
                },
                {
                    "datetime": "2026-10-01",
                    "open": "9.00",
                    "high": "11.00",
                    "low": "8.00",
                    "close": "10.00",
                    "volume": "900",
                },
            ]
        }

        with patch.object(provider, "_request", return_value=response) as request:
            result = provider.fetch_ohlcv(
                "AOT.BK",
                start=datetime(2026, 10, 1),
                end=datetime(2026, 10, 2),
            )

        self.assertEqual(result.index.strftime("%Y-%m-%d").tolist(), ["2026-10-01", "2026-10-02"])
        self.assertEqual(result["Close"].tolist(), [10.0, 11.0])
        self.assertEqual(
            request.call_args.args,
            (
                "time_series",
                {
                    "symbol": "AOT",
                    "mic_code": "XBKK",
                    "interval": "1day",
                    "outputsize": "5000",
                    "order": "ASC",
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-02",
                },
            ),
        )

    def test_twelve_data_fallback_is_preferred_when_configured(self):
        primary = data.YahooFinanceProvider()
        with patch.dict(
            "os.environ",
            {
                "DATA_PROVIDER": "YAHOO",
                "TWELVE_DATA_API_KEY": "test-key",
                "ALPHA_VANTAGE_API_KEY": "alpha-key",
            },
        ):
            fallback = data.get_fallback_data_provider(primary)

        self.assertIsInstance(fallback, data.TwelveDataProvider)

    def test_twelve_data_current_price_uses_set_symbol(self):
        provider = data.TwelveDataProvider(api_key="test-key")
        with patch.object(provider, "_request", return_value={"price": "45.50"}) as request:
            price = provider.get_current_price("AOT.BK")

        self.assertEqual(price, 45.5)
        self.assertEqual(
            request.call_args.args,
            ("price", {"symbol": "AOT", "mic_code": "XBKK"}),
        )

    def test_twelve_data_missing_key_fails_explicitly(self):
        provider = data.TwelveDataProvider(api_key="")
        with self.assertRaisesRegex(data.MarketDataProviderError, "not configured"):
            provider.fetch_ohlcv("AOT.BK")

    def test_twelve_data_http_errors_include_provider_message(self):
        provider = data.TwelveDataProvider(api_key="test-key")
        error = HTTPError(
            "https://api.twelvedata.com/time_series",
            404,
            "Not Found",
            {},
            BytesIO(b'{"message":"AOT is available starting with Pro or Venture."}'),
        )

        with patch("app.data.urlopen", side_effect=error):
            with self.assertRaisesRegex(data.MarketDataProviderError, "Pro or Venture"):
                provider._request("time_series", {"symbol": "AOT"})

    def test_missing_alpha_key_keeps_primary_failure_graceful(self):
        primary = data.YahooFinanceProvider()
        with (
            patch.dict("os.environ", {"ALPHA_VANTAGE_API_KEY": ""}),
            patch.object(data, "get_market_data_provider", return_value=primary),
            patch.object(primary, "fetch_ohlcv", side_effect=TimeoutError("Yahoo timed out")),
            patch.object(data.AlphaVantageProvider, "fetch_ohlcv") as alpha_fetch,
        ):
            result = data.fetch_ohlcv_with_fallback("AOT.BK")

        self.assertTrue(result.empty)
        alpha_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()