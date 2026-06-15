import torch
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from train_model import FallDetectionLSTM, load_data
import dataset_config

def evaluate_yolo_lstm():
    print("Loading Data (using logic from train_model.py)...")
    # load_data returns: X_train, y_train, X_test, y_test
    # We only care about X_test, y_test for rigorous evaluation (Subject 4)
    # load_data returns: X_train, y_train, X_test, y_test
    X_train, y_train, X_test, y_test = load_data()
    
    # Combine Train + Test for Full Dataset Evaluation
    X_full = np.concatenate((X_train, X_test), axis=0)
    y_full = np.concatenate((y_train, y_test), axis=0)
    
    print(f"FULL Dataset (All Subjects) shape: {X_full.shape}")
    
    if len(X_full) == 0:
        print("No data found! Please ensure 'processed_data' exists.")
        return

    # Prepare PyTorch DataLoader or just tensors
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Evaluating on device: {device}")
    
    # Check model file
    model_path = 'fall_detection_lstm.pth'
    if not hasattr(dataset_config, 'INPUT_SHAPE'):
         # Fallback if config is missing specific attr, though we saw it in view_file
         input_size = 34
    else:
         input_size = dataset_config.INPUT_SHAPE[1]

    # Initialize model
    model = FallDetectionLSTM(input_size, 64, 2, 1).to(device)
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()
    except Exception as e:
        print(f"Error loading model '{model_path}': {e}")
        print("Did you run 'python train_model.py' first?")
        return

    # Convert to Tensor
    X_tensor = torch.FloatTensor(X_full).to(device)

    print("Running Inference on FULL DATASET...")
    with torch.no_grad():
        outputs = model(X_tensor)
        # outputs are probabilities (Sigmoid)
        predicted_probs = outputs.cpu().numpy()
        predicted_labels = (predicted_probs > 0.5).astype(int)
        
    y_true = y_full.astype(int)
    
    print("\n" + "="*50)
    print("YOLO + LSTM Model Evaluation Results (FULL DATASET: Subjects 1-4)")
    print("="*50)
    
    accuracy = accuracy_score(y_true, predicted_labels)
    precision = precision_score(y_true, predicted_labels)
    recall = recall_score(y_true, predicted_labels)
    f1 = f1_score(y_true, predicted_labels)
    
    print(f"Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    
    print("\n--- Detailed Classification Report ---")
    print(classification_report(y_true, predicted_labels, target_names=["ADL", "Fall"]))
    print("="*50)
    print("Confusion Matrix:")
    print(confusion_matrix(y_true, predicted_labels))

if __name__ == "__main__":
    evaluate_yolo_lstm()
