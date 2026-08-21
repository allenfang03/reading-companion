import aiosqlite
import os
from contextlib import asynccontextmanager
from pathlib import Path
import uuid

DATABASE_PATH = Path(__file__).parent.parent / "reading_companion.db"


async def init_db():
    """Initialize the database with schema."""
    schema_path = Path(__file__).parent.parent / "schema.sql"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        with open(schema_path) as f:
            await db.executescript(f.read())
        await db.commit()


@asynccontextmanager
async def get_db():
    """Async context manager for database connections."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def get_db_session():
    """Factory for creating database sessions (for dependency injection)."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        return db
    except Exception:
        await db.close()
        raise
