"""
Background worker for indexing character mentions in books.
Uses simple pattern-based extraction instead of LLM for speed.
"""
from app.database import get_db
from app.config import settings
import re


# Common patterns that indicate a person's name (2-4 capitalized words)
NAME_PATTERN = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b')


def extract_names_simple(text: str) -> set:
    """
    Simple name extraction using capitalization patterns.
    Filters out common non-name capitalized words.
    """
    # Common words that are often capitalized but aren't names
    skip_words = {
        'the', 'and', 'but', 'for', 'not', 'you', 'all', 'can', 'had', 'her',
        'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how',
        'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
        'did', 'she', 'use', 'her', 'too', 'own', 'say', 'sit', 'end', 'put',
        'Chapter', 'Part', 'Book', 'Volume', 'Edition', 'Copyright', 'Published',
        'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Morning', 'Evening',
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
        'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
        'September', 'October', 'November', 'December', 'Spring', 'Summer', 'Fall', 'Winter',
        'Red', 'Rising', 'Golden', 'Son', 'Dawn', 'Morning', 'Star', 'Night',
        'Iron', 'Gold', 'Silver', 'Copper', 'Bronze', 'Obsidian', 'Pink',
        'Blue', 'Green', 'Black', 'White', 'Gray', 'Grey', 'Purple', 'Orange',
        'Yes', 'No', 'Maybe', 'Please', 'Thank', 'Thanks', 'Sorry', 'Hello',
        'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sir', 'Lady', 'Lord', 'King', 'Queen',
        'Prince', 'Princess', 'Duke', 'March', 'October', 'November', 'December',
        'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
    }
    
    # Also skip single-character words
    skip_single = {'a', 'i', 'i.', 'a.', 'A', 'I'}
    
    names = set()
    
    # Find capitalized sequences
    for match in NAME_PATTERN.finditer(text):
        name = match.group(1).strip()
        words = name.split()
        
        # Filter out short words, common non-names, and single chars
        filtered_words = []
        for w in words:
            w_lower = w.lower()
            if len(w) < 2 or w_lower in skip_words or w in skip_single:
                continue
            filtered_words.append(w)
        
        if len(filtered_words) >= 1 and len(name) >= 3:
            # Reconstruct the name
            clean_name = ' '.join(filtered_words)
            names.add(clean_name)
    
    return names


async def index_book_mentions(book_id: int):
    """
    Index all character mentions in a book using simple pattern matching.
    
    For each chapter:
    1. Extract names using capitalization patterns
    2. Find occurrences in text
    3. Store mentions with context snippets
    """
    async with get_db() as db:
        # Get user_id for this book
        cursor = await db.execute(
            "SELECT user_id FROM books WHERE id = ?",
            (book_id,)
        )
        book = await cursor.fetchone()
        if not book:
            print(f"Book {book_id} not found, skipping indexing")
            return
        user_id = book['user_id']
        
        # Get all chapters
        cursor = await db.execute(
            """SELECT chapter_index, text FROM chapters
               WHERE book_id = ?
               ORDER BY chapter_index""",
            (book_id,)
        )
        chapters = await cursor.fetchall()
        
        # Mark job as running
        await db.execute(
            """UPDATE jobs 
               SET status = 'running'
               WHERE book_id = ? AND job_type = 'mention_indexing'""",
            (book_id,)
        )
        await db.commit()
        
        try:
            total_chapters = len(chapters)
            print(f"Starting indexing for {total_chapters} chapters...")
            
            for idx, chapter in enumerate(chapters):
                chapter_index = chapter['chapter_index']
                text = chapter['text']
                
                # Simple name extraction
                character_names = extract_names_simple(text)
                
                if idx % 20 == 0:
                    print(f"Processing chapter {idx + 1}/{total_chapters}...")
                
                # Find occurrences of each name
                for name in character_names:
                    # Case-insensitive search
                    lower_text = text.lower()
                    lower_name = name.lower()
                    
                    start = 0
                    while True:
                        pos = lower_text.find(lower_name, start)
                        if pos == -1:
                            break
                        
                        # Extract context snippet
                        context_start = max(0, pos - settings.context_snippet_chars)
                        context_end = min(len(text), pos + len(name) + settings.context_snippet_chars)
                        
                        context_snippet = text[context_start:context_end]
                        
                        # Store mention
                        try:
                            await db.execute(
                                """INSERT OR IGNORE INTO mentions
                                   (user_id, book_id, character_name, chapter_index, offset, context_snippet)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (user_id, book_id, name.title(), chapter_index, pos, context_snippet)
                            )
                        except Exception as e:
                            pass
                        
                        start = pos + 1
            
            # Mark as complete
            await db.execute(
                """UPDATE jobs 
                   SET status = 'complete', completed_at = CURRENT_TIMESTAMP
                   WHERE book_id = ? AND job_type = 'mention_indexing'""",
                (book_id,)
            )
            await db.execute(
                "UPDATE books SET is_indexed = TRUE WHERE id = ?",
                (book_id,)
            )
            await db.commit()
            print(f"Indexing complete for book {book_id}!")
            
        except Exception as e:
            # Mark as failed
            await db.execute(
                """UPDATE jobs 
                   SET status = 'failed', error = ?
                   WHERE book_id = ? AND job_type = 'mention_indexing'""",
                (str(e), book_id)
            )
            await db.commit()
            raise
