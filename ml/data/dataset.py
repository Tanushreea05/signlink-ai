"""
PyTorch Dataset for sign language recognition.
"""

import os
import json
import torch
import numpy as np
from torch.utils.data import Dataset
from typing import List, Tuple, Optional
from pathlib import Path

from data.preprocessing import temporal_interpolation, normalize_keypoints


class SignLanguageDataset(Dataset):
    """
    Dataset for sign language recognition from keypoints.
    
    Expected data structure:
    data_dir/
        ├── class_1/
        │   ├── sample_1.npy
        │   ├── sample_2.npy
        │   └── ...
        ├── class_2/
        │   └── ...
        └── labels.json
    """
    
    def __init__(
        self,
        data_dir: str,
        sequence_length: int = 30,
        augment: bool = False,
        normalize: bool = True,
    ):
        """
        Initialize dataset.
        
        Args:
            data_dir: Directory containing data
            sequence_length: Fixed sequence length for temporal interpolation
            augment: Whether to apply data augmentation
            normalize: Whether to normalize keypoints
        """
        self.data_dir = Path(data_dir)
        self.sequence_length = sequence_length
        self.augment = augment
        self.normalize = normalize
        
        # Load data
        self.samples = []
        self.labels = []
        self.class_to_idx = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load data from directory"""
        # Load class mapping
        labels_file = self.data_dir / "labels.json"
        if labels_file.exists():
            with open(labels_file, 'r') as f:
                self.class_to_idx = json.load(f)
        else:
            # Create class mapping from directory structure
            classes = sorted([d.name for d in self.data_dir.iterdir() if d.is_dir()])
            self.class_to_idx = {cls: idx for idx, cls in enumerate(classes)}
        
        # Load samples
        for class_name, class_idx in self.class_to_idx.items():
            class_dir = self.data_dir / class_name
            if not class_dir.exists():
                continue
            
            for sample_file in class_dir.glob("*.npy"):
                self.samples.append(str(sample_file))
                self.labels.append(class_idx)
        
        print(f"Loaded {len(self.samples)} samples from {len(self.class_to_idx)} classes")
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Get sample by index.
        
        Returns:
            Tuple of (keypoints, label, length)
        """
        # Load keypoints
        keypoints = np.load(self.samples[idx])  # Shape: (seq_len, num_keypoints, 3)
        label = self.labels[idx]
        
        # Get original length
        original_length = len(keypoints)
        
        # Temporal interpolation to fixed length
        keypoints = temporal_interpolation(keypoints, self.sequence_length)
        
        # Normalize keypoints
        if self.normalize:
            for i in range(len(keypoints)):
                keypoints[i] = normalize_keypoints(keypoints[i])
        
        # Data augmentation
        if self.augment:
            keypoints = self._augment(keypoints)
        
        # Convert to tensors
        keypoints_tensor = torch.FloatTensor(keypoints)
        label_tensor = torch.LongTensor([label])[0]
        length_tensor = torch.LongTensor([min(original_length, self.sequence_length)])[0]
        
        return keypoints_tensor, label_tensor, length_tensor
    
    def _augment(self, keypoints: np.ndarray) -> np.ndarray:
        """
        Apply data augmentation.
        
        Args:
            keypoints: Keypoints array
            
        Returns:
            Augmented keypoints
        """
        # Random rotation
        if np.random.rand() < 0.5:
            angle = np.random.uniform(-15, 15)
            keypoints = self._rotate(keypoints, angle)
        
        # Random scaling
        if np.random.rand() < 0.5:
            scale = np.random.uniform(0.9, 1.1)
            keypoints = keypoints * scale
        
        # Random noise
        if np.random.rand() < 0.3:
            noise = np.random.normal(0, 0.01, keypoints.shape)
            keypoints = keypoints + noise
        
        # Random temporal shift
        if np.random.rand() < 0.3:
            shift = np.random.randint(-3, 3)
            keypoints = np.roll(keypoints, shift, axis=0)
        
        return keypoints
    
    def _rotate(self, keypoints: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate keypoints around z-axis.
        
        Args:
            keypoints: Keypoints array
            angle: Rotation angle in degrees
            
        Returns:
            Rotated keypoints
        """
        angle_rad = np.radians(angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        
        rotation_matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])
        
        # Apply rotation to each frame
        rotated = np.zeros_like(keypoints)
        for i in range(len(keypoints)):
            rotated[i] = keypoints[i] @ rotation_matrix.T
        
        return rotated


def collate_fn(batch: List[Tuple]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Custom collate function for variable length sequences.
    
    Args:
        batch: List of (keypoints, label, length) tuples
        
    Returns:
        Batched tensors
    """
    keypoints, labels, lengths = zip(*batch)
    
    # Stack tensors
    keypoints = torch.stack(keypoints)
    labels = torch.stack(labels)
    lengths = torch.stack(lengths)
    
    return keypoints, labels, lengths
