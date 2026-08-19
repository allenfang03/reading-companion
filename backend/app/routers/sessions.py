from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.models.schemas import (
    SetPositionRequest, SetPositionResponse, 
    SessionResponse, ErrorResponse
)
from app.services.fuzzy_matcher import FuzzyMatcher, resolve_offset_to_chapter
import uuid
import aiosqlite

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/set-position", response_model=SetPositionResponse)
async def set_position(request: SetPositionRequest):
    """
    Set the reader's current position in a book.
    
    Uses fuzzy matching to find the snippet in the book text.
    """
    snippet = request.snippet.strip()
    
    # Validate snippet length (10 words minimum)
    word_count = len(snippet.split())
    if word_count < 10:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "snippet_too_short",
                "message": "Please enter at least 10 words from your current position."
            }
        )
    
    async with get_db() as db:
        # Check book exists
        cursor = await db.execute(
            "SELECT id, title FROM books WHERE id = ?",
            (request.book_id,)
        )
        book = await cursor.fetchone()
        
        if not book:
            raise HTTPException(
                status_code=404,
                detail={"error": "book_not_found", "message": "Book not found"}
            )
        
        # Get all chapter texts concatenated
        cursor = await db.execute(
            """SELECT chapter_index, text, char_count 
               FROM chapters 
               WHERE book_id = ? 
               ORDER BY chapter_index""",
            (request.book_id,)
        )
        chapters = await cursor.fetchall()
        
        if not chapters:
            raise HTTPException(
                status_code=422,
                detail={"error": "no_chapters", "message": "Book has no readable chapters"}
            )
        
        # Concatenate texts for matching
        full_text = ""
        chapter_data = []
        for ch in chapters:
            chapter_data.append({'char_count': ch['char_count']})
            full_text += ch['text']
        
        # Fuzzy match
        matcher = FuzzyMatcher()
        matches = matcher.find_matches(snippet, full_text)
        
        # Handle match outcomes
        if not matches:
            return SetPositionResponse(
                status="no_match",
                session_token="",
                chapter_index=0,
                chapter_name="Chapter 1",
                offset=0,
                message="I don't see this snippet in the book. Double-check for typos or try a longer passage."
            )
        
        is_amb, top_matches = matcher.is_ambiguous(matches)
        
        if is_amb:
            return SetPositionResponse(
                status="multiple_matches",
                session_token="",
                chapter_index=0,
                chapter_name="Chapter 1",
                offset=0,
                message="This snippet appears more than once. Please enter a longer or more unique passage."
            )
        
        best_match = top_matches[0]
        
        # Resolve to chapter
        chapter_index, offset = resolve_offset_to_chapter(
            best_match['offset'], 
            chapter_data
        )
        
        # Upsert session
        session_token = str(uuid.uuid4())
        
        # Check if session exists
        cursor = await db.execute(
            "SELECT session_token FROM sessions WHERE book_id = ?",
            (request.book_id,)
        )
        existing = await cursor.fetchone()
        
        if existing:
            session_token = existing['session_token']
            await db.execute(
                """UPDATE sessions 
                   SET current_chapter_index = ?, current_offset = ?
                   WHERE session_token = ?""",
                (chapter_index, offset, session_token)
            )
        else:
            await db.execute(
                """INSERT INTO sessions (session_token, book_id, current_chapter_index, current_offset)
                   VALUES (?, ?, ?, ?)""",
                (session_token, request.book_id, chapter_index, offset)
            )
        
        await db.commit()
        
        return SetPositionResponse(
            status="position_set",
            session_token=session_token,
            chapter_index=chapter_index,
            chapter_name=f"Chapter {chapter_index + 1}",
            offset=offset
        )


@router.get("/{session_token}", response_model=SessionResponse)
async def get_session(session_token: str):
    """Get session by token for rehydration."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT s.session_token, s.book_id, s.current_chapter_index, 
                      s.current_offset, b.title, b.is_indexed
               FROM sessions s
               JOIN books b ON s.book_id = b.id
               WHERE s.session_token = ?""",
            (session_token,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "session_not_found", "message": "Session not found"}
            )
        
        return SessionResponse(
            session_token=row['session_token'],
            book_id=row['book_id'],
            title=row['title'],
            current_chapter_index=row['current_chapter_index'],
            current_offset=row['current_offset'],
            is_indexed=bool(row['is_indexed'])
        )
