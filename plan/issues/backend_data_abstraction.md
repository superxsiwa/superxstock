# Issue: Design Data Abstraction Layer for Multi-Provider Stock APIs

**Label:** `backend`, `architecture`
**Status:** `To Do`
**Assignee:** Backend Team / System Architect

## Description
The application heavily relies on `yfinance` for market data. While cost-effective, it lacks reliability, is subject to rate limiting, and does not provide robust enterprise-grade service. We need an architectural pattern (Data Abstraction Layer / Strategy Pattern) that allows the system to seamlessly switch between multiple data providers (e.g., Alpha Vantage, Polygon.io, SET API) without rewriting business logic.

## Acceptance Criteria
- [ ] Define an interface/abstract base class (e.g., `MarketDataProvider`) that outlines required methods (e.g., `fetch_ohlcv`, `get_current_price`).
- [ ] Refactor the existing `yfinance` logic into a concrete implementation of this interface (e.g., `YahooFinanceProvider`).
- [ ] Implement a Factory or Dependency Injection pattern in `backend/app/data.py` to inject the active data provider based on environment variables (e.g., `DATA_PROVIDER=YAHOO`).
- [ ] Ensure the Celery tasks and scanning engine use the generic interface rather than calling `yfinance` directly.
