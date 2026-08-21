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
        db.row_factory = aiosqlite.Row
        
        # Check if books table exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='books'"
        )
        books_exists = await cursor.fetchone() is not None
        
        if books_exists:
            # Check if user_id column exists
            cursor = await db.execute("PRAGMA table_info(books)")
            columns = [row['name'] for row in await cursor.fetchall()]
            
            if 'user_id' not in columns:
                # Old schema without user_id - need to reset
                print("Old database schema detected - resetting database")
                await db.close()
                if DATABASE_PATH.exists():
                    os.unlink(DATABASE_PATH)
                db = await aiosqlite.connect(DATABASE_PATH)
                db.row_factory = aiosqlite.Row
        
        # Create fresh schema
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
