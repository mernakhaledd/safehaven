import cv2
import os
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Configuration
DATASET_ROOT = "fall dataset/fall dataset"
OUTPUT_DIR = "mp_processed_data"
SEQUENCE_LENGTH = 30

# Initialize MediaPipe (New Task API for Py3.13+)
# We need to download the model asset first!
model_path = 'pose_landmarker_lite.task'

def download_model():
    if not os.path.exists(model_path):
        print("Downloading MediaPipe Pose Model...")
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
        urllib.request.urlretrieve(url, model_path)
        print("Model downloaded.")

def get_landmarker():
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=False)
    return vision.PoseLandmarker.create_from_options(options)

def process_video(video_path, landmarker):
    cap = cv2.VideoCapture(video_path)
    frames_data = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Convert to RGB (MediaPipe Task requires mp.Image)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        
        # Detect
        detection_result = landmarker.detect(mp_image)
        
        # Extract Landmarks
        frame_kps = []
        if detection_result.pose_landmarks:
            # List of lists (one per person). take first person.
            landmarks = detection_result.pose_landmarks[0]
            for landmark in landmarks:
                frame_kps.extend([landmark.x, landmark.y, landmark.z, landmark.visibility])
        else:
            # If no detection, pad with zeros
            frame_kps = [0] * (33 * 4)
            
        frames_data.append(frame_kps)
        
    cap.release()
    return np.array(frames_data)

def main():
    download_model()
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    landmarker = get_landmarker()
        
    # Walk through dataset
    subjects = [s for s in os.listdir(DATASET_ROOT) if s.startswith("Subject")]
    
    for subject in subjects:
        for label in ["ADL", "Fall"]:
            input_path = os.path.join(DATASET_ROOT, subject, label)
            output_path = os.path.join(OUTPUT_DIR, subject, label)
            
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            
            if not os.path.exists(input_path):
                continue
                
            print(f"Processing {subject} - {label}...")
            
            videos = [f for f in os.listdir(input_path) if f.endswith(".mp4")]
            for video in videos:
                video_file = os.path.join(input_path, video)
                save_file = os.path.join(output_path, video.replace(".mp4", ".npy"))
                
                if os.path.exists(save_file):
                    continue
                    
                data = process_video(video_file, landmarker)
                np.save(save_file, data)
                
    print("Done! MediaPipe Preprocessing Complete.")

if __name__ == "__main__":
    main()
