import cv2
import pickle
import numpy as np
import time
import os

EMBEDDINGS_FILE = "embeddings/embeddings.pkl"
# Higher is better. With SFace Cosine Similarity, threshold is often around 0.363
THRESHOLD = 0.363

detector = cv2.FaceDetectorYN_create("face_detection_yunet_2023mar.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF_create("face_recognition_sface_2021dec.onnx", "")

def load_embeddings():
    if not os.path.exists(EMBEDDINGS_FILE):
        print("Error: Embeddings file not found! Please run enroll.py first.")
        return [], []
    with open(EMBEDDINGS_FILE, "rb") as f:
        data = pickle.load(f)
    return data["encodings"], data["names"]

def process_frame(frame, known_encodings, known_names):
    height, width, _ = frame.shape
    detector.setInputSize((width, height))
    
    # Detect faces using YuNet
    _, faces = detector.detect(frame)
    
    face_locations = []
    face_names = []
    
    if faces is not None:
        for face in faces:
            # face format: [x, y, w, h, x1, y1(leye), x2, y2(reye), ... confidence]
            box = list(map(int, face[:4]))
            x, y, w, h = box
            face_locations.append((x, y, w, h))
            
            name = "Unknown"
            
            # Extract Feature
            aligned_face = recognizer.alignCrop(frame, face)
            feature = recognizer.feature(aligned_face)
            
            if len(known_encodings) > 0:
                best_match_index = -1
                max_score = -1.0
                
                # Match against all known encodings
                for idx, known_feat in enumerate(known_encodings):
                    # recognizer.match calculates L2 distance (0) or Cosine (1)
                    # For Cosine, higher score = better match (closer to 1)
                    score = recognizer.match(known_feat, feature[0], cv2.FaceRecognizerSF_FR_COSINE)
                    if score > max_score:
                        max_score = score
                        best_match_index = idx
                        
                if max_score >= THRESHOLD:
                    name = known_names[best_match_index]
                    
            face_names.append(name)
            
    return face_locations, face_names

def main():
    known_encodings, known_names = load_embeddings()
    if len(known_names) == 0:
        print("Starting without any known faces. All detections will be 'Unknown'.")

    video_capture = cv2.VideoCapture(0)
    
    print("Starting webcam. Press 'q' to quit.")
    
    last_alert_time = 0
    alert_cooldown = 5 # seconds

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Failed to grab frame from camera. Exiting...")
            break
            
        # Software resize to prevent libcamera crash while keeping FPS high
        frame = cv2.resize(frame, (640, 480))
        
        start_time = time.time()
        
        face_locations, face_names = process_frame(frame, known_encodings, known_names)
        fps = 1.0 / (time.time() - start_time)

        for (x, y, w, h), name in zip(face_locations, face_names):
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            # Draw Face Bounding Box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            # Draw Label Background
            cv2.rectangle(frame, (x, y + h), (x + w, y + h + 30), color, cv2.FILLED)
            # Draw Label Text
            cv2.putText(frame, name, (x + 5, y + h + 22), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            
            # Print to SSH terminal
            print(f"[{fps:.1f} FPS] Detected: {name}")

            if name == "Unknown":
                current_time = time.time()
                if current_time - last_alert_time > alert_cooldown:
                    print(f"\n[ALERT SYSTEM] 🚨 UNKNOWN PERSON DETECTED! at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    try:
                        from pi_supabase_trigger import send_alert_to_cloud
                        send_alert_to_cloud("UNKNOWN_PERSON", 1.0)
                    except ImportError:
                        print("[ALERT] pi_supabase_trigger.py not found.")
                    except Exception as e:
                        print(f"[ALERT SYSTEM] Failed to send alert: {e}")
                    last_alert_time = current_time

        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        try:
            cv2.imshow('Door Camera: Face Recognition Demo (SFace)', frame)
        except cv2.error:
            # Fails gracefully if running headless over SSH without a display
            pass

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
