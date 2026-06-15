import gpiozero
import time

# --- Configuration ---
green_led = gpiozero.LED(17)  # Green LED → Door UNLOCKED
red_led = gpiozero.LED(27)    # Red LED   → Door LOCKED

def lock_door():
    """Red LED ON, Green LED OFF → Door is LOCKED"""
    print("[SYSTEM] Locking door... 🔴 RED ON | 🟢 GREEN OFF")
    red_led.on()
    green_led.off()

def unlock_door():
    """Green LED ON, Red LED OFF → Door is UNLOCKED"""
    print("[SYSTEM] Unlocking door... 🔴 RED OFF | 🟢 GREEN ON")
    green_led.on()
    red_led.off()

if __name__ == "__main__":
    try:
        print("=== SafeHaven Door Lock Demo ===")

        # 1. Start locked
        lock_door()
        time.sleep(3)

        # 2. Unlock
        unlock_door()
        time.sleep(4)

        # 3. Lock again
        lock_door()
        time.sleep(3)

    except KeyboardInterrupt:
        print("\n[SYSTEM] Demo interrupted by user.")
    finally:
        green_led.off()
        red_led.off()
        print("[SYSTEM] LEDs off. Done.")
