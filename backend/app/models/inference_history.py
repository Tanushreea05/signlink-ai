"""
Inference History database model.

Stores ML inference requests and results for analytics.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class InferenceHistory(Base):
    """
    Inference history model for tracking ML predictions.
    
    Attributes:
        id: Unique inference identifier
        user_id: User who made the request
        model_name: Name of the model used
        model_version: Version of the model
        input_type: Type of input (video, image, keypoints)
        language: Sign language (ASL, ISL, BSL)
        prediction: Predicted sign/phrase
        confidence: Prediction confidence score
        latency_ms: Inference latency in milliseconds
        metadata: Additional metadata (JSON)
        created_at: Inference timestamp
    """
    
    __tablename__ = "inference_history"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Model information
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    
    # Input information
    input_type = Column(String, nullable=False)  # video, image, keypoints
    language = Column(String, nullable=False)  # ASL, ISL, BSL
    
    # Prediction results
    prediction = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=False)
    
    # Additional data
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="inference_history")
    
    def __repr__(self):
        return f"<InferenceHistory(id={self.id}, prediction={self.prediction}, confidence={self.confidence})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "input_type": self.input_type,
            "language": self.language,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
