"""
SafeHaven – Raspberry Pi Face Recognition (local only, no cloud)
================================================================
Runs on a Raspberry Pi with the official Pi Camera (via picamera2).
Falls back to a USB webcam / cv2.VideoCapture(0) if picamera2 is absent.

Behaviour
---------
• Detects every face in the live camera feed using YuNet.
• Matches each face against the enrolled embeddings (SFace cosine similarity).
• Prints to the terminal for every detection:
    – Known person  → [KNOWN]   <name>  score=X.XXX
    – Unknown face  → [UNKNOWN] Unknown score=X.XXX

Setup (on the Pi)
-----------------
1.  pip install -r requirements_pi.txt
2.  python enroll.py          # build embeddings/embeddings.pkl from dataset/
3.  python recognize_pi_camera.py
"""

import cv2
import pickle
import time
import os

# Disable display output when running headless (e.g. over SSH with no monitor).
# Must be set before any cv2 GUI call is reached.
os.environ.setdefault("DISPLAY", "")

# ── Optional Pi Camera ────────────────────────────────────────────────────────
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
    print("[CAMERA] picamera2 found – will use Raspberry Pi Camera.")
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("[CAMERA] picamera2 not found – falling back to cv2.VideoCapture(0).")

# ── Configuration ─────────────────────────────────────────────────────────────
EMBEDDINGS_FILE = "embeddings/embeddings.pkl"
THRESHOLD       = 0.363   # SFace cosine similarity (higher = stricter match)
ALERT_COOLDOWN  = 10      # seconds between repeated log messages per person
FRAME_WIDTH     = 640
FRAME_HEIGHT    = 480
# ─────────────────────────────────────────────────────────────────────────────

# Load YuNet detector and SFace recognizer (pure OpenCV, CPU-only)
detector   = cv2.FaceDetectorYN_create(
    "face_detection_yunet_2023mar.onnx", "", (320, 320)
)
recognizer = cv2.FaceRecognizerSF_create(
    "face_recognition_sface_2021dec.onnx", ""
)


# ── Embeddings ────────────────────────────────────────────────────────────────
def load_embeddings():
    if not os.path.exists(EMBEDDINGS_FILE):
        print("[ERROR] embeddings.pkl not found – run enroll.py first.")
        return [], []
    with open(EMBEDDINGS_FILE, "rb") as f:
        data = pickle.load(f)
    names = data["names"]
    print(f"[INFO] Loaded {len(names)} embeddings for: {sorted(set(names))}")
    return data["encodings"], names


# ── Frame processing ──────────────────────────────────────────────────────────
def process_frame(frame, known_encodings, known_names):
    """
    Detect and recognise all faces in *frame*.
    Returns list of (x, y, w, h, name, score).
    """
    h, w, _ = frame.shape
    detector.setInputSize((w, h))

    _, faces = detector.detect(frame)
    results  = []

    if faces is None:
        return results

    for face in faces:
        x, y, fw, fh = list(map(int, face[:4]))

        aligned   = recognizer.alignCrop(frame, face)
        feature   = recognizer.feature(aligned)
        name      = "Unknown"
        max_score = -1.0
        best_idx  = -1

        for idx, known_feat in enumerate(known_encodings):
            score = recognizer.match(
                known_feat, feature[0], cv2.FaceRecognizerSF_FR_COSINE
            )
            if score > max_score:
                max_score = score
                best_idx  = idx

        if known_encodings and max_score >= THRESHOLD:
            name = known_names[best_idx]

        results.append((x, y, fw, fh, name, max_score))

    return results


# ── Camera helpers ────────────────────────────────────────────────────────────
def init_camera():
    if PICAMERA2_AVAILABLE:
        picam2 = Picamera2()
        cfg    = picam2.create_preview_configuration(
            main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "BGR888"}
        )
        picam2.configure(cfg)
        picam2.start()
        time.sleep(1)   # warm-up
        print(f"[CAMERA] Pi Camera started at {FRAME_WIDTH}×{FRAME_HEIGHT}.")
        return picam2, "picamera2"
    else:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        if not cap.isOpened():
            raise RuntimeError("[CAMERA] Could not open any camera!")
        print(f"[CAMERA] USB/webcam started at {FRAME_WIDTH}×{FRAME_HEIGHT}.")
        return cap, "opencv"

def read_frame(cam, cam_type):
    if cam_type == "picamera2":
        return True, cam.capture_array()
    return cam.read()

def release_camera(cam, cam_type):
    if cam_type == "picamera2":
        cam.stop()
    else:
        cam.release()


# ── Snapshots: capture a frame & handle on-demand photo requests ──────────────
import requests as _rq
from pi_supabase_trigger import SUPABASE_URL as _SB_URL, SUPABASE_KEY as _SB_KEY

_SNAP_HEADERS = {"apikey": _SB_KEY, "Authorization": f"Bearer {_SB_KEY}"}


def _household_id():
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "household_id.txt")
    try:
        return open(f).read().strip()
    except Exception:
        return None


def capture_and_upload(frame):
    """Save one camera frame as a JPG in the 'snapshots' bucket; return a
    shareable signed URL (valid 7 days), or None on failure."""
    try:
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        hid  = _household_id() or "unknown"
        path = f"{hid}/{int(time.time() * 1000)}.jpg"
        up = _rq.post(
            f"{_SB_URL}/storage/v1/object/snapshots/{path}",
            headers={**_SNAP_HEADERS, "Content-Type": "image/jpeg", "x-upsert": "true"},
            data=buf.tobytes(), timeout=10,
        )
        if up.status_code not in (200, 201):
            print(f"[SNAP] upload failed {up.status_code}: {up.text}")
            return None
        sign = _rq.post(
            f"{_SB_URL}/storage/v1/object/sign/snapshots/{path}",
            headers={**_SNAP_HEADERS, "Content-Type": "application/json"},
            json={"expiresIn": 604800}, timeout=10,
        )
        if sign.status_code != 200:
            print(f"[SNAP] sign failed {sign.status_code}: {sign.text}")
            return None
        return f"{_SB_URL}/storage/v1{sign.json()['signedURL']}"
    except Exception as e:
        print(f"[SNAP] capture error: {e}")
        return None


def check_photo_requests(frame):
    """Fulfil any pending on-demand photo requests for this household."""
    hid = _household_id()
    try:
        q = (f"{_SB_URL}/rest/v1/photo_requests?status=eq.pending"
             "&select=id,requested_by,household_id")
        if hid:
            q += f"&household_id=eq.{hid}"
        rows = _rq.get(q, headers=_SNAP_HEADERS, timeout=8).json()
        if not rows:
            return
        for r in rows:
            url = capture_and_upload(frame)
            _rq.patch(
                f"{_SB_URL}/rest/v1/photo_requests?id=eq.{r['id']}",
                headers={**_SNAP_HEADERS, "Content-Type": "application/json",
                         "Prefer": "return=minimal"},
                json={"status": "done", "photo_url": url}, timeout=8,
            )
            try:
                from pi_supabase_trigger import send_alert_to_cloud
                send_alert_to_cloud("Care Receiver Photo", "Live Photo", 1.0,
                                    photo_url=url)
            except Exception as e:
                print(f"[SNAP] alert failed: {e}")
            print("[SNAP] On-demand photo request fulfilled.")
    except Exception as e:
        print(f"[SNAP] request check error: {e}")


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    known_encodings, known_names = load_embeddings()
    if not known_names:
        print("[WARN] No embeddings loaded – all detections will be 'Unknown'.")

    cam, cam_type = init_camera()

    # Per-person cooldown tracker  { person_name: last_log_timestamp }
    last_logged: dict = {}
    last_req_check = 0.0   # throttle on-demand photo-request polling

    print("\n[SYSTEM] SafeHaven Face Recognition running. Press Ctrl+C to stop.\n")

    try:
        while True:
            ret, frame = read_frame(cam, cam_type)
            if not ret or frame is None:
                print("[ERROR] Failed to grab frame – exiting.")
                break

            # Clean copy for photos (before any boxes/labels are drawn on it)
            clean_frame = frame.copy()

            t0      = time.time()
            results = process_frame(frame, known_encodings, known_names)
            fps     = 1.0 / max(time.time() - t0, 1e-6)
            now     = time.time()

            # ── On-demand: caregiver requested a live photo ───────────────
            if now - last_req_check > 3:
                check_photo_requests(clean_frame)
                last_req_check = now

            for (x, y, w, h, name, score) in results:
                # ── Draw bounding box ─────────────────────────────────────────
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.rectangle(frame, (x, y + h), (x + w, y + h + 30), color, cv2.FILLED)
                label = f"{name} ({score:.2f})" if name != "Unknown" else "Unknown"
                cv2.putText(
                    frame, label, (x + 5, y + h + 22),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1
                )

                # ── Terminal log (with per-person cooldown) ───────────────────
                if now - last_logged.get(name, 0) > ALERT_COOLDOWN:
                    ts = time.strftime('%Y-%m-%d %H:%M:%S')
                    photo_url = None
                    if name == "Unknown":
                        print(f"[{ts}] 🚨 UNKNOWN PERSON detected  score={score:.3f}")
                        alert_type = "Unknown Person Detected at the Door"

                        # Capture the intruder's photo for the caregiver
                        photo_url = capture_and_upload(clean_frame)

                        # ── Lock the door automatically ──
                        try:
                            from pi_supabase_trigger import SUPABASE_URL, SUPABASE_KEY
                            import requests
                            url = f"{SUPABASE_URL}/rest/v1/door_status?id=eq.1"
                            headers = {
                                "apikey": SUPABASE_KEY,
                                "Authorization": f"Bearer {SUPABASE_KEY}",
                                "Content-Type": "application/json",
                                "Prefer": "return=minimal"
                            }
                            requests.patch(url, headers=headers, json={"is_locked": True}, timeout=3)
                            print("[DOOR] 🔒 Door locked due to Unknown Person")
                        except Exception as e:
                            print(f"[DOOR] Failed to lock door: {e}")
                            
                    else:
                        print(f"[{ts}] 👤 KNOWN: {name}  score={score:.3f}")
                        alert_type = f"{name} Detected at the Door"
                    
                    try:
                        from pi_supabase_trigger import send_alert_to_cloud
                        send_alert_to_cloud(alert_type, name, score, photo_url=photo_url)
                    except ImportError:
                        print("[ALERT] pi_supabase_trigger.py not found.")
                    except Exception as e:
                        print(f"[ALERT SYSTEM] Failed to send alert: {e}")
                        
                    last_logged[name] = now

            # ── FPS overlay ───────────────────────────────────────────────────
            cv2.putText(
                frame, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
            )

            # ── Display (skipped gracefully when headless over SSH) ───────────
            # Completely disabled to prevent Qt C++ aborts in headless mode.
            # try:
            #     cv2.imshow("SafeHaven – Face Recognition", frame)
            #     if cv2.waitKey(1) & 0xFF == ord('q'):
            #         break
            # except Exception:
            #     pass

    except KeyboardInterrupt:
        print("\n[SYSTEM] Stopped by user.")
    finally:
        release_camera(cam, cam_type)
        # cv2.destroyAllWindows()
        print("[SYSTEM] Shutdown complete.")


if __name__ == "__main__":
    main()
