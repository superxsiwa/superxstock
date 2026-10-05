import unittest
from datetime import datetime
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