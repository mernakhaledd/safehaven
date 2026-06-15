import os
import cv2

KNOWN_FACES_DIR = "dataset/known_faces"

detector = cv2.FaceDetectorYN_create("face_detection_yunet_2023mar.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF_create("face_recognition_sface_2021dec.onnx", "")

def get_feature(img_path):
    img = cv2.imread(img_path)
    if img is None: return None
    height, width, _ = img.shape
    detector.setInputSize((width, height))
    _, faces = detector.detect(img)
    if faces is None or len(faces) == 0: return None
    face = faces[0]
    aligned_face = recognizer.alignCrop(img, face)
    feature = recognizer.feature(aligned_face)
    return feature[0]

shaden_dir = os.path.join(KNOWN_FACES_DIR, "Shaden")
merna_dir = os.path.join(KNOWN_FACES_DIR, "Merna")

m_imgs = [f for f in os.listdir(merna_dir) if f.endswith('.jpg') or f.endswith('.jpeg')]
s_imgs = [f for f in os.listdir(shaden_dir) if f.endswith('.jpg') or f.endswith('.jpeg')]

wm = get_feature(os.path.join(merna_dir, [f for f in m_imgs if "WIN_" in f][0]))
wam = get_feature(os.path.join(merna_dir, [f for f in m_imgs if "WhatsApp" in f][0]))
ws = get_feature(os.path.join(shaden_dir, [f for f in s_imgs if "WIN_" in f][0]))
was = get_feature(os.path.join(shaden_dir, [f for f in s_imgs if "WhatsApp" in f][0]))

print("L2 Distances:")
print(f"Merna (WIN vs WA): {recognizer.match(wm, wam, cv2.FaceRecognizerSF_FR_NORM_L2):.4f}")
print(f"Shaden (WIN vs WA): {recognizer.match(ws, was, cv2.FaceRecognizerSF_FR_NORM_L2):.4f}")
print(f"WIN (Merna vs Shaden): {recognizer.match(wm, ws, cv2.FaceRecognizerSF_FR_NORM_L2):.4f}")
print(f"WA (Merna vs Shaden): {recognizer.match(wam, was, cv2.FaceRecognizerSF_FR_NORM_L2):.4f}")
