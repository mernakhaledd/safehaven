#!/bin/bash
# ======================================================================
# Installs the SafeHaven headless auto-cycler so the models start and
# cycle automatically every time the Raspberry Pi boots — no GUI.
# Run ON the Pi:   sudo bash setup_autocycler.sh
# ======================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="/home/safehaven/safehaven_autocycler.sh"

echo "==> Installing cycler script..."
if [ "$SCRIPT_DIR/safehaven_autocycler.sh" != "$TARGET" ]; then
    cp "$SCRIPT_DIR/safehaven_autocycler.sh" "$TARGET"
fi
chmod +x "$TARGET"
chown safehaven:safehaven "$TARGET"

echo "==> Creating systemd service (runs on boot, headless)..."
cat << 'EOF' > /etc/systemd/system/safehaven_autocycler.service
[Unit]
Description=SafeHaven Headless Auto Model Cycler
After=multi-user.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/bin/bash /home/safehaven/safehaven_autocycler.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> Disabling the old GUI auto-start (no longer needed)..."
rm -f /home/safehaven/.config/autostart/safehaven.desktop 2>/dev/null || true
if [ -f /home/safehaven/.config/wayfire.ini ]; then
    sed -i '/safehaven_control/d' /home/safehaven/.config/wayfire.ini 2>/dev/null || true
fi

echo "==> Enabling and starting the cycler..."
systemctl daemon-reload
systemctl enable safehaven_autocycler.service
systemctl restart safehaven_autocycler.service

echo ""
echo "✅ Done. The models now cycle automatically on every boot."
echo "   Watch it:        journalctl -u safehaven_autocycler -f"
echo "   Stop cycling:    sudo systemctl stop safehaven_autocycler"
echo "   Turn off on boot: sudo systemctl disable safehaven_autocycler"
