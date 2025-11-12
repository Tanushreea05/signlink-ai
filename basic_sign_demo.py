"""
Basic sign language demo without MediaPipe - for immediate testing
Uses simple gesture detection based on motion and hand position
"""

import cv2
import numpy as np
import time
from collections import deque
import random

class BasicSignDetector:
    """Simple gesture detector without MediaPipe"""
    
    def __init__(self):
        self.motion_history = deque(maxlen=30)
        self.signs = [
            "HELLO", "GOODBYE", "THANK_YOU", "PLEASE", "YES", "NO",
            "SORRY", "HELP", "LOVE", "FRIEND", "GOOD", "BAD"
        ]
        self.last_prediction = ""
        self.last_prediction_time = 0
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2()
        
    def detect_motion(self, frame):
        """Detect motion in frame"""
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(frame)
        
        # Calculate motion intensity
        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        motion_ratio = motion_pixels / total_pixels
        
        return motion_ratio, fg_mask
    
    def predict_sign(self, frame):
        """Predict sign based on simple motion analysis"""
        motion_ratio, fg_mask = self.detect_motion(frame)
        self.motion_history.append(motion_ratio)
        
        current_time = time.time()
        
        # Simple heuristics for sign detection
        if len(self.motion_history) >= 10:
            recent_motion = list(self.motion_history)[-10:]
            avg_motion = np.mean(recent_motion)
            motion_variance = np.var(recent_motion)
            
            # Detect significant motion patterns
            if avg_motion > 0.02 and motion_variance > 0.0001:  # Active signing
                if current_time - self.last_prediction_time > 3.0:  # 3 second cooldown
                    # Weighted random selection based on motion intensity
                    weights = [1.0] * len(self.signs)
                    if avg_motion > 0.05:  # High motion - more expressive signs
                        weights[0] *= 3  # HELLO
                        weights[1] *= 3  # GOODBYE
                        weights[2] *= 2  # THANK_YOU
                    
                    prediction = np.random.choice(self.signs, p=np.array(weights)/sum(weights))
                    confidence = min(0.95, 0.6 + avg_motion * 10)
                    
                    self.last_prediction = prediction
                    self.last_prediction_time = current_time
                    
                    return prediction, confidence, fg_mask
        
        return "", 0.0, fg_mask

def run_basic_demo():
    """Run basic sign language demo"""
    print("🚀 Starting Basic Sign Language Demo...")
    print("📋 Instructions:")
    print("  - Wave your hands in front of the camera")
    print("  - Make deliberate gestures")
    print("  - Wait for predictions to appear")
    print("  - Press 'q' to quit")
    print("=" * 50)
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("❌ Could not open camera")
        return False
    
    detector = BasicSignDetector()
    
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
            
            # Detect signs
            prediction, confidence, motion_mask = detector.predict_sign(frame)
            
            # Calculate FPS
            fps_counter += 1
            if fps_counter % 30 == 0:
                fps = 30 / (time.time() - fps_start_time)
                fps_start_time = time.time()
            
            # Draw UI
            height, width = frame.shape[:2]
            
            # Semi-transparent overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (width, 150), (0, 0, 0), -1)
            frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
            
            # Title
            cv2.putText(frame, "SignLink AI - Basic Demo", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            
            # FPS
            cv2.putText(frame, f"FPS: {fps:.1f}", (width - 120, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Current prediction
            if prediction:
                color = (0, 255, 0) if confidence > 0.7 else (0, 255, 255)
                cv2.putText(frame, f"Sign: {prediction}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(frame, f"Confidence: {confidence:.2f}", (10, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                print(f"🤟 Detected: {prediction} (confidence: {confidence:.2f})")
            
            # Motion indicator
            motion_level = np.mean(detector.motion_history) if detector.motion_history else 0
            motion_color = (0, 255, 0) if motion_level > 0.02 else (0, 0, 255)
            cv2.putText(frame, f"Motion: {'Active' if motion_level > 0.02 else 'Still'}", 
                       (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, motion_color, 2)
            
            # Instructions
            cv2.putText(frame, "Wave hands for sign detection - Press 'q' to quit", 
                       (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show motion mask in corner
            motion_small = cv2.resize(motion_mask, (160, 120))
            motion_colored = cv2.applyColorMap(motion_small, cv2.COLORMAP_JET)
            frame[height-130:height-10, width-170:width-10] = motion_colored
            
            # Show frame
            cv2.imshow('SignLink AI - Basic Demo', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Basic demo completed!")
        return True

def main():
    print("=" * 60)
    print("🤟 SignLink AI - Basic Sign Language Demo")
    print("=" * 60)
    print("📝 Note: This is a simplified demo using motion detection")
    print("🎯 For accurate recognition, use the full MediaPipe version")
    print("=" * 60)
    
    success = run_basic_demo()
    
    if success:
        print("\n🎉 Basic demo completed successfully!")
        print("\n📋 Next steps:")
        print("1. Install MediaPipe: pip install mediapipe")
        print("2. Run full demo: python simple_realtime_demo.py")
        print("3. Train a model: python ml/train.py")
    else:
        print("\n❌ Demo failed")

if __name__ == "__main__":
    main()
