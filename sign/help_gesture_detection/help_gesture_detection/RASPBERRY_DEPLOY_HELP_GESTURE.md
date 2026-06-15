# Deploying Help Gesture Model to Raspberry Pi

This guide will help you upload and run your **Help Gesture Detection** model on the Raspberry Pi. We will set it up as a separate project so it doesn't interfere with your Fall Detection system.

## Phase 1: Transfer Files to Pi

**CRITICAL NOTE: Where is the SD Card?**
**LEAVE THE SD CARD INSIDE THE RASPBERRY PI.**
You do not need to take it out. The Pi should be powered on and connected to WiFi. We are sending the files "over the air" from your laptop to the Pi.

1.  **Open a NEW PowerShell window** on your laptop.
2.  **Navigate to your Help Gesture project folder**:
    ```powershell
    cd "c:\sign\help_gesture_detection\help_gesture_detection"
    ```
3.  **Create a new folder on the Pi**:
    ```powershell
    ssh safehaven@Safehavenpi1.local "mkdir -p ~/help_gesture_project"
    ```
4.  **Send the model and config**:
    ```powershell
    scp models/help_gesture_model.tflite safehaven@Safehavenpi1.local:~/help_gesture_project/
    scp models/label_map.json safehaven@Safehavenpi1.local:~/help_gesture_project/
    ```
5.  **Send the script** (Keeping original filename):
    ```powershell
    scp 4_raspberry_pi_deploy.py safehaven@Safehavenpi1.local:~/help_gesture_project/
    ```

---

## Phase 2: Setup Environment (On the Pi)

Now we need to install the specific libraries for this model.

1.  **Connect to the Pi** (in your main PowerShell window):
    ```powershell
    ssh safehaven@Safehavenpi1.local
    ```
2.  **Go to the new folder**:
    ```bash
    cd ~/help_gesture_project
    ```
3.  **Create a new Virtual Environment**:
    ```bash
    python3 -m venv venv_help
    ```
4.  **Activate it**:
    ```bash
    source venv_help/bin/activate
    ```
5.  **Install Dependencies**:
    Run these commands one by one:
    ```bash
    pip install --upgrade pip
    
    # Install OpenCV (Older version to match our system fix)
    pip install "opencv-python<4.10"
    
    # Install MediaPipe (This is the heavy one)
    pip install mediapipe
    
    # Install TFLite Runtime (Lighter than full TensorFlow)
    pip install tflite-runtime
    
    # Install GPIO for alerts
    pip install RPi.GPIO
    ```

---

## Phase 3: Run the Model

1.  **Make sure the Webcam is plugged in.**
2.  **Run the script** (using the original filename):
    ```bash
    python 4_raspberry_pi_deploy.py
    ```

### Important Headless Note
Since you are using the Pi without a monitor ("Headless"), the `cv2.imshow` command in the script might crash it. I recommend we modify the script slightly to run safely in headless mode.

**If it crashes with "cannot open display":**
We will edit the file on the Pi to disable the video window.
1.  Open the file: `nano 4_raspberry_pi_deploy.py`
2.  Scroll down to line ~238 (`cv2.imshow...`).
3.  Add a `#` at the start of that line to comment it out:
    ```python
    # cv2.imshow('Help Gesture Detection', frame)
    ```
4.  Do the same for the `cv2.waitKey` block below it.
5.  Press `Ctrl+X`, then `Y`, then `Enter` to save.

Then run `python 4_raspberry_pi_deploy.py` again.
