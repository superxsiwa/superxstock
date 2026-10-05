# SuperX Stock

A technical-analysis stock screening and paper trading MVP designed for daily stock opportunity discovery.

## Features
- Daily stock scan using RSI, MACD, EMA50, EMA90, CDC Action Zone, and volume filters
- Personal watchlists with LINE signal alerts
- Watchlist ranking and summary dashboard
- Paper trading portfolio simulation
- Basic trading-view-style dashboard layout

## Persistent configuration

Create a repository-root `.env` file once. Keep it across restarts: changing or losing this key invalidates existing JWTs. The file is ignored by Git and should not be committed.

```bash
if [ ! -f .env ]; then
	printf 'SECRET_KEY=%s\n' "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
	chmod 600 .env
fi
```

LINE alert credentials are encrypted with `SECRET_KEY`; keep this key persistent. LINE Notify has been discontinued, so alerts use the LINE Messaging API. Each user connects a LINE Messaging API channel by saving its channel access token and the LINE user ID for that channel's provider in **Alert Settings**. The LINE Official Account must be able to send push messages to that user (for example, the user must add the account as a friend). Use the same LINE provider for the channel and user ID.

The LINE channel access token is only shown when entered and is never returned by the API. Re-enter it if `SECRET_KEY` is changed or lost.

## Market data fallback

Yahoo Finance remains the primary provider. When it raises an error or returns no data, the app tries Alpha Vantage. Create a free Alpha Vantage API key and add it to the repository-root `.env` file to enable fallback:

```dotenv
ALPHA_VANTAGE_API_KEY=your_api_key
ALPHA_VANTAGE_SYMBOL_SUFFIX=.BKK
```

The symbol suffix is configurable because exchange suffixes vary by data vendor. If Alpha Vantage does not recognize a Thai symbol with `.BKK`, set the suffix to the format supported by your account. Without the key, the app continues to use Yahoo and logs when fallback is unavailable. Check Alpha Vantage's current request quotas before relying on it for repeated scans.

## Administrator access

Set `ADMIN_EMAIL` in the repository-root `.env` file to the email address of the administrator account. A newly registered account using that email is created as an admin; if the account already exists, restarting the API promotes it. Existing accounts otherwise remain `user`. Only admins can change system configuration or add/remove global stocks.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
set -a
. ./.env
set +a
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Then open:
- http://localhost:8000/

## Run with Docker Compose
Docker Compose automatically loads variables from the repository-root `.env` file. Set `DATA_PROVIDER=YAHOO` there to select the provider; YAHOO is currently the implemented provider. Compose defaults to YAHOO when the variable is omitted. It starts the API, Celery worker, and Celery Beat after TimescaleDB and Redis are healthy.

```bash
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
- GET /api/watchlist
- POST /api/watchlist
- DELETE /api/watchlist/{symbol}
- GET/PUT/DELETE /api/notifications/settings
- POST /api/notifications/test
- GET /api/analytics/signals

Signal analytics records actionable BUY/SELL signals from each daily scan. The backtest simulates one share per BUY, closes it on the next SELL signal for that symbol, marks open positions to the latest cached scan price, and reports realized/unrealized P/L and closed-trade win rate. History starts accumulating after deployment; it does not backfill earlier scans.

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
