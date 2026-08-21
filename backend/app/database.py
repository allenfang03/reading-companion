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
    
    # Run migrations if needed
    await run_migrations()


async def run_migrations():
    """Run database migrations for existing databases."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if users table exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        users_table_exists = await cursor.fetchone() is not None
        
        if not users_table_exists:
            # Migration: Add user isolation columns
            print("Running migration: Adding user isolation...")
            
            # Create users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create a default user for existing data
            default_user_id = str(uuid.uuid4())
            await db.execute("INSERT INTO users (id) VALUES (?)", (default_user_id,))
            
            # Add user_id to books table (if not exists)
            cursor = await db.execute("PRAGMA table_info(books)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                await db.execute("ALTER TABLE books ADD COLUMN user_id TEXT NOT NULL DEFAULT ?", (default_user_id,))
            
            # Add user_id to sessions table (if not exists)
            cursor = await db.execute("PRAGMA table_info(sessions)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                await db.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT NOT NULL DEFAULT ?", (default_user_id,))
            
            # Add user_id to mentions table (if not exists)
            cursor = await db.execute("PRAGMA table_info(mentions)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                await db.execute("ALTER TABLE mentions ADD COLUMN user_id TEXT NOT NULL DEFAULT ?", (default_user_id,))
            
            # Add user_id to recap_cache table (if not exists)
            cursor = await db.execute("PRAGMA table_info(recap_cache)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                await db.execute("ALTER TABLE recap_cache ADD COLUMN user_id TEXT NOT NULL DEFAULT ?", (default_user_id,))
            
            await db.commit()
            print(f"Migration complete. Default user ID: {default_user_id}")


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
