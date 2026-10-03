# SuperX Stock

A technical-analysis stock screening and paper trading MVP designed for daily stock opportunity discovery.

## Features
- Daily stock scan using RSI, MACD, EMA50, EMA90, CDC Action Zone, and volume filters
- Watchlist ranking and summary dashboard
- Paper trading portfolio simulation
- Basic trading-view-style dashboard layout

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:
- http://localhost:8000/

## API endpoints
- GET /api/health
- GET /api/scan
- GET /api/charts/{symbol}
- GET /api/portfolio
- POST /api/paper-trade
