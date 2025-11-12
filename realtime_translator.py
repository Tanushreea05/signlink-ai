"""
Real-time Sign Language to Text and Audio Translator

This script captures live camera input, extracts keypoints using MediaPipe,
performs real-time sign language recognition, and converts results to text and audio.
"""

import cv2
import numpy as np
import mediapipe as mp
import torch
import pyttsx3
import threading
import queue
import time
import json
from collections import deque
from typing import Optional, List, Tuple
import argparse
import os

# Import our ML components
from ml.data.preprocessing import KeypointExtractor, normalize_keypoints, temporal_interpolation
from ml.models.sign_language_model import create_model


class RealTimeSignTranslator:
    """Real-time sign language translator using live camera input"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        class_names_file: Optional[str] = None,
        sequence_length: int = 30,
        confidence_threshold: float = 0.7,
        device: str = "cuda"
    ):
        """
        Initialize the real-time translator.
        
        Args:
            model_path: Path to trained model checkpoint
            class_names_file: Path to class names file
            sequence_length: Number of frames for temporal analysis
            confidence_threshold: Minimum confidence for predictions
            device: Device to run inference on (cuda/cpu)
        """
        self.sequence_length = sequence_length
        self.confidence_threshold = confidence_threshold
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        
        # Initialize MediaPipe
        self.keypoint_extractor = KeypointExtractor(
            extract_hands=True,
            extract_pose=True,
            extract_face=False  # Disable face for better performance
        )
        
        # Initialize frame buffer for temporal analysis
        self.frame_buffer = deque(maxlen=sequence_length)
        self.keypoint_buffer = deque(maxlen=sequence_length)
        
        # Load model and class names
        self.model = None
        self.class_names = []
        self._load_model(model_path, class_names_file)
        
        # Initialize text-to-speech
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)  # Speech rate
        self.tts_engine.setProperty('volume', 0.8)  # Volume level
        
        # Audio queue for non-blocking TTS
        self.audio_queue = queue.Queue()
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()
        
        # Prediction smoothing
        self.prediction_history = deque(maxlen=5)
        self.last_prediction = ""
        self.last_prediction_time = 0
        self.min_prediction_interval = 2.0  # Minimum seconds between predictions
        
        print(f"✅ Real-time translator initialized on {self.device}")
        print(f"📹 Camera ready, 🤖 Model loaded, 🔊 Audio ready")
    
    def _load_model(self, model_path: Optional[str], class_names_file: Optional[str]):
        """Load trained model and class names"""
        if model_path and os.path.exists(model_path):
            try:
                # Load checkpoint
                checkpoint = torch.load(model_path, map_location=self.device)
                
                # Load class names
                if class_names_file and os.path.exists(class_names_file):
                    with open(class_names_file, 'r') as f:
                        self.class_names = [line.strip() for line in f]
                else:
                    # Try to load from model directory
                    model_dir = os.path.dirname(model_path)
                    class_file = os.path.join(model_dir, "class_names.txt")
                    if os.path.exists(class_file):
                        with open(class_file, 'r') as f:
                            self.class_names = [line.strip() for line in f]
                    else:
                        # Default class names for demo
                        self.class_names = self._get_default_class_names()
                
                # Create and load model
                self.model = create_model(
                    model_type="standard",
                    num_classes=len(self.class_names)
                )
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.model = self.model.to(self.device)
                self.model.eval()
                
                print(f"✅ Model loaded: {len(self.class_names)} classes")
                
            except Exception as e:
                print(f"⚠️ Error loading model: {e}")
                print("🔄 Using mock predictions for demo")
                self.model = None
                self.class_names = self._get_default_class_names()
        else:
            print("⚠️ No model provided, using mock predictions for demo")
            self.class_names = self._get_default_class_names()
    
    def _get_default_class_names(self) -> List[str]:
        """Get default class names for demo"""
        return [
            "HELLO", "GOODBYE", "THANK_YOU", "PLEASE", "YES", "NO",
            "SORRY", "HELP", "LOVE", "FRIEND", "GOOD", "BAD",
            "HAPPY", "SAD", "WATER", "FOOD", "HOME", "WORK",
            "FAMILY", "TIME", "TODAY", "TOMORROW", "YESTERDAY",
            "MORNING", "AFTERNOON", "EVENING", "NIGHT", "HOW",
            "WHAT", "WHERE", "WHEN", "WHY", "WHO"
        ]
    
    def _audio_worker(self):
        """Background worker for text-to-speech"""
        while True:
            try:
                text = self.audio_queue.get(timeout=1)
                if text:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️ TTS Error: {e}")
    
    def _predict_sign(self, keypoints_sequence: np.ndarray) -> Tuple[str, float]:
        """
        Predict sign from keypoints sequence.
        
        Args:
            keypoints_sequence: Sequence of keypoints
            
        Returns:
            Tuple of (prediction, confidence)
        """
        if self.model is None:
            # Mock prediction for demo
            mock_signs = ["HELLO", "THANK_YOU", "GOODBYE", "YES", "NO", "PLEASE"]
            prediction = np.random.choice(mock_signs)
            confidence = np.random.uniform(0.7, 0.95)
            return prediction, confidence
        
        try:
            # Preprocess keypoints
            processed = self._preprocess_keypoints(keypoints_sequence)
            
            # Run inference
            with torch.no_grad():
                logits, _ = self.model(processed)
                probabilities = torch.softmax(logits, dim=1)
                
                # Get prediction
                max_prob, max_idx = torch.max(probabilities, dim=1)
                prediction = self.class_names[max_idx.item()]
                confidence = max_prob.item()
                
                return prediction, confidence
                
        except Exception as e:
            print(f"⚠️ Prediction error: {e}")
            return "UNKNOWN", 0.0
    
    def _preprocess_keypoints(self, keypoints_sequence: np.ndarray) -> torch.Tensor:
        """Preprocess keypoints for model input"""
        # Normalize keypoints
        normalized = []
        for frame in keypoints_sequence:
            normalized.append(normalize_keypoints(frame))
        keypoints_sequence = np.array(normalized)
        
        # Temporal interpolation to fixed length
        if len(keypoints_sequence) != self.sequence_length:
            keypoints_sequence = temporal_interpolation(keypoints_sequence, self.sequence_length)
        
        # Convert to tensor and add batch dimension
        tensor = torch.FloatTensor(keypoints_sequence).unsqueeze(0)
        return tensor.to(self.device)
    
    def _smooth_prediction(self, prediction: str, confidence: float) -> Optional[str]:
        """
        Smooth predictions to avoid jitter.
        
        Args:
            prediction: Current prediction
            confidence: Prediction confidence
            
        Returns:
            Smoothed prediction or None if not confident enough
        """
        current_time = time.time()
        
        # Check confidence threshold
        if confidence < self.confidence_threshold:
            return None
        
        # Add to history
        self.prediction_history.append((prediction, confidence, current_time))
        
        # Check if enough time has passed since last prediction
        if current_time - self.last_prediction_time < self.min_prediction_interval:
            return None
        
        # Find most common prediction in recent history
        recent_predictions = [p for p, c, t in self.prediction_history 
                            if current_time - t < 3.0 and c > self.confidence_threshold]
        
        if len(recent_predictions) < 2:
            return None
        
        # Get most frequent prediction
        from collections import Counter
        most_common = Counter(recent_predictions).most_common(1)
        
        if most_common and most_common[0][1] >= 2:  # At least 2 occurrences
            final_prediction = most_common[0][0]
            
            # Avoid repeating the same prediction too quickly
            if final_prediction != self.last_prediction:
                self.last_prediction = final_prediction
                self.last_prediction_time = current_time
                return final_prediction
        
        return None
    
    def _draw_landmarks(self, image: np.ndarray, keypoint_data) -> np.ndarray:
        """Draw MediaPipe landmarks on image"""
        if keypoint_data.hand_landmarks:
            for hand_landmarks in keypoint_data.hand_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(
                    image, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                    mp.solutions.drawing_styles.get_default_hand_connections_style()
                )
        
        if keypoint_data.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                image, keypoint_data.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS,
                mp.solutions.drawing_styles.get_default_pose_landmarks_style()
            )
        
        return image
    
    def _draw_ui(self, image: np.ndarray, prediction: str, confidence: float, fps: float) -> np.ndarray:
        """Draw UI elements on image"""
        height, width = image.shape[:2]
        
        # Draw semi-transparent overlay
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (width, 120), (0, 0, 0), -1)
        image = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)
        
        # Draw title
        cv2.putText(image, "SignLink AI - Real-time Translator", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Draw FPS
        cv2.putText(image, f"FPS: {fps:.1f}", (width - 120, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Draw prediction
        if prediction:
            color = (0, 255, 0) if confidence > self.confidence_threshold else (0, 255, 255)
            cv2.putText(image, f"Sign: {prediction}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            cv2.putText(image, f"Confidence: {confidence:.2f}", (10, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw instructions
        cv2.putText(image, "Press 'q' to quit, 's' to save frame", (10, height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return image
    
    def run(self, camera_id: int = 0, save_frames: bool = False):
        """
        Run real-time sign language translation.
        
        Args:
            camera_id: Camera device ID
            save_frames: Whether to save frames for debugging
        """
        print(f"🚀 Starting real-time translation...")
        print(f"📹 Camera ID: {camera_id}")
        print(f"🎯 Confidence threshold: {self.confidence_threshold}")
        print(f"⏱️ Sequence length: {self.sequence_length} frames")
        print(f"🔊 Audio enabled")
        print("\nControls:")
        print("  'q' - Quit")
        print("  's' - Save current frame")
        print("  'r' - Reset prediction history")
        print("=" * 50)
        
        # Initialize camera
        cap = cv2.VideoCapture(camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not cap.isOpened():
            print(f"❌ Error: Could not open camera {camera_id}")
            return
        
        # FPS calculation
        fps_counter = 0
        fps_start_time = time.time()
        fps = 0
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Error: Could not read frame")
                    break
                
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Extract keypoints
                keypoint_data = self.keypoint_extractor.extract_from_frame(frame_rgb)
                keypoints_array = keypoint_data.to_array()
                
                # Add to buffer
                self.keypoint_buffer.append(keypoints_array)
                
                # Draw landmarks
                frame = self._draw_landmarks(frame, keypoint_data)
                
                # Predict if we have enough frames
                prediction = ""
                confidence = 0.0
                
                if len(self.keypoint_buffer) >= self.sequence_length:
                    # Get recent keypoints sequence
                    keypoints_sequence = np.array(list(self.keypoint_buffer))
                    
                    # Predict sign
                    prediction, confidence = self._predict_sign(keypoints_sequence)
                    
                    # Smooth prediction
                    final_prediction = self._smooth_prediction(prediction, confidence)
                    
                    if final_prediction:
                        print(f"🤟 Detected: {final_prediction} (confidence: {confidence:.2f})")
                        
                        # Add to audio queue for TTS
                        try:
                            self.audio_queue.put_nowait(final_prediction)
                        except queue.Full:
                            pass  # Skip if queue is full
                
                # Calculate FPS
                fps_counter += 1
                if fps_counter % 30 == 0:
                    fps = 30 / (time.time() - fps_start_time)
                    fps_start_time = time.time()
                
                # Draw UI
                frame = self._draw_ui(frame, prediction, confidence, fps)
                
                # Display frame
                cv2.imshow('SignLink AI - Real-time Translator', frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Quitting...")
                    break
                elif key == ord('s') and save_frames:
                    filename = f"frame_{frame_count:06d}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"💾 Saved frame: {filename}")
                elif key == ord('r'):
                    self.prediction_history.clear()
                    self.keypoint_buffer.clear()
                    print("🔄 Reset prediction history")
                
                frame_count += 1
                
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")
        
        finally:
            # Cleanup
            cap.release()
            cv2.destroyAllWindows()
            print("🧹 Cleanup complete")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Real-time Sign Language Translator")
    parser.add_argument("--model", type=str, help="Path to trained model checkpoint")
    parser.add_argument("--classes", type=str, help="Path to class names file")
    parser.add_argument("--camera", type=int, default=0, help="Camera device ID")
    parser.add_argument("--confidence", type=float, default=0.7, help="Confidence threshold")
    parser.add_argument("--sequence-length", type=int, default=30, help="Sequence length for temporal analysis")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use (cuda/cpu)")
    parser.add_argument("--save-frames", action="store_true", help="Save frames for debugging")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤟 SignLink AI - Real-time Sign Language Translator")
    print("=" * 60)
    print(f"🎯 Model: {args.model or 'Mock predictions (demo mode)'}")
    print(f"📹 Camera: {args.camera}")
    print(f"🎚️ Confidence: {args.confidence}")
    print(f"📏 Sequence: {args.sequence_length} frames")
    print(f"💻 Device: {args.device}")
    print("=" * 60)
    
    # Create translator
    translator = RealTimeSignTranslator(
        model_path=args.model,
        class_names_file=args.classes,
        sequence_length=args.sequence_length,
        confidence_threshold=args.confidence,
        device=args.device
    )
    
    # Run translation
    translator.run(camera_id=args.camera, save_frames=args.save_frames)


if __name__ == "__main__":
    main()
