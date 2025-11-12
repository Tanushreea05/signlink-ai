"""
Security utilities for authentication and authorization.

Handles JWT token generation, password hashing, and permission checks.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token (e.g., user_id, email)
        expires_delta: Token expiration time (default from settings)
        
    Returns:
        Encoded JWT token
        
    Example:
        token = create_access_token({"sub": user.id, "email": user.email})
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time (default from settings)
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Get current user ID from JWT token.
    
    Dependency for protected routes that require authentication.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is invalid
        
    Example:
        @app.get("/profile")
        async def get_profile(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get full token payload for current user.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Complete token payload
    """
    token = credentials.credentials
    return decode_token(token)


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Required role (e.g., "admin", "enterprise")
        
    Returns:
        Dependency function
        
    Example:
        @app.get("/admin/users")
        async def admin_users(user_id: str = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(
        payload: Dict[str, Any] = Depends(get_current_user_payload)
    ) -> str:
        user_role = payload.get("role", "user")
        
        # Define role hierarchy
        role_hierarchy = {
            "user": 0,
            "pro": 1,
            "admin": 2,
            "enterprise": 2,
        }
        
        required_level = role_hierarchy.get(required_role, 0)
        user_level = role_hierarchy.get(user_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return payload.get("sub")
    
    return role_checker


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a refresh token.
    
    Args:
        token: Refresh token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or not a refresh token
    """
    payload = decode_token(token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected refresh token.",
        )
    
    return payload


def create_api_key() -> str:
    """
    Generate a secure API key for service-to-service authentication.
    
    Returns:
        API key string
    """
    import secrets
    return f"sk_{secrets.token_urlsafe(32)}"


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.
    
    Args:
        api_key: Plain API key
        stored_hash: Hashed API key from database
        
    Returns:
        True if API key is valid, False otherwise
    """
    return pwd_context.verify(api_key, stored_hash)
