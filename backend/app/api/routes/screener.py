from fastapi import APIRouter, HTTPException
from app.core.engine import fetch_and_analyze
import math

router = APIRouter(prefix="/api/screener", tags=["Screener"])

@router.get("/analyze/{symbol}")
def analyze_stock(symbol: str, period: str = "1y"):
    df = fetch_and_analyze(symbol, period)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Stock data not found or invalid symbol")
    
    # Get the latest row (most recent trading day)
    latest = df.iloc[-1]
    
    # Find MACD columns dynamically as pandas-ta names can vary slightly
    macd_col = [c for c in df.columns if c.startswith('MACD_')][0]
    macds_col = [c for c in df.columns if c.startswith('MACDs_')][0]
    macdh_col = [c for c in df.columns if c.startswith('MACDh_')][0]

    # Construct clean response
    response = {
        "symbol": symbol.upper(),
        "date": str(df.index[-1].date()),
        "close_price": float(latest['Close']),
        "volume": int(latest['Volume']),
        "indicators": {
            "rsi": float(latest['RSI']),
            "macd": float(latest[macd_col]),
            "macd_signal": float(latest[macds_col]),
            "macd_hist": float(latest[macdh_col]),
            "ema_50": float(latest['EMA_50']),
            "ema_90": float(latest['EMA_90'])
        },
        "cdc_action_zone": {
            "trend": latest['CDC_Trend'],
            "signal": latest['Signal']
        }
    }

    return response
