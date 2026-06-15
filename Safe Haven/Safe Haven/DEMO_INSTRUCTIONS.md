# Safe Haven Demo Guide (Cloud Integration)

This guide is your cheat sheet for running the presentation.

**System Type:** Cloud-Based (Supabase).
**Network:** Devices only need Internet access. They do NOT need to be on same WiFi.

---

## 🟢 Part 1: Start the Mobile App (Laptop)

1. Open **VS Code** on your laptop.
2. Open a **New Terminal** (Ctrl + `).
3. Start the app:
   ```powershell
   cd "c:\Users\DELL\OneDrive\Documents\grad project\Safe Haven\Safe Haven"
   npm run web
   ```
4. Open Browser: `http://localhost:8081`
5. **Check Success:**
   - Log in.
   - Click the Big Red Text: **"View ALERTS (Integration Live)"**.
   - Verify Banner says: **"● Connected to Safe Haven Cloud"**.

---

## 🔴 Part 2: Detection Models (Raspberry Pi)

You need to connect to your Pi via SSH to run the models.
Since you have 1 Camera, **run only one model at a time.**

**1. Log into Pi:**
Open PowerShell: `ssh safehaven@Safehavenpi1`

### Scenario A: Fall Detection
To demo Fall Detection:

1. **Run:**
   ```bash
   cd ~/fall_detection_project
   # Activate venv if you have one, or just:
   source venv/bin/activate
   python3 inference.py
   ```
2. **Action:** Simulate a fall in front of camera.
3. **Observe:** The alert appears on your Laptop instantly.
4. **Stop:** Press **Ctrl + C**.

### Scenario B: Help Gesture
Open PowerShell: `ssh safehaven@Safehavenpi1`
To demo Help Gesture:

1. **Run:**
   ```bash
   cd ~/help_gesture_project
   source venv_help/bin/activate
   python 4_raspberry_pi_deploy_lite.py
   ```
2. **Action:** Show "Help" Gesture (Palm -> Tuck Thumb -> Fist).
3. **Observe:** The alert appears on your Laptop instantly.
4. **Stop:** Press **Ctrl + C**.

---

## ❓ FAQ for Demo

**Q: Where is the data stored?**
A: It is sent to a Supabase Cloud Database (PostgreSQL) in real-time.

**Q: Does it work if I am outside?**
A: Yes. As long as the Pi has internet (WiFi/Hotspot) and your laptop has internet, they can talk.

**Q: Why don't you run both models at once?**
A: "For this demo hardware, we have a single camera input. In a production version, we would use a more powerful edge device or multiple camera streams."

**Troubleshooting:**
- **App Stuck?** Refresh the browser.
- **Pi Script Crash?** Camera might be busy. Run `pkill python` on Pi to reset.
