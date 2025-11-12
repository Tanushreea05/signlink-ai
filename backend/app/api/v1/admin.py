"""
Admin API endpoints.

Handles administrative operations like user management and system monitoring.
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.inference_history import InferenceHistory
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    is_active: bool = None,
    admin_id: str = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all users (admin only).
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        role: Filter by role
        is_active: Filter by active status
        admin_id: Admin user ID
        db: Database session
        
    Returns:
        List of users
    """
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    admin_id: str = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user by ID (admin only).
    
    Args:
        user_id: User ID to retrieve
        admin_id: Admin user ID
        db: Database session
        
    Returns:
        User details
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


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    admin_id: str = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update user role (admin only).
    
    Args:
        user_id: User ID to update
        new_role: New role to assign
        admin_id: Admin user ID
        db: Database session
        
    Returns:
        Updated user
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
    
    user.role = new_role
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    admin_id: str = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Activate user account (admin only).
    
    Args:
        user_id: User ID to activate
        admin_id: Admin user ID
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
    
    user.is_active = True
    
    await db.commit()
    
    return {"message": f"User {user_id} activated successfully"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    admin_id: str = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Deactivate user account (admin only).
    
    Args:
        user_id: User ID to deactivate
        admin_id: Admin user ID
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
    
    user.is_active = False
    
    await db.commit()
    
    return {"message": f"User {user_id} deactivated successfully"}


@router.get("/stats/overview")
async def get_system_stats(
    admin_id: str = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get system overview statistics (admin only).
    
    Args:
        admin_id: Admin user ID
        db: Database session
        
    Returns:
        System statistics
    """
    # Total users
    result = await db.execute(select(func.count(User.id)))
    total_users = result.scalar()
    
    # Active users
    result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = result.scalar()
    
    # Total inferences
    result = await db.execute(select(func.count(InferenceHistory.id)))
    total_inferences = result.scalar()
    
    # Average confidence
    result = await db.execute(select(func.avg(InferenceHistory.confidence)))
    avg_confidence = result.scalar() or 0.0
    
    # Users by role
    result = await db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    users_by_role = {role.value: count for role, count in result.all()}
    
    # Inferences by language
    result = await db.execute(
        select(InferenceHistory.language, func.count(InferenceHistory.id))
        .group_by(InferenceHistory.language)
    )
    inferences_by_language = {lang: count for lang, count in result.all()}
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_inferences": total_inferences,
        "average_confidence": round(avg_confidence, 3),
        "users_by_role": users_by_role,
        "inferences_by_language": inferences_by_language,
    }


@router.get("/stats/usage")
async def get_usage_stats(
    days: int = 30,
    admin_id: str = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get usage statistics for the last N days (admin only).
    
    Args:
        days: Number of days to include
        admin_id: Admin user ID
        db: Database session
        
    Returns:
        Usage statistics
    """
    from datetime import datetime, timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Inferences per day
    result = await db.execute(
        select(
            func.date(InferenceHistory.created_at).label("date"),
            func.count(InferenceHistory.id).label("count")
        )
        .where(InferenceHistory.created_at >= start_date)
        .group_by(func.date(InferenceHistory.created_at))
        .order_by(func.date(InferenceHistory.created_at))
    )
    inferences_per_day = [
        {"date": str(date), "count": count}
        for date, count in result.all()
    ]
    
    # New users per day
    result = await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count")
        )
        .where(User.created_at >= start_date)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    new_users_per_day = [
        {"date": str(date), "count": count}
        for date, count in result.all()
    ]
    
    return {
        "period_days": days,
        "inferences_per_day": inferences_per_day,
        "new_users_per_day": new_users_per_day,
    }
