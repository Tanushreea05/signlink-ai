"""
Authentication API endpoints.

Handles user registration, login, token refresh, and password management.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    get_current_user_id,
)
from app.core.config import settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created user object
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        tenant_id=settings.DEFAULT_TENANT_ID,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Login user and return JWT tokens.
    
    Args:
        credentials: User login credentials
        request: HTTP request object
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "tenant_id": user.tenant_id,
    }
    
    access_token = create_access_token(token_data)
    refresh_token_str = create_refresh_token({"sub": user.id})
    
    # Store refresh token in database
    refresh_token = RefreshToken(
        id=str(uuid.uuid4()),
        token=get_password_hash(refresh_token_str),  # Hash the token
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    
    db.add(refresh_token)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token
        db: Database session
        
    Returns:
        New access and refresh tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    # Verify refresh token
    try:
        payload = verify_refresh_token(refresh_data.refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    
    # Find user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Verify refresh token exists and is valid
    token_hash = get_password_hash(refresh_data.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        )
    )
    stored_tokens = result.scalars().all()
    
    # Check if any stored token matches
    token_valid = False
    for stored_token in stored_tokens:
        if verify_password(refresh_data.refresh_token, stored_token.token):
            if stored_token.is_valid():
                token_valid = True
                # Revoke old token
                stored_token.is_revoked = True
                break
    
    if not token_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Create new tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "tenant_id": user.tenant_id,
    }
    
    new_access_token = create_access_token(token_data)
    new_refresh_token_str = create_refresh_token({"sub": user.id})
    
    # Store new refresh token
    new_refresh_token = RefreshToken(
        id=str(uuid.uuid4()),
        token=get_password_hash(new_refresh_token_str),
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    
    db.add(new_refresh_token)
    await db.commit()
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    refresh_data: RefreshTokenRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Logout user by revoking refresh token.
    
    Args:
        refresh_data: Refresh token to revoke
        user_id: Current user ID
        db: Database session
        
    Returns:
        Success message
    """
    # Revoke all refresh tokens for user
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        )
    )
    tokens = result.scalars().all()
    
    for token in tokens:
        token.is_revoked = True
    
    await db.commit()
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user profile.
    
    Args:
        user_id: Current user ID from token
        db: Database session
        
    Returns:
        User profile
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
