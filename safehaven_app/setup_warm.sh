#!/bin/bash
# ======================================================================
# Installs the SafeHaven WARM orchestrator (Option B) as the boot service.
# Run ON the Pi ONLY AFTER you have tested it manually and it works:
#     sudo bash setup_warm.sh
#
# It replaces the old auto-cycler (which reloaded models each turn).
# Your original model scripts and the old cycler are left in place as a
# fallback — this only changes which service starts on boot.
# ======================================================================
set -e

VENV_PY="/home/safehaven/mp_fall_project/venv_mp/bin/python"
WARM="/home/safehaven/safehaven_warm.py"

if [ ! -f "$WARM" ]; then
    echo "ERROR: $WARM not found. Copy safehaven_warm.py to /home/safehaven first."
    exit 1
fi

echo "==> Stopping the old cycler and any running models..."
systemctl stop safehaven_autocycler 2>/dev/null || true
systemctl disable safehaven_autocycler 2>/dev/null || true
for s in face_recognition fall_detection help_gesture; do
    systemctl stop "$s" 2>/dev/null || true
done

echo "==> Creating the warm service..."
cat << EOF > /etc/systemd/system/safehaven_warm.service
[Unit]
Description=SafeHaven Warm Multi-Model Orchestrator
After=multi-user.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=safehaven
WorkingDirectory=/home/safehaven
Environment="PYTHONUNBUFFERED=1"
ExecStart=$VENV_PY $WARM
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable safehaven_warm.service
systemctl restart safehaven_warm.service

echo ""
echo "✅ Warm orchestrator is now the boot service."
echo "   Watch it:         journalctl -u safehaven_warm -f"
echo "   Stop it:          sudo systemctl stop safehaven_warm"
echo "   Roll back to old: sudo systemctl disable safehaven_warm && sudo systemctl enable --now safehaven_autocycler"
