# Clean Start Guide: Help Gesture Model on Raspberry Pi

This guide assumes your computer restarted and you want to start from scratch. We will use **Python 3.10** because it is the most compatible version for AI libraries.

## Step 1: Connect to Raspberry Pi

1.  Open **PowerShell** on your laptop.
2.  Connect to your Pi:
    ```powershell
    ssh safehaven@Safehavenpi1.local
    ```
3.  **Clean up previous attempts** (Copy and paste this into the Pi terminal):
    ```bash
    cd ~
    rm -rf help_gesture_project
    rm -rf Python-3.10.13
    rm Python-3.10.13.tgz
    ```

## Step 2: Install Python 3.10 (The Automatic Way)

Instead of typing many commands, we will send a script to the Pi to do the work.

1.  **Open a SECOND PowerShell window** on your laptop.
2.  Navigate to your project folder:
    ```powershell
    cd "c:\sign\help_gesture_detection\help_gesture_detection"
    ```
3.  **Send the installation script**:
    ```powershell
    scp install_python310.sh safehaven@Safehavenpi1.local:~/
    ```
4.  **Go back to the FIRST PowerShell window** (the one connected to the Pi).
5.  **Run the script**:
    ```bash
    chmod +x install_python310.sh
    ./install_python310.sh
    ```
    *   **WAIT**: This step will take about **15-20 minutes**. You will see a lot of text scrolling. This is normal.
    *   It is compiling Python from scratch.

## Step 3: Set Up the Project (Once Step 2 is done)

Once the previous step says "Done!", run these commands on the Pi to set up your project using the new Python 3.10.

1.  **Create Project Folder**:
    ```bash
    mkdir -p ~/help_gesture_project
    cd ~/help_gesture_project
    ```
2.  **Create Virtual Environment (Using Python 3.10)**:
    ```bash
    python3.10 -m venv venv_help
    ```
3.  **Activate it**:
    ```bash
    source venv_help/bin/activate
    ```
4.  **Install Libraries**:
    ```bash
    pip install --upgrade pip
    pip install opencv-python mediapipe-rpi4 tflite-runtime RPi.GPIO
    ```

## Step 4: Transfer Model Files

1.  Go to your **Second PowerShell Window** (on your laptop).
2.  Run these commands to send the files:
    ```powershell
    scp models/help_gesture_model.tflite safehaven@Safehavenpi1.local:~/help_gesture_project/
    scp models/label_map.json safehaven@Safehavenpi1.local:~/help_gesture_project/
    scp 4_raspberry_pi_deploy.py safehaven@Safehavenpi1.local:~/help_gesture_project/
    ```

## Step 5: Run It

1.  Go back to the **First PowerShell Window** (Pi).
2.  Run the model:
    ```bash
    python 4_raspberry_pi_deploy.py
    ```

## How to Run Again (Daily Usage)

If you turn off the Pi and come back later, follow these simple steps to start the model again:

1.  **Connect**:
    ```powershell
    ssh safehaven@Safehavenpi1.local
    ```

2.  **Go to Folder**:
    ```bash
    cd ~/help_gesture_project
    ```

3.  **Activate Environment** (IMPORTANT!):
    ```bash
    source venv_help/bin/activate
    ```
    *(You must see `(venv_help)` at the start of the line)*

4.  **Run**:
    ```bash
    python 4_raspberry_pi_deploy.py
    ```
