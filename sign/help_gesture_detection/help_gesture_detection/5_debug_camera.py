#!/usr/bin/env python3
"""
Debug script to verify camera and inference on Raspberry Pi.
Prints verbose status to console to debug "silent" failures.
"""

import cv2
import numpy as np
import json
import os
import sys
import time
from datetime import datetime

# Import TFLite
try:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter
    print("INFO: Using tensorflow.lite.Interpreter", flush=True)
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
        Interpreter = tflite.Interpreter
        print("INFO: Using tflite_runtime.interpreter", flush=True)
    except ImportError:
        print("ERROR: Neither 'tensorflow' nor 'tflite_runtime' found.", flush=True)
        sys.exit(1)

# Import MediaPipe
try:
    import mediapipe_rpi4 as mp
    print("INFO: Using mediapipe_rpi4", flush=True)
except ImportError:
    try:
        import mediapipe as mp
        print("INFO: Using standard mediapipe", flush=True)
    except ImportError:
        print("ERROR: MediaPipe not available.", flush=True)
        sys.exit(1)

class DebugRecognizer:
    def __init__(self, model_path='help_gesture_model.tflite', label_map_path='label_map.json'):
        print(f"INFO: Loading model from {model_path}...", flush=True)
        if not os.path.exists(model_path):
            print(f"ERROR: Model file {model_path} not found!", flush=True)
            sys.exit(1)
            
        self.interpreter = Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        print("INFO: Model loaded successfully.", flush=True)
        
        if os.path.exists(label_map_path):
            with open(label_map_path, 'r') as f:
                self.label_map = json.load(f)
            self.label_map = {int(k): v for k, v in self.label_map.items()}
            print(f"INFO: Labels: {self.label_map}", flush=True)
        else:
            print("WARNING: No label map found, using raw indices.", flush=True)
            self.label_map = {}

        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("INFO: MediaPipe Hands initialized.", flush=True)

    def process_loop(self):
        # Camera Setup
        print("INFO: Initializing Camera...", flush=True)
        use_picamera2 = False
        camera = None
        cap = None

        try:
            # Try picamera2 first
            from picamera2 import Picamera2
            camera = Picamera2()
            config = camera.create_preview_configuration(
                main={"format": 'XRGB8888', "size": (640, 480)}
            )
            camera.configure(config)
            camera.start()
            use_picamera2 = True
            print("INFO: SUCCESS - Using Picamera2 (libcamera).", flush=True)
        except Exception as e:
            print(f"INFO: Picamera2 failed ({e}), trying OpenCV...", flush=True)
            try:
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    raise Exception("VideoCapture(0) returned false")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print("INFO: SUCCESS - Using OpenCV VideoCapture(0).", flush=True)
            except Exception as e2:
                print(f"ERROR: Could not verify any camera. {e2}", flush=True)
                sys.exit(1)

        print("INFO: Starting Inference Loop. Press Ctrl+C to stop.", flush=True)
        print("INFO: Saving debug image to 'debug_frame.jpg' every 30 frames.", flush=True)
        
        frame_cnt = 0
        try:
            while True:
                start_time = time.time()
                
                # Capture
                if use_picamera2:
                    frame = camera.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    ret = True
                else:
                    ret, frame = cap.read()
                
                if not ret:
                    print("ERROR: Failed to read frame.", flush=True)
                    time.sleep(1)
                    continue

                frame_cnt += 1
                
                # Process
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_frame)
                
                # Check detections
                has_hands = False
                if results.multi_hand_landmarks:
                    has_hands = True 
                    # Just print first hand location to prove it works
                    hand0 = results.multi_hand_landmarks[0].landmark[0] # Wrist
                    print(f"\rFrame {frame_cnt}: Hands Detected! Wrist at ({hand0.x:.2f}, {hand0.y:.2f})", end='', flush=True)
                    
                    # Optional: Run interpreter (simplified) if needed, but MP check is enough for now
                else:
                    print(f"\rFrame {frame_cnt}: No hands.", end='', flush=True)

                # Save debug image occasionally
                if frame_cnt % 30 == 0:
                    if results.multi_hand_landmarks:
                        for hand_landmarks in results.multi_hand_landmarks:
                            mp.solutions.drawing_utils.draw_landmarks(frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                    cv2.imwrite("debug_frame.jpg", frame)
                    print(" [Saved debug_frame.jpg]", end='', flush=True)

        except KeyboardInterrupt:
            print("\nINFO: Stopping...", flush=True)
        finally:
            if use_picamera2 and camera:
                camera.stop()
            if cap:
                cap.release()

if __name__ == "__main__":
    detect = DebugRecognizer()
    detect.process_loop()
