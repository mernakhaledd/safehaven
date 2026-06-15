#!/usr/bin/env python3
"""
Training Script for Help Gesture Recognition Model
This script trains a neural network classifier on the collected landmark data.
"""

import numpy as np
import os
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import json

class GestureModelTrainer:
    def __init__(self, dataset_dir='dataset', model_dir='models'):
        """Initialize the trainer"""
        self.dataset_dir = dataset_dir
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        self.X_data = []
        self.y_data = []
        self.label_encoder = LabelEncoder()
        
    def load_dataset(self):
        """Load all landmark data from the dataset directory"""
        print("\n" + "="*60)
        print("Loading Dataset...")
        print("="*60)
        
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
    
    def build_model(self, input_dim, num_classes):
        """Build a neural network for gesture classification"""
        model = keras.Sequential([
            keras.layers.Input(shape=(input_dim,)),
            
            # Dense layers with dropout for regularization
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
            
            # Output layer
            keras.layers.Dense(num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train(self, epochs=100, batch_size=32, augment=True):
        """Train the gesture recognition model"""
        # Load dataset
        X, y = self.load_dataset()
        
        # Augment data if requested
        if augment:
            X, y = self.augment_data(X, y)
        
        # Split dataset
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"\nTraining set: {len(X_train)} samples")
        print(f"Test set: {len(X_test)} samples")
        
        # Build model
        num_classes = len(self.label_encoder.classes_)
        model = self.build_model(X.shape[1], num_classes)
        
        print("\n" + "="*60)
        print("Model Architecture:")
        print("="*60)
        model.summary()
        
        # Callbacks
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True
        )
        
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6
        )
        
        # Train model
        print("\n" + "="*60)
        print("Training Model...")
        print("="*60)
        
        history = model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )
        
        # Evaluate model
        print("\n" + "="*60)
        print("Evaluating Model...")
        print("="*60)
        
        test_loss, test_accuracy = model.evaluate(X_test, y_test)
        print(f"\nTest Accuracy: {test_accuracy*100:.2f}%")
        print(f"Test Loss: {test_loss:.4f}")
        
        # Save model
        model_path = os.path.join(self.model_dir, 'help_gesture_model.h5')
        model.save(model_path)
        print(f"\nModel saved to: {model_path}")
        
        # Save label encoder
        label_map = {i: label for i, label in enumerate(self.label_encoder.classes_)}
        label_map_path = os.path.join(self.model_dir, 'label_map.json')
        with open(label_map_path, 'w') as f:
            json.dump(label_map, f, indent=2)
        print(f"Label map saved to: {label_map_path}")
        
        # Convert to TensorFlow Lite for Raspberry Pi
        self.convert_to_tflite(model)
        
        # Plot training history
        self.plot_training_history(history)
        
        return model, history
    
    def convert_to_tflite(self, model):
        """Convert the model to TensorFlow Lite format for deployment"""
        print("\n" + "="*60)
        print("Converting to TensorFlow Lite...")
        print("="*60)
        
        # Convert to TFLite
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        
        # Save TFLite model
        tflite_path = os.path.join(self.model_dir, 'help_gesture_model.tflite')
        with open(tflite_path, 'wb') as f:
            f.write(tflite_model)
        
        print(f"TFLite model saved to: {tflite_path}")
        print(f"TFLite model size: {len(tflite_model) / 1024:.2f} KB")
        print("This model can be deployed on Raspberry Pi!")
        
    def plot_training_history(self, history):
        """Plot training metrics"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Accuracy plot
        ax1.plot(history.history['accuracy'], label='Train Accuracy')
        ax1.plot(history.history['val_accuracy'], label='Val Accuracy')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Accuracy')
        ax1.set_title('Model Accuracy')
        ax1.legend()
        ax1.grid(True)
        
        # Loss plot
        ax2.plot(history.history['loss'], label='Train Loss')
        ax2.plot(history.history['val_loss'], label='Val Loss')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.set_title('Model Loss')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plot_path = os.path.join(self.model_dir, 'training_history.png')
        plt.savefig(plot_path, dpi=150)
        print(f"\nTraining plot saved to: {plot_path}")
        plt.close()

if __name__ == "__main__":
    trainer = GestureModelTrainer(dataset_dir='dataset', model_dir='models')
    model, history = trainer.train(epochs=100, batch_size=32, augment=True)
    
    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Run '3_test_realtime.py' to test the model")
    print("2. Deploy 'models/help_gesture_model.tflite' to Raspberry Pi")
    print("="*60)