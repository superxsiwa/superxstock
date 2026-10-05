from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)

class SystemConfig(Base):
    __tablename__ = "system_config"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String(20), nullable=False, default="user", server_default="user")
    
    portfolios = relationship("Portfolio", back_populates="owner")

class Watchlist(Base):
    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)

class UserNotificationSettings(Base):
    __tablename__ = "user_notification_settings"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    line_user_id = Column(String, nullable=False)
    encrypted_channel_access_token = Column(String, nullable=False)

class SignalHistory(Base):
    __tablename__ = "signal_history"
    __table_args__ = (UniqueConstraint("symbol", "signal_date", name="uq_signal_history_symbol_date"),)
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    recommendation = Column(String(4), nullable=False)
    price = Column(Float, nullable=False)
    signal_date = Column(Date, nullable=False, index=True)

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    initial_balance = Column(Float, default=100000.0)
    current_cash = Column(Float, default=100000.0)
    
    owner = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, index=True)
    average_cost = Column(Float)
    quantity = Column(Integer)
    
    portfolio = relationship("Portfolio", back_populates="positions")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, index=True)
    side = Column(String) # BUY or SELL
    price = Column(Float)
    quantity = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="transactions")
