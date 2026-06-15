import os
import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from tensorflow.keras.models import load_model

DATA_DIR = "mp_processed_data"
SEQ_LEN = 30
# NUM_FEATURES in training was 132. The model will expect inputs of shape (None, 30, 132)

def load_data():
    X, y = [], []
    
    if not os.path.exists(DATA_DIR):
        print(f"Data directory {DATA_DIR} not found.")
        return np.array([]), np.array([])

    subjects = os.listdir(DATA_DIR)
    print(f"Found subjects: {subjects}")
    for subj in subjects:
        subj_path = os.path.join(DATA_DIR, subj)
        if not os.path.isdir(subj_path):
            continue
            
        # Check output folders
        for label, class_id in [("ADL", 0), ("Fall", 1)]:
            path = os.path.join(subj_path, label)
            if not os.path.exists(path): continue
            
            files = [f for f in os.listdir(path) if f.endswith(".npy")]
            for f in files:
                data = np.load(os.path.join(path, f))
                
                # The training script uses: for i in range(0, len(data) - SEQ_LEN, 5)
                # We should use the same logic to generate the samples for evaluation
                for i in range(0, len(data) - SEQ_LEN, 5): 
                    seq = data[i:i+SEQ_LEN]
                    X.append(seq)
                    y.append(class_id)
                        
    return np.array(X), np.array(y)

def evaluate():
    print("Loading Data...")
    X, y = load_data()
    print(f"Data shape: {X.shape}")
    
    if len(X) == 0:
        print("No data found! Please ensure 'mp_processed_data' exists and contains .npy files.")
        return

    print("Loading Model...")
    model_path = "mp_fall_model.h5"
    if not os.path.exists(model_path):
        print(f"Model file {model_path} not found.")
        return

    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print("Predicting...")
    # Batch prediction
    y_pred_prob = model.predict(X, verbose=1)
    y_pred = (y_pred_prob > 0.5).astype(int)

    print("\n--- Evaluation Metrics (Train + Test set combined / Whole Dataset) ---")
    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred)
    recall = recall_score(y, y_pred)
    f1 = f1_score(y, y_pred)

    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")

    print("\n--- Detailed Report ---")
    print(classification_report(y, y_pred, target_names=["ADL", "Fall"]))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y, y_pred))

if __name__ == "__main__":
    evaluate()
