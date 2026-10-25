"""Database setup: a single SQLite file managed through SQLAlchemy.

The app uses the classic SQLAlchemy pattern:
- ``engine``    -- the connection pool to the SQLite file
- ``SessionLocal`` -- a factory that creates database sessions
- ``Base``      -- the declarative base every model inherits from
- ``get_db``    -- a FastAPI dependency that hands each request a session
                   and guarantees it is closed afterwards
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# The database file lives next to the backend folder by default.
# Tests (or deployments) can point elsewhere with the DATABASE_URL env var.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./weather.db")

# check_same_thread=False is required for SQLite when FastAPI serves
# requests from different threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yield one session per request, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
