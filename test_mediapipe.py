"""
Test MediaPipe functionality
"""

import cv2
import mediapipe as mp
import numpy as np

def test_mediapipe():
    """Test MediaPipe hands detection"""
    print("🚀 Testing MediaPipe...")
    
    # Initialize MediaPipe
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Camera not available")
        return False
    
    print("✅ MediaPipe and camera initialized")
    print("📹 Show your hands to the camera")
    print("Press 'q' to quit")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process with MediaPipe
            results = hands.process(rgb_frame)
            
            # Draw landmarks
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Print detection
                if frame_count % 30 == 0:  # Every 30 frames
                    print(f"✋ Hands detected: {len(results.multi_hand_landmarks)}")
            
            # Add text
            cv2.putText(frame, "MediaPipe Test - Press 'q' to quit", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if results.multi_hand_landmarks:
                cv2.putText(frame, f"Hands: {len(results.multi_hand_landmarks)}", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show frame
            cv2.imshow('MediaPipe Test', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
    
    print("✅ MediaPipe test completed!")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🖐️ MediaPipe Hands Test")
    print("=" * 50)
    
    success = test_mediapipe()
    
    if success:
        print("\n🎉 MediaPipe is working correctly!")
        print("Ready for sign language detection!")
    else:
        print("\n❌ MediaPipe test failed")
