from pydantic import BaseModel, Field
from typing import Literal, Optional


class TradeRequest(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=10)
    action: Literal["BUY", "SELL"]
    quantity: int = Field(..., gt=0)
    price: Optional[float] = None


class TradeResponse(BaseModel):
    ok: bool
    message: str
    position: dict
    portfolio: dict


class StockSignal(BaseModel):
    symbol: str
    name: str
    price: float
    change_pct: float
    rsi: float
    macd: float
    ema50: float
    ema90: float
    volume_ratio: float
    action_zone: str
    recommendation: str
    score: int
    confidence: int

class StockCreate(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=20)
    name: Optional[str] = None
    is_active: bool = True

class StockResponse(BaseModel):
    id: int
    symbol: str
    name: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class ConfigUpdate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: int = Field(..., ge=1)

class WatchlistCreate(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=20)

class LineNotificationUpdate(BaseModel):
    line_user_id: str = Field(..., pattern=r"^U[0-9a-fA-F]{32}$")
    channel_access_token: Optional[str] = Field(None, min_length=1)
