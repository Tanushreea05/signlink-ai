# 🤟 Real-time Sign Language Translator Guide

## 🚀 Quick Start (5 Minutes)

### Option 1: Simple Demo (No Model Required)

```bash
# 1. Install dependencies
pip install opencv-python mediapipe pyttsx3 numpy

# 2. Run simple demo
python simple_realtime_demo.py
```

### Option 2: Automated Setup

```bash
# Run setup script
python setup_realtime.py

# Then run demo
python simple_realtime_demo.py
# OR
run_demo.bat  # Windows
./run_demo.sh # Linux/Mac
```

### Option 3: Full System with Trained Model

```bash
# 1. Generate sample data
python ml/data/generate_sample_data.py --output sample_data

# 2. Train model (5-10 minutes)
python ml/train.py --config ml/configs/demo_config.yaml --epochs 10

# 3. Run real-time translator
python realtime_translator.py --model models/checkpoints/best_model.pth
```

## 📹 Camera Setup

### Requirements
- **Camera**: Built-in webcam or USB camera
- **Resolution**: 720p or higher recommended
- **Frame Rate**: 30 FPS minimum
- **Lighting**: Good, even lighting on hands and face
- **Background**: Contrasting, non-cluttered background

### Positioning
- **Distance**: 2-3 feet from camera
- **Height**: Camera at chest/shoulder level
- **Angle**: Straight on, slight downward angle OK
- **Hands**: Keep both hands visible in frame

## 🎯 Usage Instructions

### Controls
- **'q'**: Quit application
- **'s'**: Save current frame (debug mode)
- **'r'**: Reset prediction history
- **Ctrl+C**: Emergency stop

### Best Practices
1. **Start with clear signs**: HELLO, THANK_YOU, GOODBYE
2. **Hold signs steady**: 2-3 seconds per sign
3. **Wait for feedback**: Listen for audio confirmation
4. **Good lighting**: Face a window or use good lighting
5. **Stable position**: Keep camera and body stable

## 🔧 Configuration Options

### Command Line Arguments

```bash
python realtime_translator.py [OPTIONS]

Options:
  --model PATH          Path to trained model checkpoint
  --classes PATH        Path to class names file  
  --camera INT          Camera device ID (default: 0)
  --confidence FLOAT    Confidence threshold (default: 0.7)
  --sequence-length INT Frames for temporal analysis (default: 30)
  --device STRING       Device: cuda/cpu (default: cuda)
  --save-frames         Save frames for debugging
```

### Examples

```bash
# Basic usage with default camera
python realtime_translator.py

# Use specific model and camera
python realtime_translator.py --model my_model.pth --camera 1

# Lower confidence for more predictions
python realtime_translator.py --confidence 0.5

# CPU-only mode
python realtime_translator.py --device cpu

# Debug mode with frame saving
python realtime_translator.py --save-frames
```

## 🤖 Model Training

### Quick Training

```bash
# Generate synthetic data
python ml/data/generate_sample_data.py \
  --output sample_data \
  --signs-per-language 10 \
  --samples-per-sign 20

# Train model
python ml/train.py \
  --config ml/configs/demo_config.yaml \
  --epochs 20 \
  --batch-size 8
```

### Custom Dataset

```bash
# 1. Organize your data:
# sample_data/
# ├── train/
# │   ├── HELLO/
# │   │   ├── sample_001.npy
# │   │   └── sample_002.npy
# │   └── GOODBYE/
# └── val/

# 2. Create class names file
echo -e "HELLO\nGOODBYE\nTHANK_YOU" > models/class_names.txt

# 3. Train
python ml/train.py --config your_config.yaml
```

## 🔊 Audio Configuration

### Text-to-Speech Engines

#### Windows (Default: SAPI)
```python
# Automatic - uses Windows built-in TTS
import pyttsx3
engine = pyttsx3.init()
```

#### Linux (Requires espeak)
```bash
# Install espeak
sudo apt-get install espeak espeak-data

# Test
espeak "Hello world"
```

#### macOS (Default: NSSpeechSynthesizer)
```python
# Automatic - uses macOS built-in TTS
import pyttsx3
engine = pyttsx3.init()
```

### Audio Settings

```python
# Adjust speech rate (words per minute)
engine.setProperty('rate', 150)    # Default: 200

# Adjust volume (0.0 to 1.0)
engine.setProperty('volume', 0.8)  # Default: 1.0

# Change voice (if available)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)  # Female voice
engine.setProperty('voice', voices[1].id)  # Male voice
```

## 🐛 Troubleshooting

### Camera Issues

**Problem**: Camera not detected
```bash
# List available cameras (Linux)
ls /dev/video*

# Test camera (Windows)
python -c "import cv2; cap=cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed')"
```

**Problem**: Poor video quality
- Check camera resolution: `cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)`
- Improve lighting conditions
- Clean camera lens
- Try different USB port

### Audio Issues

**Problem**: No audio output
```bash
# Windows: Check audio drivers
# Linux: Install audio packages
sudo apt-get install pulseaudio alsa-utils

# Test TTS
python -c "import pyttsx3; e=pyttsx3.init(); e.say('test'); e.runAndWait()"
```

**Problem**: Audio delay
- Use headphones to avoid feedback
- Reduce system audio latency
- Close other audio applications

### Performance Issues

**Problem**: Low FPS
- Reduce camera resolution
- Use CPU-only mode: `--device cpu`
- Close other applications
- Reduce sequence length: `--sequence-length 15`

**Problem**: High CPU usage
- Enable GPU acceleration: `--device cuda`
- Reduce MediaPipe complexity
- Lower camera frame rate

### Model Issues

**Problem**: Poor predictions
- Increase training data
- Improve data quality
- Adjust confidence threshold
- Retrain with better parameters

**Problem**: Model not loading
- Check file path
- Verify model format
- Check class names file
- Ensure compatible PyTorch version

## 📊 Performance Optimization

### Hardware Recommendations

**Minimum Requirements**:
- CPU: Intel i5 / AMD Ryzen 5
- RAM: 8GB
- Camera: 720p USB webcam
- OS: Windows 10, Ubuntu 18.04, macOS 10.14

**Recommended**:
- CPU: Intel i7 / AMD Ryzen 7
- RAM: 16GB
- GPU: NVIDIA GTX 1060 or better
- Camera: 1080p webcam with good low-light performance

### Software Optimization

```python
# Optimize OpenCV
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer lag
cap.set(cv2.CAP_PROP_FPS, 30)        # Set target FPS

# Optimize MediaPipe
hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=2,              # Reduce if only one hand needed
    min_detection_confidence=0.7, # Higher = fewer false positives
    min_tracking_confidence=0.5   # Lower = more responsive
)
```

## 🎯 Sign Language Tips

### Effective Signing
1. **Clear hand shapes**: Make distinct finger positions
2. **Proper spacing**: Keep hands separated when needed
3. **Consistent movement**: Smooth, deliberate motions
4. **Face the camera**: Maintain good angle
5. **Practice common signs**: Start with basic vocabulary

### Common Signs to Practice
- **Greetings**: HELLO, GOODBYE, NICE-TO-MEET-YOU
- **Courtesy**: PLEASE, THANK_YOU, SORRY, EXCUSE_ME
- **Basic needs**: WATER, FOOD, HELP, BATHROOM
- **Responses**: YES, NO, MAYBE, I-DON'T-KNOW
- **Family**: MOTHER, FATHER, SISTER, BROTHER

## 📈 Accuracy Improvement

### Data Collection Tips
1. **Multiple angles**: Record from different viewpoints
2. **Various lighting**: Different lighting conditions
3. **Different signers**: Multiple people for diversity
4. **Consistent labeling**: Accurate sign annotations
5. **Quality control**: Review and clean data

### Training Tips
1. **Data augmentation**: Rotation, scaling, noise
2. **Balanced dataset**: Equal samples per class
3. **Validation split**: 20% for testing
4. **Early stopping**: Prevent overfitting
5. **Learning rate scheduling**: Gradual reduction

## 🤝 Contributing

### Adding New Signs
1. Collect video data for new sign
2. Extract keypoints using MediaPipe
3. Add to training dataset
4. Update class names file
5. Retrain model
6. Test accuracy

### Improving the System
- Better gesture recognition algorithms
- Multi-language support
- Real-time feedback mechanisms
- Mobile app integration
- Cloud-based inference

## 📞 Support

### Getting Help
- **Documentation**: Check this guide first
- **Issues**: Create GitHub issue with details
- **Discussions**: Join community discussions
- **Email**: Contact maintainers

### Reporting Bugs
Include:
- Operating system and version
- Python version
- Camera specifications
- Error messages and logs
- Steps to reproduce

---

**Happy Signing! 🤟**

For more information, see:
- [Main README](README.md)
- [Architecture Documentation](docs/architecture.md)
- [Project Summary](PROJECT_SUMMARY.md)
