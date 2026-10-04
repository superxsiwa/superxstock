# Issue: Implement WebSocket Endpoint for Live Price Streaming

**Label:** `backend`, `real-time`
**Status:** `To Do`
**Assignee:** Backend Team

## Description
Currently, stock prices are fetched on a scheduled basis (End-of-Day). For a realistic paper trading experience, users should be able to view live or near-live stock price updates during market hours without continuously refreshing the page.

## Acceptance Criteria
- [ ] Create a new WebSocket endpoint in FastAPI (e.g., `/ws/market-stream`).
- [ ] Set up a connection manager to handle active WebSocket clients.
- [ ] Implement a mechanism (via Celery or a background FastAPI task) to fetch intra-day prices for watchlist symbols and push updates to connected clients.
- [ ] Secure the WebSocket connection by verifying the user's JWT token during the initial handshake.
- [ ] Document the WebSocket payload structure for the frontend team to consume.
