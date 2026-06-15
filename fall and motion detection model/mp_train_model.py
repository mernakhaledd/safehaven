import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.model_selection import train_test_split

DATA_DIR = "mp_processed_data"
SEQ_LEN = 30
NUM_FEATURES = 33 * 4 # 132

def load_data():
    X, y = [], []
    
    subjects = os.listdir(DATA_DIR)
    for subj in subjects:
        # Check output folders
        for label, class_id in [("ADL", 0), ("Fall", 1)]:
            path = os.path.join(DATA_DIR, subj, label)
            if not os.path.exists(path): continue
            
            for f in os.listdir(path):
                if f.endswith(".npy"):
                    data = np.load(os.path.join(path, f))
                    
                    # Create Sequences
                    for i in range(0, len(data) - SEQ_LEN, 5): # Step 5 for overlap
                        seq = data[i:i+SEQ_LEN]
                        X.append(seq)
                        y.append(class_id)
                        
    return np.array(X), np.array(y)

def train():
    print("Loading Data...")
    X, y = load_data()
    print(f"Data shape: {X.shape}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(SEQ_LEN, NUM_FEATURES)),
        LSTM(32, return_sequences=False),
        Dropout(0.5),
        Dense(32, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    
    print("Training...")
    model.fit(X_train, y_train, epochs=15, batch_size=32, validation_data=(X_test, y_test))
    
    model.save("mp_fall_model.h5")
    print("Saved Keras model.")
    
    # Convert to TFLite (Compatibility Mode)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16] # Reduce size, potentially use older ops
    
    # Enable Select TF Ops (Required for LSTM)
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS, 
        tf.lite.OpsSet.SELECT_TF_OPS
    ]
    converter._experimental_lower_tensor_list_ops = False
    
    tflite_model = converter.convert()
    
    with open("mp_fall_model.tflite", "wb") as f:
        f.write(tflite_model)
    print("Saved TFLite model!")

if __name__ == "__main__":
    train()
