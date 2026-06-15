# AI Solution Design: Camera-Based Motion & Fall Detection System

## 1. Model Choice & Architecture

### Recommended Architecture: **Hybrid Vision-Pose Pipeline**
We will use a **Two-Stage Architecture**:
1.  **Stage 1: Person Detection & Pose Estimation (YOLOv8-Pose)**
    *   **Why?** YOLOv8-Pose is State-of-the-Art (SOTA) for real-time speed and accuracy. The "Nano" (n) or "Small" (s) versions are highly optimized for edge devices (Jetson/Raspberry Pi).
    *   It detects the person (Bounding Box) and their skeletal keypoints (17 joints) in a single pass.
2.  **Stage 2: Temporal Fall Classifier (LSTM or Lightweight Recurrent Network)**
    *   **Why?** Falls are dynamic events, not static images. An LSTM (Long Short-Term Memory) network analyzes the *sequence* of keypoint movements over time (e.g., last 30 frames) to distinguish between "falling" and "lying down fast".
    *   This is far more lightweight than using 3D CNNs (like I3D) on raw video pixels.

### Why this is suitable:
*   **Privacy Preserving:** We process skeletons, not storing raw video faces in the cloud.
*   **Efficiency:** Keypoint data is tiny (vectors of numbers) compared to video frames, allowing the LSTM to run in microseconds.
*   **Accuracy:** Decouples "Is there a person?" from "Is the person falling?", reducing false positives from shadows or pets (YOLO filters those out).

---

## 2. Data Preparation

### Preprocessing Strategy
Since the dataset has "Subject 1, 2, 3, 4" and different angles:
1.  **Frame Extraction**: Convert video clips to sequences of frames (e.g., 30 FPS).
2.  **Keypoint Extraction**: Run YOLOv8-Pose on every frame to extract the 17 keypoints $(x, y, confidence)$.
3.  **Normalization**:
    *   Center the pose: Subtract the hip center coordinates from all points so movement is relative to the body, not the room.
    *   Scale invariance: Divide by the height of the bounding box so the model works for people near (large) and far (small).
4.  **Windowing (Sliding Window)**:
    *   Create input sequences of fixed length (e.g., 30 frames / 1 second).
    *   Label: If the window contains the peak of a "Fall" event, label as `1`, otherwise `0`.

### Handling Multiple Angles
*   Because we use **2D Keypoints**, angles can distort the skeleton.
*   **Strategy**: Train the LSTM on data from *all* angles mixed together. This forces the model to learn invariant features (like sudden vertical acceleration) rather than memorizing a specific view.
*   **Augmentation**: Randomly flip keypoints horizontally during training to double the dataset size.

---

## 3. Training Strategy

### Split
*   **Train:** Subjects 1, 2, 3
*   **Test/Validation:** Subject 4 (Leave-One-Subject-Out cross-validation is best for medical devices to prove it works on *new* people).

### Loss Function
*   **Binary Cross-Entropy Loss**: Since we are classifying Fall vs. Normal (or Motion).

### Metrics (Critical for Medical Systems)
*   **Recall (Sensitivity):** MOST IMPORTANT. We cannot miss a fall. Target > 95%.
*   **Precision:** Important to avoid annoying existing users.
*   **F1-Score:** Good balance metric.

---

## 4. Motion Detection vs. Fall Detection Logic

The logic flows hierarchically to save compute and organize alerts.

**The Pipeline:**
1.  **Frame Input** -> **YOLOv8-Pose**
2.  **Check 1: Is a person detected?**
    *   *No*: Do nothing.
    *   *Yes*:
        *   **TRIGGER**: Send "Motion Detected" event (Non-emergency).
        *   **Pass Data**: Push keypoints into a buffer (queue of last 30 frames).
3.  **Check 2: Is the buffer full?**
    *   *Yes*: Pass the 30-frame sequence to **LSTM Fall Classifier**.
4.  **Check 3: LSTM Output Score**
    *   *Score > Threshold (e.g., 0.85)*: **TRIGGER** "Fall Detected" (Emergency).
    *   *Score < Threshold*: Continue monitoring.

---

## 5. Inference & Output

### Live Feed Logic
*   **Input**: RTSP Stream or WebCam ($640 \times 480$ resolution is sufficient).
*   **Process**:
    *   Skip frames if hardware is slow (process every 2nd or 3rd frame).
    *   Maintain a "Rolling Buffer" of keypoints.

### Defined Outputs
*   **Status Enum**: `IDLE` | `MOTION` | `FALL_WARNING` | `FALL_CONFIRMED`
*   **JSON Payload Example**:
    ```json
    {
      "event_type": "FALL",
      "timestamp": "2023-10-27T10:00:00Z",
      "confidence": 0.98,
      "camera_id": "living_room_1"
    }
    ```

---

## 6. Optimization for Edge (RPi / Jetson)

1.  **Model Quantization**: Convert the YOLO model to `INT8` (TensorRT) or `TFLite` format. This speeds up inference by 2-4x.
2.  **Resolution Reduction**: Run YOLO at $320 \times 320$ or $416 \times 416$.
3.  **Class Filtering**: Configure YOLO to look *only* for class `0` (Person), ignoring chairs/cups/etc. reduces post-processing time.

---

## 7. Deployment Readiness

*   **Mobile App Connection**:
    *   The Edge Device needs a lightweight HTTP Server (FastAPI).
    *   **WebSocket is preferred**: Real-time two-way communication.
    *   When Fall is detected -> `ws.send(alert_json)`.
    *   Mobile App uses Push Notifications (Firebase/FCM) triggered by the backend receiving this socket message.

---

## 8. Implementation Next Steps (Deliverables)

1.  **Move Dataset**: Please move your dataset folder into `c:\Users\DELL\OneDrive\Documents\grad project`.
2.  **Environment Setup**: Install `ultralytics` (YOLO), `torch`, `opencv`, `numpy`.
3.  **Data Analysis**: I will write a script to visualize your keypoints.
4.  **Training**: Train the LSTM on extracted points.
5.  **Integration**: Build the `main.py` pipeline.
