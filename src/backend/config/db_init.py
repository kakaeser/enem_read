"""
Database initialization module.

Provides both sync (legacy desktop) and async (FastAPI) init functions,
plus a CLI for first-time setup and migration.

Usage (CLI):
    python -m backend.config.db_init [--migrate]
"""

import asyncio
import argparse
import logging

from backend.config.connection import DBConnectionHandler
from backend.config.base import Base

# Import all entities so SQLAlchemy registers them before create_all
from backend.entities.participante import Participante  # noqa: F401
from backend.entities.questao import Questao  # noqa: F401
from backend.entities.resposta import Resposta  # noqa: F401
from backend.entities.exam import Exam  # noqa: F401

logger = logging.getLogger(__name__)


def init_db():
    """Synchronous table creation (used by the desktop app on startup)."""
    db = DBConnectionHandler()
    engine = db.get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created (sync).")


async def async_init_db():
    """
    Async table creation for FastAPI startup.
    Creates all tables that don't yet exist without dropping existing data.
    """
    from backend.config.async_connection import AsyncDBConnectionHandler

    engine = AsyncDBConnectionHandler.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (async).")


def _run_migration():
    """Run the single-to-multi-exam migration interactively."""
    from backend.migrations.run_migration import main as migration_main
    migration_main()


def _cli():
    parser = argparse.ArgumentParser(
        description="Initialize the Enem da Read database."
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run the single-to-multi-exam migration after table creation.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("Creating database tables...")
    init_db()
    print("Tables ready.")

    if args.migrate:
        print()
        _run_migration()


if __name__ == "__main__":
    _cli()
