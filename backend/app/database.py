import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "student.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_path}")
# Expose the resolved path for modules that need direct sqlite3 access (e.g. chat)
DB_PATH = DATABASE_URL.replace("sqlite:///", "")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
