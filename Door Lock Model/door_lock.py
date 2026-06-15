import signal
import sys
import time
from gpiozero import LED
from supabase import create_client, Client

# ── Configuration ─────────────────────────────────────────────────────────────
RED_LED_PIN = 17    # Red LED = Locked
GREEN_LED_PIN = 27  # Green LED = Unlocked

# Supabase Credentials (match the ones from your Face Recognition model)
SUPABASE_URL = "https://bpndcpacnsglieziysbn.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwbmRjcGFjbnNnbGlleml5c2JuIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzkyODkxNTIsImV4cCI6MjA5NDg2NTE1Mn0"
    ".GRiGTRY7lFswrm613nGpiwvCtfYn9zWqSlbNBUvNjLw"
)

# ── Setup GPIO (gpiozero auto-detects the right backend for Pi 3 / 4 / 5) ─────
red_led = LED(RED_LED_PIN)
green_led = LED(GREEN_LED_PIN)

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def cleanup_and_exit(signum=None, frame=None):
    """Turn LEDs OFF and release GPIO pins on shutdown.

    Called for Ctrl+C (SIGINT) AND `systemctl stop` (SIGTERM) so the LEDs
    never get stuck on after the script stops.
    """
    print("\nStopping Door Lock Controller (cleanup)...")
    try:
        red_led.off()
        green_led.off()
    finally:
        red_led.close()
        green_led.close()
        print("GPIO cleaned up.")
        sys.exit(0)


# Register the cleanup for both interactive (Ctrl+C) and systemd (stop) shutdowns.
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)


def set_door_state(is_locked: bool):
    """Updates the physical LEDs based on the locked state"""
    if is_locked:
        print("[DOOR] State changed: LOCKED 🔴 (Red ON, Green OFF)")
        red_led.on()
        green_led.off()
    else:
        print("[DOOR] State changed: UNLOCKED 🟢 (Red OFF, Green ON)")
        red_led.off()
        green_led.on()


def main():
    print("Starting Smart Door Lock Controller...")

    # Track the last known state to avoid printing redundantly
    last_state = None

    try:
        while True:
            # Poll Supabase for the current door status
            try:
                response = supabase.table("door_status").select("is_locked").eq("id", 1).execute()
                data = response.data

                if data and len(data) > 0:
                    current_is_locked = data[0]["is_locked"]

                    if current_is_locked != last_state:
                        set_door_state(current_is_locked)
                        last_state = current_is_locked
            except Exception as e:
                print(f"[ERROR] Failed to fetch from Supabase: {e}")

            # Check every 1 second
            time.sleep(1)

    except KeyboardInterrupt:
        cleanup_and_exit()


if __name__ == "__main__":
    main()
