
import numpy as np
import os
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import seaborn as sns
import json

class GestureModelTrainer:
    def __init__(self, dataset_dir='dataset', model_dir='models'):
        """Initialize the trainer"""
        self.dataset_dir = dataset_dir
        self.model_dir = model_dir
        # os.makedirs(model_dir, exist_ok=True) # Not creating dirs in evaluation
        
        self.X_data = []
        self.y_data = []
        self.label_encoder = LabelEncoder()
        
    def load_dataset(self):
        """Load all landmark data from the dataset directory"""
        print("\n" + "="*60)
        print("Loading Dataset...")
        print("="*60)
        
        # Check if dataset dir exists
        if not os.path.exists(self.dataset_dir):
            print(f"Error: Dataset directory '{self.dataset_dir}' not found.")
            return np.array([]), np.array([])

        gesture_classes = []
        
        for gesture_name in os.listdir(self.dataset_dir):
            gesture_path = os.path.join(self.dataset_dir, gesture_name)
            
            if not os.path.isdir(gesture_path):
                continue
            
            gesture_files = [f for f in os.listdir(gesture_path) if f.endswith('.npy')]
            print(f"Loading {gesture_name}: {len(gesture_files)} samples")
            
            for filename in gesture_files:
                filepath = os.path.join(gesture_path, filename)
                landmarks = np.load(filepath)
                
                self.X_data.append(landmarks)
                self.y_data.append(gesture_name)
        
        # Convert to numpy arrays
        if len(self.X_data) == 0:
            print("No data found!")
            return np.array([]), np.array([])

        self.X_data = np.array(self.X_data)
        self.y_data = np.array(self.y_data)
        
        # Encode labels
        self.y_encoded = self.label_encoder.fit_transform(self.y_data)
        
        print(f"\nTotal samples loaded: {len(self.X_data)}")
        print(f"Feature dimensions: {self.X_data.shape[1]}")
        print(f"Classes: {list(self.label_encoder.classes_)}")
        print("="*60)
        
        return self.X_data, self.y_encoded
    
    def augment_data(self, X, y, augmentation_factor=3):
        """Augment the dataset with slight variations"""
        print("\nAugmenting data...")
        
        X_augmented = [X]
        y_augmented = [y]
        
        for _ in range(augmentation_factor):
            # Add small random noise
            noise = np.random.normal(0, 0.01, X.shape)
            X_noisy = X + noise
            
            X_augmented.append(X_noisy)
            y_augmented.append(y)
        
        X_final = np.vstack(X_augmented)
        y_final = np.concatenate(y_augmented)
        
        print(f"Dataset size after augmentation: {len(X_final)}")
        
        return X_final, y_final

def evaluate_model():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(base_dir, 'dataset')
    model_dir = os.path.join(base_dir, 'models')
    model_path = os.path.join(model_dir, 'help_gesture_model.h5')

    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return

    # Use the trainer class to load and process data exactly as done during training
    trainer = GestureModelTrainer(dataset_dir=dataset_dir, model_dir=model_dir)
    
    # 1. Load Dataset
    X, y = trainer.load_dataset()
    if len(X) == 0:
        return

    # 2. Augment Data (Must match training exactly to reproduce the test split)
    # The training script used default augmentation_factor=3 and augment=True
    X, y = trainer.augment_data(X, y, augmentation_factor=3)

    # 3. Slit Data
    # The training script used test_size=0.2, random_state=42, stratify=y
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nEvaluation Set Size: {len(X_test)} samples")

    # 4. Load Model
    print(f"Loading model from {model_path}...")
    try:
        model = keras.models.load_model(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # 5. Predict
    print("Running predictions...")
    y_pred_probs = model.predict(X_test)
    y_pred = np.argmax(y_pred_probs, axis=1)

    # 6. Calculate Metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')

    # Get class names for report
    class_names = trainer.label_encoder.classes_

    print("\n" + "="*60)
    print("EVALUATION RESULTS FOR RESEARCH PAPER")
    print("="*60)
    
    print(f"\nOverall Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"Weighted Precision: {precision:.4f}")
    print(f"Weighted Recall:    {recall:.4f}")
    print(f"Weighted F1 Score:  {f1:.4f}")

    print("\nDetailed Classification Report:")
    print("-" * 60)
    print(classification_report(y_test, y_pred, target_names=class_names, digits=4))
    print("-" * 60)

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix:")
    print(cm)
    
    # Save results to a text file for easy copy-pasting
    results_path = os.path.join(base_dir, 'research_paper_metrics.txt')
    with open(results_path, 'w') as f:
        f.write("Model Evaluation Metrics\n")
        f.write("========================\n\n")
        f.write(f"Accuracy:  {accuracy:.4f}\n")
        f.write(f"Precision: {precision:.4f}\n")
        f.write(f"Recall:    {recall:.4f}\n")
        f.write(f"F1 Score:  {f1:.4f}\n\n")
        f.write("Detailed Report:\n")
        f.write(classification_report(y_test, y_pred, target_names=class_names, digits=4))
        f.write("\nConfusion Matrix:\n")
        f.write(np.array2string(cm))
    
    print(f"\nResults saved to: {results_path}")
    print("="*60)

if __name__ == "__main__":
    evaluate_model()
