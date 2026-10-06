from __future__ import annotations
import math
from typing import Dict, List
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException

from .data import get_current_price_with_fallback, get_market_data
from app.models.all_models import Portfolio, Position, Stock, Transaction

def ema(values: List[float], period: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    multiplier = 2 / (period + 1)
    ema_value = values[0]
    for value in values[1:]:
        ema_value = (value - ema_value) * multiplier + ema_value
    return float(ema_value)


def rsi(values: List[float], period: int = 14) -> float:
    if len(values) < period + 1:
        return 50.0
    deltas = []
    for i in range(1, len(values)):
        deltas.append(values[i] - values[i - 1])

    gains = sum(max(d, 0) for d in deltas[-period:])
    losses = abs(sum(min(d, 0) for d in deltas[-period:]))
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    rs = gains / losses
    return round(100 - (100 / (1 + rs)), 2)


def macd(values: List[float]) -> tuple[float, float]:
    if len(values) < 26:
        return 0.0, 0.0
    fast = ema(values[-26:], 12)
    slow = ema(values[-26:], 26)
    macd_value = fast - slow
    signal_value = ema([fast, slow], 9) if False else macd_value
    return round(macd_value, 2), round(signal_value, 2)


def current_volume_ratio(history: List[dict]) -> float:
    if len(history) < 10:
        return 1.0
    recent_volume = history[-1]["volume"]
    avg_volume = sum(item["volume"] for item in history[-20:]) / 20
    if avg_volume == 0:
        return 1.0
    return round(recent_volume / avg_volume, 2)


def action_zone(price: float, ema50: float, ema90: float, volume_ratio: float) -> str:
    if price > ema50 > ema90 and volume_ratio >= 1.1:
        return "Bullish Breakout"
    if ema50 < ema90 and price < ema50:
        return "Bearish Momentum"
    if price > ema50 and ema50 > ema90:
        return "Trend Support"
    return "Neutral"


def classify_signal(rsi_value: float, macd_value: float, ema50: float, ema90: float, volume_ratio: float, price: float) -> str:
    trending_up = ema50 > ema90
    momentum_bull = rsi_value > 55 and macd_value > 0
    momentum_bear = rsi_value < 45 and macd_value < 0

    if trending_up and momentum_bull and volume_ratio >= 1.0:
        return "BUY"
    if not trending_up and momentum_bear:
        return "SELL"
    return "WATCH"


def compute_score(rsi_value: float, macd_value: float, volume_ratio: float, trend_strength: float) -> int:
    score = 50
    score += (rsi_value - 50) * 0.3
    score += min(macd_value * 10, 20)
    score += min((volume_ratio - 1) * 30, 20)
    score += trend_strength * 10
    return max(0, min(100, int(round(score))))


def generate_signal_for_symbol(symbol: str, info: Dict) -> Dict:
    history = info["history"]
    closes = [item["close"] for item in history]
    price = history[-1]["close"]
    ema50 = ema(closes[-50:], 50)
    ema90 = ema(closes[-90:], 90)
    rsi_value = rsi(closes)
    macd_value, _ = macd(closes)
    volume_ratio = current_volume_ratio(history)
    recommendation = classify_signal(rsi_value, macd_value, ema50, ema90, volume_ratio, price)
    zone = action_zone(price, ema50, ema90, volume_ratio)
    trend_strength = (ema50 - ema90) / max(ema90, 1) * 100
    score = compute_score(rsi_value, macd_value, volume_ratio, trend_strength)
    confidence = min(95, max(45, score - 15))

    return {
        "symbol": symbol,
        "name": info["name"],
        "price": round(price, 2),
        "change_pct": info["change_pct"],
        "rsi": round(rsi_value, 2),
        "macd": round(macd_value, 2),
        "ema50": round(ema50, 2),
        "ema90": round(ema90, 2),
        "volume_ratio": round(volume_ratio, 2),
        "action_zone": zone,
        "recommendation": recommendation,
        "score": score,
        "confidence": confidence,
    }


def scan_market() -> List[Dict]:
    market = get_market_data()
    scan_results = [generate_signal_for_symbol(symbol, info) for symbol, info in market.items()]
    scan_results.sort(key=lambda x: x["score"], reverse=True)
    return scan_results


def get_symbol_chart(symbol: str) -> List[Dict]:
    market = get_market_data()
    normalized_symbol = symbol.strip().upper().removesuffix(".BK")
    data = market.get(normalized_symbol)
    if not data:
        raise ValueError(f"Symbol {symbol} not found")
    return data["history"]


def get_portfolio_summary(db: Session, user_id: int) -> Dict:
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not portfolio:
        portfolio = Portfolio(user_id=user_id, initial_balance=250000.0, current_cash=250000.0)
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

    quote_symbols = {
        stock.symbol.removesuffix(".BK").upper(): stock.symbol
        for stock in db.query(Stock).filter(Stock.is_active.is_(True)).all()
        if stock.symbol and stock.symbol.upper().endswith(".BK")
    }
    positions = []
    total_market_value = 0.0
    total_unrealized_pnl = 0.0
    has_unpriced_positions = False
    for pos in sorted(portfolio.positions, key=lambda position: position.symbol or ""):
        if pos.quantity <= 0:
            continue
        symbol = (pos.symbol or "").strip().upper()
        quote_symbol = quote_symbols.get(symbol.removesuffix(".BK"))
        price = get_current_price_with_fallback(quote_symbol) if quote_symbol else None
        if price is not None and (not math.isfinite(price) or price <= 0):
            price = None

        if price is None:
            market_value = None
            unrealized_pnl = None
            has_unpriced_positions = True
        else:
            market_value = price * pos.quantity
            unrealized_pnl = (price - pos.average_cost) * pos.quantity
            total_market_value += market_value
            total_unrealized_pnl += unrealized_pnl

        positions.append({
            "symbol": symbol,
            "quantity": pos.quantity,
            "avg_price": round(pos.average_cost, 2),
            "price": round(price, 2) if price is not None else None,
            "market_value": round(market_value, 2) if market_value is not None else None,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "price_available": price is not None,
        })

    transactions = [
        {
            "symbol": t.symbol,
            "action": t.side,
            "quantity": t.quantity,
            "price": t.price,
            "timestamp": t.timestamp.isoformat() + "Z"
        }
        for t in sorted(portfolio.transactions, key=lambda x: x.timestamp, reverse=True)
    ]

    return {
        "cash": round(portfolio.current_cash, 2),
        "total_value": (
            round(portfolio.current_cash + total_market_value, 2)
            if not has_unpriced_positions
            else None
        ),
        "unrealized_pnl": (
            round(total_unrealized_pnl, 2) if not has_unpriced_positions else None
        ),
        "positions": positions,
        "transactions": transactions,
    }


def process_trade(db: Session, user_id: int, symbol: str, action: str, quantity: int, price: float | None) -> Dict:
    market = get_market_data()
    if symbol not in market:
        raise ValueError(f"Symbol {symbol} not found")

    if price is None:
        price = market[symbol]["current_price"]

    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not portfolio:
        portfolio = Portfolio(user_id=user_id, initial_balance=250000.0, current_cash=250000.0)
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

    total_cost = price * quantity

    if action == "BUY":
        if portfolio.current_cash < total_cost:
            raise ValueError("Not enough cash for this purchase")
        portfolio.current_cash -= total_cost

        position = db.query(Position).filter(Position.portfolio_id == portfolio.id, Position.symbol == symbol).first()
        if position:
            total_val = (position.average_cost * position.quantity) + total_cost
            position.quantity += quantity
            position.average_cost = total_val / position.quantity
        else:
            new_position = Position(portfolio_id=portfolio.id, symbol=symbol, average_cost=price, quantity=quantity)
            db.add(new_position)
            
    elif action == "SELL":
        position = db.query(Position).filter(Position.portfolio_id == portfolio.id, Position.symbol == symbol).first()
        if not position or position.quantity < quantity:
            raise ValueError("Not enough shares to sell")
        
        portfolio.current_cash += total_cost
        position.quantity -= quantity
        if position.quantity == 0:
            db.delete(position)
    else:
        raise ValueError("Unsupported action")

    new_transaction = Transaction(
        portfolio_id=portfolio.id,
        symbol=symbol,
        side=action,
        price=price,
        quantity=quantity,
        timestamp=datetime.utcnow()
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(portfolio)

    return get_portfolio_summary(db, user_id)
