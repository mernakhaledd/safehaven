#!/bin/bash
# ======================================================================
# Safe Haven Control Panel - installer
# Run ON the Raspberry Pi, from the folder containing safehaven_control.py:
#     bash install_app.sh
# Does NOT touch your model code or your systemd services.
# ======================================================================
set -e

APP_DIR="$HOME/safehaven_app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> 1/3 Installing CustomTkinter..."
# Bookworm needs --break-system-packages; older OS ignores the fallback
pip3 install customtkinter --break-system-packages 2>/dev/null \
    || pip3 install customtkinter

echo "==> 2/3 Copying app to $APP_DIR ..."
mkdir -p "$APP_DIR"
if [ "$SCRIPT_DIR" != "$APP_DIR" ]; then
    cp "$SCRIPT_DIR/safehaven_control.py" "$APP_DIR/"
else
    echo "    (already in $APP_DIR, skipping copy)"
fi

echo "==> 3/3 Setting up auto-launch on boot..."
# XDG autostart works on BOTH the old X11/LXDE desktop and the new
# Wayland (labwc) desktop on Bookworm.
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/safehaven.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Safe Haven Control Panel
Exec=python3 $APP_DIR/safehaven_control.py
X-GNOME-Autostart-enabled=true
EOF

# Extra fallback for Pis using the wayfire compositor
if [ -f "$HOME/.config/wayfire.ini" ] && ! grep -q safehaven_control "$HOME/.config/wayfire.ini"; then
    printf '\n[autostart]\nsafehaven = python3 %s/safehaven_control.py\n' "$APP_DIR" >> "$HOME/.config/wayfire.ini"
fi

echo ""
echo "✅ Done!"
echo "   Launch now with:   python3 $APP_DIR/safehaven_control.py"
echo "   Or reboot - the app will open automatically on the desktop."
