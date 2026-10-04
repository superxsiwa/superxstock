import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import decode_access_token
from app.data import get_market_data_provider
from app.models.all_models import User, Stock

router = APIRouter(tags=["Market Stream"])
logger = logging.getLogger(__name__)
POLL_INTERVAL_SECONDS = 60
AUTH_TIMEOUT_SECONDS = 5


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    def connect(self, websocket: WebSocket) -> None:
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        for connection in tuple(self.active_connections):
            try:
                await connection.send_json(message)
            except (OSError, RuntimeError, WebSocketDisconnect):
                self.disconnect(connection)


manager = ConnectionManager()
publisher_task: asyncio.Task | None = None


def fetch_current_prices() -> list[dict[str, float | str]]:
    db = SessionLocal()
    try:
        active_stocks = db.query(Stock).filter(Stock.is_active == True).all()
        symbols = [s.symbol for s in active_stocks]
    finally:
        db.close()

    try:
        provider = get_market_data_provider()
    except Exception:
        logger.exception("Failed to initialize the market data provider")
        return []

    prices = []
    for symbol in symbols:
        try:
            price = provider.get_current_price(symbol)
        except Exception:
            logger.exception("Failed to fetch current price for %s", symbol)
            continue
        if price is not None:
            prices.append({"symbol": symbol, "price": price})
    return prices


async def publish_market_prices() -> None:
    while manager.active_connections:
        prices = await asyncio.to_thread(fetch_current_prices)
        if prices:
            await manager.broadcast({
                "type": "price_update",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "prices": prices,
            })
        else:
            await manager.broadcast({"type": "error", "code": "market_data_unavailable"})
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.websocket("/ws/market-stream")
async def market_stream(websocket: WebSocket, db: Session = Depends(get_db)) -> None:
    global publisher_task

    await websocket.accept()
    try:
        auth_message = await asyncio.wait_for(
            websocket.receive_json(), timeout=AUTH_TIMEOUT_SECONDS
        )
    except WebSocketDisconnect:
        return
    except (asyncio.TimeoutError, ValueError):
        await websocket.close(code=4401, reason="Authentication required")
        return

    if not isinstance(auth_message, dict) or auth_message.get("type") != "auth":
        await websocket.close(code=4401, reason="Authentication required")
        return

    token = auth_message.get("token")
    subject = decode_access_token(token) if isinstance(token, str) else None
    user = db.query(User).filter(User.email == subject).first() if subject else None
    if user is None:
        await websocket.close(code=4401, reason="Invalid credentials")
        return

    manager.connect(websocket)
    if publisher_task is None or publisher_task.done():
        publisher_task = asyncio.create_task(publish_market_prices())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        if not manager.active_connections and publisher_task is not None:
            publisher_task.cancel()
            publisher_task = None