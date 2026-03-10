from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
import os


class AsyncDBConnectionHandler:
    """Async database connection handler for FastAPI async operations"""
    
    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        """Get or create async engine"""
        if cls._engine is None:
            base_dir = os.path.join(
                os.environ.get("LOCALAPPDATA", os.getcwd()),
                "enem_read"
            )
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "database.db")
            
            # Use aiosqlite for async SQLite
            connection_string = f"sqlite+aiosqlite:///{db_path}"
            
            cls._engine = create_async_engine(
                connection_string,
                echo=False,
                future=True
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls):
        """Get or create async session factory"""
        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                cls.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
        return cls._session_factory

    @classmethod
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency for FastAPI to get async database session.
        Handles commit/rollback automatically.
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
