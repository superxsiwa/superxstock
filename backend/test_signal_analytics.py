import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analytics import calculate_signal_performance
from app.core.database import Base
from app.models.all_models import SignalHistory


class SignalAnalyticsTests(unittest.TestCase):
    def test_calculates_closed_and_open_trade_metrics(self):
        history = [
            {"symbol": "AOT.BK", "recommendation": "BUY", "price": 10.0, "signal_date": "2026-01-01"},
            {"symbol": "AOT.BK", "recommendation": "SELL", "price": 13.0, "signal_date": "2026-01-02"},
            {"symbol": "AOT.BK", "recommendation": "BUY", "price": 10.0, "signal_date": "2026-01-03"},
            {"symbol": "AOT.BK", "recommendation": "SELL", "price": 8.0, "signal_date": "2026-01-04"},
            {"symbol": "PTT.BK", "recommendation": "BUY", "price": 5.0, "signal_date": "2026-01-05"},
        ]

        result = calculate_signal_performance(history, {"PTT.BK": 7.0})

        self.assertEqual(result["summary"], {
            "total_signals": 5,
            "closed_trades": 2,
            "open_positions": 1,
            "win_rate_pct": 50.0,
            "realized_pnl_thb": 1.0,
            "unrealized_pnl_thb": 2.0,
            "total_pnl_thb": 3.0,
            "max_drawdown_thb": 2.0,
        })
        self.assertEqual(
            [point["pnl_thb"] for point in result["equity_curve"][:2]],
            [3.0, 1.0],
        )

    def test_ignores_sell_without_open_buy_and_keeps_first_open_buy(self):
        history = [
            {"symbol": "AOT.BK", "recommendation": "SELL", "price": 12.0, "signal_date": "2026-01-01"},
            {"symbol": "AOT.BK", "recommendation": "BUY", "price": 10.0, "signal_date": "2026-01-02"},
            {"symbol": "AOT.BK", "recommendation": "BUY", "price": 11.0, "signal_date": "2026-01-03"},
        ]

        result = calculate_signal_performance(history, {"AOT.BK": 12.0})

        self.assertEqual(result["summary"]["closed_trades"], 0)
        self.assertEqual(result["summary"]["win_rate_pct"], 0.0)
        self.assertEqual(result["open_trades"][0]["buy_price"], 10.0)
        self.assertEqual(result["summary"]["unrealized_pnl_thb"], 2.0)


class SignalHistoryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_worker_records_only_actionable_signals_once_per_symbol_and_day(self):
        from app import worker

        signals = [
            {"symbol": "AOT.BK", "recommendation": "BUY", "price": 42.0},
            {"symbol": "PTT.BK", "recommendation": "WATCH", "price": 35.0},
            {"symbol": "AOT.BK", "recommendation": "SELL", "price": 43.0},
        ]
        with patch.object(worker, "SessionLocal", self.Session):
            worker._record_signal_history(signals)
            worker._record_signal_history(signals)

        with self.Session() as db:
            records = db.query(SignalHistory).all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].symbol, "AOT.BK")
        self.assertEqual(records[0].recommendation, "BUY")
        self.assertEqual(records[0].price, 42.0)


if __name__ == "__main__":
    unittest.main()