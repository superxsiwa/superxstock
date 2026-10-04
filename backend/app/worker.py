import os
import json
import redis
from celery import Celery
from app.data import fetch_real_market_data, THAI_SYMBOLS
from app.services import generate_signal_for_symbol

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
    
    for sym in THAI_SYMBOLS:
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
    
    return f"Scanned {len(scan_results)} symbols successfully."
