import cv2
import pickle
import numpy as np
import time
import os

# Try to import GPIO and picamera2 (Raspberry Pi specific)
try:
    import gpiozero
    GPIO_AVAILABLE = True
    green_led = gpiozero.LED(17)  # Green LED → Door UNLOCKED
    red_led   = gpiozero.LED(27)  # Red LED   → Door LOCKED
    print("[GPIO] GPIO initialized successfully.")
except ImportError:
    GPIO_AVAILABLE = False
    print("[GPIO] gpiozero not found. Running without GPIO (PC mode).")

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
    print("[CAMERA] picamera2 found. Will use Raspberry Pi Camera.")
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("[CAMERA] picamera2 not found. Falling back to cv2.VideoCapture(0).")

# ─── Configuration ────────────────────────────────────────────────────────────
EMBEDDINGS_FILE   = "embeddings/embeddings.pkl"
THRESHOLD         = 0.363   # SFace cosine similarity threshold (higher = stricter)
UNLOCK_DURATION   = 5       # seconds the door stays unlocked after a known face
ALERT_COOLDOWN    = 10      # seconds between repeated unknown-person alerts
FRAME_WIDTH       = 640
FRAME_HEIGHT      = 480
# ──────────────────────────────────────────────────────────────────────────────

detector   = cv2.FaceDetectorYN_create("face_detection_yunet_2023mar.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF_create("face_recognition_sface_2021dec.onnx", "")


# ─── GPIO helpers ─────────────────────────────────────────────────────────────
def lock_door():
    print("[DOOR] 🔴 LOCKED")
    if GPIO_AVAILABLE:
        red_led.on()
        green_led.off()

def unlock_door():
    print("[DOOR] 🟢 UNLOCKED")
    if GPIO_AVAILABLE:
        green_led.on()
        red_led.off()

def cleanup_gpio():
    if GPIO_AVAILABLE:
        green_led.off()
        red_led.off()


# ─── Embeddings ───────────────────────────────────────────────────────────────
def load_embeddings():
    if not os.path.exists(EMBEDDINGS_FILE):
        print("[ERROR] Embeddings file not found! Run enroll.py first.")
        return [], []
    with open(EMBEDDINGS_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"[INFO] Loaded {len(data['names'])} embeddings: {set(data['names'])}")
    return data["encodings"], data["names"]


# ─── Frame processing ─────────────────────────────────────────────────────────
def process_frame(frame, known_encodings, known_names):
    height, width, _ = frame.shape
    detector.setInputSize((width, height))

    _, faces = detector.detect(frame)

    face_locations = []
    face_names     = []

    if faces is not None:
        for face in faces:
            x, y, w, h = list(map(int, face[:4]))
            face_locations.append((x, y, w, h))

            name = "Unknown"
            aligned_face = recognizer.alignCrop(frame, face)
            feature      = recognizer.feature(aligned_face)

            if known_encodings:
                best_idx   = -1
                max_score  = -1.0
                for idx, known_feat in enumerate(known_encodings):
                    score = recognizer.match(known_feat, feature[0], cv2.FaceRecognizerSF_FR_COSINE)
                    if score > max_score:
                        max_score = score
                        best_idx  = idx

                if max_score >= THRESHOLD:
                    name = known_names[best_idx]

            face_names.append(name)

    return face_locations, face_names


# ─── Camera setup ─────────────────────────────────────────────────────────────
def init_camera():
    """Returns a capture object (Picamera2 or cv2.VideoCapture)."""
    if PICAMERA2_AVAILABLE:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "BGR888"}
        )
        picam2.configure(config)
        picam2.start()
        time.sleep(1)  # warm-up
        print(f"[CAMERA] Pi Camera started at {FRAME_WIDTH}x{FRAME_HEIGHT}.")
        return picam2, "picamera2"
    else:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        if not cap.isOpened():
            raise RuntimeError("[CAMERA] Could not open any camera!")
        print(f"[CAMERA] USB/webcam started at {FRAME_WIDTH}x{FRAME_HEIGHT}.")
        return cap, "opencv"

def read_frame(cam, cam_type):
    """Reads one BGR frame from whichever camera backend is active."""
    if cam_type == "picamera2":
        frame = cam.capture_array()
        return True, frame
    else:
        return cam.read()

def release_camera(cam, cam_type):
    if cam_type == "picamera2":
        cam.stop()
    else:
        cam.release()


# ─── Main loop ────────────────────────────────────────────────────────────────
def main():
    known_encodings, known_names = load_embeddings()

    cam, cam_type = init_camera()

    lock_door()  # start in locked state

    last_alert_time  = 0
    last_unlock_time = 0
    door_unlocked    = False

    print("\n[SYSTEM] SafeHaven running. Press 'q' to quit.\n")

    try:
        while True:
            ret, frame = read_frame(cam, cam_type)
            if not ret or frame is None:
                print("[ERROR] Failed to grab frame. Exiting.")
                break

            start_time = time.time()
            face_locations, face_names = process_frame(frame, known_encodings, known_names)
            fps = 1.0 / max(time.time() - start_time, 1e-6)

            now = time.time()

            # ── Door logic ────────────────────────────────────────────────────
            known_detected = any(n != "Unknown" for n in face_names)

            if known_detected:
                if not door_unlocked:
                    unlock_door()
                    door_unlocked = True
                last_unlock_time = now

            if door_unlocked and (now - last_unlock_time > UNLOCK_DURATION):
                lock_door()
                door_unlocked = False

            # ── Draw results ──────────────────────────────────────────────────
            for (x, y, w, h), name in zip(face_locations, face_names):
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.rectangle(frame, (x, y + h), (x + w, y + h + 30), color, cv2.FILLED)
                cv2.putText(frame, name, (x + 5, y + h + 22),
                            cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

                print(f"[{fps:.1f} FPS] Detected: {name}")

                # ── Unknown alert ─────────────────────────────────────────────
                if name == "Unknown" and (now - last_alert_time > ALERT_COOLDOWN):
                    ts = time.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"\n[ALERT] 🚨 UNKNOWN PERSON at {ts}")
                    try:
                        from pi_supabase_trigger import send_alert_to_cloud
                        send_alert_to_cloud("UNKNOWN_PERSON", 1.0)
                    except Exception as e:
                        print(f"[ALERT] Could not send cloud alert: {e}")
                    last_alert_time = now

            # ── FPS overlay ───────────────────────────────────────────────────
            door_status = "UNLOCKED" if door_unlocked else "LOCKED"
            cv2.putText(frame, f"FPS: {fps:.1f}  Door: {door_status}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # ── Display (skipped gracefully if headless SSH) ───────────────────
            try:
                cv2.imshow("SafeHaven - Door Camera", frame)
            except cv2.error:
                pass

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[SYSTEM] Interrupted by user.")
    finally:
        lock_door()
        cleanup_gpio()
        release_camera(cam, cam_type)
        cv2.destroyAllWindows()
        print("[SYSTEM] Shutdown complete.")


if __name__ == "__main__":
    main()
