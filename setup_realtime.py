"""
Setup script for real-time sign language translator.

This script helps set up the environment and dependencies for real-time translation.
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import shutil
from pathlib import Path


def run_command(command, description=""):
    """Run a system command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} detected. Python 3.8+ required.")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def check_camera():
    """Check if camera is available"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("✅ Camera is working")
                return True
        print("⚠️ Camera not detected or not working")
        return False
    except ImportError:
        print("⚠️ OpenCV not installed, cannot test camera")
        return False


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    # Install basic requirements
    if not run_command("pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install from requirements file
    if os.path.exists("requirements_realtime.txt"):
        if not run_command("pip install -r requirements_realtime.txt", "Installing real-time requirements"):
            return False
    else:
        # Install manually if requirements file doesn't exist
        packages = [
            "opencv-python==4.8.1.78",
            "mediapipe==0.10.8",
            "torch==2.1.1",
            "torchvision==0.16.1",
            "numpy==1.24.3",
            "pyttsx3==2.90",
            "Pillow==10.1.0",
            "scipy==1.11.4"
        ]
        
        for package in packages:
            if not run_command(f"pip install {package}", f"Installing {package}"):
                print(f"⚠️ Failed to install {package}, continuing...")
    
    return True


def setup_audio_windows():
    """Setup audio for Windows"""
    if platform.system() != "Windows":
        return True
    
    print("🔊 Setting up Windows audio...")
    try:
        # Test pyttsx3
        import pyttsx3
        engine = pyttsx3.init()
        engine.say("Audio test")
        engine.runAndWait()
        print("✅ Windows TTS working")
        return True
    except Exception as e:
        print(f"⚠️ Windows TTS setup issue: {e}")
        print("💡 Try installing: pip install pywin32")
        return False


def setup_audio_linux():
    """Setup audio for Linux"""
    if platform.system() != "Linux":
        return True
    
    print("🔊 Setting up Linux audio...")
    
    # Check for espeak
    if not run_command("which espeak", "Checking espeak"):
        print("💡 Install espeak: sudo apt-get install espeak espeak-data")
        return False
    
    return True


def create_sample_model():
    """Create a sample model for testing"""
    print("🤖 Creating sample model structure...")
    
    # Create model directory
    model_dir = Path("models/checkpoints")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Create class names file
    class_names = [
        "HELLO", "GOODBYE", "THANK_YOU", "PLEASE", "YES", "NO",
        "SORRY", "HELP", "LOVE", "FRIEND", "GOOD", "BAD",
        "HAPPY", "SAD", "WATER", "FOOD", "HOME", "WORK",
        "FAMILY", "TIME", "HOW", "WHAT", "WHERE", "WHEN"
    ]
    
    with open(model_dir / "class_names.txt", "w") as f:
        for name in class_names:
            f.write(f"{name}\n")
    
    print("✅ Sample model structure created")
    return True


def test_mediapipe():
    """Test MediaPipe installation"""
    print("🖐️ Testing MediaPipe...")
    try:
        import mediapipe as mp
        import cv2
        import numpy as np
        
        # Create a simple test
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(static_image_mode=True, max_num_hands=1)
        
        # Create a dummy image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        results = hands.process(test_image)
        
        print("✅ MediaPipe working correctly")
        return True
    except Exception as e:
        print(f"❌ MediaPipe test failed: {e}")
        return False


def create_demo_script():
    """Create a quick demo launcher script"""
    demo_script = """@echo off
echo Starting SignLink AI Real-time Demo...
echo.
echo Make sure your camera is connected and working!
echo Press Ctrl+C to stop the demo.
echo.
python simple_realtime_demo.py
pause
"""
    
    with open("run_demo.bat", "w") as f:
        f.write(demo_script)
    
    # Also create a shell script for Linux/Mac
    shell_script = """#!/bin/bash
echo "Starting SignLink AI Real-time Demo..."
echo ""
echo "Make sure your camera is connected and working!"
echo "Press Ctrl+C to stop the demo."
echo ""
python3 simple_realtime_demo.py
"""
    
    with open("run_demo.sh", "w") as f:
        f.write(shell_script)
    
    # Make shell script executable
    if platform.system() != "Windows":
        os.chmod("run_demo.sh", 0o755)
    
    print("✅ Demo launcher scripts created")
    return True


def main():
    """Main setup function"""
    print("=" * 60)
    print("🤟 SignLink AI - Real-time Translator Setup")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Test MediaPipe
    if not test_mediapipe():
        print("❌ MediaPipe test failed")
        return False
    
    # Setup audio based on platform
    system = platform.system()
    if system == "Windows":
        setup_audio_windows()
    elif system == "Linux":
        setup_audio_linux()
    else:
        print("✅ macOS detected - TTS should work out of the box")
    
    # Check camera
    check_camera()
    
    # Create sample model structure
    create_sample_model()
    
    # Create demo scripts
    create_demo_script()
    
    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. Test the simple demo:")
    print("   python simple_realtime_demo.py")
    print("\n2. Or use the launcher:")
    if platform.system() == "Windows":
        print("   run_demo.bat")
    else:
        print("   ./run_demo.sh")
    
    print("\n3. For full functionality, train a model:")
    print("   python ml/data/generate_sample_data.py")
    print("   python ml/train.py --config ml/configs/demo_config.yaml")
    print("   python realtime_translator.py --model models/checkpoints/best_model.pth")
    
    print("\n🎯 Camera Tips:")
    print("- Ensure good lighting")
    print("- Keep hands visible in frame")
    print("- Use contrasting background")
    print("- Position camera at chest level")
    
    print("\n🔊 Audio Tips:")
    print("- Adjust system volume")
    print("- Use headphones to avoid feedback")
    print("- Check microphone permissions if needed")
    
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ Setup successful! Ready to use real-time translator.")
