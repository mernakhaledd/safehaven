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

win_features = []
whatsapp_features = []

for person in ["Merna", "Shaden"]:
    person_dir = os.path.join(KNOWN_FACES_DIR, person)
    for f in os.listdir(person_dir):
        if not (f.endswith('.jpg') or f.endswith('.jpeg')): continue
        feat = get_feature(os.path.join(person_dir, f))
        if feat is None: continue
        if "WIN" in f:
            win_features.append(feat)
        elif "WhatsApp" in f:
            whatsapp_features.append(feat)

print(f"Total WIN images with faces: {len(win_features)}")
print(f"Total WhatsApp images with faces: {len(whatsapp_features)}")

# Check distance within WIN
win_dists = []
for i in range(min(5, len(win_features))):
    for j in range(i+1, min(5, len(win_features))):
        win_dists.append(recognizer.match(win_features[i], win_features[j], cv2.FaceRecognizerSF_FR_COSINE))
print(f"Avg distance within WIN images: {sum(win_dists)/len(win_dists):.4f}")

# Check distance within WhatsApp
wa_dists = []
for i in range(min(5, len(whatsapp_features))):
    for j in range(i+1, min(5, len(whatsapp_features))):
        wa_dists.append(recognizer.match(whatsapp_features[i], whatsapp_features[j], cv2.FaceRecognizerSF_FR_COSINE))
print(f"Avg distance within WhatsApp images: {sum(wa_dists)/len(wa_dists):.4f}")

# Check distance between WIN and WhatsApp
cross_dists = []
for i in range(min(5, len(win_features))):
    for j in range(min(5, len(whatsapp_features))):
        cross_dists.append(recognizer.match(win_features[i], whatsapp_features[j], cv2.FaceRecognizerSF_FR_COSINE))
print(f"Avg distance between WIN and WhatsApp images: {sum(cross_dists)/len(cross_dists):.4f}")
