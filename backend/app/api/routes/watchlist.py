from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.all_models import Stock, User, Watchlist
from app.schemas import WatchlistCreate

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


@router.get("", response_model=list[str])
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entries = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.symbol)
        .all()
    )
    return [entry.symbol for entry in entries]


@router.post("", status_code=201)
def add_to_watchlist(
    watchlist_in: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    symbol = watchlist_in.symbol.strip().upper()
    stock = db.query(Stock).filter(Stock.symbol == symbol, Stock.is_active.is_(True)).first()
    if stock is None:
        raise HTTPException(status_code=404, detail="Active stock not found.")

    existing = db.query(Watchlist).filter_by(user_id=current_user.id, symbol=symbol).first()
    if existing:
        raise HTTPException(status_code=409, detail="Stock is already in your watchlist.")

    entry = Watchlist(user_id=current_user.id, symbol=symbol)
    db.add(entry)
    db.commit()
    return {"symbol": entry.symbol}


@router.delete("/{symbol}")
def remove_from_watchlist(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(Watchlist).filter_by(
        user_id=current_user.id,
        symbol=symbol.strip().upper(),
    ).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")

    db.delete(entry)
    db.commit()
    return {"ok": True}