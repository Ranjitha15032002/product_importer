# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# default to the importer credentials used in the instructions, but allow override
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://importer:importer@localhost:5432/importer"
)

# Create engine with sensible pool settings for local dev.
# Tune pool_size / max_overflow for production based on DB size and worker concurrency.
engine = create_engine(
    DATABASE_URL,
    pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "40")),
    future=True,
)

# Session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

# FastAPI dependency - yields a DB session and ensures it's closed afterwards
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
