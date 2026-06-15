import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import dataset_config
from sklearn.metrics import classification_report, confusion_matrix

# --- Neural Network Model ---
class FallDetectionLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, num_classes):
        super(FallDetectionLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM Layer
        # batch_first=True -> (batch, seq, feature)
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        
        # Fully Connected Layer
        self.fc = nn.Linear(hidden_size, num_classes)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x.shape: (batch, seq_len, input_size)
        
        # Initialize hidden state and cell state
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        # Forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        out = self.sigmoid(out)
        return out

# --- Dataset Handler ---
class PoseDataset(Dataset):
    def __init__(self, data, labels):
        self.data = torch.FloatTensor(data)
        self.labels = torch.FloatTensor(labels)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]

def create_sequences(data, seq_length):
    # Data is (Total_Frames, 34)
    # We want sliding windows
    sequences = []
    if len(data) < seq_length:
        # Pad if too short using the last frame
        padding = np.tile(data[-1], (seq_length - len(data), 1))
        data = np.vstack((data, padding))
        
    for i in range(len(data) - seq_length + 1):
        seq = data[i:i+seq_length]
        sequences.append(seq)
    
    return np.array(sequences)

def load_data():
    X_train, y_train = [], []
    X_test, y_test = [], []
    
    processed_dir = dataset_config.PROCESSED_DATA_ROOT
    seq_len = dataset_config.FRAME_SEQUENCE_LENGTH
    
    # Subject 4 is Test, others Train
    test_subject = "Subject 4"
    
    subjects = [d for d in os.listdir(processed_dir) if os.path.isdir(os.path.join(processed_dir, d))]
    
    print("Loading data and creating sequences...")
    for subj in subjects:
        is_test = (subj == test_subject)
        
        for label_name in ["ADL", "Fall"]:
            label_val = 1 if label_name == "Fall" else 0
            
            dir_path = os.path.join(processed_dir, subj, label_name)
            if not os.path.exists(dir_path):
                continue
                
            files = [f for f in os.listdir(dir_path) if f.endswith('.npy')]
            
            for f in files:
                file_path = os.path.join(dir_path, f)
                # Load the full video sequence of keypoints
                video_data = np.load(file_path) # Shape (Frames, 34)
                
                # Normalize if not already (check if preprocess_data did it - yes, xyn is 0-1)
                
                # Create sliding windows
                # For training, we can use overlap to augment
                # For this simple version, let's step by 10 frames to reduce redundancy
                step = 10 
                
                if len(video_data) < seq_len:
                    continue

                for i in range(0, len(video_data) - seq_len + 1, step):
                    seq = video_data[i:i+seq_len]
                    
                    if is_test:
                        X_test.append(seq)
                        y_test.append(label_val)
                    else:
                        X_train.append(seq)
                        y_train.append(label_val)
                        
    return np.array(X_train), np.array(y_train), np.array(X_test), np.array(y_test)

def train():
    # Hyperparameters
    input_size = 34 # 17 keypoints * 2 (x, y)
    hidden_size = 64
    num_layers = 2
    num_classes = 1 # Binary classification
    batch_size = 32
    num_epochs = 20
    learning_rate = 0.001
    
    # Load Data
    X_train, y_train, X_test, y_test = load_data()
    print(f"Train shapes: X={X_train.shape}, y={y_train.shape}")
    print(f"Test shapes: X={X_test.shape}, y={y_test.shape}")
    
    if len(X_train) == 0:
        print("No training data found! Run preprocess_data.py first.")
        return

    train_dataset = PoseDataset(X_train, y_train)
    test_dataset = PoseDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    # Device configuration
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Training on device: {device}")
    
    model = FallDetectionLSTM(input_size, hidden_size, num_layers, num_classes).to(device)
    
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Training Loop
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0
        correct = 0
        total = 0
        
        for sequences, labels in train_loader:
            sequences = sequences.to(device)
            labels = labels.unsqueeze(1).to(device)
            
            # Forward
            outputs = model(sequences)
            loss = criterion(outputs, labels)
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            predicted = (outputs > 0.5).float()
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        acc = 100 * correct / total
        print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {train_loss/len(train_loader):.4f}, Accuracy: {acc:.2f}%')
        
    # Evaluation
    print("\nEvaluating on Test Set (Subject 4)...")
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for sequences, labels in test_loader:
            sequences = sequences.to(device)
            labels = labels.unsqueeze(1).to(device)
            outputs = model(sequences)
            predicted = (outputs > 0.5).float()
            
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
    print(classification_report(all_labels, all_preds, target_names=['ADL', 'Fall']))
    
    # Save Model
    torch.save(model.state_dict(), 'fall_detection_lstm.pth')
    print("Model saved as 'fall_detection_lstm.pth'")

if __name__ == "__main__":
    train()
