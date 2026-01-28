from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "sqlite:///./ping.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    views = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def create_tables() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
