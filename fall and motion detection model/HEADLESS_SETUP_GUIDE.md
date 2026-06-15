# Headless Setup and Deployment Guide (No Monitor)

Since you are connecting via WiFi without a monitor (Headless), you will control the Raspberry Pi entirely from your Windows PowerShell using SSH.

**Your Configuration:**
*   **Hostname:** `Safehavenpi1`
*   **Username:** `safehaven`
*   **Method:** PowerShell (SSH)

## Step 1: Connect to the Raspberry Pi (SSH)

1.  On your Windows PC, open **PowerShell**.
2.  Run the following command to connect:
    ```powershell
    ssh safehaven@Safehavenpi1.local
    ```
    *   If that doesn't work, try `ssh safehaven@Safehavenpi1`.
    *   If asked "Are you sure you want to continue connecting?", type `yes` and press Enter.
3.  Enter the password you created when setting up the SD card.
    *   *Note: You won't see the characters appearing when typing the password. This is normal.*

**Success:** You should see a prompt like `safehaven@Safehavenpi1:~ $`. You are now inside the Pi!

## Step 2: Update the System

Run this command inside the SSH session to make sure the Pi is ready:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y libgl1 libglib2.0-0
```

## Step 3: Transfer Files from Windows to Pi

You cannot use the drag-and-drop method since you have no visual desktop. We will use `scp` (Secure Copy) from **Windows PowerShell**.

1.  Open a **NEW** PowerShell window (keep the SSH one open for running commands).
2.  Navigate to your project folder on Windows:
    ```powershell
    cd "c:\Users\DELL\OneDrive\Documents\grad project\fall and motion detection model"
    ```
3.  Run this command to send all files to the Pi:
    ```powershell
    scp -r . safehaven@Safehavenpi1.local:~/fall_detection_project
    ```
    *   This copies the *current folder* (`.`) to a folder named `fall_detection_project` in your home directory on the Pi.
    *   Enter your Pi password when prompted.

## Step 4: Setup Python Environment (On the Pi)

Go back to your **first PowerShell window** (the one connected to the Pi via SSH).

1.  Navigate to the new folder:
    ```bash
    cd ~/fall_detection_project
    ```
2.  Create the virtual environment:
    ```bash
    python3 -m venv venv
    ```
3.  Activate it:
    ```bash
    source venv/bin/activate
    ```
4.  Install dependencies:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
    *This will take a few minutes (especially installing torch).*

## Step 5: Run the Fall Detection Model

Ensure your Webcam is plugged into the Pi. Then run:

```bash
python inference.py
```

**Note on Headless Running:**
*   Since you have no monitor, you won't see the video feed window.
*   I have modified `inference.py` to detect this. Instead of crashing, it will print status updates to your terminal (e.g., `[HEADLESS] Fall Prob: 0.12`).
*   If a fall is detected, you will see the **ALERT** message in the logs.

## Troubleshooting

*   **"Could not resolve hostname"**: If `Safehavenpi1.local` doesn't work, you need the IP address.
    *   Log in to your WiFi Router's admin page to find the IP of `Safehavenpi1`.
    *   Then use `ssh safehaven@<IP_ADDRESS>`.
*   **"Permission denied"**: Ensure you are typing the correct password.
