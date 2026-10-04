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
pip install -r backend/requirements.txt
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Then open:
- http://localhost:8000/

## Run with Docker Compose
Set a stable JWT signing key before starting the services. Compose starts the API, Celery worker, and Celery Beat after TimescaleDB and Redis are healthy.

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose up --build
```

The API is available at http://localhost:8000/. Set `DATABASE_URL` or `REDIS_URL` in the environment to override the Compose defaults.

## Frontend development
The React/Vite dashboard proxies `/api` and `/ws` to the local backend. Start it in another terminal:

```bash
cd frontend
npm install
npm run dev
```

The production build is served by FastAPI at `/`; rebuild it with `cd frontend && npm run build`.

## API endpoints
- GET /api/health
- GET /api/scan
- GET /api/charts/{symbol}
- GET /api/portfolio
- POST /api/paper-trade

## Live market stream
Connect to `ws://localhost:8000/ws/market-stream`, then send the access token as the first message:

```json
{"type":"auth","token":"<access_token>"}
```

Authenticated clients receive one shared price update every 60 seconds while at least one client is connected:

```json
{
	"type": "price_update",
	"timestamp": "2026-10-04T10:30:00+00:00",
	"prices": [{"symbol": "AOT.BK", "price": 45.25}]
}
```

If no prices are available, the server sends `{"type":"error","code":"market_data_unavailable"}`. Missing or invalid credentials close the connection with code `4401`.
