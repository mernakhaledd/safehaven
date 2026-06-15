import os
import cv2
import pickle

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

merna_dir = os.path.join(KNOWN_FACES_DIR, "Merna")
merna_imgs = [f for f in os.listdir(merna_dir) if f.endswith('.jpg') or f.endswith('.jpeg')]

shaden_dir = os.path.join(KNOWN_FACES_DIR, "Shaden")
shaden_imgs = [f for f in os.listdir(shaden_dir) if f.endswith('.jpg') or f.endswith('.jpeg')]

win_merna = [f for f in merna_imgs if "WIN_" in f][0]
whatsapp_merna = [f for f in merna_imgs if "WhatsApp" in f][0]
win_shaden = [f for f in shaden_imgs if "WIN_" in f][0]
whatsapp_shaden = [f for f in shaden_imgs if "WhatsApp" in f][0]

feat_wm = get_feature(os.path.join(merna_dir, win_merna))
feat_wam = get_feature(os.path.join(merna_dir, whatsapp_merna))
feat_ws = get_feature(os.path.join(shaden_dir, win_shaden))
feat_was = get_feature(os.path.join(shaden_dir, whatsapp_shaden))

print(f"Dist(WIN_Merna, WIN_Shaden) = {recognizer.match(feat_wm, feat_ws, cv2.FaceRecognizerSF_FR_COSINE):.4f}")
print(f"Dist(WhatsApp_Merna, WhatsApp_Shaden) = {recognizer.match(feat_wam, feat_was, cv2.FaceRecognizerSF_FR_COSINE):.4f}")

print(f"Dist(WIN_Merna, WhatsApp_Shaden) = {recognizer.match(feat_wm, feat_was, cv2.FaceRecognizerSF_FR_COSINE):.4f}")
print(f"Dist(WhatsApp_Merna, WIN_Shaden) = {recognizer.match(feat_wam, feat_ws, cv2.FaceRecognizerSF_FR_COSINE):.4f}")
