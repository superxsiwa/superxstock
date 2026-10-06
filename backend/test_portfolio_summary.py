import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.all_models import Portfolio, Position, Stock, User
from app.services import get_portfolio_summary


class PortfolioSummaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.user = User(email="portfolio@example.com", password_hash="unused")
        self.db.add(self.user)
        self.db.flush()

        portfolio = Portfolio(
            user_id=self.user.id,
            initial_balance=100.0,
            current_cash=100.0,
        )
        self.db.add_all([
            Stock(symbol="AOT.BK", name="AOT", is_active=True),
            Stock(symbol="PTT.BK", name="PTT", is_active=True),
            portfolio,
        ])
        self.db.flush()
        self.db.add_all([
            Position(
                portfolio_id=portfolio.id,
                symbol="AOT",
                average_cost=10.0,
                quantity=5,
            ),
            Position(
                portfolio_id=portfolio.id,
                symbol="PTT.BK",
                average_cost=20.0,
                quantity=2,
            ),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_summary_marks_positions_to_current_price_and_sums_unrealized_pnl(self):
        with patch(
            "app.services.get_current_price_with_fallback",
            side_effect={"AOT.BK": 12.0, "PTT.BK": 18.0}.get,
        ) as get_current_price:
            result = get_portfolio_summary(self.db, self.user.id)

        self.assertEqual(result["total_value"], 196.0)
        self.assertEqual(result["unrealized_pnl"], 6.0)
        self.assertEqual(result["positions"], [
            {
                "symbol": "AOT",
                "quantity": 5,
                "avg_price": 10.0,
                "price": 12.0,
                "market_value": 60.0,
                "unrealized_pnl": 10.0,
                "price_available": True,
            },
            {
                "symbol": "PTT.BK",
                "quantity": 2,
                "avg_price": 20.0,
                "price": 18.0,
                "market_value": 36.0,
                "unrealized_pnl": -4.0,
                "price_available": True,
            },
        ])
        get_current_price.assert_any_call("AOT.BK")
        get_current_price.assert_any_call("PTT.BK")

    def test_unavailable_quote_is_explicit_and_invalidates_aggregate_valuation(self):
        with patch("app.services.get_current_price_with_fallback", return_value=None):
            result = get_portfolio_summary(self.db, self.user.id)

        self.assertIsNone(result["total_value"])
        self.assertIsNone(result["unrealized_pnl"])
        self.assertTrue(all(not position["price_available"] for position in result["positions"]))
        self.assertTrue(all(position["price"] is None for position in result["positions"]))
        self.assertTrue(all(position["market_value"] is None for position in result["positions"]))
        self.assertTrue(all(position["unrealized_pnl"] is None for position in result["positions"]))


if __name__ == "__main__":
    unittest.main()
