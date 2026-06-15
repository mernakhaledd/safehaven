#!/bin/bash
# ======================================================================
# SafeHaven Headless Auto-Cycler
# Runs automatically on boot (via safehaven_autocycler.service).
# No GUI, no screen, nothing to open. It simply starts each AI model
# in turn for 15 seconds, loops forever, and frees the camera between
# models so they never clash.
# ======================================================================

SERVICES=("face_recognition" "fall_detection" "help_gesture")
RUN_SECONDS=15      # how long each model runs
GAP_SECONDS=3       # pause so the camera is released before the next model

# When the cycler is stopped (or crashes), stop whatever model is running too,
# so it never leaves a model holding the camera in the background.
cleanup() {
    echo "[CYCLER] Stopping all models before exit."
    for s in "${SERVICES[@]}"; do
        systemctl stop "$s" 2>/dev/null
    done
}
trap cleanup EXIT INT TERM

echo "[CYCLER] SafeHaven auto-cycler starting."

# Make sure nothing is already holding the camera
for s in "${SERVICES[@]}"; do
    systemctl stop "$s" 2>/dev/null
done
sleep "$GAP_SECONDS"

# Loop forever: each model runs RUN_SECONDS, then the next one
while true; do
    for s in "${SERVICES[@]}"; do
        echo "[CYCLER] Starting $s for ${RUN_SECONDS}s"
        systemctl start "$s"
        sleep "$RUN_SECONDS"
        systemctl stop "$s"
        sleep "$GAP_SECONDS"
    done
done
