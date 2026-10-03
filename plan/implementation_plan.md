## Refactor SuperX Stock to Production-Ready Architecture

The goal of this plan is to transform the SuperX Stock MVP from a prototype (using in-memory state and mock data) into a robust, scalable system. We will implement database persistence, real market data ingestion, and asynchronous background processing.

## User Review Required

> [!WARNING]
> **Data Loss Warning:** Moving from in-memory to a real database means any existing mock portfolio data generated in memory will be gone. We will start fresh with an empty database.

> [!IMPORTANT]
> **Dependency Additions:** We will add `yfinance` (for real stock data), `celery`, and `redis` (for background jobs) to your `requirements.txt`.

## Open Questions

> [!NOTE]
> 1. **Authentication:** The current system lacks user authentication. Anyone can hit the `/api/paper-trade` endpoint. Should we include JWT Authentication (Login/Register) in this implementation phase, or defer it to a later time?
> 2. **Data Scope:** I plan to use a predefined list of Thai stocks (e.g., AOT.BK, PTT.BK) for `yfinance`. Do you have a specific list of stock symbols you want to track, or is a generic top 10 list fine for now?

## Proposed Changes

---
### Infrastructure & Dependencies
We need to update the dependencies to support the new architecture.

#### [MODIFY] backend/requirements.txt
```diff
 fastapi==0.111.0
 uvicorn[standard]==0.30.1
 pandas==2.2.3
 numpy==2.1.3
 python-multipart==0.0.1
+sqlalchemy==2.0.30
+psycopg2-binary==2.9.9
+yfinance==0.2.40
+celery==5.4.0
+redis==5.0.4
```

---
### Phase 1: Database Persistence (Repository Layer)
We will refactor the core trading logic to interact with the database instead of the in-memory `PORTFOLIO` dictionary.

#### [MODIFY] backend/app/services.py
- Remove `PORTFOLIO = {"cash": 250000.0, "positions": {}, "transactions": []}`
- Inject `Session` into functions like `process_trade` and `get_portfolio_summary`.
- Rewrite `process_trade` to perform CRUD operations on `Portfolio`, `Position`, and `Transaction` SQLAlchemy models.

#### [MODIFY] backend/app/main.py
- Ensure `Depends(get_db)` is passed down correctly to the API routes that need it (like paper trading).

---
### Phase 2: Market Data Ingestion
Replace the random walk data generator with real historical data.

#### [MODIFY] backend/app/data.py
- Remove `generate_daily_history` function.
- Implement `fetch_real_market_data(symbol: str)` using `yfinance` to pull OHLCV data.
- Update `get_market_data()` to utilize the real data fetched from `yfinance`.

---
### Phase 3: Background Tasks & Asynchronous Scanning
Offload heavy indicator calculations (RSI, MACD) to background workers.

#### [NEW] backend/app/worker.py
```python
from celery import Celery
import redis
import json

celery_app = Celery("superx_tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")
redis_client = redis.Redis(host='localhost', port=6379, db=2)

@celery_app.task
def fetch_and_scan_daily_market():
    # Fetch data using yfinance
    # Calculate RSI, MACD, EMA
    # Save the scan results JSON into Redis cache
    pass
```

#### [MODIFY] backend/app/api/routes/screener.py
- Refactor `GET /api/scan` to read directly from the Redis cache instead of calling the calculation services on the fly. If cache is empty, return a 503 indicating the background job hasn't completed.

## Verification Plan

### Manual Verification
1. Run `docker-compose up -d` to ensure TimescaleDB and Redis are running.
2. Install new requirements: `pip install -r backend/requirements.txt`
3. Run the Celery worker: `celery -A app.worker.celery_app worker --loglevel=info` (inside backend dir)
4. Start the FastAPI server: `uvicorn app.main:app --reload`
5. **Verify Screener:** Hit `GET /api/scan` and confirm it pulls from Redis (should return quickly).
6. **Verify Paper Trading:** Hit `POST /api/paper-trade` and verify changes are persisted in the PostgreSQL database using a DB client (like DBeaver or pgAdmin).
