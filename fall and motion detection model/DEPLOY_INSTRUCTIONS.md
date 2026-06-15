# Deployment Guide: Fall Detection System on Raspberry Pi 5

**First Time User?**
If you haven't set up your Raspberry Pi yet, please read **[RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md)** first.

## Prerequisites

*   **Raspberry Pi 5** (4GB or 8GB RAM recommended)
*   **MicroSD Card** (16GB minimum) with **Raspberry Pi OS (64-bit)** installed.
*   **USB Webcam** or **Raspberry Pi Camera Module**.
*   **Internet Connection** on the Pi.

## Step 1: Transfer Files to Raspberry Pi

You need to move your project files to the Raspberry Pi. You can use a USB flash drive, or transfer them over the network (using SCP or FileZilla).

**Files required:**
*   `inference.py`
*   `train_model.py`
*   `dataset_config.py`
*   `fall_detection_lstm.pth`
*   `yolov8n-pose.pt`
*   `requirements.txt`

**Recommended:** Create a folder named `fall_detection` on your Pi's Desktop and put these files inside.

## Step 2: System Setup (On the Raspberry Pi)

Open a **Terminal** on your Raspberry Pi and run the following commands to update the system and install system dependencies.

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies for OpenCV
sudo apt install -y libgl1-mesa-glx
```

## Step 3: Set up Python Environment

Raspberry Pi OS (Bookworm) requires using a Virtual Environment to install Python packages.

1.  **Navigate to your project folder:**
    ```bash
    cd ~/Desktop/fall_detection
    ```
    *(Adjust the path if you placed the folder elsewhere)*

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    ```

3.  **Activate the environment:**
    ```bash
    source venv/bin/activate
    ```
    *(You should see `(venv)` appear at the start of your command prompt)*

4.  **Install Python Libraries:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
    *Note: The `ultralytics` package (YOLOv8) will automatically install `torch` and `torchvision`. This might take a few minutes.*

## Step 4: connect Hardware

1.  Connect your **Webcam** to a USB port.
2.  If using a **Pi Camera**, ensure it is connected and enabled.

## Step 5: Run the Model

With the virtual environment activated (`source venv/bin/activate`), run:

```bash
python inference.py
```

### Troubleshooting
*   **"Model file not found"**: Ensure `fall_detection_lstm.pth` is in the same folder where you are running the command.
*   **Camera issues**: If the camera doesn't open, try running `python inference.py 0` or change the `0` to `1` (sometimes the Pi maps cameras differently).
*   **Slow performance**: The Raspberry Pi 5 is fast, but if it feels sluggish:
    *   Ensure you are using the official Power Supply (5V 5A).
    *   YOLOv8 Nano (`yolov8n-pose.pt`) is optimized for speed, but running both YOLO and LSTM logic in Python can be demanding.

## Step 6 (Optional): Auto-Start on Boot

If you want this to run automatically when the Pi turns on:

1.  Create a startup script `start_fall_detection.sh`:
    ```bash
    #!/bin/bash
    cd /home/pi/Desktop/fall_detection
    source venv/bin/activate
    python inference.py
    ```
2.  Make it executable:
    ```bash
    chmod +x start_fall_detection.sh
    ```
3.  Add it to your autostart configuration or crontab (e.g., `@reboot /home/pi/Desktop/fall_detection/start_fall_detection.sh`).
