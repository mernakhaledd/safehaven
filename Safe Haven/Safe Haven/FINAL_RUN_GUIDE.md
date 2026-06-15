# Safe Haven: Final Run Guide 🚀

This guide explains exactly how to start your Raspberry Pi AI systems for the demo.

## Prerequisites
- Raspberry Pi is ON and connected to Wi-Fi.
- You are SSH'd into the Pi: `ssh safehaven@Safehavenpi1`

---

## 🟢 1. Run Fall Detection (The New System)
This uses the **MediaPipe + TFLite** model we just built. It is fast and accurate.

```bash
cd ~/mp_fall_project
source venv_mp/bin/activate
python 10_mp_pi_deploy.py
```

**What to expect:**
- Takes ~10s to load.
- Prints `Fall Prob: 0.xx`.
- If you fall, prints `🚨 FALL DETECTED!` and sends alert to App.

---

## 🔵 2. Run Help Gesture (The Original System)
This uses the original MediaPipe Hands model.

```bash
cd ~/help_gesture_project
source venv_help/bin/activate
python 4_raspberry_pi_deploy_lite.py
```

**What to expect:**
- Prints `Prediction: Neutral`.
- If you do the sign, prints `🚨 HELP GESTURE DETECTED!` and sends alert to App.

---

## ⚡ Pro Tip: Run Both at Once
You can open **Two SSH Windows** (Terminal tabs).
- Window 1: Run Fall Detection.
- Window 2: Run Help Gesture.

*Note: Running both at once might slow down the frame rate since they share the CPU. For the best demo, run one at a time.*

---

## 🛠 Troubleshooting
**If it says `ModuleNotFoundError`:**
You probably forgot to activate the environment (`source venv...`).

**If it says `Camera busy`:**
Another script is using the camera. Press `Ctrl+C` in other windows to stop them.

**If Supabase alert fails:**
Check Wi-Fi. The scripts print `[CLOUD] ☁️ Alert Sent` if successful.
