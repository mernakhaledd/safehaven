#!/usr/bin/env python3
"""
Real-time Testing Script for Help Gesture Recognition
This script uses the trained model to detect help gestures in real-time.
"""

import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
import json
import os
from datetime import datetime

class GestureRecognizer:
    def __init__(self, model_path='models/help_gesture_model.h5', 
                 label_map_path='models/label_map.json'):
        """Initialize the gesture recognizer"""
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Load model
        print(f"Loading model from: {model_path}")
        self.model = tf.keras.models.load_model(model_path)
        
        # Load label map
        with open(label_map_path, 'r') as f:
            self.label_map = json.load(f)
        # Convert keys to integers
        self.label_map = {int(k): v for k, v in self.label_map.items()}
        
        print(f"Model loaded successfully!")
        print(f"Gesture classes: {list(self.label_map.values())}")
        
        # For smoothing predictions
        self.prediction_history = []
        self.history_size = 5
        
        # Alert tracking
        self.help_detected = False
        self.help_detection_time = None
        self.alert_cooldown = 3  # seconds
        
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
        """Predict gesture from landmarks"""
        if landmarks is None:
            return None, 0.0
        
        # Normalize
        normalized = self.normalize_landmarks(landmarks)
        
        # Predict
        input_data = np.expand_dims(normalized, axis=0)
        predictions = self.model.predict(input_data, verbose=0)[0]
        
        # Get class with highest probability
        class_idx = np.argmax(predictions)
        confidence = predictions[class_idx]
        gesture_name = self.label_map[class_idx]
        
        return gesture_name, confidence
    
    def smooth_prediction(self, gesture, confidence):
        """Smooth predictions over time to reduce jitter"""
        self.prediction_history.append((gesture, confidence))
        
        if len(self.prediction_history) > self.history_size:
            self.prediction_history.pop(0)
        
        # Count occurrences of each gesture
        gesture_counts = {}
        for g, c in self.prediction_history:
            if g not in gesture_counts:
                gesture_counts[g] = []
            gesture_counts[g].append(c)
        
        # Find most common gesture
        if gesture_counts:
            most_common = max(gesture_counts.items(), 
                            key=lambda x: (len(x[1]), np.mean(x[1])))
            return most_common[0], np.mean(most_common[1])
        
        return gesture, confidence
    
    def draw_prediction(self, frame, gesture, confidence):
        """Draw prediction info on frame"""
        h, w = frame.shape[:2]
        
        # Determine color based on gesture
        if gesture == 'help_gesture':
            color = (0, 0, 255)  # Red for help
            text_color = (255, 255, 255)
        else:
            color = (0, 255, 0)  # Green for normal
            text_color = (255, 255, 255)
        
        # Draw semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, h-120), (400, h-10), color, -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        # Draw text
        cv2.putText(frame, f"Gesture: {gesture}", (20, h-90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        cv2.putText(frame, f"Confidence: {confidence*100:.1f}%", (20, h-50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        
        # Alert if help gesture detected
        if gesture == 'help_gesture' and confidence > 0.8:
            current_time = datetime.now()
            
            # Check cooldown
            if (self.help_detection_time is None or 
                (current_time - self.help_detection_time).seconds > self.alert_cooldown):
                
                self.help_detected = True
                self.help_detection_time = current_time
                
                # Draw ALERT
                cv2.rectangle(frame, (w//4, h//4), (3*w//4, 3*h//4), (0, 0, 255), 10)
                cv2.putText(frame, "HELP DETECTED!", (w//4 + 20, h//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
                
                print(f"\n{'='*60}")
                print(f"ALERT: HELP GESTURE DETECTED!")
                print(f"Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Confidence: {confidence*100:.1f}%")
                print(f"{'='*60}\n")
        
        return frame
    
    def run(self, source=0):
        """Run real-time gesture recognition"""
        cap = cv2.VideoCapture(source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("\n" + "="*60)
        print("HELP GESTURE REAL-TIME DETECTION")
        print("="*60)
        print("\nInstructions:")
        print("1. Position your hands to show the HELP gesture")
        print("2. The system will detect and classify your gesture")
        print("3. When HELP is detected, an alert will be triggered")
        print("4. Press 'q' to quit")
        print("5. Press 's' to save a snapshot")
        print("="*60 + "\n")
        
        snapshot_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process hands
            results = self.hands.process(rgb_frame)
            
            # Draw hand landmarks
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        self.mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
            
            # Predict gesture
            landmarks = self.extract_landmarks(results)
            if landmarks is not None:
                gesture, confidence = self.predict_gesture(landmarks)
                gesture, confidence = self.smooth_prediction(gesture, confidence)
                frame = self.draw_prediction(frame, gesture, confidence)
            else:
                cv2.putText(frame, "No hands detected", (20, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Display FPS
            cv2.putText(frame, f"Press 'q' to quit | 's' to save", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow('Help Gesture Detection', frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save snapshot
                snapshot_count += 1
                filename = f"snapshot_{snapshot_count}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Snapshot saved: {filename}")
        
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    recognizer = GestureRecognizer(
        model_path='models/help_gesture_model.h5',
        label_map_path='models/label_map.json'
    )
    recognizer.run(source=0)