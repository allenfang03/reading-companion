from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.database import get_db
from app.models.schemas import BookUploadResponse, BookListResponse, BookResponse
from app.services.epub_parser import parse_epub, validate_epub_file
from app.services.llm_service import llm_service
from app.config import settings
import aiosqlite
import uuid
import os
import tempfile

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/upload", response_model=BookUploadResponse)
async def upload_book(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and parse an EPUB book.
    
    Returns book metadata and kicks off background mention indexing.
    """
    # Check file extension
    if not file.filename.endswith('.epub'):
        raise HTTPException(
            status_code=415,
            detail="Only EPUB files are supported"
        )
    
    # Save to temp file for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Validate EPUB
        if not validate_epub_file(tmp_path):
            raise HTTPException(
                status_code=415,
                detail="Invalid EPUB file format"
            )
        
        # Parse EPUB
        try:
            title, chapters = parse_epub(tmp_path)
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=f"EPUB parsing error: {str(e)}"
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"EPUB parsing error: {tb}")
            raise HTTPException(
                status_code=422,
                detail=f"Failed to parse EPUB: {str(e)}"
            )
        
        # Store in database
        async with get_db() as db:
            # Insert book
            cursor = await db.execute(
                "INSERT INTO books (title, is_indexed) VALUES (?, ?)",
                (title, False)
            )
            book_id = cursor.lastrowid
            
            # Insert chapters
            for idx, chapter in enumerate(chapters):
                await db.execute(
                    """INSERT INTO chapters (book_id, chapter_index, text, char_count)
                       VALUES (?, ?, ?, ?)""",
                    (book_id, idx, chapter['text'], chapter['char_count'])
                )
            
            # Create jobs record for parsing (complete) and indexing (pending)
            await db.execute(
                """INSERT INTO jobs (book_id, job_type, status) VALUES (?, ?, ?)""",
                (book_id, 'parsing', 'complete')
            )
            await db.execute(
                """INSERT INTO jobs (book_id, job_type, status) VALUES (?, ?, ?)""",
                (book_id, 'mention_indexing', 'pending')
            )
            
            await db.commit()
        
        # Note: In production, you'd use a proper task queue
        # For v1, mention indexing could be triggered on-demand or via separate endpoint
        # For now, we'll trigger it in background if API key is available
        if settings.anthropic_api_key:
            background_tasks.add_task(run_mention_indexing, book_id)
        
        return BookUploadResponse(
            book_id=book_id,
            title=title,
            num_chapters=len(chapters),
            status="parsing"
        )
    
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def run_mention_indexing(book_id: int):
    """Background task to index character mentions."""
    from app.workers.mention_indexer import index_book_mentions
    
    try:
        await index_book_mentions(book_id)
    except Exception as e:
        # Log error but don't crash
        print(f"Mention indexing failed for book {book_id}: {e}")


@router.get("", response_model=BookListResponse)
async def list_books():
    """List all books, sorted by creation date (newest first)."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT id, title, is_indexed FROM books 
               ORDER BY created_at DESC"""
        )
        rows = await cursor.fetchall()
        
        books = [
            BookResponse(id=row['id'], title=row['title'], is_indexed=bool(row['is_indexed']))
            for row in rows
        ]
        
        return BookListResponse(books=books)
