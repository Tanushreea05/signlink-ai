"""
User management API endpoints.

Handles user profile operations and settings.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, PasswordChange

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user profile.
    
    Args:
        user_id: Current user ID
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


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update user profile.
    
    Args:
        user_data: Updated user data
        user_id: Current user ID
        db: Database session
        
    Returns:
        Updated user profile
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
    
    # Update fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.email is not None:
        # Check if email is already taken
        result = await db.execute(
            select(User).where(User.email == user_data.email, User.id != user_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = user_data.email
        user.is_verified = False  # Require re-verification
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change user password.
    
    Args:
        password_data: Current and new password
        user_id: Current user ID
        db: Database session
        
    Returns:
        Success message
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
    
    # Verify current password
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user.hashed_password = get_password_hash(password_data.new_password)
    
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.delete("/account")
async def delete_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete user account.
    
    Args:
        user_id: Current user ID
        db: Database session
        
    Returns:
        Success message
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
    
    # Soft delete by deactivating account
    user.is_active = False
    
    await db.commit()
    
    return {"message": "Account deleted successfully"}
