#!/usr/bin/env python3
"""
Raspberry Pi Deployment Script for Help Gesture Recognition
This script uses TensorFlow Lite for efficient inference on Raspberry Pi.
"""

import cv2
import numpy as np
import json
import os
from datetime import datetime
import RPi.GPIO as GPIO  # Optional: for triggering external alerts

# Try mediapipe-rpi4 first, fallback to mediapipe
try:
    import mediapipe_rpi4 as mp
except ImportError:
    import mediapipe as mp

# Try tflite_runtime first, fallback to tensorflow
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow as tf
    tflite = tf.lite

class RaspberryPiGestureRecognizer:
    def __init__(self, model_path='help_gesture_model.tflite', 
                 label_map_path='label_map.json',
                 alert_pin=None):
        """Initialize the gesture recognizer for Raspberry Pi"""
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Load TFLite model
        print(f"Loading TFLite model from: {model_path}")
        self.interpreter = tflite.Interpreter(model_path=model_path)
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
        if alert_pin is not None:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(alert_pin, GPIO.OUT)
            GPIO.output(alert_pin, GPIO.LOW)
        
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
    
    def predict_gesture(self, landmarks):
        """Predict gesture using TFLite model"""
        if landmarks is None:
            return None, 0.0
        
        # Normalize
        normalized = self.normalize_landmarks(landmarks)
        
        # Prepare input
        input_data = np.expand_dims(normalized, axis=0).astype(np.float32)
        
        # Set input tensor
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        
        # Run inference
        self.interpreter.invoke()
        
        # Get output
        predictions = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
        
        # Get class with highest probability
        class_idx = np.argmax(predictions)
        confidence = predictions[class_idx]
        gesture_name = self.label_map[class_idx]
        
        return gesture_name, confidence
    
    def smooth_prediction(self, gesture, confidence):
        """Smooth predictions over time"""
        self.prediction_history.append((gesture, confidence))
        
        if len(self.prediction_history) > self.history_size:
            self.prediction_history.pop(0)
        
        gesture_counts = {}
        for g, c in self.prediction_history:
            if g not in gesture_counts:
                gesture_counts[g] = []
            gesture_counts[g].append(c)
        
        if gesture_counts:
            most_common = max(gesture_counts.items(), 
                            key=lambda x: (len(x[1]), np.mean(x[1])))
            return most_common[0], np.mean(most_common[1])
        
        return gesture, confidence
    
    def trigger_alert(self):
        """Trigger external alert (e.g., LED, buzzer, notification)"""
        print(f"\n{'='*60}")
        print(f"🚨 HELP GESTURE DETECTED! 🚨")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # Trigger GPIO pin if configured
        if self.alert_pin is not None:
            GPIO.output(self.alert_pin, GPIO.HIGH)
            # Keep alert active for 2 seconds
            import time
            time.sleep(2)
            GPIO.output(self.alert_pin, GPIO.LOW)
        
        # You can add more alert mechanisms here:
        # - Send notification
        # - Play sound
        # - Send email/SMS
        # - Log to file
        
    def run(self, source=0, save_video=False):
        """Run real-time gesture recognition on Raspberry Pi"""
        cap = cv2.VideoCapture(source)
        
        # Set camera properties for Raspberry Pi
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("\n" + "="*60)
        print("RASPBERRY PI - HELP GESTURE DETECTION")
        print("="*60)
        print("\nSystem is ready. Monitoring for help gestures...")
        print("Press Ctrl+C to stop\n")
        
        # Video writer (optional)
        video_writer = None
        if save_video:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            video_writer = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process hands
                results = self.hands.process(rgb_frame)
                
                # Draw hand landmarks (optional, remove for better performance)
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        self.mp_draw.draw_landmarks(
                            frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                        )
                
                # Predict gesture
                landmarks = self.extract_landmarks(results)
                if landmarks is not None:
                    gesture, confidence = self.predict_gesture(landmarks)
                    gesture, confidence = self.smooth_prediction(gesture, confidence)
                    
                    # Check for help gesture
                    if gesture == 'help_gesture' and confidence > 0.8:
                        current_time = datetime.now()
                        
                        if (self.help_detection_time is None or 
                            (current_time - self.help_detection_time).seconds > self.alert_cooldown):
                            
                            self.help_detection_time = current_time
                            self.trigger_alert()
                    
                    # Display info (optional)
                    cv2.putText(frame, f"{gesture}: {confidence*100:.1f}%", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Save video if enabled
                if video_writer is not None:
                    video_writer.write(frame)
                
                # Display frame (optional, comment out for headless operation)
                cv2.imshow('Help Gesture Detection', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\nStopping detection...")
        finally:
            cap.release()
            if video_writer is not None:
                video_writer.release()
            cv2.destroyAllWindows()
            
            # Cleanup GPIO
            if self.alert_pin is not None:
                GPIO.cleanup()
            
            print("\nSystem stopped.")

if __name__ == "__main__":
    # Configuration
    MODEL_PATH = 'help_gesture_model.tflite'
    LABEL_MAP_PATH = 'label_map.json'
    ALERT_PIN = 17  # GPIO pin for external alert (set to None to disable)
    
    recognizer = RaspberryPiGestureRecognizer(
        model_path=MODEL_PATH,
        label_map_path=LABEL_MAP_PATH,
        alert_pin=ALERT_PIN  # Set to None if not using GPIO
    )
    
    recognizer.run(source=0, save_video=False)