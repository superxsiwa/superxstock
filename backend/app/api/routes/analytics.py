import json
import os

import redis
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics import calculate_signal_performance
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.all_models import SignalHistory, User

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)],
)

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.Redis.from_url(f"{redis_url}/2")


@router.get("/signals")
def get_signal_analytics(db: Session = Depends(get_db)):
    history = db.query(SignalHistory).order_by(
        SignalHistory.signal_date,
        SignalHistory.id,
    ).all()
    signals = [
        {
            "symbol": signal.symbol,
            "recommendation": signal.recommendation,
            "price": signal.price,
            "signal_date": signal.signal_date.isoformat(),
        }
        for signal in history
    ]

    latest_prices = {}
    cached_prices = redis_client.get("latest_market_prices")
    if cached_prices:
        try:
            latest_prices = json.loads(cached_prices)
        except (TypeError, ValueError, KeyError):
            latest_prices = {}
    else:
        cached_scan = redis_client.get("daily_scan_results")
        if cached_scan:
            try:
                latest_prices = {
                    stock["symbol"]: stock["price"]
                    for stock in json.loads(cached_scan).get("stocks", [])
                }
            except (TypeError, ValueError, KeyError):
                latest_prices = {}

    return calculate_signal_performance(signals, latest_prices)