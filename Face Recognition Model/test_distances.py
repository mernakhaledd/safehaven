import os
import cv2
import pickle

EMBEDDINGS_FILE = "embeddings/embeddings.pkl"
KNOWN_FACES_DIR = "dataset/known_faces"

with open(EMBEDDINGS_FILE, "rb") as f:
    data = pickle.load(f)

known_encodings = data["encodings"]
known_names = data["names"]

detector = cv2.FaceDetectorYN_create("face_detection_yunet_2023mar.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF_create("face_recognition_sface_2021dec.onnx", "")

# Pick one image from Merna
merna_dir = os.path.join(KNOWN_FACES_DIR, "Merna")
merna_imgs = [f for f in os.listdir(merna_dir) if f.endswith('.jpg') or f.endswith('.jpeg')]
merna_img_path = os.path.join(merna_dir, merna_imgs[0])
print(f"Testing with Merna image: {merna_imgs[0]}")

img = cv2.imread(merna_img_path)
height, width, _ = img.shape
detector.setInputSize((width, height))
_, faces = detector.detect(img)
face = faces[0]
aligned_face = recognizer.alignCrop(img, face)
feature = recognizer.feature(aligned_face)

print("\nDistances to known embeddings:")
for name_target in set(known_names):
    distances = []
    for idx, (known_feat, k_name) in enumerate(zip(known_encodings, known_names)):
        if k_name == name_target:
            dist = recognizer.match(known_feat, feature[0], cv2.FaceRecognizerSF_FR_COSINE)
            distances.append(dist)
    if distances:
        print(f"To {name_target}: Min = {min(distances):.4f}, Max = {max(distances):.4f}, Avg = {sum(distances)/len(distances):.4f}")
