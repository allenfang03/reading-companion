from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.models.schemas import UserResponse
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def create_user():
    """
    Create a new user and return their unique ID.
    This ID is stored in localStorage to maintain user isolation.
    """
    user_id = str(uuid.uuid4())
    
    async with get_db() as db:
        await db.execute(
            "INSERT INTO users (id) VALUES (?)",
            (user_id,)
        )
        await db.commit()
    
    return UserResponse(id=user_id)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Verify that a user exists."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(id=row['id'])
