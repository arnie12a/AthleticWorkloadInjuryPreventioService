import os
import getpass

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_USER = getpass.getuser()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg://{DB_USER}@localhost:5432/athletic_workload"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()