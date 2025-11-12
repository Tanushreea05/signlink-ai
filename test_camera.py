"""
Quick camera test script to verify camera functionality
"""

import sys

def test_camera():
    """Test if camera is accessible"""
    try:
        import cv2
        print("✅ OpenCV imported successfully")
        
        # Try to open camera
        print("🔍 Testing camera access...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Camera 0 not accessible, trying camera 1...")
            cap = cv2.VideoCapture(1)
            
        if not cap.isOpened():
            print("❌ No camera found. Please check:")
            print("  - Camera is connected")
            print("  - Camera permissions are granted")
            print("  - No other application is using the camera")
            return False
            
        # Test reading a frame
        ret, frame = cap.read()
        if ret:
            height, width = frame.shape[:2]
            print(f"✅ Camera working! Resolution: {width}x{height}")
            
            # Show camera feed for 5 seconds
            print("📹 Showing camera feed for 5 seconds...")
            print("Press 'q' to quit early")
            
            import time
            start_time = time.time()
            
            while time.time() - start_time < 5:
                ret, frame = cap.read()
                if ret:
                    cv2.imshow('Camera Test - Press Q to quit', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                        
            cv2.destroyAllWindows()
            cap.release()
            print("✅ Camera test completed successfully!")
            return True
        else:
            print("❌ Could not read from camera")
            cap.release()
            return False
            
    except ImportError:
        print("❌ OpenCV not installed. Run: pip install opencv-python")
        return False
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🎥 SignLink AI - Camera Test")
    print("=" * 50)
    
    success = test_camera()
    
    if success:
        print("\n🎉 Camera test passed! Ready for real-time translation.")
        print("\nNext steps:")
        print("1. Run: python simple_realtime_demo.py")
        print("2. Or run: python realtime_translator.py")
    else:
        print("\n❌ Camera test failed. Please fix camera issues first.")
        
    input("\nPress Enter to exit...")
