"""
Simplified Real-time Sign Language Demo

A lightweight version that works without a trained model,
using MediaPipe for keypoint detection and mock predictions.
"""

import cv2
import numpy as np
import mediapipe as mp
import pyttsx3
import threading
import queue
import time
from collections import deque, Counter
import random


class SimpleSignTranslator:
    """Simplified real-time sign language translator"""
    
    def __init__(self):
        """Initialize the simple translator"""
        # Initialize MediaPipe
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Common sign language words
        self.signs = [
            "HELLO", "GOODBYE", "THANK_YOU", "PLEASE", "YES", "NO",
            "SORRY", "HELP", "LOVE", "FRIEND", "GOOD", "BAD",
            "HAPPY", "SAD", "WATER", "FOOD", "HOME", "WORK",
            "FAMILY", "TIME", "HOW", "WHAT", "WHERE", "WHEN"
        ]
        
        # Initialize TTS
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.8)
        
        # Audio queue
        self.audio_queue = queue.Queue()
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()
        
        # Prediction smoothing
        self.prediction_history = deque(maxlen=10)
        self.last_prediction = ""
        self.last_prediction_time = 0
        self.min_prediction_interval = 3.0
        
        # Hand gesture tracking
        self.gesture_buffer = deque(maxlen=30)
        
        print("✅ Simple Sign Translator Ready!")
        print("📹 Camera initialized, 🤖 Gesture detection ready, 🔊 Audio ready")
    
    def _audio_worker(self):
        """Background TTS worker"""
        while True:
            try:
                text = self.audio_queue.get(timeout=1)
                if text:
                    print(f"🔊 Speaking: {text}")
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️ TTS Error: {e}")
    
    def _extract_hand_features(self, hand_landmarks) -> np.ndarray:
        """Extract simple features from hand landmarks"""
        if not hand_landmarks:
            return np.zeros(21 * 3)  # 21 landmarks * 3 coordinates
        
        # Convert landmarks to numpy array
        landmarks = []
        for landmark in hand_landmarks.landmark:
            landmarks.extend([landmark.x, landmark.y, landmark.z])
        
        return np.array(landmarks)
    
    def _classify_gesture(self, features: np.ndarray) -> tuple:
        """Simple gesture classification based on hand features"""
        if len(features) == 0:
            return "NO_HANDS", 0.0
        
        # Simple heuristics for common gestures
        # This is a mock implementation - in reality, you'd use ML
        
        # Calculate hand position and shape features
        thumb_tip = features[4*3:4*3+3] if len(features) >= 15 else np.zeros(3)
        index_tip = features[8*3:8*3+3] if len(features) >= 27 else np.zeros(3)
        middle_tip = features[12*3:12*3+3] if len(features) >= 39 else np.zeros(3)
        
        # Simple gesture detection based on finger positions
        if len(features) >= 63:  # Full hand detected
            # Mock classification based on random selection weighted by hand activity
            hand_activity = np.std(features) * 100  # Measure of hand movement/shape
            
            if hand_activity > 5:  # Active hand movement
                # More likely to be a sign
                weights = [3, 2, 2, 1, 1, 1, 1, 1, 1, 1] + [0.5] * (len(self.signs) - 10)
                sign = np.random.choice(self.signs[:len(weights)], p=np.array(weights)/sum(weights))
                confidence = min(0.95, 0.6 + hand_activity * 0.01)
            else:
                # Less active, lower confidence
                sign = np.random.choice(self.signs)
                confidence = 0.3 + np.random.random() * 0.3
        else:
            sign = "UNCLEAR"
            confidence = 0.2
        
        return sign, confidence
    
    def _smooth_prediction(self, prediction: str, confidence: float) -> str:
        """Smooth predictions to reduce jitter"""
        current_time = time.time()
        
        # Only consider high-confidence predictions
        if confidence < 0.7:
            return ""
        
        # Add to history
        self.prediction_history.append((prediction, confidence, current_time))
        
        # Check timing
        if current_time - self.last_prediction_time < self.min_prediction_interval:
            return ""
        
        # Get recent predictions
        recent = [(p, c) for p, c, t in self.prediction_history 
                 if current_time - t < 5.0 and c > 0.7]
        
        if len(recent) < 3:
            return ""
        
        # Find most common prediction
        predictions = [p for p, c in recent]
        most_common = Counter(predictions).most_common(1)
        
        if most_common and most_common[0][1] >= 2:
            final_prediction = most_common[0][0]
            
            if final_prediction != self.last_prediction and final_prediction != "UNCLEAR":
                self.last_prediction = final_prediction
                self.last_prediction_time = current_time
                return final_prediction
        
        return ""
    
    def _draw_info(self, image: np.ndarray, prediction: str, confidence: float, fps: float) -> np.ndarray:
        """Draw information overlay"""
        height, width = image.shape[:2]
        
        # Semi-transparent overlay
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (width, 150), (0, 0, 0), -1)
        image = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)
        
        # Title
        cv2.putText(image, "SignLink AI - Live Demo", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # FPS
        cv2.putText(image, f"FPS: {fps:.1f}", (width - 120, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Current prediction
        if prediction:
            color = (0, 255, 0) if confidence > 0.7 else (0, 255, 255)
            cv2.putText(image, f"Current: {prediction}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(image, f"Confidence: {confidence:.2f}", (10, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Last spoken
        if self.last_prediction:
            cv2.putText(image, f"Last spoken: {self.last_prediction}", (10, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Instructions
        cv2.putText(image, "Show hand signs to camera - Press 'q' to quit", 
                   (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return image
    
    def run(self, camera_id: int = 0):
        """Run the simple real-time translator"""
        print("🚀 Starting Simple Sign Language Demo...")
        print("📋 Instructions:")
        print("  - Show hand signs to the camera")
        print("  - Keep hands visible and well-lit")
        print("  - Wait for audio feedback")
        print("  - Press 'q' to quit")
        print("=" * 50)
        
        # Initialize camera
        cap = cv2.VideoCapture(camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        if not cap.isOpened():
            print(f"❌ Error: Could not open camera {camera_id}")
            return
        
        # FPS tracking
        fps_counter = 0
        fps_start_time = time.time()
        fps = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Flip for mirror effect
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process with MediaPipe
                hand_results = self.hands.process(rgb_frame)
                pose_results = self.pose.process(rgb_frame)
                
                # Draw landmarks
                if hand_results.multi_hand_landmarks:
                    for hand_landmarks in hand_results.multi_hand_landmarks:
                        self.mp_drawing.draw_landmarks(
                            frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                            self.mp_drawing_styles.get_default_hand_landmarks_style(),
                            self.mp_drawing_styles.get_default_hand_connections_style()
                        )
                
                if pose_results.pose_landmarks:
                    self.mp_drawing.draw_landmarks(
                        frame, pose_results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                        self.mp_drawing_styles.get_default_pose_landmarks_style()
                    )
                
                # Extract features and classify
                prediction = ""
                confidence = 0.0
                
                if hand_results.multi_hand_landmarks:
                    # Use first hand for simplicity
                    hand_features = self._extract_hand_features(hand_results.multi_hand_landmarks[0])
                    prediction, confidence = self._classify_gesture(hand_features)
                    
                    # Smooth prediction
                    final_prediction = self._smooth_prediction(prediction, confidence)
                    
                    if final_prediction:
                        print(f"🤟 Detected: {final_prediction} (confidence: {confidence:.2f})")
                        
                        # Speak the prediction
                        try:
                            self.audio_queue.put_nowait(final_prediction)
                        except queue.Full:
                            pass
                
                # Calculate FPS
                fps_counter += 1
                if fps_counter % 30 == 0:
                    fps = 30 / (time.time() - fps_start_time)
                    fps_start_time = time.time()
                
                # Draw UI
                frame = self._draw_info(frame, prediction, confidence, fps)
                
                # Show frame
                cv2.imshow('SignLink AI - Simple Demo', frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("🧹 Demo finished!")


def main():
    """Main function"""
    print("=" * 60)
    print("🤟 SignLink AI - Simple Real-time Demo")
    print("=" * 60)
    print("📝 Note: This is a demo version with mock predictions")
    print("🎯 For real predictions, train a model first")
    print("=" * 60)
    
    translator = SimpleSignTranslator()
    translator.run()


if __name__ == "__main__":
    main()
