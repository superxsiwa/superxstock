from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import scan_market, get_symbol_chart, get_portfolio_summary, process_trade
from app.schemas import TradeRequest, TradeResponse
import redis
import json
import os

router = APIRouter(prefix="/api", tags=["Frontend"])

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.Redis.from_url(f"{redis_url}/2")

@router.get("/scan")
def api_scan_market():
    # Attempt to fetch from cache (Phase 3)
    cached = redis_client.get("daily_scan_results")
    if cached:
        return json.loads(cached)
    
    # Fallback to direct synchronous calculation if cache is empty
    stocks = scan_market()
    return {"stocks": stocks}

@router.get("/charts/{symbol}")
def api_symbol_chart(symbol: str):
    try:
        history = get_symbol_chart(symbol)
        # Frontend expects chartData.candles
        candles = []
        for h in history:
            candles.append({"close": h["close"]})
        return {"candles": candles}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

from app.core.security import get_current_user
from app.models.all_models import User

@router.get("/portfolio")
def api_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_portfolio_summary(db, user_id=current_user.id)

@router.post("/paper-trade", response_model=TradeResponse)
def api_paper_trade(trade: TradeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        portfolio = process_trade(
            db=db,
            user_id=current_user.id,
            symbol=trade.symbol,
            action=trade.action,
            quantity=trade.quantity,
            price=trade.price
        )
        return TradeResponse(
            ok=True,
            message=f"{trade.action} {trade.quantity} {trade.symbol} successful",
            position=portfolio["positions"],
            portfolio=portfolio
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
