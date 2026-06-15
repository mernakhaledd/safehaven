#!/usr/bin/env python3
"""
SafeHaven Warm Orchestrator  (Option B, robust camera handling)
===============================================================
Warm-loads help + fall once, and rotates the camera between three turns:

    FACE  -> original face_recognition service (picamera2), untouched.
    FALL  -> warm MediaPipe Pose + TFLite (rpicam-vid).
    HELP  -> warm MediaPipe Hands + TFLite (rpicam-vid).

The camera is handed between picamera2 (face) and rpicam-vid (fall/help).
This version never blocks forever waiting for frames: if the camera is not
producing (a cold-boot handoff race), it automatically closes and reopens
rpicam-vid until frames flow again.

Run with the FALL venv (full TensorFlow + mediapipe + opencv):
    /home/safehaven/mp_fall_project/venv_mp/bin/python safehaven_warm.py
Test one warm model: ... safehaven_warm.py fall   |   ... help
"""

import os
import sys
import json
import time
import pickle
import select
import subprocess
from datetime import datetime

import cv2
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
FACE_DIR = "/home/safehaven/face_recognition/Face Recognition Model"
HELP_DIR = "/home/safehaven/help_gesture_project"
FALL_DIR = "/home/safehaven/mp_fall_project"

sys.path.insert(0, FACE_DIR)
from pi_supabase_trigger import send_alert_to_cloud   # noqa: E402

# ── Settings ──────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 640, 480
FRAME_LEN = int(WIDTH * HEIGHT * 1.5)     # YUV420
FRAMERATE = 10
RUN_SECONDS = 15
GAP_SECONDS = 4
FACE_SERVICE = "face_recognition"
ORDER = ["face", "fall", "help"]
WARM = ["fall", "help"]


# ══════════════════════════════════════════════════════════════════════════════
# HELP  (mirrors 6_universal_deploy.py)
# ══════════════════════════════════════════════════════════════════════════════
class HelpModel:
    def __init__(self):
        print("[WARM] Loading help model (MediaPipe Hands + TFLite)...")
        try:
            import tensorflow as tf
            Interpreter = tf.lite.Interpreter
        except ImportError:
            import tflite_runtime.interpreter as tflite
            Interpreter = tflite.Interpreter
        import mediapipe as mp

        self.interpreter = Interpreter(model_path=os.path.join(HELP_DIR, "help_gesture_model.tflite"))
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        lm = os.path.join(HELP_DIR, "label_map.json")
        if os.path.exists(lm):
            self.label_map = {int(k): v for k, v in json.load(open(lm)).items()}
        else:
            self.label_map = {0: 'help_gesture', 1: 'no_gesture'}

        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False, max_num_hands=2,
            min_detection_confidence=0.7, min_tracking_confidence=0.5)

        self.prediction_history = []
        self.history_size = 5
        self.help_detection_time = None
        self.alert_cooldown = 3
        self.consecutive_frames = 0

    def on_activate(self):
        self.prediction_history = []
        self.consecutive_frames = 0

    def _extract(self, results):
        if not results.multi_hand_landmarks:
            return None
        lst = []
        for hand in results.multi_hand_landmarks:
            v = []
            for lm in hand.landmark:
                v.extend([lm.x, lm.y, lm.z])
            lst.append(v)
        if len(lst) == 2:
            return np.concatenate(lst)
        if len(lst) == 1:
            return np.concatenate([lst[0], np.zeros(63)])
        return None

    def _normalize(self, landmarks):
        coords = landmarks.reshape(-1, 3)
        if len(coords) >= 21:
            coords[:21] -= coords[0]
            if len(coords) > 21:
                coords[21:] -= coords[21]
        return coords.flatten()

    def _smooth(self, prediction):
        self.prediction_history.append(prediction)
        if len(self.prediction_history) > self.history_size:
            self.prediction_history.pop(0)
        return np.bincount(np.array(self.prediction_history)).argmax()

    def _predict(self, landmarks):
        normalized = self._normalize(landmarks)
        data = np.expand_dims(normalized, axis=0).astype(np.float32)
        self.interpreter.set_tensor(self.input_details[0]['index'], data)
        self.interpreter.invoke()
        out = self.interpreter.get_tensor(self.output_details[0]['index'])
        prediction = np.argmax(out[0])
        confidence = out[0][prediction]
        smoothed = self._smooth(int(prediction))
        return self.label_map[smoothed], float(confidence)

    def process(self, frame_rgb):
        results = self.hands.process(frame_rgb)
        landmarks = self._extract(results)
        if landmarks is None:
            self.consecutive_frames = 0
            return
        label, conf = self._predict(landmarks)
        if label == 'help_gesture' and conf > 0.98:
            self.consecutive_frames += 1
            if self.consecutive_frames >= 5:
                print(f"!!! HELP DETECTED !!! ({conf:.2f})")
                now = datetime.now()
                if (self.help_detection_time is None or
                        (now - self.help_detection_time).total_seconds() > self.alert_cooldown):
                    try:
                        send_alert_to_cloud("HELP_GESTURE", 0.95)
                        print("[WARM][help] alert sent.")
                    except Exception as e:
                        print(f"[WARM][help] alert failed: {e}")
                    self.help_detection_time = now
                    self.consecutive_frames = 0
        else:
            self.consecutive_frames = 0


# ══════════════════════════════════════════════════════════════════════════════
# FALL  (mirrors 10_mp_pi_deploy.py)
# ══════════════════════════════════════════════════════════════════════════════
class FallModel:
    def __init__(self):
        print("[WARM] Loading fall model (MediaPipe Pose + TFLite)...")
        try:
            import tensorflow as tf
            Interpreter = tf.lite.Interpreter
        except ImportError:
            import tflite_runtime.interpreter as tflite
            Interpreter = tflite.Interpreter
        import mediapipe as mp

        self.interpreter = Interpreter(model_path=os.path.join(FALL_DIR, "mp_fall_model.tflite"))
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.buffer = []
        self.last_alert = 0
        self.cooldown = 5
        self.last_print = 0.0

    def on_activate(self):
        self.buffer = []

    def process(self, frame_rgb):
        results = self.pose.process(frame_rgb)
        if results.pose_landmarks:
            kps = []
            for lm in results.pose_landmarks.landmark:
                kps.extend([lm.x, lm.y, lm.z, lm.visibility])
        else:
            kps = [0] * 132
        self.buffer.append(kps)
        if len(self.buffer) > 30:
            self.buffer.pop(0)
        if len(self.buffer) == 30:
            data = np.expand_dims(self.buffer, axis=0).astype(np.float32)
            self.interpreter.set_tensor(self.input_details[0]['index'], data)
            self.interpreter.invoke()
            prob = self.interpreter.get_tensor(self.output_details[0]['index'])[0][0]
            if time.time() - self.last_print > 1:
                print(f"[WARM][fall] Fall Prob: {prob:.2f}")
                self.last_print = time.time()
            if prob > 0.85 and (time.time() - self.last_alert > self.cooldown):
                print(f"🚨 FALL DETECTED! ({prob:.2f})")
                try:
                    send_alert_to_cloud("FALL", float(prob))
                    print("[WARM][fall] alert sent.")
                except Exception as e:
                    print(f"[WARM][fall] alert failed: {e}")
                self.last_alert = time.time()


# ══════════════════════════════════════════════════════════════════════════════
# Camera (rpicam-vid) — robust, never blocks forever
# ══════════════════════════════════════════════════════════════════════════════
def open_camera():
    cmd = ['rpicam-vid', '-t', '0', '--inline',
           '--width', str(WIDTH), '--height', str(HEIGHT),
           '--framerate', str(FRAMERATE), '--codec', 'yuv420', '-o', '-']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, bufsize=0)


def _read_exact(fd, n, deadline):
    """Read exactly n bytes (frame-aligned) or None if 'deadline' passes."""
    buf = bytearray()
    while len(buf) < n:
        if time.time() > deadline:
            return None
        r, _, _ = select.select([fd], [], [], 0.3)
        if not r:
            continue
        try:
            chunk = os.read(fd, n - len(buf))
        except OSError:
            return None
        if not chunk:        # EOF: camera process died
            return None
        buf += chunk
    return bytes(buf)


def _decode(raw):
    yuv = np.frombuffer(raw, dtype=np.uint8).reshape((int(HEIGHT * 1.5), WIDTH))
    bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def read_frame(proc, timeout=2.0):
    raw = _read_exact(proc.stdout.fileno(), FRAME_LEN, time.time() + timeout)
    if raw is None:
        return None
    return _decode(raw)


def flush_camera(proc):
    """Discard frames buffered from a previous turn (frame-aligned)."""
    fd = proc.stdout.fileno()
    while select.select([fd], [], [], 0)[0]:
        if _read_exact(fd, FRAME_LEN, time.time() + 0.5) is None:
            break


def kill_camera(proc):
    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def ensure_camera(proc):
    """Return a camera that is actually delivering frames, reopening if needed."""
    for attempt in range(6):
        if proc is None:
            proc = open_camera()
            time.sleep(1.5)            # let rpicam-vid spin up
        if read_frame(proc, timeout=5) is not None:
            return proc
        print(f"[WARM] camera not producing (try {attempt + 1}/6) — reopening...")
        kill_camera(proc)
        proc = None
        time.sleep(GAP_SECONDS)
    print("[WARM] camera could not be opened after retries.")
    return None


def systemctl(action, service):
    subprocess.run(["sudo", "systemctl", action, service],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    only = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if only and only not in ORDER:
        print(f"Unknown model '{only}'. Use one of: {ORDER}")
        sys.exit(1)

    # Let the system / camera stack settle on a cold boot.
    time.sleep(3)

    for s in [FACE_SERVICE, "fall_detection", "help_gesture"]:
        systemctl("stop", s)
    time.sleep(GAP_SECONDS)

    builders = {"fall": FallModel, "help": HelpModel}
    if only in ("fall", "help"):
        print(f"[WARM] Loading only the {only} model (test mode)...")
        models = {only: builders[only]()}
    elif only == "face":
        models = {}
    else:
        print("[WARM] Loading help + fall (one-time)...")
        models = {k: builders[k]() for k in WARM}
    print("[WARM] Ready.")

    sequence = [only] if only else ORDER
    proc = None

    try:
        while True:
            for key in sequence:
                if key == "face":
                    kill_camera(proc)
                    proc = None
                    time.sleep(GAP_SECONDS)
                    print("\n[WARM] === FACE active (original service) ===")
                    systemctl("start", FACE_SERVICE)
                    if only:
                        while True:
                            time.sleep(1)
                    time.sleep(RUN_SECONDS)
                    systemctl("stop", FACE_SERVICE)
                    time.sleep(GAP_SECONDS)
                else:
                    proc = ensure_camera(proc)
                    if proc is None:
                        time.sleep(2)
                        continue
                    models[key].on_activate()
                    flush_camera(proc)
                    print(f"\n[WARM] === {key.upper()} active "
                          f"({'∞' if only else RUN_SECONDS}s) ===")
                    end = time.time() + RUN_SECONDS
                    last_ok = time.time()
                    while only or time.time() < end:
                        rgb = read_frame(proc, timeout=2)
                        if rgb is None:
                            if time.time() - last_ok > 6:
                                print("[WARM] camera stalled — reopening...")
                                kill_camera(proc)
                                proc = ensure_camera(None)
                                if proc is None:
                                    break
                                models[key].on_activate()
                                flush_camera(proc)
                                last_ok = time.time()
                            continue
                        last_ok = time.time()
                        try:
                            models[key].process(rgb)
                        except Exception as e:
                            print(f"[WARM][{key}] process error: {e}")
    except KeyboardInterrupt:
        print("\n[WARM] Stopping.")
    finally:
        kill_camera(proc)
        systemctl("stop", FACE_SERVICE)


if __name__ == "__main__":
    main()
