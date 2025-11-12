"""
Ultra-simple camera test without dependencies
"""

import subprocess
import sys

def check_camera_windows():
    """Check camera on Windows using PowerShell"""
    try:
        # Use PowerShell to check for camera devices
        result = subprocess.run([
            "powershell", 
            "Get-PnpDevice -Class Camera | Select-Object FriendlyName, Status"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            output = result.stdout
            if "OK" in output or "Camera" in output:
                print("✅ Camera device detected by Windows")
                print("Camera devices found:")
                print(output)
                return True
            else:
                print("⚠️ No camera devices found")
                return False
        else:
            print("⚠️ Could not check camera devices")
            return False
            
    except Exception as e:
        print(f"⚠️ Error checking camera: {e}")
        return False

def main():
    print("=" * 50)
    print("🎥 Quick Camera Check")
    print("=" * 50)
    
    print("🔍 Checking for camera devices...")
    camera_found = check_camera_windows()
    
    if camera_found:
        print("\n✅ Camera appears to be available!")
        print("\n📋 Next steps:")
        print("1. Install dependencies: pip install opencv-python mediapipe pyttsx3")
        print("2. Test camera: python test_camera.py")
        print("3. Run demo: python simple_realtime_demo.py")
    else:
        print("\n❌ No camera detected. Please:")
        print("- Connect a webcam or enable built-in camera")
        print("- Check camera permissions in Windows Settings")
        print("- Make sure no other app is using the camera")
    
    print("\n🎯 Camera Tips:")
    print("- Use good lighting (face a window)")
    print("- Position camera at chest level")
    print("- Ensure hands are visible in frame")
    print("- Use contrasting background")

if __name__ == "__main__":
    main()
    input("\nPress Enter to continue...")
