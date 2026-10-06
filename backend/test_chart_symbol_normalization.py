import unittest
from unittest.mock import patch

from app.services import get_symbol_chart


class SymbolChartTests(unittest.TestCase):
    def test_chart_lookup_accepts_bare_and_exchange_suffixed_symbols(self):
        history = [{"close": 2.92}]
        market = {"IRPC": {"history": history}}

        with patch("app.services.get_market_data", return_value=market):
            self.assertEqual(get_symbol_chart("IRPC.BK"), history)
            self.assertEqual(get_symbol_chart("irpc"), history)

    def test_missing_symbol_keeps_the_requested_symbol_in_error(self):
        with patch("app.services.get_market_data", return_value={}):
            with self.assertRaisesRegex(ValueError, "Symbol IRPC.BK not found"):
                get_symbol_chart("IRPC.BK")


if __name__ == "__main__":
    unittest.main()
