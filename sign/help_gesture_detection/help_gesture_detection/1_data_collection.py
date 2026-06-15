#!/usr/bin/env python3
"""
Data Collection Script for Help Gesture Recognition
This script captures hand landmarks from your webcam to build a training dataset.
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import json
from datetime import datetime

class DataCollector:
    def __init__(self, output_dir='dataset'):
        """Initialize the data collector with MediaPipe hands"""
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # We need 2 hands for the help gesture
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Gesture classes
        self.gesture_classes = {
            '0': 'help_gesture',
            '1': 'no_gesture',
            '2': 'other_gesture'
        }
        
        self.current_gesture = None
        self.samples_collected = {gesture: 0 for gesture in self.gesture_classes.values()}
        
    def extract_landmarks(self, results):
        """Extract hand landmarks as a feature vector"""
        if not results.multi_hand_landmarks:
            return None
            
        landmarks_list = []
        
        # Process each detected hand
        for hand_landmarks in results.multi_hand_landmarks:
            landmarks = []
            for landmark in hand_landmarks.landmark:
                landmarks.extend([landmark.x, landmark.y, landmark.z])
            landmarks_list.append(landmarks)
        
        # If we have 2 hands, concatenate them
        if len(landmarks_list) == 2:
            feature_vector = np.concatenate(landmarks_list)
        elif len(landmarks_list) == 1:
            # Pad with zeros if only one hand detected
            feature_vector = np.concatenate([landmarks_list[0], np.zeros(63)])
        else:
            return None
            
        return feature_vector
    
    def normalize_landmarks(self, landmarks):
        """Normalize landmarks relative to wrist position"""
        if landmarks is None:
            return None
        
        # Reshape to get individual coordinates
        coords = landmarks.reshape(-1, 3)
        
        # Get wrist position (first landmark of each hand)
        if len(coords) >= 21:
            wrist1 = coords[0]
            coords[:21] -= wrist1  # Normalize first hand
            
            if len(coords) > 21:
                wrist2 = coords[21]
                coords[21:] -= wrist2  # Normalize second hand
        
        return coords.flatten()
    
    def save_sample(self, landmarks, gesture_name):
        """Save a landmark sample to disk"""
        if landmarks is None:
            return False
            
        # Normalize landmarks
        normalized = self.normalize_landmarks(landmarks)
        
        # Create gesture directory
        gesture_dir = os.path.join(self.output_dir, gesture_name)
        os.makedirs(gesture_dir, exist_ok=True)
        
        # Save as numpy file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(gesture_dir, f"{gesture_name}_{timestamp}.npy")
        np.save(filename, normalized)
        
        self.samples_collected[gesture_name] += 1
        return True
    
    def draw_info(self, frame):
        """Draw information overlay on the frame"""
        # Draw background for text
        cv2.rectangle(frame, (10, 10), (630, 180), (0, 0, 0), -1)
        
        # Instructions
        y_offset = 30
        cv2.putText(frame, "HELP GESTURE DATA COLLECTION", (20, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        y_offset += 30
        cv2.putText(frame, "Press '0' - Collect HELP gesture samples", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        y_offset += 25
        cv2.putText(frame, "Press '1' - Collect NO gesture samples", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        y_offset += 25
        cv2.putText(frame, "Press '2' - Collect OTHER gesture samples", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        y_offset += 25
        cv2.putText(frame, "Press 'q' - Quit", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show samples collected
        y_offset += 35
        for gesture, count in self.samples_collected.items():
            cv2.putText(frame, f"{gesture}: {count} samples", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y_offset += 25
        
        return frame
    
    def run(self):
        """Main collection loop"""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        collecting = False
        collection_gesture = None
        
        print("\n" + "="*60)
        print("HELP GESTURE DATA COLLECTION")
        print("="*60)
        print("\nInstructions:")
        print("1. Position your hands to show the HELP gesture")
        print("   (Right hand thumbs up, left hand palm up below it)")
        print("2. Press '0' and hold to collect HELP gesture samples")
        print("3. Move around, change angles, distances for variety")
        print("4. Press '1' to collect negative samples (no gesture)")
        print("5. Press '2' to collect other random gestures")
        print("6. Collect at least 200-300 samples per class")
        print("7. Press 'q' to quit\n")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB for MediaPipe
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
            
            # Draw info overlay
            frame = self.draw_info(frame)
            
            # Auto-collect samples when key is held down
            if collecting and collection_gesture is not None:
                landmarks = self.extract_landmarks(results)
                if self.save_sample(landmarks, collection_gesture):
                    # Visual feedback
                    cv2.circle(frame, (640, 360), 50, (0, 255, 0), -1)
            
            cv2.imshow('Data Collection', frame)
            
            # Key handling
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('0'):
                collecting = True
                collection_gesture = self.gesture_classes['0']
            elif key == ord('1'):
                collecting = True
                collection_gesture = self.gesture_classes['1']
            elif key == ord('2'):
                collecting = True
                collection_gesture = self.gesture_classes['2']
            elif key == 255:  # No key pressed
                collecting = False
                collection_gesture = None
        
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n" + "="*60)
        print("Data Collection Complete!")
        print("="*60)
        for gesture, count in self.samples_collected.items():
            print(f"{gesture}: {count} samples collected")
        print(f"\nData saved to: {self.output_dir}/")
        print("="*60)

if __name__ == "__main__":
    collector = DataCollector(output_dir='dataset')
    collector.run()