import os
import cv2
import pickle
import numpy as np

KNOWN_FACES_DIR = "dataset/known_faces"
EMBEDDINGS_FILE = "embeddings/embeddings.pkl"

# Initialize OpenCV's lightweight face detection (YuNet) and recognition (SFace) models
# These run on ANY CPU (and Raspberry Pi) purely via OpenCV! No C++ compiling needed.
detector = cv2.FaceDetectorYN_create("face_detection_yunet_2023mar.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF_create("face_recognition_sface_2021dec.onnx", "")

def main():
    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)
        print(f"Created {KNOWN_FACES_DIR}. Please add subfolders for each person with their images, then run again.")
        return

    if not os.path.exists(os.path.dirname(EMBEDDINGS_FILE)):
        os.makedirs(os.path.dirname(EMBEDDINGS_FILE))

    known_encodings = []
    known_names = []

    print("Processing faces using OpenCV SFace...")
    for name in os.listdir(KNOWN_FACES_DIR):
        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        
        if not os.path.isdir(person_dir):
            continue
            
        for filename in os.listdir(person_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(person_dir, filename)
                img = cv2.imread(img_path)
                if img is None:
                    continue
                
                # SFace works with BGR directly, no conversion needed!
                height, width, _ = img.shape
                detector.setInputSize((width, height))
                
                _, faces = detector.detect(img)
                
                if faces is None or len(faces) == 0:
                    print(f"Skipping {img_path} - no face detected.")
                    continue
                    
                if len(faces) > 1:
                    print(f"Warning: Multiple faces found in {img_path}, using the highest confidence one.")

                # Extract the 128D Embedding feature for the first face
                face = faces[0]
                aligned_face = recognizer.alignCrop(img, face)
                feature = recognizer.feature(aligned_face)
                
                known_encodings.append(feature[0])
                known_names.append(name)
                print(f"Enrolled {name} from {filename}")

    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump({"encodings": known_encodings, "names": known_names}, f)
        
    print(f"\nEnrollment complete! Saved {len(known_names)} embeddings to {EMBEDDINGS_FILE}")

if __name__ == "__main__":
    main()
