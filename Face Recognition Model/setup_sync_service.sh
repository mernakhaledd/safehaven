#!/bin/bash
# SafeHaven — installs the Face Sync Agent as an always-on background service.
# Run ON the Raspberry Pi:  sudo bash setup_sync_service.sh

echo "Setting up Face Sync Agent service..."

cat << 'EOF' > /etc/systemd/system/face_sync.service
[Unit]
Description=SafeHaven Face Sync Agent (cloud enrollment)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=safehaven
WorkingDirectory=/home/safehaven/face_recognition/Face Recognition Model
Environment="PATH=/home/safehaven/face_recognition/Face Recognition Model/venv/bin:/usr/bin"
ExecStart=/home/safehaven/face_recognition/"Face Recognition Model"/venv/bin/python /home/safehaven/face_recognition/"Face Recognition Model"/pi_sync_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable face_sync.service
systemctl restart face_sync.service

echo ""
echo "✅ Face Sync Agent installed and running."
echo "   Watch it work:   journalctl -u face_sync -f"
