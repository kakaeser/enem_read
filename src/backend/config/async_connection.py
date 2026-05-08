from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event, text
from typing import AsyncGenerator

from backend.core.config import settings


class AsyncDBConnectionHandler:
    """Async database connection handler for FastAPI async operations."""

    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        """Get or create the async SQLAlchemy engine (singleton)."""
        if cls._engine is None:
            cls._engine = create_async_engine(
                settings.DATABASE_URL_ASYNC,
                echo=settings.DEBUG,
                future=True,
                # Connection pool settings for SQLite (StaticPool keeps one connection)
                connect_args={"check_same_thread": False},
            )

            # Enable SQLite foreign key enforcement on every new connection.
            # Without this, SQLite ignores FK constraints entirely, so orphaned
            # rows can accumulate even when the schema defines FK columns.
            @event.listens_for(cls._engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return cls._engine

    @classmethod
    def get_session_factory(cls):
        """Get or create the async session factory (singleton)."""
        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                cls.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        return cls._session_factory

    @classmethod
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency that yields an async database session.
        Commits on success, rolls back on any exception, and always closes.
        """
        session_factory = cls.get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @classmethod
    async def dispose(cls):
        """Dispose the engine and reset singletons (useful for testing)."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
