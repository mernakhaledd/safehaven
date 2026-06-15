import os
import cv2
import pickle
import numpy as np

EMBEDDINGS_FILE = "embeddings/embeddings.pkl"
TEST_FACES_DIR = "dataset/test_faces"
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

def evaluate():
    if not os.path.exists(TEST_FACES_DIR):
        os.makedirs(TEST_FACES_DIR)
        print(f"Created {TEST_FACES_DIR}. Please add subfolders matching ground truth names (or 'Unknown') for testing.")
        return

    known_encodings, known_names = load_embeddings()
    total_images = 0
    correct_predictions = 0

    print("Starting Evaluation (OpenCV SFace)...\n")

    for ground_truth_name in os.listdir(TEST_FACES_DIR):
        person_dir = os.path.join(TEST_FACES_DIR, ground_truth_name)
        if not os.path.isdir(person_dir):
            continue

        for filename in os.listdir(person_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                total_images += 1
                img_path = os.path.join(person_dir, filename)
                img = cv2.imread(img_path)
                
                if img is None:
                    continue
                
                height, width, _ = img.shape
                detector.setInputSize((width, height))
                
                _, faces = detector.detect(img)
                
                if faces is None or len(faces) == 0:
                    print(f"[MISS] {img_path} - No face detected.")
                    continue

                # Take the first face
                face = faces[0]
                aligned_face = recognizer.alignCrop(img, face)
                feature = recognizer.feature(aligned_face)

                predicted_name = "Unknown"
                max_score = -1.0

                if len(known_encodings) > 0:
                    for idx, known_feat in enumerate(known_encodings):
                        score = recognizer.match(known_feat, feature[0], cv2.FaceRecognizerSF_FR_COSINE)
                        if score > max_score:
                            max_score = score
                            best_match_index = idx

                    if max_score >= THRESHOLD:
                        predicted_name = known_names[best_match_index]

                is_correct = (predicted_name == ground_truth_name)
                
                if is_correct:
                    correct_predictions += 1
                    print(f"[OK] {filename}: predicted {predicted_name} (Score: {max_score:.3f})")
                else:
                    print(f"[ERROR] {filename}: Ext:{ground_truth_name} VS Pred:{predicted_name} (Score: {max_score:.3f})")

    if total_images > 0:
        accuracy = (correct_predictions / total_images) * 100
        print(f"\nEvaluation Summary:")
        print(f"Total Test Images: {total_images}")
        print(f"Correct Matches  : {correct_predictions}")
        print(f"Accuracy         : {accuracy:.2f}%")
    else:
        print("No test images found. Please add images to dataset/test_faces/<Name>/")

if __name__ == "__main__":
    evaluate()
