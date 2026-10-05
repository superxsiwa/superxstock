import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Connect to TimescaleDB (PostgreSQL) running via Docker
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://superx:superxpassword@localhost:5432/superxstock",
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_user_role_column(database_engine=engine):
    with database_engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("users")}
        if "role" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
