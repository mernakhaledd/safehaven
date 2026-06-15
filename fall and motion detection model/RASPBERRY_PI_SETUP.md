# Raspberry Pi 5 Setup Guide (First Time User)

Since this is your first time using a Raspberry Pi 5, this guide will walk you through setting up the operating system on your 16GB MicroSD card.

**Note:** A 16GB card is perfectly fine for this project. The Standard Raspberry Pi OS takes up about 4-5GB, leaving you ~10GB for your project files and system operations.

## Phase 1: Prepare the MicroSD Card (On your Windows PC)

To get the Raspberry Pi running, you need to write the operating system image to the SD card.

1.  **Download Raspberry Pi Imager**:
    *   Go to the official website: [https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/)
    *   Download and install "Raspberry Pi Imager for Windows".

2.  **Insert SD Card**:
    *   Plug your 16GB MicroSD card into your computer (you might need an SD card adapter if your laptop doesn't have a MicroSD slot).

3.  **Open Raspberry Pi Imager**:
    *   **Choose Device**: Select **Raspberry Pi 5**.
    *   **Choose OS**: Click "Choose OS". Select **Raspberry Pi OS (64-bit)**.
        *   *Tip: Do NOT choose the "Lite" version for your first time; having a Desktop interface makes things much easier.*
    *   **Choose Storage**: Click "Choose Storage" and select your 16GB MicroSD card.

4.  **Configure Settings (Crucial Step)**:
    *   When you click "Next", it will ask if you want to apply OS customization settings. Select **EDIT SETTINGS**.
    *   **General Tab**:
        *   **Set Setup User**: Create a username (e.g., `admin` or `pi`) and a secure password. **Remember these credentials!**
        *   **Set Wireless LAN**: Check this box. Enter your WiFi name (SSID) and Password.
        *   **Set Locale**: Set your Time Zone and Keyboard Layout.
    *   **Services Tab**:
        *   **Enable SSH**: Check this box and select "Use password authentication". This allows you to control the Pi remotely if needed later.
    *   Click **SAVE**.

5.  **Write**:
    *   Click **YES** to apply settings.
    *   Click **YES** to confirm erasing the SD card.
    *   Wait for the "Write" and "Verify" process to finish. It will take a few minutes.
    *   When done, remove the card from your PC.

## Phase 2: Hardware Assembly

1.  **Insert SD Card**: Slide the MicroSD card into the slot on the underside of the Raspberry Pi 5.
2.  **Connect Monitor**: Use a micro-HDMI to HDMI cable to connect the Pi to a monitor or TV. Use the port closest to the USB-C power port (HDMI0).
3.  **Connect Peripherals**: Plug in your USB Keyboard and Mouse.
4.  **Connect Camera**: Plug in your Webcam.
5.  **Power On**: Plug the USB-C power supply into the Pi.
    *   *Note: The Pi 5 needs a good power supply (5V 5A recommended). If you are using a standard phone charger, it might give a "low voltage" warning but should still boot.*

## Phase 3: First Boot

1.  The Pi should turn on, and you will see a red LED.
2.  On your monitor, you will see the Raspberry Pi Desktop load up.
3.  Since we pre-configured the WiFi and User in Phase 1, it should automatically connect to the internet.
4.  **Update Config**:
    *   Open the "Terminal" (the black icon in the top taskbar).
    *   Type the following command and press Enter:
        ```bash
        sudo apt update
        ```
    *   This ensures your package lists are up to date.

## Phase 4: Deploy Your Project

Now that your Pi is running and online, you can proceed with the **Deployment Guide** I created earlier (`DEPLOY_INSTRUCTIONS.md`).

**How to get your files onto the Pi (Easiest Method for Beginners):**
Since you are on the same WiFi:
1.  **On the Pi**: Open the web browser (Chromium).
2.  **Email/Cloud**: Log into your email or Google Drive/OneDrive.
3.  **Download**: Upload your project folder from your PC to the cloud, and then download it onto the Pi's "Desktop".
4.  **Unzip**: If you zipped the folder, right-click and "Extract Here".

Once the files are on the Pi's Desktop, follow strict **Step 3** in the `DEPLOY_INSTRUCTIONS.md` file.
