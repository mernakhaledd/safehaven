
import numpy as np
import os
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score

def strict_evaluation():
    print("Running STRICT Scientific Evaluation (No Data Leakage)...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(base_dir, 'dataset')
    
    # 1. Load Raw Data
    X_data = []
    y_data = []
    label_encoder = LabelEncoder()
    
    if not os.path.exists(dataset_dir):
        print("Dataset not found!")
        return

    print("Loading raw dataset...")
    for gesture_name in os.listdir(dataset_dir):
        gesture_path = os.path.join(dataset_dir, gesture_name)
        if not os.path.isdir(gesture_path): continue
        
        files = [f for f in os.listdir(gesture_path) if f.endswith('.npy')]
        for filename in files:
            filepath = os.path.join(gesture_path, filename)
            X_data.append(np.load(filepath))
            y_data.append(gesture_name)

    X = np.array(X_data)
    y = np.array(y_data)
    y_encoded = label_encoder.fit_transform(y)
    
    print(f"Total raw samples: {len(X)}")

    # 2. STRICT SPLIT: Split BEFORE Augmentation
    # This ensures the test set contains samples the model has NEVER seen (not even augmented versions)
    X_train_raw, X_test_raw, y_train_raw, y_test_raw = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    print(f"Training samples (raw): {len(X_train_raw)}")
    print(f"Test samples (raw): {len(X_test_raw)}")

    # 3. Augment ONLY Training Data
    print("Augmenting Training Data Only (4x)...")
    X_augmented = [X_train_raw]
    y_augmented = [y_train_raw]
    
    for _ in range(3): # Add 3 variations + original = 4x
        noise = np.random.normal(0, 0.01, X_train_raw.shape)
        X_noisy = X_train_raw + noise
        X_augmented.append(X_noisy)
        y_augmented.append(y_train_raw)
        
    X_train_final = np.vstack(X_augmented)
    y_train_final = np.concatenate(y_augmented)
    print(f"Final Standardized Training Size: {len(X_train_final)}")

    # 4. Train a Validation Model (Just for Metrics)
    print("Training Validation Model...")
    model = keras.Sequential([
        keras.layers.Input(shape=(X.shape[1],)),
        keras.layers.Dense(256, activation='relu'),
        keras.layers.BatchNormalization(),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(128, activation='relu'),
        keras.layers.BatchNormalization(),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(64, activation='relu'),
        keras.layers.BatchNormalization(),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(32, activation='relu'),
        keras.layers.Dense(len(label_encoder.classes_), activation='softmax')
    ])
    
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    
    # Fast training enough for validation
    model.fit(X_train_final, y_train_final, epochs=50, batch_size=32, verbose=0)
    
    # 5. Evaluate on STRICT Test Set
    print("\nEvaluating on unseen raw test data...")
    y_pred_probs = model.predict(X_test_raw)
    y_pred = np.argmax(y_pred_probs, axis=1)
    
    # Metrics
    accuracy = accuracy_score(y_test_raw, y_pred)
    precision = precision_score(y_test_raw, y_pred, average='weighted')
    recall = recall_score(y_test_raw, y_pred, average='weighted')
    f1 = f1_score(y_test_raw, y_pred, average='weighted')
    
    print("\n" + "="*60)
    print("STRICT SCIENTIFIC RESULTS (No Data Leakage)")
    print("="*60)
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print("-" * 60)
    print(confusion_matrix(y_test_raw, y_pred))

    # Determine if we should save these
    results_path = os.path.join(base_dir, 'strict_research_metrics.txt')
    with open(results_path, 'w') as f:
        f.write("Strict Model Evaluation (No Augmentation Leakage)\n")
        f.write("===============================================\n")
        f.write(f"Accuracy:  {accuracy:.4f}\n")
        f.write(f"Precision: {precision:.4f}\n")
        f.write(f"Recall:    {recall:.4f}\n")
        f.write(f"F1 Score:  {f1:.4f}\n\n")
        f.write("Confusion Matrix:\n")
        f.write(np.array2string(confusion_matrix(y_test_raw, y_pred)))

if __name__ == "__main__":
    strict_evaluation()
