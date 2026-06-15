# Raspberry Pi Re-Setup Guide (32GB Card & New WiFi)

This guide walks you through setting up your Raspberry Pi from scratch using your new 32GB SD card and connecting it to a new WiFi network. Since you are running "Headless" (no monitor attached to the Pi), we will configure everything before we even turn it on.

## Phase 1: Flash the OS with Network Settings

**On your Windows PC:**

1.  **Insert your 32GB MicroSD card** into your PC.
2.  Open **Raspberry Pi Imager**.
3.  **Choose Device**: Select **Raspberry Pi 5**.
4.  **Choose OS**: Select **Raspberry Pi OS (64-bit)**.
    *   *Note: You can choose "Raspberry Pi OS Lite (64-bit)" found under "Raspberry Pi OS (Other)" if you want a lighter installation since you aren't using a monitor, but the standard Desktop version is also fine and easier if you ever decide to plug in a screen.*
5.  **Choose Storage**: Select your 32GB SD Card.
6.  **Configure Settings (CRITICAL STEP)**:
    *   Click **Next**.
    *   When asked to apply OS customisation settings, select **EDIT SETTINGS**.
    *   **General Tab**:
        *   **Set Setup User**: 
            *   Username: `safehaven` (Recommended to keep consistency with previous guides)
            *   Password: Create a secure password.
        *   **Set Wireless LAN**:
            *   **SSID**: Enter your **NEW WiFi Name** EXACTLY.
            *   **Password**: Enter your **NEW WiFi Password**.
            *   **Country Code**: Select your country (likely US or your local code).
        *   **Set Locale**: Select your Time Zone and Keyboard Layout.
    *   **Services Tab**:
        *   **Enable SSH**: **CHECK THIS BOX**.
        *   Select "Use password authentication".
    *   Click **SAVE**, then **YES** to apply.
7.  **Write**: Click **YES** to flash the card. Wait for it to finish and verify.

---

## Phase 2: Boot and Connect

1.  **Insert the SD card** into the Raspberry Pi 5.
2.  **Power on the Pi** (Connect USB-C power).
3.  Wait about 2-3 minutes for it to boot and connect to the new WiFi.

**Connect via PowerShell:**

1.  Open **Windows PowerShell**.
2.  Run the SSH command using the hostname you set (default is usually `raspberrypi` unless you changed it in settings. If you set hostname to `Safehavenpi1` in the Imager settings, use that. If you forgot to set hostname, try `raspberrypi`).
    
    *Recommended command (if you set hostname to `Safehavenpi1`):*
    ```powershell
    ssh safehaven@Safehavenpi1.local
    ```
    
    *If you didn't change the hostname in the Imager:*
    ```powershell
    ssh safehaven@raspberrypi.local
    ```

3.  Type `yes` if asked to fingerprint.
4.  Enter the password you created in Phase 1.

---

## Phase 3: Transfer Your Code

Now we need to move your fall detection code from your PC to the Pi.

1.  Open a **NEW** PowerShell window (keep the SSH one open).
2.  Navigate to your project folder:
    ```powershell
    cd "c:\Users\DELL\OneDrive\Documents\grad project\fall and motion detection model"
    ```
3.  Use `scp` to copy the files.
    *   *Replace `Safehavenpi1` with `raspberrypi` if you didn't set a custom hostname.*
    ```powershell
    scp -r . safehaven@Safehavenpi1.local:~/fall_detection_project
    ```
4.  Enter your Pi password when prompted.

---

## Phase 4: Setup Environment on Pi

Go back to your **SSH PowerShell window** (where you are logged into the Pi).

1.  **Update System & Install OpenCV dependencies**:
    ```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y libgl1 libglib2.0-0
    ```

2.  **Navigate to project folder**:
    ```bash
    cd ~/fall_detection_project
    ```

3.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    ```

4.  **Activate Environment**:
    ```bash
    source venv/bin/activate
    ```

5.  **Install Python Dependencies**:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
    *Note: This will install `torch`, `opencv`, `ultralytics`, `numpy`, etc. It takes a few minutes.*

---

## Phase 5: Run the Model

1.  **Run Inference**:
    ```bash
    python inference.py
    ```

**Headless Notes:**
*   You will not see a camera window since there is no monitor.
*   The script is designed to print `[HEADLESS] Fall Prob: ...` in the terminal.
*   If you fall, you should see the alert text in the terminal.

## Troubleshooting

### "Remote Host Identification Has Changed" Error
If you see a big warning box saying `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!`, don't panic. This is normal when you re-install the OS. Your computer remembers the "old" Pi and notices the "new" Pi has a different security signature.

**To fix it:**
1.  Run this command in PowerShell:
    ```powershell
    ssh-keygen -R Safehavenpi1.local
    ```
    *(If you use a different hostname, replace `Safehavenpi1.local` with that).*
2.  Try the `ssh` command again. It will ask "Are you sure...", type `yes`.

## How to Run Again (Daily Usage)

If you turn off the Pi and come back later, follow these simple steps to start the model again:

1.  **Connect**:
    ```powershell
    ssh safehaven@Safehavenpi1.local
    ```

2.  **Go to Folder**:
    ```bash
    cd ~/fall_detection_project
    ```

3.  **Activate Environment** (IMPORTANT!):
    ```bash
    source venv/bin/activate
    ```
    *(You must see `(venv)` at the start of the line)*

4.  **Run**:
    ```bash
    python inference.py
    ```
