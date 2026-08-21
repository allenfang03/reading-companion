-- Users table (for URL-based isolation)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main book record
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_indexed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_books_user ON books(user_id);

-- Chapter text and boundaries
CREATE TABLE IF NOT EXISTS chapters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  chapter_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  char_count INTEGER NOT NULL,
  summary_cache TEXT NULL,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  UNIQUE(book_id, chapter_index)
);

-- Character mention index
CREATE TABLE IF NOT EXISTS mentions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  book_id INTEGER NOT NULL,
  character_name TEXT NOT NULL,
  chapter_index INTEGER NOT NULL,
  offset INTEGER NOT NULL,
  context_snippet TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mentions_lookup ON mentions(user_id, book_id, character_name, chapter_index, offset);

-- Reading sessions
CREATE TABLE IF NOT EXISTS sessions (
  session_token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  book_id INTEGER NOT NULL UNIQUE,
  current_chapter_index INTEGER NOT NULL DEFAULT 0,
  current_offset INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- Recap cache
CREATE TABLE IF NOT EXISTS recap_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  book_id INTEGER NOT NULL,
  chapter_index INTEGER NOT NULL,
  offset_bucket INTEGER NOT NULL,
  llm_response TEXT NOT NULL,
  cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, book_id, chapter_index, offset_bucket)
);

-- Background job tracking
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP NULL,
  error TEXT NULL,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);
