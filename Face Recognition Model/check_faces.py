import os
import cv2

KNOWN_FACES_DIR = "dataset/known_faces"
detector = cv2.FaceDetectorYN_create("face_detection_yunet_2023mar.onnx", "", (320, 320))

def count_faces(img_path):
    img = cv2.imread(img_path)
    if img is None: return -1
    height, width, _ = img.shape
    detector.setInputSize((width, height))
    _, faces = detector.detect(img)
    if faces is None: return 0
    return len(faces)

for person in ["Merna", "Shaden"]:
    person_dir = os.path.join(KNOWN_FACES_DIR, person)
    for f in os.listdir(person_dir):
        if f.endswith('.jpg') or f.endswith('.jpeg'):
            path = os.path.join(person_dir, f)
            c = count_faces(path)
            if c != 1:
                print(f"File {person}/{f} has {c} faces!")
