from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")

_pool_kwargs = (
    {"poolclass": NullPool}                         # SQLite: no pool, avoids "database is locked"
    if _is_sqlite else
    {                                               # PostgreSQL: tunable pool
        "pool_size":     settings.db_pool_size,
        "max_overflow":  settings.db_max_overflow,
        "pool_timeout":  settings.db_pool_timeout,
        "pool_pre_ping": True,
    }
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
