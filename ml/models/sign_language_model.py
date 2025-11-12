"""
Sign Language Recognition Model Architecture.

Implements a temporal CNN-LSTM model for sign language recognition from keypoints.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class SignLanguageModel(nn.Module):
    """
    Sign Language Recognition Model.
    
    Architecture:
    - Input: Temporal sequence of keypoints (hand, pose, face)
    - Feature extraction: 1D CNN layers
    - Temporal modeling: Bidirectional LSTM
    - Classification: Fully connected layers
    
    Args:
        num_keypoints: Number of keypoints per frame (default: 543)
        num_classes: Number of sign classes to predict
        hidden_dim: Hidden dimension for LSTM (default: 256)
        num_lstm_layers: Number of LSTM layers (default: 2)
        dropout: Dropout rate (default: 0.3)
    """
    
    def __init__(
        self,
        num_keypoints: int = 543,  # MediaPipe: 21*2 hands + 33 pose + 468 face
        num_classes: int = 100,
        hidden_dim: int = 256,
        num_lstm_layers: int = 2,
        dropout: float = 0.3,
    ):
        super(SignLanguageModel, self).__init__()
        
        self.num_keypoints = num_keypoints
        self.num_classes = num_classes
        self.hidden_dim = hidden_dim
        
        # Feature extraction layers (1D CNN over keypoints)
        self.conv1 = nn.Conv1d(num_keypoints * 3, 128, kernel_size=3, padding=1)  # x, y, z
        self.bn1 = nn.BatchNorm1d(128)
        
        self.conv2 = nn.Conv1d(128, 256, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(256)
        
        self.conv3 = nn.Conv1d(256, 512, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm1d(512)
        
        # Temporal modeling (Bidirectional LSTM)
        self.lstm = nn.LSTM(
            input_size=512,
            hidden_size=hidden_dim,
            num_layers=num_lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_lstm_layers > 1 else 0,
        )
        
        # Attention mechanism
        self.attention = nn.Linear(hidden_dim * 2, 1)
        
        # Classification head
        self.fc1 = nn.Linear(hidden_dim * 2, 512)
        self.dropout1 = nn.Dropout(dropout)
        
        self.fc2 = nn.Linear(512, 256)
        self.dropout2 = nn.Dropout(dropout)
        
        self.fc3 = nn.Linear(256, num_classes)
        
    def forward(
        self,
        x: torch.Tensor,
        lengths: torch.Tensor = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (batch, seq_len, num_keypoints, 3)
            lengths: Actual sequence lengths for each sample in batch
            
        Returns:
            Tuple of (logits, attention_weights)
        """
        batch_size, seq_len, num_kp, coords = x.shape
        
        # Reshape for CNN: (batch * seq_len, num_keypoints * 3, 1)
        x = x.reshape(batch_size * seq_len, num_kp * coords, 1)
        
        # Feature extraction
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        
        # Reshape for LSTM: (batch, seq_len, features)
        x = x.squeeze(-1)  # Remove last dimension
        x = x.reshape(batch_size, seq_len, -1)
        
        # Temporal modeling with LSTM
        if lengths is not None:
            # Pack padded sequence for variable length inputs
            x = nn.utils.rnn.pack_padded_sequence(
                x, lengths.cpu(), batch_first=True, enforce_sorted=False
            )
        
        lstm_out, (hidden, cell) = self.lstm(x)
        
        if lengths is not None:
            # Unpack sequence
            lstm_out, _ = nn.utils.rnn.pad_packed_sequence(
                lstm_out, batch_first=True
            )
        
        # Attention mechanism
        attention_scores = self.attention(lstm_out)  # (batch, seq_len, 1)
        attention_weights = F.softmax(attention_scores, dim=1)
        
        # Apply attention
        context = torch.sum(attention_weights * lstm_out, dim=1)  # (batch, hidden*2)
        
        # Classification
        x = F.relu(self.fc1(context))
        x = self.dropout1(x)
        
        x = F.relu(self.fc2(x))
        x = self.dropout2(x)
        
        logits = self.fc3(x)
        
        return logits, attention_weights.squeeze(-1)


class LightweightSignModel(nn.Module):
    """
    Lightweight model for mobile/edge deployment.
    
    Simplified architecture with fewer parameters for faster inference.
    """
    
    def __init__(
        self,
        num_keypoints: int = 543,
        num_classes: int = 100,
        hidden_dim: int = 128,
    ):
        super(LightweightSignModel, self).__init__()
        
        # Simplified feature extraction
        self.conv1 = nn.Conv1d(num_keypoints * 3, 64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        
        # Single LSTM layer
        self.lstm = nn.LSTM(
            input_size=128,
            hidden_size=hidden_dim,
            num_layers=1,
            batch_first=True,
            bidirectional=False,
        )
        
        # Simple classification head
        self.fc = nn.Linear(hidden_dim, num_classes)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        batch_size, seq_len, num_kp, coords = x.shape
        
        # Reshape and extract features
        x = x.reshape(batch_size * seq_len, num_kp * coords, 1)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        
        # Reshape for LSTM
        x = x.squeeze(-1)
        x = x.reshape(batch_size, seq_len, -1)
        
        # LSTM
        lstm_out, (hidden, _) = self.lstm(x)
        
        # Use last hidden state
        logits = self.fc(hidden.squeeze(0))
        
        return logits


def create_model(
    model_type: str = "standard",
    num_classes: int = 100,
    **kwargs
) -> nn.Module:
    """
    Factory function to create sign language models.
    
    Args:
        model_type: Type of model ("standard" or "lightweight")
        num_classes: Number of sign classes
        **kwargs: Additional model parameters
        
    Returns:
        PyTorch model
    """
    if model_type == "standard":
        return SignLanguageModel(num_classes=num_classes, **kwargs)
    elif model_type == "lightweight":
        return LightweightSignModel(num_classes=num_classes, **kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


if __name__ == "__main__":
    # Test model
    model = SignLanguageModel(num_classes=100)
    
    # Create dummy input: (batch=2, seq_len=30, keypoints=543, coords=3)
    x = torch.randn(2, 30, 543, 3)
    
    # Forward pass
    logits, attention = model(x)
    
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {logits.shape}")
    print(f"Attention shape: {attention.shape}")
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
