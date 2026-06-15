# Safe Haven Control Panel

A desktop app for the Raspberry Pi that controls your three existing
systemd services (no model code is changed):

- `face_recognition`
- `fall_detection`
- `help_gesture`

## Deploy to the Pi (from this PC)

```bash
# 1. Copy the folder to the Pi
scp -r "safehaven_app" safehaven@Safehavenpi1:~/

# 2. SSH in and install
ssh safehaven@Safehavenpi1
bash ~/safehaven_app/install_app.sh
```

## Test it

```bash
python3 ~/safehaven_app/safehaven_control.py
```

The window must run on the Pi's own screen (or VNC) — not over plain SSH.

## What you get

- One card per model with **Start / Stop / Restart** buttons
- Live status, refreshed every second: 🟢 RUNNING · 🟡 LOADING · 🔴 ERROR · ⚪ STOPPED
- **STOP ALL** button
- **⚡ Presentation Demo**: pick a model, set 5–30 s (default 10), it
  starts the model, counts down, and stops it automatically
- Auto-opens when the Pi boots to the desktop (installed by the script)

## Notes

- Buttons run exactly `sudo systemctl start|stop|restart <service>` —
  the same commands you typed before.
- To remove auto-launch: `rm ~/.config/autostart/safehaven.desktop`
