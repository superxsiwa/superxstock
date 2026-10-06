# SuperX Stock

A technical-analysis stock screening and paper trading MVP designed for daily stock opportunity discovery.

## Features
- Daily stock scan using RSI, MACD, EMA50, EMA90, CDC Action Zone, and volume filters
- Personal watchlists with LINE signal alerts
- Watchlist ranking and summary dashboard
- Paper trading portfolio simulation
- Current-price portfolio valuation and unrealized P/L for Thai-stock positions (THB)
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

Yahoo Finance remains the primary provider. When it raises an error or returns no data, the app uses EODHD if its token is configured; otherwise, it uses Twelve Data, then Alpha Vantage. EODHD lists Airports of Thailand as `AOT.BK` on its Thailand `BK` exchange. Add an EODHD API token to the repository-root `.env` file:

```dotenv
EODHD_API_TOKEN=your_api_token
TWELVE_DATA_API_KEY=your_api_key
ALPHA_VANTAGE_API_KEY=your_api_key
ALPHA_VANTAGE_SYMBOL_SUFFIX=.BKK
```

EODHD returns daily EOD history and a global live quote delayed by about 15-20 minutes. The quote is cached for 15 minutes because the market stream polls every 60 seconds. Its free plan has a 20 API-call daily limit and one year of history; each symbol costs one call, so a full fallback scan of 50 stocks can exceed the free quota if Yahoo is unavailable. Verify your account's AOT access and current limits in the [EODHD dashboard](https://eodhd.com/cp/dashboard). EODHD has a [free signup](https://eodhd.com/register).

Twelve Data account plans control which symbols and data are accessible; its API reports AOT time-series access as Pro/Venture-only. A public demo key can find AOT but does not grant time-series access. Alpha Vantage's symbol suffix is configurable because exchange suffixes vary by vendor, though Thai symbols may not be available for every account. Without any fallback key, the app continues to use Yahoo and logs when fallback is unavailable.

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
Docker Compose automatically loads variables from the repository-root `.env` file. `DATA_PROVIDER` defaults to `YAHOO`; `YAHOO`, `EODHD`, `TWELVE_DATA`, and `ALPHA_VANTAGE` are supported primary providers. Optional fallback tokens are passed to the API, Celery worker, and Celery Beat. Compose starts these services after TimescaleDB and Redis are healthy.

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

`GET /api/portfolio` includes a current quote, market value, and unrealized P/L for each open Thai-stock position, plus aggregate unrealized P/L. Values are in THB. If a current quote is unavailable, that position is marked unavailable and aggregate valuation is omitted rather than substituted with cost basis. Multiple portfolios, FX conversion, journals, dividends, and AI indicator capture are outside this MVP slice.

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
