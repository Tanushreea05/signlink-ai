"""
Refresh Token database model.

Stores refresh tokens for JWT authentication.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class RefreshToken(Base):
    """
    Refresh token model for managing JWT refresh tokens.
    
    Attributes:
        id: Unique token identifier
        token: Hashed refresh token
        user_id: Associated user ID
        expires_at: Token expiration timestamp
        is_revoked: Whether token has been revoked
        created_at: Token creation timestamp
    """
    
    __tablename__ = "refresh_tokens"
    
    id = Column(String, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Expiration and revocation
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    
    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired() and not self.is_revoked
