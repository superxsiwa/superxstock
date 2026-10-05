import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import redis
from celery import Celery
from app.data import fetch_real_market_data
from app.services import generate_signal_for_symbol
from app.core.database import SessionLocal
from app.line_messaging import decrypt_channel_access_token, send_line_message
from app.models.all_models import SignalHistory, Stock, UserNotificationSettings, Watchlist

logger = logging.getLogger(__name__)

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

celery_app = Celery(
    "superx_tasks",
    broker=f"{redis_url}/0",
    backend=f"{redis_url}/1"
)
celery_app.conf.timezone = os.environ.get("CELERY_TIMEZONE", "Asia/Bangkok")

from celery.schedules import crontab

redis_client = redis.Redis.from_url(f"{redis_url}/2")

celery_app.conf.beat_schedule = {
    "scan-market-every-weekday-1730": {
        "task": "app.worker.fetch_and_scan_daily_market",
        "schedule": crontab(hour=17, minute=30, day_of_week="1-5"),
    },
}

@celery_app.task
def fetch_and_scan_daily_market():
    scan_results = []
    
    db = SessionLocal()
    try:
        active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
        symbols = [s.symbol for s in active_stocks]
    finally:
        db.close()
        
    for sym in symbols:
        history = fetch_real_market_data(sym)
        if not history:
            continue
            
        info = {
            "name": sym.replace(".BK", ""),
            "history": history,
            "change_pct": round(((history[-1]["close"] - history[-2]["close"]) / history[-2]["close"]) * 100, 2) if len(history) > 1 else 0,
        }
        
        signal = generate_signal_for_symbol(sym, info)
        scan_results.append(signal)
    
    scan_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Cache the result
    redis_client.setex("daily_scan_results", 86400, json.dumps({"stocks": scan_results}))
    try:
        latest_prices = json.loads(redis_client.get("latest_market_prices") or "{}")
    except (TypeError, ValueError):
        latest_prices = {}
    latest_prices.update({signal["symbol"]: signal["price"] for signal in scan_results})
    redis_client.set("latest_market_prices", json.dumps(latest_prices))
    try:
        _record_signal_history(scan_results)
    except Exception:
        logger.exception("Failed to persist signal history")
    _send_watchlist_alerts(scan_results)
    
    return f"Scanned {len(scan_results)} symbols successfully."


def _record_signal_history(scan_results):
    signal_date = datetime.now(ZoneInfo("Asia/Bangkok")).date()
    db = SessionLocal()
    try:
        for signal in scan_results:
            if signal["recommendation"] not in {"BUY", "SELL"}:
                continue
            exists = db.query(SignalHistory.id).filter_by(
                symbol=signal["symbol"],
                signal_date=signal_date,
            ).first()
            if exists is None:
                db.add(SignalHistory(
                    symbol=signal["symbol"],
                    recommendation=signal["recommendation"],
                    price=signal["price"],
                    signal_date=signal_date,
                ))
        db.commit()
    finally:
        db.close()


def _send_watchlist_alerts(scan_results):
    actionable_signals = {
        signal["symbol"]: signal
        for signal in scan_results
        if signal["recommendation"] in {"BUY", "SELL"}
    }
    if not actionable_signals:
        return

    db = SessionLocal()
    try:
        subscriptions = (
            db.query(Watchlist, UserNotificationSettings)
            .join(
                UserNotificationSettings,
                UserNotificationSettings.user_id == Watchlist.user_id,
            )
            .filter(Watchlist.symbol.in_(actionable_signals))
            .all()
        )
        recipients = [
            (
                watchlist.user_id,
                watchlist.symbol,
                settings.line_user_id,
                settings.encrypted_channel_access_token,
            )
            for watchlist, settings in subscriptions
        ]
    finally:
        db.close()

    for user_id, symbol, line_user_id, encrypted_token in recipients:
        signal = actionable_signals[symbol]
        message = (
            f"SuperX Stock signal: {signal['recommendation']} {symbol} "
            f"at {signal['price']:.2f} THB."
        )
        try:
            token = decrypt_channel_access_token(encrypted_token)
            send_line_message(token, line_user_id, message)
        except Exception:
            logger.exception("Failed to send LINE alert for user %s and %s", user_id, symbol)
