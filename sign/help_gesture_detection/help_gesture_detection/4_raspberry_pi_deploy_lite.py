#!/usr/bin/env python3
"""
Raspberry Pi Deployment Script for Help Gesture Recognition (MediaPipe-Free)
This script uses only TensorFlow Lite for efficient inference on Raspberry Pi.
It extracts hand landmarks from video and feeds them to the model.
"""

import cv2
import numpy as np
import numpy as np
import json
import os
from datetime import datetime
import subprocess
import sys

# Try importing TensorFlow, otherwise fallback to TFLite Runtime
try:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
        Interpreter = tflite.Interpreter
    except ImportError:
        print("ERROR: Neither 'tensorflow' nor 'tflite_runtime' found.")
        print("Please install one of them:")
        print("  pip install tensorflow")
        print("  OR")
        print("  pip install tflite-runtime")
        sys.exit(1)

# Try to import RPi.GPIO for alerts (optional)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("Warning: RPi.GPIO not available. GPIO alerts disabled.")

class LiteGestureRecognizer:
    def __init__(self, model_path='help_gesture_model.tflite', 
                 label_map_path='label_map.json',
                 alert_pin=None):
        """Initialize the gesture recognizer using MediaPipe subprocess"""
        
        # Load TFLite model
        print(f"Loading TFLite model from: {model_path}")
        self.interpreter = Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        
        # Get input and output details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        print(f"Model input shape: {self.input_details[0]['shape']}")
        print(f"Model output shape: {self.output_details[0]['shape']}")
        
        # Load label map
        with open(label_map_path, 'r') as f:
            self.label_map = json.load(f)
        self.label_map = {int(k): v for k, v in self.label_map.items()}
        
        print(f"Model loaded successfully!")
        print(f"Gesture classes: {list(self.label_map.values())}")
        
        # Prediction smoothing
        self.prediction_history = []
        self.history_size = 5
        
        # Alert settings
        self.help_detected = False
        self.help_detection_time = None
        self.alert_cooldown = 3  # seconds
        
        # GPIO setup for external alerts (optional)
        self.alert_pin = alert_pin
        if alert_pin is not None and HAS_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(alert_pin, GPIO.OUT)
            GPIO.output(alert_pin, GPIO.LOW)
        
        # Try to import MediaPipe for hand detection
        try:
            import mediapipe_rpi4 as mp
            self.mp = mp
        except ImportError:
            try:
                import mediapipe as mp
                self.mp = mp
            except ImportError:
                print("ERROR: MediaPipe not available!")
                print("Please install: pip install mediapipe-rpi4")
                sys.exit(1)
        
        # Initialize MediaPipe hands
        self.hands = self.mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = self.mp.solutions.drawing_utils
    
    def extract_landmarks(self, results):
        """Extract hand landmarks as a feature vector"""
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
        """Normalize landmarks relative to wrist position"""
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
        """Smooth predictions over multiple frames"""
        self.prediction_history.append(prediction)
        if len(self.prediction_history) > self.history_size:
            self.prediction_history.pop(0)
        
        # Return the most common prediction
        history_array = np.array(self.prediction_history)
        return np.bincount(history_array).argmax()
    
    def predict(self, landmarks):
        """Run inference on the model"""
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
        if self.alert_pin is not None and HAS_GPIO:
            GPIO.output(self.alert_pin, GPIO.HIGH)
            print("[ALERT] Help gesture detected! GPIO pin activated.")
            
        if self.alert_pin is not None and HAS_GPIO:
            GPIO.output(self.alert_pin, GPIO.HIGH)
            print("[ALERT] Help gesture detected! GPIO pin activated.")
            
        # INTEGRATION: Send alert to Cloud (Supabase)
        try:
            try:
                from pi_supabase_trigger import send_alert_to_cloud
                send_alert_to_cloud("HELP_GESTURE", 0.95)
            except ImportError:
                 print("[ALERT] pi_supabase_trigger.py not found. Copy it to the same folder!")
        except Exception as e:
            print(f"[ALERT] Failed to send cloud alert: {e}")
    
    def run(self):
        """Main inference loop"""
        # Try to use picamera2 (native libcamera for Raspberry Pi)
        use_picamera2 = False
        camera = None
        
        try:
            from picamera2 import Picamera2
            from libcamera import controls
            camera = Picamera2()
            config = camera.create_preview_configuration(
                main={"format": 'XRGB8888', "size": (1280, 720)}
            )
            camera.configure(config)
            camera.start()
            use_picamera2 = True
            print("Using picamera2 (native libcamera interface)")
        except ImportError:
            print("picamera2 not available, falling back to OpenCV V4L2...")
            try:
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
            except Exception as e:
                print(f"ERROR: Could not initialize camera: {e}")
                print("Please ensure:")
                print("  1. Camera is connected and enabled (raspi-config)")
                print("  2. Install picamera2: sudo apt install -y python3-picamera2")
                print("  3. Or enable libcamera-to-v4l2 bridge: libcamera-to-v4l2 -c 0 &")
                sys.exit(1)
        
        print("\n" + "="*60)
        print("Help Gesture Detection - Running on Raspberry Pi")
        print("="*60)
        print("\nPress 'q' to quit")
        print("="*60 + "\n")
        
        frame_count = 0
        help_detected_count = 0
        
        try:
            while True:
                if use_picamera2:
                    frame = camera.capture_array()
                    # picamera2 returns RGB, convert to BGR for OpenCV
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    ret = True
                else:
                    ret, frame = cap.read()
                
                if not ret:
                    print("Failed to grab frame")
                    break
                
                frame_count += 1
                
                # Process frame with MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_frame)
                
                # Get landmarks
                landmarks = self.extract_landmarks(results)
                
                # Make prediction if landmarks detected
                if landmarks is not None:
                    gesture_label, confidence = self.predict(landmarks)
                    
                    # Log detections
                    if gesture_label == 'help_gesture' and confidence > 0.7:
                        help_detected_count += 1
                        current_time = datetime.now()
                        
                        print(f"[{current_time.strftime('%H:%M:%S')}] "
                              f"HELP GESTURE DETECTED! Confidence: {confidence:.4f}")
                        
                        # Check cooldown for alert
                        if self.help_detection_time is None or \
                           (current_time - self.help_detection_time).total_seconds() > self.alert_cooldown:
                            self.trigger_alert()
                            self.help_detection_time = current_time
                    
                    # Draw on frame
                    text = f"{gesture_label}: {confidence:.2f}"
                    color = (0, 255, 0) if gesture_label == 'help_gesture' else (0, 255, 255)
                    cv2.putText(frame, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                               1, color, 2)
                
                # Draw hand landmarks
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        self.mp_draw.draw_landmarks(frame, hand_landmarks, 
                                                   self.mp.solutions.hands.HAND_CONNECTIONS)
                
                # Draw frame info
                cv2.putText(frame, f"Frame: {frame_count}", (50, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, f"Help detected: {help_detected_count}", (50, 130), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Display frame (optional - may not work in headless mode)
                try:
                    cv2.imshow('Help Gesture Detection', frame)
                except:
                    # Headless mode - just process without displaying
                    pass
                
                # Check for quit
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
        
        except KeyboardInterrupt:
            print("\n\nShutdown requested by user")
        
        finally:
            if use_picamera2 and camera is not None:
                camera.stop()
            else:
                cap.release()
            cv2.destroyAllWindows()
            if HAS_GPIO and self.alert_pin is not None:
                GPIO.cleanup()
            
            print("\n" + "="*60)
            print(f"Inference Complete")
            print(f"Total frames processed: {frame_count}")
            print(f"Help gestures detected: {help_detected_count}")
            print("="*60)

def main():
    # Configuration
    MODEL_PATH = 'help_gesture_model.tflite'
    LABEL_MAP_PATH = 'label_map.json'
    ALERT_PIN = None  # Set to GPIO pin number if you want LED/buzzer alerts
    
    # Check if model files exist
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model file not found: {MODEL_PATH}")
        sys.exit(1)
    
    if not os.path.exists(LABEL_MAP_PATH):
        print(f"ERROR: Label map not found: {LABEL_MAP_PATH}")
        sys.exit(1)
    
    # Initialize and run
    recognizer = LiteGestureRecognizer(
        model_path=MODEL_PATH,
        label_map_path=LABEL_MAP_PATH,
        alert_pin=ALERT_PIN
    )
    
    recognizer.run()

if __name__ == '__main__':
    main()
