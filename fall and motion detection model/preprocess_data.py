import os
import cv2
import numpy as np
from ultralytics import YOLO
import dataset_config
from tqdm import tqdm

def preprocess_video(video_path, model, output_path):
    cap = cv2.VideoCapture(video_path)
    frames_data = []
    
    # Get video properties
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
    if width == 0 or height == 0:
        print(f"Error reading {video_path}")
        return False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Run YOLO inference
        # verbose=False to keep clutter down
        results = model(frame, verbose=False, task='pose')
        
        # Extract keypoints
        # result.keypoints.xyn gives normalized (0-1) coordinates
        # shape is (1, 17, 2). If multiple people, we take the one with highest conf?
        # For this dataset, usually one person. We'll take the first detection.
        
        if results[0].keypoints is not None and results[0].keypoints.shape[1] > 0:
            # Get normalized keypoints (x, y)
            # xyn is (N, 17, 2)
            keypoints = results[0].keypoints.xyn.cpu().numpy()
            
            if len(keypoints) > 0:
                # Take the first person detected
                person_kps = keypoints[0] # Shape (17, 2)
                
                # Flatten to (34,) vector
                flat_kps = person_kps.flatten()
                frames_data.append(flat_kps)
            else:
                # No person detected, append zeros
                frames_data.append(np.zeros(34))
        else:
             frames_data.append(np.zeros(34))

    cap.release()
    
    # Save as .npy
    if len(frames_data) > 0:
        np.save(output_path, np.array(frames_data))
        return True
    return False

def main():
    # Load model once using YOLOv8 Nano Pose (fastest)
    print("Loading YOLOv8n-pose model...")
    model = YOLO('yolov8n-pose.pt') 
    
    if not os.path.exists(dataset_config.PROCESSED_DATA_ROOT):
        os.makedirs(dataset_config.PROCESSED_DATA_ROOT)

    root_dir = dataset_config.DATASET_ROOT
    if not os.path.exists(root_dir):
        print(f"Error: Dataset root '{root_dir}' not found.")
        return

    subjects = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    
    total_videos = 0
    processed_count = 0

    print(f"Found subjects: {subjects}")

    for subject in subjects:
        subject_path = os.path.join(root_dir, subject)
        
        for category in ["ADL", "Fall"]:
            cat_path = os.path.join(subject_path, category)
            if not os.path.exists(cat_path):
                continue
                
            # Create output directory
            output_dir = os.path.join(dataset_config.PROCESSED_DATA_ROOT, subject, category)
            os.makedirs(output_dir, exist_ok=True)
            
            print(f"Processing {subject} - {category}...")
            
            videos = [f for f in os.listdir(cat_path) if f.lower().endswith(('.mp4', '.avi', '.mkv'))]
            
            for vid in tqdm(videos):
                total_videos += 1
                input_vid = os.path.join(cat_path, vid)
                output_npy = os.path.join(output_dir, os.path.splitext(vid)[0] + ".npy")
                
                if not os.path.exists(output_npy):
                    success = preprocess_video(input_vid, model, output_npy)
                    if success:
                        processed_count += 1
                else:
                    # Skip if already processed
                    processed_count += 1

    print(f"Processing complete. Processed {processed_count}/{total_videos} videos.")

if __name__ == "__main__":
    main()
