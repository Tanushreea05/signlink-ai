"""
User database model.

Defines the User table schema and relationships.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    USER = "user"
    PRO = "pro"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class User(Base):
    """
    User model for authentication and profile management.
    
    Attributes:
        id: Unique user identifier (UUID)
        email: User email address (unique)
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        role: User role (user, pro, admin, enterprise)
        is_active: Whether user account is active
        is_verified: Whether email is verified
        tenant_id: Multi-tenant identifier
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login_at: Last login timestamp
    """
    
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    # Role and permissions
    role = Column(
        SQLEnum(UserRole),
        default=UserRole.USER,
        nullable=False
    )
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Multi-tenancy
    tenant_id = Column(String, index=True, nullable=False)
    
    # Billing
    stripe_customer_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=True)
    
    # Usage tracking
    api_calls_count = Column(Integer, default=0)
    inference_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    inference_history = relationship("InferenceHistory", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
