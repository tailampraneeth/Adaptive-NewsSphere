import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserSignup(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")


class UserLogin(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Plain password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime
    interaction_count: int

    class Config:
        from_attributes = True
