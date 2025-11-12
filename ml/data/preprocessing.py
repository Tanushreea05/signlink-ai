"""
Data preprocessing for sign language recognition.

Handles keypoint extraction from videos using MediaPipe.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class KeypointData:
    """Container for extracted keypoints"""
    hand_left: Optional[np.ndarray] = None  # Shape: (21, 3)
    hand_right: Optional[np.ndarray] = None  # Shape: (21, 3)
    pose: Optional[np.ndarray] = None  # Shape: (33, 3)
    face: Optional[np.ndarray] = None  # Shape: (468, 3)
    
    def to_array(self) -> np.ndarray:
        """
        Convert all keypoints to single array.
        
        Returns:
            Array of shape (543, 3) with all keypoints
        """
        keypoints = []
        
        # Add hand keypoints (21 * 2 = 42 points)
        if self.hand_left is not None:
            keypoints.append(self.hand_left)
        else:
            keypoints.append(np.zeros((21, 3)))
        
        if self.hand_right is not None:
            keypoints.append(self.hand_right)
        else:
            keypoints.append(np.zeros((21, 3)))
        
        # Add pose keypoints (33 points)
        if self.pose is not None:
            keypoints.append(self.pose)
        else:
            keypoints.append(np.zeros((33, 3)))
        
        # Add face keypoints (468 points)
        if self.face is not None:
            keypoints.append(self.face)
        else:
            keypoints.append(np.zeros((468, 3)))
        
        return np.vstack(keypoints)


class KeypointExtractor:
    """
    Extract keypoints from video frames using MediaPipe.
    """
    
    def __init__(
        self,
        extract_hands: bool = True,
        extract_pose: bool = True,
        extract_face: bool = False,  # Face can be expensive
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        """
        Initialize MediaPipe extractors.
        
        Args:
            extract_hands: Whether to extract hand keypoints
            extract_pose: Whether to extract pose keypoints
            extract_face: Whether to extract face keypoints
            min_detection_confidence: Minimum confidence for detection
            min_tracking_confidence: Minimum confidence for tracking
        """
        self.extract_hands = extract_hands
        self.extract_pose = extract_pose
        self.extract_face = extract_face
        
        # Initialize MediaPipe solutions
        if extract_hands:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        
        if extract_pose:
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        
        if extract_face:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
    
    def extract_from_frame(self, frame: np.ndarray) -> KeypointData:
        """
        Extract keypoints from a single frame.
        
        Args:
            frame: RGB image frame
            
        Returns:
            KeypointData object with extracted keypoints
        """
        keypoint_data = KeypointData()
        
        # Convert BGR to RGB if needed
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
        
        # Extract hand keypoints
        if self.extract_hands:
            results = self.hands.process(frame_rgb)
            if results.multi_hand_landmarks:
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Determine if left or right hand
                    handedness = results.multi_handedness[idx].classification[0].label
                    
                    # Extract landmarks
                    landmarks = np.array([
                        [lm.x, lm.y, lm.z]
                        for lm in hand_landmarks.landmark
                    ])
                    
                    if handedness == "Left":
                        keypoint_data.hand_left = landmarks
                    else:
                        keypoint_data.hand_right = landmarks
        
        # Extract pose keypoints
        if self.extract_pose:
            results = self.pose.process(frame_rgb)
            if results.pose_landmarks:
                keypoint_data.pose = np.array([
                    [lm.x, lm.y, lm.z]
                    for lm in results.pose_landmarks.landmark
                ])
        
        # Extract face keypoints
        if self.extract_face:
            results = self.face_mesh.process(frame_rgb)
            if results.multi_face_landmarks:
                keypoint_data.face = np.array([
                    [lm.x, lm.y, lm.z]
                    for lm in results.multi_face_landmarks[0].landmark
                ])
        
        return keypoint_data
    
    def extract_from_video(
        self,
        video_path: str,
        max_frames: Optional[int] = None,
        sample_rate: int = 1,
    ) -> List[KeypointData]:
        """
        Extract keypoints from video file.
        
        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to process
            sample_rate: Process every Nth frame
            
        Returns:
            List of KeypointData for each frame
        """
        cap = cv2.VideoCapture(video_path)
        keypoints_sequence = []
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Sample frames
            if frame_count % sample_rate == 0:
                keypoints = self.extract_from_frame(frame)
                keypoints_sequence.append(keypoints)
            
            frame_count += 1
            
            # Check max frames
            if max_frames and len(keypoints_sequence) >= max_frames:
                break
        
        cap.release()
        return keypoints_sequence
    
    def close(self):
        """Release MediaPipe resources"""
        if self.extract_hands:
            self.hands.close()
        if self.extract_pose:
            self.pose.close()
        if self.extract_face:
            self.face_mesh.close()


def normalize_keypoints(keypoints: np.ndarray) -> np.ndarray:
    """
    Normalize keypoints to be translation and scale invariant.
    
    Args:
        keypoints: Array of shape (num_keypoints, 3)
        
    Returns:
        Normalized keypoints
    """
    # Center around mean
    centered = keypoints - keypoints.mean(axis=0)
    
    # Scale by standard deviation
    std = centered.std()
    if std > 0:
        normalized = centered / std
    else:
        normalized = centered
    
    return normalized


def temporal_interpolation(
    keypoints_sequence: List[np.ndarray],
    target_length: int
) -> np.ndarray:
    """
    Interpolate keypoint sequence to fixed length.
    
    Args:
        keypoints_sequence: List of keypoint arrays
        target_length: Target sequence length
        
    Returns:
        Interpolated sequence of shape (target_length, num_keypoints, 3)
    """
    from scipy.interpolate import interp1d
    
    current_length = len(keypoints_sequence)
    
    if current_length == target_length:
        return np.array(keypoints_sequence)
    
    # Stack keypoints
    keypoints_array = np.array(keypoints_sequence)  # (seq_len, num_kp, 3)
    
    # Create interpolation function
    x_old = np.linspace(0, 1, current_length)
    x_new = np.linspace(0, 1, target_length)
    
    # Interpolate each keypoint coordinate
    interpolated = np.zeros((target_length, *keypoints_array.shape[1:]))
    
    for i in range(keypoints_array.shape[1]):  # For each keypoint
        for j in range(keypoints_array.shape[2]):  # For each coordinate (x, y, z)
            f = interp1d(x_old, keypoints_array[:, i, j], kind='linear')
            interpolated[:, i, j] = f(x_new)
    
    return interpolated


if __name__ == "__main__":
    # Test keypoint extraction
    extractor = KeypointExtractor(
        extract_hands=True,
        extract_pose=True,
        extract_face=False
    )
    
    # Create dummy frame
    dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Extract keypoints
    keypoints = extractor.extract_from_frame(dummy_frame)
    
    print("Extracted keypoints:")
    print(f"  Left hand: {keypoints.hand_left.shape if keypoints.hand_left is not None else None}")
    print(f"  Right hand: {keypoints.hand_right.shape if keypoints.hand_right is not None else None}")
    print(f"  Pose: {keypoints.pose.shape if keypoints.pose is not None else None}")
    
    # Convert to array
    keypoints_array = keypoints.to_array()
    print(f"\nCombined keypoints shape: {keypoints_array.shape}")
    
    extractor.close()
