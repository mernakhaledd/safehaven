#!/usr/bin/env python3
"""
Universal Raspberry Pi Deployment Script - Subprocess Pipe Mode
LOGIC MIRRORED EXACTLY FROM: 4_raspberry_pi_deploy_lite.py
"""

import cv2
import numpy as np
import json
import os
import sys
import subprocess
import time
from datetime import datetime

# Import TFLite
try:
    import tflite_runtime.interpreter as tflite
    Interpreter = tflite.Interpreter
except ImportError:
    try:
        import tensorflow as tf
        Interpreter = tf.lite.Interpreter
    except ImportError:
        print("ERROR: Neither 'tensorflow' nor 'tflite_runtime' found.")
        sys.exit(1)

# Import MediaPipe
try:
    import mediapipe as mp
except ImportError:
    try:
        import mediapipe_rpi4 as mp
    except ImportError:
        print("ERROR: MediaPipe not available!")
        sys.exit(1)

class SubprocessGestureRecognizer:
    def __init__(self, model_path='help_gesture_model.tflite', label_map_path='label_map.json'):
        print(f"Loading Model: {model_path}")
        self.interpreter = Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Load label map
        if os.path.exists(label_map_path):
            with open(label_map_path, 'r') as f:
                self.label_map = {int(k): v for k, v in json.load(f).items()}
        else:
            self.label_map = {0: 'help_gesture', 1: 'no_gesture'}
            
        print(f"Classes: {list(self.label_map.values())}")
        
        # Initialize MediaPipe (Same as original)
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Prediction smoothing (Exact same settings as original)
        self.prediction_history = []
        self.history_size = 5
        
        # Alert Settings
        self.help_detected = False
        self.help_detection_time = None
        self.alert_cooldown = 3 

        self.width = 640
        self.height = 480
        self.frame_len = int(self.width * self.height * 1.5)

    def extract_landmarks(self, results):
        """Extract hand landmarks as a feature vector - EXACT COPY"""
        if not results.multi_hand_landmarks:
            return None
            
        landmarks_list = []
        
        for hand_landmarks in results.multi_hand_landmarks:
            landmarks = []
            for landmark in hand_landmarks.landmark:
                landmarks.extend([landmark.x, landmark.y, landmark.z])
            landmarks_list.append(landmarks)
        
        if len(landmarks_list) == 2:
            feature_vector = np.concatenate(landmarks_list)
        elif len(landmarks_list) == 1:
            feature_vector = np.concatenate([landmarks_list[0], np.zeros(63)])
        else:
            return None
            
        return feature_vector

    def normalize_landmarks(self, landmarks):
        """Normalize landmarks relative to wrist position - EXACT COPY"""
        if landmarks is None:
            return None
        
        coords = landmarks.reshape(-1, 3)
        
        if len(coords) >= 21:
            wrist1 = coords[0]
            coords[:21] -= wrist1
            
            if len(coords) > 21:
                wrist2 = coords[21]
                coords[21:] -= wrist2
        
        return coords.flatten()

    def smooth_predictions(self, prediction):
        """Smooth predictions over multiple frames - EXACT COPY"""
        self.prediction_history.append(prediction)
        if len(self.prediction_history) > self.history_size:
            self.prediction_history.pop(0)
        
        # Return the most common prediction
        history_array = np.array(self.prediction_history)
        return np.bincount(history_array).argmax()

    def predict(self, landmarks):
        """Run inference on the model - EXACT COPY logic"""
        if landmarks is None:
            return None, 0
        
        # Normalize landmarks
        normalized = self.normalize_landmarks(landmarks)
        
        # Prepare input for model
        input_data = np.expand_dims(normalized, axis=0).astype(np.float32)
        
        # Run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        
        # Get output
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        # Get prediction
        prediction = np.argmax(output_data[0])
        confidence = output_data[0][prediction]
        
        # Smooth prediction
        smoothed_prediction = self.smooth_predictions(int(prediction))
        
        return self.label_map[smoothed_prediction], float(confidence)

    def trigger_alert(self):
        """Trigger GPIO alert and Send HTTP Alert"""
        # GPIO (Optional/Future)
        # print("[ALERT] GPIO pin activated.")
            
        # INTEGRATION: Send alert to Cloud (Supabase)
        try:
            try:
                # Try to import the trigger module
                from pi_supabase_trigger import send_alert_to_cloud
                print(f"[ALERT] Sending finding to Supabase...")
                send_alert_to_cloud("HELP_GESTURE", 0.95)
                print(f"[SUCCESS] Alert sent to mobile app!")
            except ImportError:
                 print("[ALERT] ERROR: pi_supabase_trigger.py not found. Please upload it to this folder!")
        except Exception as e:
            print(f"[ALERT] Failed to send cloud alert: {e}")

    def run(self):
        print("Starting Camera via rpicam-vid subprocess pipe...")
        
        cmd = [
            'rpicam-vid',
            '-t', '0', 
            '--inline', 
            '--width', str(self.width),
            '--height', str(self.height),
            '--framerate', '30',
            '--codec', 'yuv420',
            '-o', '-'
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)
        print("Subprocess started. Beginning inference loop...")
        
        try:
            while True:
                raw_data = process.stdout.read(self.frame_len)
                if len(raw_data) != self.frame_len:
                    time.sleep(0.01)
                    continue
                
                # Decode Frame
                yuv_data = np.frombuffer(raw_data, dtype=np.uint8).reshape((int(self.height * 1.5), self.width))
                bgr_frame = cv2.cvtColor(yuv_data, cv2.COLOR_YUV2BGR_I420)
                rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                
                # Logic copied from original run() loop
                results = self.hands.process(rgb_frame)
                landmarks = self.extract_landmarks(results)
                
                if landmarks is not None:
                    gesture_label, confidence = self.predict(landmarks)
                    
                    # STRICTER CHECK: Only accept if > 98% confidence (Ultra Strict)
                    if gesture_label == 'help_gesture' and confidence > 0.98:
                        
                        # Continuity Check
                        if not hasattr(self, 'consecutive_frames'):
                            self.consecutive_frames = 0
                        self.consecutive_frames += 1
                        
                        # Only accept if seen 5 times in a row
                        if self.consecutive_frames >= 5:
                            print(f"!!! HELP DETECTED !!! ({confidence:.2f})")
                            
                            current_time = datetime.now()
                            if self.help_detection_time is None or \
                               (current_time - self.help_detection_time).total_seconds() > self.alert_cooldown:
                                self.trigger_alert()
                                self.help_detection_time = current_time
                                self.consecutive_frames = 0 # Reset count after alert
                    else:
                        self.consecutive_frames = 0

        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            process.terminate()

if __name__ == '__main__':
    app = SubprocessGestureRecognizer()
    app.run()
