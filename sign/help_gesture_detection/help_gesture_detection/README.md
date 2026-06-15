# Help Gesture Detection System

A complete end-to-end system for detecting a custom "help" gesture using MediaPipe and deep learning, deployable on laptop and Raspberry Pi.

## 🎯 Project Overview

This system detects a specific "help" gesture where:
- Right hand shows thumbs up
- Left hand is positioned palm-up below the right hand

The model can recognize this gesture from any angle, distance, and lighting condition.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Camera Input                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           MediaPipe Hand Detection                       │
│     (Detects 21 landmarks per hand × 2 hands)           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│          Feature Extraction & Normalization              │
│         (126-dimensional feature vector)                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Deep Neural Network Classifier                   │
│       (Dense layers with dropout & batch norm)          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           Gesture Classification                         │
│    (help_gesture / no_gesture / other_gesture)          │
└─────────────────────────────────────────────────────────┘
```

## 📋 Requirements

### For Laptop (Training & Testing)
```bash
opencv-python==4.8.1.78
mediapipe==0.10.9
numpy==1.24.3
tensorflow==2.15.0
scikit-learn==1.3.2
matplotlib==3.8.2
```

### For Raspberry Pi (Deployment)
```bash
opencv-python
mediapipe
numpy
tflite-runtime
RPi.GPIO  # Optional: for hardware alerts
```

## 🚀 Quick Start Guide

### Step 1: Setup Environment (Laptop)

```bash
# Clone or download the project
cd help_gesture_detection

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Collect Training Data

```bash
python 1_data_collection.py
```

**Instructions:**
1. Press **'0'** and hold to collect HELP gesture samples
2. Move your hands around, change angles, distances, lighting
3. Collect **200-300 samples** (more is better)
4. Press **'1'** to collect negative samples (no gesture or random poses)
5. Collect **200-300 negative samples**
6. Press **'2'** for other random gestures (optional)
7. Press **'q'** when done

**Tips for good data collection:**
- Vary the distance from camera (close, medium, far)
- Try different angles and orientations
- Change lighting conditions
- Include background variations
- Collect samples from different people (if possible)

### Step 3: Train the Model

```bash
python 2_train_model.py
```

This will:
- Load all collected samples
- Augment the dataset
- Train a neural network
- Save the model in two formats:
  - `models/help_gesture_model.h5` (for laptop)
  - `models/help_gesture_model.tflite` (for Raspberry Pi)
- Generate training history plot

**Expected output:**
```
Training set: ~800 samples
Test set: ~200 samples
Test Accuracy: 95-99%
```

### Step 4: Test on Laptop

```bash
python 3_test_realtime.py
```

**Features:**
- Real-time gesture detection
- Confidence scores
- Visual alerts when help gesture is detected
- Press 's' to save snapshots
- Press 'q' to quit

### Step 5: Deploy to Raspberry Pi

#### 5a. Transfer Files to Raspberry Pi

```bash
# Copy necessary files to Raspberry Pi
scp models/help_gesture_model.tflite pi@raspberrypi.local:~/
scp models/label_map.json pi@raspberrypi.local:~/
scp 4_raspberry_pi_deploy.py pi@raspberrypi.local:~/
```

#### 5b. Install Dependencies on Raspberry Pi

```bash
# SSH into Raspberry Pi
ssh pi@raspberrypi.local

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-opencv python3-pip

# Install Python packages
pip3 install mediapipe tflite-runtime numpy
```

#### 5c. Run on Raspberry Pi

```bash
python3 4_raspberry_pi_deploy.py
```

## 📊 Model Performance

### Architecture Details

```
Input: 126 features (21 landmarks × 3 coords × 2 hands)
├── Dense(256) + ReLU + BatchNorm + Dropout(0.3)
├── Dense(128) + ReLU + BatchNorm + Dropout(0.3)
├── Dense(64) + ReLU + BatchNorm + Dropout(0.2)
├── Dense(32) + ReLU
└── Dense(3) + Softmax (output classes)

Total Parameters: ~100K
TFLite Model Size: ~400 KB
```

### Performance Metrics

| Metric | Value |
|--------|-------|
| Test Accuracy | 95-99% |
| Inference Time (Laptop) | ~10-15 ms |
| Inference Time (RPi 4) | ~30-50 ms |
| Model Size | 400 KB |
| FPS (Laptop) | 30-60 |
| FPS (Raspberry Pi) | 15-25 |

## 🔧 Advanced Configuration

### Adjusting Detection Sensitivity

In `3_test_realtime.py` or `4_raspberry_pi_deploy.py`:

```python
# Change detection confidence threshold
if gesture == 'help_gesture' and confidence > 0.8:  # Default: 0.8
    # Trigger alert
```

Lower threshold (e.g., 0.7) = more sensitive (more false positives)
Higher threshold (e.g., 0.9) = less sensitive (fewer false positives)

### Prediction Smoothing

```python
self.history_size = 5  # Number of frames to smooth over
```

Higher value = smoother but slower response
Lower value = more responsive but jittery

### GPIO Alert Configuration (Raspberry Pi)

```python
# Set GPIO pin for alert (LED, buzzer, etc.)
ALERT_PIN = 17  # BCM pin numbering

# Or disable GPIO alerts
ALERT_PIN = None
```

## 🎨 Customization

### Adding More Gesture Classes

1. Modify `gesture_classes` in `1_data_collection.py`:
```python
self.gesture_classes = {
    '0': 'help_gesture',
    '1': 'no_gesture',
    '2': 'other_gesture',
    '3': 'thumbs_up',      # Add new gesture
    '4': 'peace_sign',     # Add new gesture
}
```

2. Collect data for new gestures
3. Retrain the model

### Custom Alert Actions

In `4_raspberry_pi_deploy.py`, modify `trigger_alert()`:

```python
def trigger_alert(self):
    # Send email notification
    # Play audio alert
    # Send HTTP request to server
    # Activate relay/actuator
    # Log to database
    pass
```

## 📁 Project Structure

```
help_gesture_detection/
├── 1_data_collection.py       # Data collection script
├── 2_train_model.py           # Model training script
├── 3_test_realtime.py         # Laptop testing script
├── 4_raspberry_pi_deploy.py   # Raspberry Pi deployment
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── dataset/                   # Training data (created after step 2)
│   ├── help_gesture/
│   ├── no_gesture/
│   └── other_gesture/
└── models/                    # Trained models (created after step 3)
    ├── help_gesture_model.h5
    ├── help_gesture_model.tflite
    ├── label_map.json
    └── training_history.png
```

## 🐛 Troubleshooting

### Camera Not Working

```bash
# Test camera access
python3 -c "import cv2; print(cv2.VideoCapture(0).read())"

# Try different camera index
cap = cv2.VideoCapture(1)  # or 2, 3, etc.
```

### Low FPS on Raspberry Pi

1. Reduce camera resolution:
```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
```

2. Disable visualization:
```python
# Comment out these lines
# self.mp_draw.draw_landmarks(...)
# cv2.imshow(...)
```

3. Use Raspberry Pi Camera Module (faster than USB camera)

### Poor Detection Accuracy

1. Collect more training data (500+ samples per class)
2. Ensure variety in training data (angles, distances, lighting)
3. Adjust confidence threshold
4. Retrain with more epochs

### MediaPipe Installation Issues

```bash
# For Raspberry Pi OS (32-bit)
pip3 install mediapipe-rpi4

# For other systems
pip3 install mediapipe --upgrade
```

## 🎯 Use Cases

- **Elderly Care**: Emergency help signal detection
- **Security Systems**: Distress signal recognition
- **Smart Home**: Custom gesture controls
- **Accessibility**: Assistive technology for disabled persons
- **IoT Projects**: Gesture-based device control

## 📈 Future Enhancements

- [ ] Add multi-person detection
- [ ] Implement gesture tracking across frames
- [ ] Add cloud logging and analytics
- [ ] Support for more complex gesture sequences
- [ ] Mobile app integration
- [ ] Web dashboard for monitoring

## 📚 Technical References

- [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands.html)
- [TensorFlow Lite for Microcontrollers](https://www.tensorflow.org/lite/microcontrollers)
- [OpenCV Documentation](https://docs.opencv.org/)

## 🤝 Contributing

Feel free to:
- Report bugs
- Suggest improvements
- Add new features
- Share your results

## 📝 License

This project is open source and available for educational and personal use.

## 🙏 Acknowledgments

- Google MediaPipe team for the hand tracking solution
- TensorFlow team for the deep learning framework
- OpenCV community for computer vision tools

---

**Happy Gesture Detecting! 🖐️**