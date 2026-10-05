from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_admin_user
from app.models.all_models import Stock, SystemConfig
from app.schemas import StockCreate, StockResponse

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])

@router.get("/", response_model=List[StockResponse])
def get_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    return stocks

@router.post("/", response_model=StockResponse, dependencies=[Depends(get_admin_user)])
def add_stock(stock_in: StockCreate, db: Session = Depends(get_db)):
    limit_setting = db.query(SystemConfig).filter(SystemConfig.key == "MAX_STOCKS").first()
    if limit_setting is None:
        raise HTTPException(status_code=503, detail="MAX_STOCKS configuration is not initialized.")
    try:
        max_stocks = int(limit_setting.value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=503, detail="MAX_STOCKS configuration is invalid.")

    count = db.query(Stock).count()
    if count >= max_stocks:
        raise HTTPException(status_code=400, detail=f"Cannot add more than {max_stocks} stocks to prevent API rate limits.")

    # Check if already exists
    existing = db.query(Stock).filter(Stock.symbol == stock_in.symbol.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stock symbol already exists.")

    new_stock = Stock(
        symbol=stock_in.symbol.upper(),
        name=stock_in.name or stock_in.symbol.upper(),
        is_active=stock_in.is_active
    )
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    return new_stock

@router.delete("/{stock_id}", response_model=dict, dependencies=[Depends(get_admin_user)])
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found.")
    
    db.delete(stock)
    db.commit()
    return {"ok": True, "message": f"Deleted {stock.symbol}"}
