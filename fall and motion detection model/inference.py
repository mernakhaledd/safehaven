import cv2
import os
import torch
import numpy as np
import collections
from ultralytics import YOLO
import dataset_config
from train_model import FallDetectionLSTM
import time

# Alert System Mock
def send_alert(event_type, confidence):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[ALERT SYSTEM] 🚨 {event_type} DETECTED! ({confidence*100:.1f}%) at {timestamp}")
    
    print(f"\n[ALERT SYSTEM] 🚨 {event_type} DETECTED! ({confidence*100:.1f}%) at {timestamp}")
    
    # INTEGRATION: Send alert to Cloud (Supabase)
    try:
        # Try to import the local helper if it exists in the same folder
        try:
            from pi_supabase_trigger import send_alert_to_cloud
            send_alert_to_cloud(event_type, confidence)
        except ImportError:
            # Fallback if file not moved yet, or just print
            print("[ALERT] pi_supabase_trigger.py not found. Copy it to the same folder!")
            
    except Exception as e:
        print(f"[ALERT SYSTEM] Failed to send alert: {e}")

def run_inference(source=0):
    # Load Models
    print("Loading YOLO model...")
    yolo_model = YOLO('yolov8n-pose.pt')
    
    print("Loading LSTM model...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    lstm_model = FallDetectionLSTM(
        input_size=dataset_config.INPUT_SHAPE[1],
        hidden_size=64, # Must match training
        num_layers=2,
        num_classes=1
    ).to(device)
    
    model_path = 'fall_detection_lstm.pth'
    if not os.path.exists(model_path):
        print("Error: Model file not found. Please train first.")
        return

    lstm_model.load_state_dict(torch.load(model_path, map_location=device))
    lstm_model.eval()
    
    # Open Source
    # Open Source
    print(f"Opening Camera (Source: {source})...")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open video source {source}. Is the camera plugged in?")
        return
        
    # Buffer to store last 30 frames of keypoints
    sequence_length = dataset_config.FRAME_SEQUENCE_LENGTH
    # Deque is efficient for sliding window (append, popleft)
    keypoint_buffer = collections.deque(maxlen=sequence_length)
    
    # Status
    last_alert_time = 0
    alert_cooldown = 5 # seconds
    
    print("Starting Inference... Press 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # 1. YOLO Inference
        results = yolo_model(frame, verbose=False, task='pose')
        
        person_detected = False
        kps_flat = np.zeros(34) # Default empty
        
        # Visualize YOLO results
        annotated_frame = results[0].plot()
        
        if results[0].keypoints is not None and results[0].keypoints.shape[1] > 0:
            # Person detected
            keypoints = results[0].keypoints.xyn.cpu().numpy()
            if len(keypoints) > 0:
                person_detected = True
                kps_flat = keypoints[0].flatten()
                
                # Check for "Motion" - simplistically, if a person is here, there is motion
                # Ideally, compare with previous frame, but YOLO detection implies 'active object'
                cv2.putText(annotated_frame, "Status: MONITORING", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 2. Maintain Buffer
        keypoint_buffer.append(kps_flat)
        
        # 3. Fall Detection Logic
        fall_prob = 0.0
        status_text = "Buffering..."
        color = (0, 255, 0)
        
        if len(keypoint_buffer) == sequence_length and person_detected:
            # Prepare input for LSTM
            # Shape: (1, 30, 34)
            input_seq = np.array(keypoint_buffer)
            input_tensor = torch.FloatTensor(input_seq).unsqueeze(0).to(device)
            
            with torch.no_grad():
                output = lstm_model(input_tensor)
                fall_prob = output.item()
            
            # Display Probability
            color = (0, 255, 0)
            status_text = f"Fall Prob: {fall_prob:.2f}"
            
            if fall_prob > 0.5:
                color = (0, 255, 255) # Warning
            
            if fall_prob > 0.85: # Threshold
                color = (0, 0, 255) # Red for Fall
                status_text = "FALL DETECTED!"
                
                # Trigger Alert (with cooldown)
                if time.time() - last_alert_time > alert_cooldown:
                    send_alert("FALL", fall_prob)
                    last_alert_time = time.time()
            
            cv2.putText(annotated_frame, status_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Show Output
        # Check if we are running in a headless environment (no display)
        # If running via SSH without X11 forwarding, this prevents crashing.
        if os.environ.get('DISPLAY') is not None:
            cv2.imshow("Fall Detection System", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            # Headless mode: Print status periodically or on important events
            if time.time() % 2 < 0.2: 
                print(f"[HEADLESS] {status_text}")
                
            if "FALL" in status_text:
                print(f"\n!!! ALERT: {status_text} !!!\n")

            if cv2.waitKey(1) & 0xFF == ord('q'): 
                break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import os
    import sys
    
    # Check if a video file argument is provided
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        source = 0 # Webcam
        
    run_inference(source)
