from pathlib import Path

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Import Database setup and Models
from app.core.database import engine, Base, get_db
from app.models import all_models


# Create tables in the database (For MVP - usually done via Alembic)
Base.metadata.create_all(bind=engine)

# Seed default stocks if empty
from app.core.database import SessionLocal
def seed_default_stocks():
    db = SessionLocal()
    try:
        from app.models.all_models import Stock
        if db.query(Stock).count() == 0:
            THAI_SYMBOLS = ["AOT.BK", "ADVANC.BK", "BDMS.BK", "CPALL.BK", "DELTA.BK", "KBANK.BK", "PTT.BK", "PTTEP.BK", "SCB.BK", "TRUE.BK"]
            for sym in THAI_SYMBOLS:
                db.add(Stock(symbol=sym, name=sym, is_active=True))
            db.commit()
    finally:
        db.close()
seed_default_stocks()

app = FastAPI(
    title="SuperX Stock Screener & Paper Trading API",
    description="MVP Backend for stock analysis and paper trading.",
    version="0.1.0"
)

# Register API Routers
from app.api.routes import frontend, auth, market_stream, stocks
app.include_router(auth.router)
app.include_router(frontend.router)
app.include_router(market_stream.router)
app.include_router(stocks.router)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
STATIC_DIR = PROJECT_ROOT / "static"

if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

@app.get("/")
def read_root():
    frontend_index = FRONTEND_DIST / "index.html"
    if frontend_index.is_file():
        return FileResponse(frontend_index)
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/db-test")
def test_db_connection(db: Session = Depends(get_db)):
    # Test DB by counting users
    user_count = db.query(all_models.User).count()
    return {"message": "Database connection successful!", "user_count": user_count}
