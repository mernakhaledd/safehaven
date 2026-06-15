#!/usr/bin/env python3
"""
MediaPipe Fall Detection for Raspberry Pi
This version is OPTIMIZED for the Pi 4 CPU.
It runs at 20-30 FPS, unlike the failed YOLO approach.
"""

import cv2
import numpy as np
import time
import os
import sys
import subprocess

# TFLite Runtime
try:
    import tflite_runtime.interpreter as tflite
    Interpreter = tflite.Interpreter
except ImportError:
    try:
        import tensorflow as tf
        Interpreter = tf.lite.Interpreter
    except ImportError:
        print("ERROR: Install tensorflow or tflite-runtime")
        sys.exit(1)

# MediaPipe
try:
    import mediapipe as mp
except ImportError:
    print("ERROR: Install mediapipe")
    sys.exit(1)

# Alert System
def send_alert(confidence):
    try:
        from pi_supabase_trigger import send_alert_to_cloud
        send_alert_to_cloud("FALL", confidence)
    except ImportError:
        pass

class MPFallDetector:
    def __init__(self):
        print("Loading TFLite Model...")
        self.interpreter = Interpreter(model_path="mp_fall_model.tflite")
        self.interpreter.allocate_tensors()
        
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Buffer
        self.sequence_length = 30
        self.keypoints_buffer = []
        
        # MediaPipe
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        # Alert Config
        self.last_alert = 0
        self.cooldown = 5
        
        # Camera
        self.width = 640
        self.height = 480
        self.frame_len = int(self.width * self.height * 1.5)

    def run(self):
        print("Starting rpicam-vid pipe...")
        cmd = [
            'rpicam-vid', '-t', '0', '--inline', 
            '--width', str(self.width), '--height', str(self.height),
            '--framerate', '30', '--codec', 'yuv420', '-o', '-'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.frame_len)
        
        try:
            while True:
                raw_data = process.stdout.read(self.frame_len)
                if len(raw_data) != self.frame_len:
                    time.sleep(0.01)
                    continue
                    
                yuv_data = np.frombuffer(raw_data, dtype=np.uint8).reshape((int(self.height * 1.5), self.width))
                frame = cv2.cvtColor(yuv_data, cv2.COLOR_YUV2BGR_I420)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                self.process_frame(frame)
                
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            process.terminate()

    def process_frame(self, frame):
        results = self.pose.process(frame)
        
        kps = []
        if results.pose_landmarks:
            for lm in results.pose_landmarks.landmark:
                kps.extend([lm.x, lm.y, lm.z, lm.visibility])
        else:
            kps = [0] * 132
            
        self.keypoints_buffer.append(kps)
        if len(self.keypoints_buffer) > 30:
            self.keypoints_buffer.pop(0)
            
        if len(self.keypoints_buffer) == 30:
            # Inference
            input_data = np.expand_dims(self.keypoints_buffer, axis=0).astype(np.float32)
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()
            output = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            prob = output[0][0]
            print(f"\rFall Prob: {prob:.2f}", end='')
            
            if prob > 0.85:
                if time.time() - self.last_alert > self.cooldown:
                    print(f"\n🚨 FALL DETECTED! ({prob:.2f})")
                    send_alert(prob)
                    self.last_alert = time.time()

if __name__ == "__main__":
    app = MPFallDetector()
    app.run()
