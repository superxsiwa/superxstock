from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connect to TimescaleDB (PostgreSQL) running via Docker
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://superx:superxpassword@localhost:5432/superxstock"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
