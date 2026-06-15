# Intelligent Camera-Based Fall Detection System
## Graduation Project

### Project Overview
This system uses computer vision to detect falls in real-time using a standard camera. It is designed for medical home security, running efficiently on edge devices.

### Architecture
1.  **Pose Estimation**: YOLOv8-Pose extracts skeletal keypoints (privacy-preserving).
2.  **Fall Classification**: LSTM (Recurrent Neural Network) analyzes the motion patterns of the keypoints to detect falls.

### Setup Instructions

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Data Preparation**
    The system expects the dataset in `fall dataset/fall dataset/`.
    Run the preprocessing script to extract keypoints from videos:
    ```bash
    python preprocess_data.py
    ```
    *This creates a `processed_data` folder with `.npy` files.*

3.  **Train the Model**
    Train the LSTM network on the extracted data:
    ```bash
    python train_model.py
    ```
    *This saves the best model as `fall_detection_lstm.pth`.*

4.  **Run Inference**
    To run on your webcam:
    ```bash
    python inference.py
    ```
    To run on a specific video file:
    ```bash
    python inference.py "path/to/video.mp4"
    ```

### Files Description
*   `dataset_config.py`: Configuration paths.
*   `preprocess_data.py`: Converts video frames to skeleton keypoints.
*   `train_model.py`: Defines and trains the LSTM neural network.
*   `inference.py`: Real-time detection script.
*   `check_data.py`: Helper to verify dataset structure.

