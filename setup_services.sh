#!/bin/bash

# SafeHaven Systemd Service Setup Script
# Run this on your Raspberry Pi!
# Command: sudo bash setup_services.sh

echo "========================================="
echo "   Setting up SafeHaven Services..."
echo "========================================="

# 1. Door Lock Service (Starts Automatically on Boot)
echo "Setting up Door Lock Service..."
cat << 'EOF' > /etc/systemd/system/door_lock.service
[Unit]
Description=SafeHaven Door Lock Listener
After=network.target

[Service]
Type=simple
User=safehaven
WorkingDirectory=/home/safehaven
Environment="PATH=/home/safehaven/face_recognition/Face Recognition Model/venv/bin:/usr/bin"
ExecStart=/home/safehaven/face_recognition/"Face Recognition Model"/venv/bin/python /home/safehaven/door_lock.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 2. Face Recognition Service (On-Demand)
echo "Setting up Face Recognition Service..."
cat << 'EOF' > /etc/systemd/system/face_recognition.service
[Unit]
Description=SafeHaven Face Recognition Model
After=network.target

[Service]
Type=simple
User=safehaven
WorkingDirectory=/home/safehaven/face_recognition/Face Recognition Model
Environment="PATH=/home/safehaven/face_recognition/Face Recognition Model/venv/bin:/usr/bin"
ExecStart=/home/safehaven/face_recognition/"Face Recognition Model"/venv/bin/python /home/safehaven/face_recognition/"Face Recognition Model"/recognize_pi_camera.py
Restart=no
EOF

# 3. Fall Detection Service (On-Demand)
echo "Setting up Fall Detection Service..."
cat << 'EOF' > /etc/systemd/system/fall_detection.service
[Unit]
Description=SafeHaven Fall Detection Model
After=network.target

[Service]
Type=simple
User=safehaven
WorkingDirectory=/home/safehaven/mp_fall_project
Environment="PATH=/home/safehaven/mp_fall_project/venv_mp/bin:/usr/bin"
ExecStart=/home/safehaven/mp_fall_project/venv_mp/bin/python 10_mp_pi_deploy.py
Restart=no
EOF

# 4. Help Gesture Service (On-Demand)
echo "Setting up Help Gesture Service..."
cat << 'EOF' > /etc/systemd/system/help_gesture.service
[Unit]
Description=SafeHaven Help Gesture Model
After=network.target

[Service]
Type=simple
User=safehaven
WorkingDirectory=/home/safehaven/help_gesture_project
Environment="PATH=/home/safehaven/help_gesture_project/venv_help/bin:/usr/bin"
ExecStart=/home/safehaven/help_gesture_project/venv_help/bin/python 6_universal_deploy.py
Restart=no
EOF

# Reload systemd to recognize the new files
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable only the Door Lock to start on boot
echo "Enabling Door Lock to start on boot..."
systemctl enable door_lock.service

# Start the door lock service immediately
echo "Starting Door Lock Service..."
systemctl start door_lock.service

echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "How to use your new services:"
echo ""
echo "The Door Lock is running automatically in the background."
echo ""
echo "To start a vision model for demonstration, type:"
echo "  sudo systemctl start face_recognition"
echo "  sudo systemctl start fall_detection"
echo "  sudo systemctl start help_gesture"
echo ""
echo "CRITICAL: Remember to STOP one model before starting the next one!"
echo "To stop a model, type:"
echo "  sudo systemctl stop face_recognition"
echo "========================================="
