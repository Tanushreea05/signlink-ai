"""
Minimal camera demo for testing - no ML dependencies required
"""

def run_camera_demo():
    """Run basic camera demo"""
    try:
        import cv2
        import numpy as np
        import time
        
        print("🚀 Starting camera demo...")
        print("📹 Press 'q' to quit, 's' to take screenshot")
        
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Could not open camera")
            return False
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("✅ Camera initialized successfully")
        
        # FPS calculation
        fps_counter = 0
        fps_start_time = time.time()
        fps = 0
        
        screenshot_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame")
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Calculate FPS
            fps_counter += 1
            if fps_counter % 30 == 0:
                fps = 30 / (time.time() - fps_start_time)
                fps_start_time = time.time()
            
            # Draw info on frame
            height, width = frame.shape[:2]
            
            # Semi-transparent overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (width, 100), (0, 0, 0), -1)
            frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
            
            # Draw text
            cv2.putText(frame, "SignLink AI - Camera Test", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(frame, f"FPS: {fps:.1f}", (width - 120, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to quit, 's' for screenshot", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame
            cv2.imshow('SignLink AI - Camera Demo', frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("👋 Quitting...")
                break
            elif key == ord('s'):
                screenshot_count += 1
                filename = f"screenshot_{screenshot_count:03d}.jpg"
                cv2.imwrite(filename, frame)
                print(f"📸 Screenshot saved: {filename}")
        
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Camera demo completed")
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install: pip install opencv-python")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("🎥 SignLink AI - Minimal Camera Demo")
    print("=" * 60)
    print("📋 This demo tests your camera without ML dependencies")
    print("🎯 Perfect for verifying camera setup before full demo")
    print("=" * 60)
    
    success = run_camera_demo()
    
    if success:
        print("\n🎉 Camera demo successful!")
        print("\n📋 Next steps:")
        print("1. Install ML packages: pip install mediapipe pyttsx3")
        print("2. Run full demo: python simple_realtime_demo.py")
    else:
        print("\n❌ Camera demo failed")
        print("Please check camera connection and permissions")

if __name__ == "__main__":
    main()
