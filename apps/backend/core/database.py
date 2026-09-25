"""Database initialization and session management."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Database location
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATA_DIR, 'edgeforge.db')}"

_engine = None
_session_factory = None


class Base(DeclarativeBase):
    pass


def get_engine():
    return _engine


async def init_db():
    global _engine, _session_factory
    _engine = create_async_engine(DATABASE_URL, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    # Import all models so they register with Base
    from models import db_models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print(f"  Database initialized: {os.path.join(DATA_DIR, 'edgeforge.db')}")


async def get_session() -> AsyncSession:
    async with _session_factory() as session:
        yield session
