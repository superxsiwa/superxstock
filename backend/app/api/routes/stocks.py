from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.all_models import Stock
from app.schemas import StockCreate, StockResponse

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])

MAX_STOCKS = 50

@router.get("/", response_model=List[StockResponse])
def get_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    return stocks

@router.post("/", response_model=StockResponse)
def add_stock(stock_in: StockCreate, db: Session = Depends(get_db)):
    # Check limit
    count = db.query(Stock).count()
    if count >= MAX_STOCKS:
        raise HTTPException(status_code=400, detail=f"Cannot add more than {MAX_STOCKS} stocks to prevent API rate limits.")

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

@router.delete("/{stock_id}", response_model=dict)
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found.")
    
    db.delete(stock)
    db.commit()
    return {"ok": True, "message": f"Deleted {stock.symbol}"}
