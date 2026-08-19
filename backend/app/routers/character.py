from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.database import get_db
from app.models.schemas import CharacterResponse
from app.services.llm_service import llm_service
from app.services.fuzzy_matcher import FuzzyMatcher
from rapidfuzz import fuzz

router = APIRouter(prefix="/character", tags=["character"])


@router.get("", response_model=CharacterResponse)
async def lookup_character(
    session_token: str = Query(..., description="Session token"),
    name: str = Query(..., description="Character name to look up")
):
    """
    Look up a character by name and return a spoiler-safe description.
    """
    # Normalize name
    name = name.strip()
    if not name:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_name",
                "message": "Please enter a character name."
            }
        )
    
    # Convert to title-case for lookup
    normalized_name = name.title()
    
    async with get_db() as db:
        # Get session
        cursor = await db.execute(
            """SELECT s.book_id, s.current_chapter_index, s.current_offset, b.is_indexed
               FROM sessions s
               JOIN books b ON s.book_id = b.id
               WHERE s.session_token = ?""",
            (session_token,)
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
        
        # Check if book is indexed
        if not session['is_indexed']:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "not_indexed",
                    "message": "Character lookup is not available yet. The book is still being processed."
                }
            )
        
        # Query mentions
        cursor = await db.execute(
            """SELECT context_snippet FROM mentions
               WHERE book_id = ?
                 AND character_name = ?
                 AND ((chapter_index < ?)
                      OR (chapter_index = ? AND offset <= ?))
               ORDER BY chapter_index, offset""",
            (book_id, normalized_name, current_chapter_index, current_chapter_index, current_offset)
        )
        mentions = await cursor.fetchall()
        
        snippets = [m['context_snippet'] for m in mentions]
        
        if not snippets:
            # No mentions found - try fuzzy suggestion
            suggestion = await _suggest_similar_name(db, book_id, normalized_name)
            
            message = f"This character hasn't appeared yet, as far as I can tell up to where you are."
            if suggestion:
                message += f"\n\nDidn't find results for '{name}'? Try searching for '{suggestion}' instead."
            else:
                message += f"\n\nDidn't find results for '{name}'? Try searching by the character's most commonly used name, as the book refers to them. Nicknames and aliases are not yet supported."
            
            return CharacterResponse(
                status="not_found",
                message=message
            )
        
        # Check if LLM is available
        if not llm_service.is_available():
            # Return raw snippets without LLM synthesis
            snippets_preview = snippets[:5]  # Limit to 5 snippets
            combined_snippets = "\n\n---\n\n".join(snippets_preview)
            return CharacterResponse(
                status="found_no_llm",
                character=normalized_name,
                description=f"**[LLM not configured - showing mention snippets]**\n\nFound {len(snippets)} mentions in the book. Here are a few examples:\n\n{combined_snippets}\n\n*Configure ANTHROPIC_API_KEY to enable AI-powered character descriptions.*",
                mentions_count=len(snippets)
            )
        
        # Generate description
        try:
            description = await llm_service.synthesize_character(normalized_name, snippets)
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"[Character lookup error] {type(e).__name__}: {error_msg}")
            print(traceback.format_exc())
            if "timeout" in error_msg.lower():
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
                    "message": f"The AI service is temporarily unavailable: {error_msg[:200]}",
                    "retry_after": 60
                }
            )
        
        return CharacterResponse(
            status="found",
            character=normalized_name,
            description=description,
            mentions_count=len(snippets)
        )


async def _suggest_similar_name(db, book_id: int, searched_name: str) -> Optional[str]:
    """
    Suggest a similar character name using fuzzy matching.
    """
    cursor = await db.execute(
        """SELECT DISTINCT character_name FROM mentions WHERE book_id = ?""",
        (book_id,)
    )
    names = await cursor.fetchall()
    
    matcher = FuzzyMatcher(threshold=60)  # Lower threshold for suggestions
    
    suggestions = []
    for row in names:
        name = row['character_name']
        score = fuzz.ratio(searched_name.lower(), name.lower())
        if score >= 60:
            suggestions.append((name, score))
    
    if suggestions:
        suggestions.sort(key=lambda x: -x[1])
        return suggestions[0][0]
    
    return None
