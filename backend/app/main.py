from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Import Database setup and Models
from app.core.database import engine, Base, get_db
from app.models import all_models


# Create tables in the database (For MVP - usually done via Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SuperX Stock Screener & Paper Trading API",
    description="MVP Backend for stock analysis and paper trading.",
    version="0.1.0"
)

# Register API Routers
from app.api.routes import frontend, auth
app.include_router(auth.router)
app.include_router(frontend.router)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/")
def read_root():
    return FileResponse("../static/index.html")

app.mount("/static", StaticFiles(directory="../static"), name="static")

@app.get("/db-test")
def test_db_connection(db: Session = Depends(get_db)):
    # Test DB by counting users
    user_count = db.query(all_models.User).count()
    return {"message": "Database connection successful!", "user_count": user_count}
