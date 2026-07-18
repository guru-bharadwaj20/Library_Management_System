"""Pydantic request/response models — the API's public contract."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---- Auth ----
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


# ---- Books ----
class BookCreate(BaseModel):
    book_id: str
    title: str
    author: str = ""
    total_copies: int = Field(default=1, ge=0)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    book_id: str
    title: str
    author: str
    total_copies: int
    available_copies: int


# ---- Students ----
class StudentCreate(BaseModel):
    student_id: str
    name: str


class StudentOut(BaseModel):
    student_id: str
    name: str
    borrowed_book_ids: list[str] = []


# ---- Borrow ----
class BorrowRequest(BaseModel):
    book_id: str
    student_id: str


class IssueResponse(BaseModel):
    message: str
    due_date: datetime
    book_id: str
    student_id: str


class ReturnResponse(BaseModel):
    message: str
    penalty: float
    book_id: str
    student_id: str


class BorrowRecordOut(BaseModel):
    id: int
    book_id: str
    title: str
    student_id: str
    student_name: str
    issue_date: datetime
    due_date: datetime
    return_date: datetime | None
    penalty: float


# ---- AI ----
class AISearchRequest(BaseModel):
    query: str


class AIHit(BaseModel):
    """A book the AI surfaced, enriched with live catalogue data + its rationale."""
    book_id: str
    title: str
    author: str
    available_copies: int
    reason: str


class AISearchResponse(BaseModel):
    query: str
    hits: list[AIHit]


class AIRecommendResponse(BaseModel):
    student_id: str
    recommendations: list[AIHit]
