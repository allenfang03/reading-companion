from fastapi import APIRouter, HTTPException, Query
from app.database import get_db
from app.models.schemas import RecapResponse
from app.services.llm_service import llm_service
from app.config import settings
import math

router = APIRouter(prefix="/recap", tags=["recap"])


@router.get("", response_model=RecapResponse)
async def get_recap(
    session_token: str = Query(..., description="Session token"),
    user_id: str = Query(..., description="User ID for isolation")
):
    """
    Get a recap of events since the reader last read.
    
    Includes:
    - Full text of previous chapter (if not at chapter 0)
    - Text of current chapter up to current offset
    """
    async with get_db() as db:
        # Get session
        cursor = await db.execute(
            """SELECT s.book_id, s.current_chapter_index, s.current_offset
               FROM sessions s
               WHERE s.session_token = ? AND s.user_id = ?""",
            (session_token, user_id)
        )
        session = await cursor.fetchone()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={"error": "session_not_found", "message": "Session not found"}
            )
        
        book_id = session['book_id']
        current_chapter_index = session['current_chapter_index']
        current_offset = session['current_offset']
        
        # Compute offset bucket for caching
        offset_bucket = math.floor(current_offset / settings.offset_bucket_size)
        
        # Check cache
        cursor = await db.execute(
            """SELECT llm_response FROM recap_cache
               WHERE user_id = ? AND book_id = ? AND chapter_index = ? AND offset_bucket = ?""",
            (user_id, book_id, current_chapter_index, offset_bucket)
        )
        cached = await cursor.fetchone()
        
        if cached:
            return RecapResponse(
                cached=True,
                recap=cached['llm_response'],
                chapter_index=current_chapter_index,
                offset_bucket=offset_bucket
            )
        
        # Assemble text
        text_parts = []
        
        # Add previous chapter if not at chapter 0
        if current_chapter_index > 0:
            cursor = await db.execute(
                """SELECT text FROM chapters
                   WHERE book_id = ? AND chapter_index = ?""",
                (book_id, current_chapter_index - 1)
            )
            prev_chapter = await cursor.fetchone()
            if prev_chapter:
                text_parts.append(prev_chapter['text'])
        
        # Add current chapter up to offset
        cursor = await db.execute(
            """SELECT text FROM chapters
               WHERE book_id = ? AND chapter_index = ?""",
            (book_id, current_chapter_index)
        )
        current_chapter = await cursor.fetchone()
        
        if current_chapter:
            current_text = current_chapter['text'][:current_offset]
            if text_parts:
                text_parts.append("[END OF PREVIOUS CHAPTER]\n\n")
            text_parts.append(current_text)
        
        assembled_text = "".join(text_parts)
        
        if not assembled_text.strip():
            return RecapResponse(
                cached=False,
                recap="You're at the very beginning of the book. Start reading to build up context for a recap!",
                chapter_index=current_chapter_index,
                offset_bucket=offset_bucket
            )
        
        # Check if LLM is available
        if not llm_service.is_available():
            # Return plain text summary without LLM
            preview = assembled_text[:1000] + "..." if len(assembled_text) > 1000 else assembled_text
            return RecapResponse(
                cached=False,
                recap=f"**[LLM not configured - showing raw text preview]**\n\n{preview}\n\n*Configure ANTHROPIC_API_KEY to enable AI-powered recaps.*",
                chapter_index=current_chapter_index,
                offset_bucket=offset_bucket
            )
        
        # Estimate tokens and generate recap
        estimated_tokens = len(assembled_text) / 4
        
        try:
            recap = await llm_service.generate_recap(assembled_text, int(estimated_tokens))
        except Exception as e:
            if "timeout" in str(e).lower():
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "llm_timeout",
                        "message": "The AI service took too long to respond. Please try again.",
                        "retry_after": 30
                    }
                )
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "llm_unavailable",
                    "message": "The AI service is temporarily unavailable. Please try again.",
                    "retry_after": 60
                }
            )
        
        # Cache the result
        await db.execute(
            """INSERT OR REPLACE INTO recap_cache 
               (user_id, book_id, chapter_index, offset_bucket, llm_response)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, book_id, current_chapter_index, offset_bucket, recap)
        )
        await db.commit()
        
        return RecapResponse(
            cached=False,
            recap=recap,
            chapter_index=current_chapter_index,
            offset_bucket=offset_bucket
        )
