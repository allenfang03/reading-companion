import aiosqlite
import os
from contextlib import asynccontextmanager
from pathlib import Path
import uuid

DATABASE_PATH = Path(__file__).parent.parent / "reading_companion.db"


async def init_db():
    """Initialize the database with schema."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if books table exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='books'"
        )
        books_exists = await cursor.fetchone() is not None
        
        # Check if users table exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        users_exists = await cursor.fetchone() is not None
        
        if books_exists and not users_exists:
            # Migration needed - tables exist but no user isolation
            await migrate_to_user_isolation()
        elif not books_exists:
            # Fresh database - run schema
            schema_path = Path(__file__).parent.parent / "schema.sql"
            with open(schema_path) as f:
                await db.executescript(f.read())
            await db.commit()
        # else: tables exist with users table - already migrated, do nothing


async def migrate_to_user_isolation():
    """Run database migrations for existing databases."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if users table exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        users_table_exists = await cursor.fetchone() is not None
        
        if not users_table_exists:
            print("Running migration: Adding user isolation...")
            
            # Create a default user for existing data
            default_user_id = str(uuid.uuid4())
            await db.execute("INSERT INTO users (id) VALUES (?)", (default_user_id,))
            
            # Add user_id column to books table (nullable first, then NOT NULL)
            cursor = await db.execute("PRAGMA table_info(books)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                # Add as nullable first
                await db.execute("ALTER TABLE books ADD COLUMN user_id TEXT")
                # Update existing rows
                await db.execute("UPDATE books SET user_id = ? WHERE user_id IS NULL", (default_user_id,))
                # Recreate table with NOT NULL constraint (requires recreating)
                await db.execute("""
                    CREATE TABLE books_new AS SELECT * FROM books;
                    DROP TABLE books;
                    CREATE TABLE books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_indexed BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    );
                    INSERT INTO books SELECT id, user_id, title, created_at, is_indexed FROM books_new;
                    DROP TABLE books_new;
                """)
            
            # Add user_id column to sessions table
            cursor = await db.execute("PRAGMA table_info(sessions)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                await db.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
                await db.execute("UPDATE sessions SET user_id = ? WHERE user_id IS NULL", (default_user_id,))
                await db.execute("""
                    CREATE TABLE sessions_new AS SELECT * FROM sessions;
                    DROP TABLE sessions;
                    CREATE TABLE sessions (
                        session_token TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        book_id INTEGER NOT NULL UNIQUE,
                        current_chapter_index INTEGER NOT NULL DEFAULT 0,
                        current_offset INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                    INSERT INTO sessions SELECT session_token, user_id, book_id, current_chapter_index, current_offset, created_at FROM sessions_new;
                    DROP TABLE sessions_new;
                """)
            
            # Add user_id column to mentions table
            cursor = await db.execute("PRAGMA table_info(mentions)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                await db.execute("ALTER TABLE mentions ADD COLUMN user_id TEXT")
                await db.execute("UPDATE mentions SET user_id = ? WHERE user_id IS NULL", (default_user_id,))
                await db.execute("""
                    CREATE TABLE mentions_new AS SELECT * FROM mentions;
                    DROP TABLE mentions;
                    CREATE TABLE mentions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        book_id INTEGER NOT NULL,
                        character_name TEXT NOT NULL,
                        chapter_index INTEGER NOT NULL,
                        offset INTEGER NOT NULL,
                        context_snippet TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                    INSERT INTO mentions SELECT id, user_id, book_id, character_name, chapter_index, offset, context_snippet FROM mentions_new;
                    DROP TABLE mentions_new;
                """)
            
            # Add user_id column to recap_cache table
            cursor = await db.execute("PRAGMA table_info(recap_cache)")
            columns = [row['name'] for row in await cursor.fetchall()]
            if 'user_id' not in columns:
                await db.execute("ALTER TABLE recap_cache ADD COLUMN user_id TEXT")
                await db.execute("UPDATE recap_cache SET user_id = ? WHERE user_id IS NULL", (default_user_id,))
                await db.execute("""
                    CREATE TABLE recap_cache_new AS SELECT * FROM recap_cache;
                    DROP TABLE recap_cache;
                    CREATE TABLE recap_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        book_id INTEGER NOT NULL,
                        chapter_index INTEGER NOT NULL,
                        offset_bucket INTEGER NOT NULL,
                        llm_response TEXT NOT NULL,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
                        UNIQUE(user_id, book_id, chapter_index, offset_bucket)
                    );
                    INSERT INTO recap_cache SELECT id, user_id, book_id, chapter_index, offset_bucket, llm_response, cached_at FROM recap_cache_new;
                    DROP TABLE recap_cache_new;
                """)
            
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
