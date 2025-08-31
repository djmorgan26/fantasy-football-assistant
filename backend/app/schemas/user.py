from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    espn_s2: Optional[str] = Field(None, description="ESPN S2 cookie for private leagues")
    espn_swid: Optional[str] = Field(None, description="ESPN SWID cookie for private leagues")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8, description="New password must be at least 8 characters")
    espn_s2: Optional[str] = Field(None, description="ESPN S2 cookie for private leagues")
    espn_swid: Optional[str] = Field(None, description="ESPN SWID cookie for private leagues")


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    has_espn_credentials: bool = Field(description="Whether user has stored ESPN credentials")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, user):
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            has_espn_credentials=bool(user.espn_s2_encrypted or user.espn_swid_encrypted)
        )