from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserResponse(BaseModel):
    id: str


class BookBase(BaseModel):
    title: str


class BookCreate(BookBase):
    pass


class BookResponse(BaseModel):
    id: int
    title: str
    is_indexed: bool


class BookListResponse(BaseModel):
    books: List[BookResponse]


class BookUploadResponse(BaseModel):
    book_id: int
    title: str
    num_chapters: int
    status: str


class ChapterResponse(BaseModel):
    id: int
    chapter_index: int
    char_count: int


class SessionBase(BaseModel):
    book_id: int


class SessionCreate(SessionBase):
    snippet: str = Field(..., min_length=1)


class SetPositionRequest(BaseModel):
    book_id: int
    snippet: str = Field(..., min_length=10, description="At least 10 words from current position")


class SetPositionResponse(BaseModel):
    status: str
    session_token: str
    chapter_index: int
    chapter_name: str
    offset: int
    message: Optional[str] = None


class SessionResponse(BaseModel):
    session_token: str
    book_id: int
    title: str
    current_chapter_index: int
    current_offset: int
    is_indexed: bool


class RecapResponse(BaseModel):
    cached: bool
    recap: str
    chapter_index: int
    offset_bucket: int


class CharacterResponse(BaseModel):
    status: str
    character: Optional[str] = None
    description: Optional[str] = None
    mentions_count: Optional[int] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    retry_after: Optional[int] = None
