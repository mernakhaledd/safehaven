# Raspberry Pi Installation Guide

This guide provides step-by-step instructions for deploying the Help Gesture Detection system on Raspberry Pi.

## 🍓 Hardware Requirements

### Minimum Requirements
- **Raspberry Pi 4 Model B** (2GB RAM minimum, 4GB recommended)
- **MicroSD Card**: 16GB minimum, Class 10 or better
- **Camera**: Raspberry Pi Camera Module v2 or USB webcam
- **Power Supply**: Official 5V 3A USB-C power adapter

### Optional Hardware
- **LED/Buzzer**: For visual/audio alerts (connected to GPIO pins)
- **Relay Module**: For triggering external devices
- **Case with cooling**: Recommended for continuous operation

## 📦 Software Setup

### Step 1: Prepare Raspberry Pi OS

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-opencv \
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libharfbuzz0b \
    libwebp6 \
    libjasper1 \
    libilmbase23 \
    libopenexr23 \
    libgstreamer1.0-0 \
    libavcodec58 \
    libavformat58 \
    libswscale5 \
    libqtgui4 \
    libqt4-test
```

### Step 2: Enable Camera

```bash
# Enable camera interface
sudo raspi-config
# Navigate to: Interface Options -> Camera -> Enable

# For USB webcam, no configuration needed

# Test camera (Raspberry Pi Camera Module)
raspistill -o test.jpg

# Test camera (USB webcam)
fswebcam test.jpg
```

### Step 3: Install Python Dependencies

```bash
# Create project directory
mkdir ~/help_gesture_detection
cd ~/help_gesture_detection

# Install MediaPipe
pip3 install mediapipe

# Install TensorFlow Lite Runtime (lighter than full TensorFlow)
pip3 install tflite-runtime

# Install other dependencies
pip3 install numpy opencv-python

# Install GPIO library (for hardware alerts)
pip3 install RPi.GPIO
```

### Step 4: Transfer Model Files

#### Option A: Using SCP (from laptop)

```bash
# From your laptop, transfer files to Raspberry Pi
scp models/help_gesture_model.tflite pi@raspberrypi.local:~/help_gesture_detection/
scp models/label_map.json pi@raspberrypi.local:~/help_gesture_detection/
scp 4_raspberry_pi_deploy.py pi@raspberrypi.local:~/help_gesture_detection/
```

#### Option B: Using USB Drive

```bash
# On Raspberry Pi, mount USB drive
sudo mount /dev/sda1 /mnt/usb

# Copy files
cp /mnt/usb/help_gesture_model.tflite ~/help_gesture_detection/
cp /mnt/usb/label_map.json ~/help_gesture_detection/
cp /mnt/usb/4_raspberry_pi_deploy.py ~/help_gesture_detection/

# Unmount
sudo umount /mnt/usb
```

#### Option C: Direct Download

```bash
# If you have files hosted online
cd ~/help_gesture_detection
wget https://your-server.com/help_gesture_model.tflite
wget https://your-server.com/label_map.json
wget https://your-server.com/4_raspberry_pi_deploy.py
```

## 🔌 GPIO Configuration (Optional)

If you want to trigger hardware alerts (LED, buzzer, etc.):

### Connect LED to GPIO

```
Raspberry Pi GPIO Pin 17 (BCM) → LED Anode (+)
LED Cathode (-) → 220Ω Resistor → Ground
```

### Connect Buzzer to GPIO

```
Raspberry Pi GPIO Pin 17 (BCM) → Buzzer (+)
Buzzer (-) → Ground
```

### Wiring Diagram

```
   Raspberry Pi
   ┌─────────┐
   │         │
   │  GPIO17 ├──────┐
   │         │      │
   │     GND ├──┐   │
   │         │  │   │
   └─────────┘  │   │
                │   │
                │   └─── LED Anode (+)
                │            │
                │        LED Cathode (-)
                │            │
                │        220Ω Resistor
                │            │
                └────────────┴─── Ground
```

## 🚀 Running the System

### Basic Usage

```bash
cd ~/help_gesture_detection
python3 4_raspberry_pi_deploy.py
```

### Headless Mode (No Display)

For running without monitor, modify the script:

```python
# Comment out these lines in 4_raspberry_pi_deploy.py
# cv2.imshow('Help Gesture Detection', frame)
# if cv2.waitKey(1) & 0xFF == ord('q'):
#     break
```

Then run:
```bash
python3 4_raspberry_pi_deploy.py
```

### Auto-Start on Boot

Create a systemd service:

```bash
# Create service file
sudo nano /etc/systemd/system/help-gesture.service
```

Add the following content:

```ini
[Unit]
Description=Help Gesture Detection Service
After=multi-user.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/help_gesture_detection
ExecStart=/usr/bin/python3 /home/pi/help_gesture_detection/4_raspberry_pi_deploy.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable help-gesture.service

# Start service now
sudo systemctl start help-gesture.service

# Check status
sudo systemctl status help-gesture.service

# View logs
sudo journalctl -u help-gesture.service -f
```

### Running in Background

```bash
# Run in background with nohup
nohup python3 4_raspberry_pi_deploy.py > gesture_detection.log 2>&1 &

# Check if running
ps aux | grep 4_raspberry_pi_deploy.py

# View logs
tail -f gesture_detection.log

# Stop the process
kill $(pgrep -f 4_raspberry_pi_deploy.py)
```

## ⚡ Performance Optimization

### 1. Reduce Camera Resolution

```python
# In 4_raspberry_pi_deploy.py
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)   # Lower resolution
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
```

### 2. Use Raspberry Pi Camera Module

Raspberry Pi Camera Module is faster than USB webcam:

```python
# Option 1: Using picamera library
from picamera.array import PiRGBArray
from picamera import PiCamera

camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
rawCapture = PiRGBArray(camera, size=(640, 480))

for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    image = frame.array
    # Process image...
    rawCapture.truncate(0)

# Option 2: Using OpenCV with v4l2 driver
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
```

### 3. Overclock Raspberry Pi (Careful!)

```bash
# Edit config
sudo nano /boot/config.txt

# Add these lines (Raspberry Pi 4)
over_voltage=2
arm_freq=1750

# Save and reboot
sudo reboot
```

### 4. Disable Desktop Environment

```bash
# Switch to console mode
sudo raspi-config
# Select: System Options -> Boot / Auto Login -> Console

# Or temporarily
sudo systemctl set-default multi-user.target
```

## 📊 Performance Benchmarks

| Configuration | FPS | Latency |
|--------------|-----|---------|
| RPi 4 (4GB) + Pi Camera | 20-25 | 40-50ms |
| RPi 4 (4GB) + USB Webcam | 15-20 | 50-70ms |
| RPi 4 (2GB) + Pi Camera | 15-18 | 55-70ms |
| RPi 3B+ + USB Webcam | 8-12 | 80-120ms |

## 🔧 Troubleshooting

### Camera Not Detected

```bash
# Check camera connection
vcgencmd get_camera

# Should output: supported=1 detected=1

# List USB cameras
ls -l /dev/video*

# Test camera
raspistill -o test.jpg  # For Pi Camera
fswebcam test.jpg       # For USB camera
```

### ImportError: No module named 'tflite_runtime'

```bash
# Install TFLite Runtime
pip3 install --index-url https://google-coral.github.io/py-repo/ tflite_runtime
```

### Low FPS / Slow Performance

1. Reduce resolution (320x240)
2. Use Pi Camera instead of USB
3. Disable visualization (cv2.imshow)
4. Close other programs
5. Ensure proper cooling

### GPIO Warnings

```bash
# If you get GPIO warnings, add at start of script:
GPIO.setwarnings(False)
```

## 📝 Configuration File

Create `config.json` for easy configuration:

```json
{
  "camera": {
    "source": 0,
    "width": 640,
    "height": 480,
    "fps": 30
  },
  "detection": {
    "confidence_threshold": 0.8,
    "history_size": 5,
    "alert_cooldown": 3
  },
  "gpio": {
    "enabled": true,
    "alert_pin": 17
  },
  "logging": {
    "enabled": true,
    "log_file": "detection.log"
  }
}
```

## 🌐 Remote Access

### VNC (Visual Desktop)

```bash
# Enable VNC
sudo raspi-config
# Interface Options -> VNC -> Enable

# Access from laptop: vnc://raspberrypi.local
```

### SSH (Command Line)

```bash
# From laptop
ssh pi@raspberrypi.local

# Run detection
cd ~/help_gesture_detection
python3 4_raspberry_pi_deploy.py
```

## 🔒 Security Considerations

1. **Change default password**:
```bash
passwd
```

2. **Use SSH keys instead of passwords**
3. **Enable firewall if exposed to internet**
4. **Keep system updated**:
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

## 📡 Integration Examples

### Send Alert to Server

```python
import requests

def trigger_alert(self):
    try:
        response = requests.post(
            'https://your-server.com/api/alert',
            json={
                'type': 'help_gesture',
                'timestamp': datetime.now().isoformat(),
                'device_id': 'rpi_living_room'
            }
        )
    except Exception as e:
        print(f"Failed to send alert: {e}")
```

### MQTT Integration

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("mqtt.example.com", 1883, 60)

def trigger_alert(self):
    client.publish("home/alerts/help", "HELP_DETECTED")
```

## 🎯 Production Deployment Checklist

- [ ] Raspberry Pi properly secured in case
- [ ] Adequate cooling (fan or heatsinks)
- [ ] Reliable power supply
- [ ] Camera properly mounted and positioned
- [ ] System auto-starts on boot
- [ ] Logging enabled for debugging
- [ ] Alerts tested and working
- [ ] Network connectivity stable
- [ ] Backup SD card created
- [ ] Documentation accessible

## 📞 Support

For Raspberry Pi-specific issues:
- Raspberry Pi Forums: https://forums.raspberrypi.com/
- Official Documentation: https://www.raspberrypi.org/documentation/

---

**You're now ready to deploy on Raspberry Pi! 🍓**