from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import get_db
from app.database.models.user import User
from app.database.models.user_profile import UserProfile
from app.api.schemas.auth import UserSignup, UserLogin, TokenResponse, UserResponse
from app.utils.auth import hash_password, verify_password, create_access_token
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup, db: AsyncSession = Depends(get_db)):
    """
    Registers a new user, hashes their password, and instantiates their profile.
    """
    # Check if user already exists
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered.",
        )
    
    # Hash password and save new User
    hashed_pwd = hash_password(payload.password)
    new_user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        interaction_count=0
    )
    db.add(new_user)
    await db.flush()  # Generates User.id UUID
    
    # Instantiate user profile defaults (crucial for profile health diagnostics)
    user_profile = UserProfile(
        user_id=new_user.id,
        muted_categories=[],
        muted_publishers=[]
    )
    db.add(user_profile)
    
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticates email and password, returning a JWT token on success.
    """
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
        
    # Generate token
    token_data = {"sub": user.email, "id": str(user.id)}
    access_token = create_access_token(data=token_data)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns current authenticated user details.
    """
    return current_user
