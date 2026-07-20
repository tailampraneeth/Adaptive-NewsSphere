import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.connection import get_db
from app.database.models.user import User
from app.api.schemas.auth import (
    UserSignup, UserLogin, TokenResponse, UserResponse, UserOnboard, UserUpdate,
    ForgotPasswordRequest, ResetPasswordRequest
)
from app.utils.auth import hash_password, verify_password, create_access_token
from app.api.dependencies import get_current_user
from app.services.email import send_reset_password_email

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup, db: AsyncSession = Depends(get_db)):
    """Registers a new user with onboarding initially set to incomplete."""
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address already registered.",
        )
    
    hashed_pwd = hash_password(payload.password)
    new_user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        onboarding_complete=False,
        preferred_categories=[],
        preferred_publishers=[],
        hidden_categories=[],
        hidden_publishers=[]
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates credentials and returns a JWT access token."""
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
        
    token_data = {"sub": user.email, "id": str(user.id)}
    access_token = create_access_token(data=token_data)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user details."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates user preferences and profile parameters."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/onboard", response_model=UserResponse)
async def onboard(
    payload: UserOnboard,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Completes the onboarding workflow for a new user."""
    if current_user.onboarding_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed.",
        )
    
    current_user.name = payload.name
    current_user.country = payload.country
    current_user.preferred_categories = payload.preferred_categories
    current_user.preferred_publishers = payload.preferred_publishers
    current_user.theme = payload.theme or "dark"
    current_user.brief_time = payload.brief_time or "morning"
    current_user.onboarding_complete = True
    
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes the authenticated user account and all cascade dependencies."""
    await db.delete(current_user)
    await db.commit()
    return


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates password reset flow. Generates secure single-use token and sends email.
    Prevents user enumeration by returning a generic success message even if email is not found.
    Rate-limits requests to max 1 per 60 seconds per user.
    """
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    generic_response = {"message": "If the email is registered, a password reset link has been sent."}
    
    if not user:
        return generic_response
        
    # Rate limiting: max 1 request per 60 seconds
    now = datetime.now(timezone.utc)
    if user.reset_token_expires_at:
        expires_at = user.reset_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        # Since token expiration is T + 30 minutes, last request time was expires_at - 30 minutes.
        last_request_time = expires_at - timedelta(minutes=30)
        if now - last_request_time < timedelta(seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many password reset requests. Please wait 60 seconds before trying again."
            )
            
    # Generate high-entropy token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    user.reset_token_hash = token_hash
    user.reset_token_expires_at = now + timedelta(minutes=30)
    
    await db.commit()
    
    # Send email in background tasks (non-blocking)
    background_tasks.add_task(send_reset_password_email, user.email, token)
    
    return generic_response


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validates token and resets user password. Token is single-use and cleared on success.
    """
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    
    stmt = select(User).where(User.reset_token_hash == token_hash)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )
        
    expires_at = user.reset_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )
        
    # Reset password
    user.hashed_password = hash_password(payload.new_password)
    # Enforce single-use: clear token details
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    
    await db.commit()
    
    return {"message": "Password reset successfully."}
