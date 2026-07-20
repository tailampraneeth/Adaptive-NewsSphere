import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserSignup(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Plain password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOnboard(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    preferred_categories: List[str] = Field(default_factory=list)
    preferred_publishers: List[str] = Field(default_factory=list)
    theme: Optional[str] = "dark"
    brief_time: Optional[str] = "morning"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    theme: Optional[str] = None
    preferred_categories: Optional[List[str]] = None
    preferred_publishers: Optional[List[str]] = None
    hidden_categories: Optional[List[str]] = None
    hidden_publishers: Optional[List[str]] = None
    brief_time: Optional[str] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    theme: str
    preferred_categories: List[str]
    preferred_publishers: List[str]
    hidden_categories: List[str]
    hidden_publishers: List[str]
    onboarding_complete: bool
    brief_time: str
    created_at: datetime

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Reset password verification token")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")
