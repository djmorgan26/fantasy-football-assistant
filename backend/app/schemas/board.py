"""Request/response shapes for the content board."""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.board import PostKind, ReactionKind


class PostCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)
    title: Optional[str] = Field(None, max_length=300)
    kind: PostKind = PostKind.POST
    week: Optional[int] = Field(None, ge=1, le=25)
    media_paths: List[str] = []
    allow_training: bool = True


class PostUpdate(BaseModel):
    body: Optional[str] = Field(None, min_length=1, max_length=8000)
    title: Optional[str] = Field(None, max_length=300)
    allow_training: Optional[bool] = None


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    parent_id: Optional[int] = None


class ReactionRequest(BaseModel):
    reaction: ReactionKind


class CommentResponse(BaseModel):
    id: int
    post_id: int
    parent_id: Optional[int] = None
    body: str
    author_id: Optional[int] = None
    author_name: str
    is_mine: bool
    created_at: Optional[datetime] = None


class PostResponse(BaseModel):
    id: int
    league_id: int
    kind: str
    title: Optional[str] = None
    body: str
    media_paths: List[str] = []
    week: Optional[int] = None
    is_ai: bool
    generated_by: Optional[str] = None
    allow_training: bool
    author_id: Optional[int] = None
    author_name: str
    is_mine: bool
    score: int
    reactions: Dict[str, int]
    my_reactions: List[str]
    comment_count: int
    comments: List[CommentResponse] = []
    created_at: Optional[datetime] = None


class VoiceSampleResponse(BaseModel):
    id: int
    title: Optional[str] = None
    text: str
    score: int
    tags: List[str] = []
    author_name: Optional[str] = None


class BoardStatsResponse(BaseModel):
    posts: int
    comments: int
    reactions: int
    voice_samples: int
    top_reaction: Optional[str] = None
