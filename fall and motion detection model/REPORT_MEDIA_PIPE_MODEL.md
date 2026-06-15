# MediaPipe + TFLite Fall Model (Raspberry Pi)

This report documents the lightweight pipeline built as the Raspberry Pi alternative. It focuses solely on the MediaPipe + TFLite LSTM path.

## Motivation
- Keep Pi inference CPU-only and real time (~20–30 FPS on Pi 4).
- Preserve privacy by processing skeleton keypoints only.
- Maintain temporal reasoning for fall dynamics with minimal compute.

## Data Pipeline
- Source videos: fall dataset/fall dataset/Subject*/{ADL,Fall}.
- Keypoint extractor: MediaPipe Pose Landmarker Lite (pose_landmarker_lite.task) → 33 joints with x, y, z, visibility (132 features/frame).
- Preprocessing script: mp_preprocess_data.py
  - Runs Pose Landmarker per frame; pads missing detections with zeros.
  - Saves per-video arrays to mp_processed_data/Subject*/{ADL,Fall} as .npy.
- Training sequences: sliding windows of 30 frames, stride 5, labels ADL=0 / Fall=1.

## Model Architecture (Training)
- Script: mp_train_model.py
- Input: (30, 132) → 30 frames, 33 landmarks × 4 values.
- Layers: LSTM(64, return_sequences) → LSTM(32) → Dropout(0.5) → Dense(32, ReLU) → Dense(1, sigmoid).
- Loss/optimizer/metrics: binary_crossentropy, Adam, accuracy.
- Split: random train/val (test_size=0.2); not subject-wise.
- Outputs: mp_fall_model.h5 (Keras) and mp_fall_model.tflite (float16, SELECT_TF_OPS enabled for LSTM).

## Deployment Loop (Raspberry Pi)
- Script: 10_mp_pi_deploy.py
- Camera ingest: rpicam-vid piping YUV420 640×480 @30 FPS to stdout.
- Pose inference: MediaPipe Pose on CPU → 132-D keypoints per frame.
- Buffer: latest 30 frames retained; inference when buffer is full.
- LSTM inference: TFLite runtime (or TensorFlow fallback) runs mp_fall_model.tflite.
- Alerting: fall probability > 0.85 triggers alert with 5 s cooldown; optional cloud hook via pi_supabase_trigger.
- Console: live probability; alerts printed when threshold crossed.

## Known Limitations and Recommendations
- Evaluation split is random; prefer subject-wise (leave-one-subject-out) for generalization claims.
- Threshold 0.85 is heuristic; calibrate on Pi-captured validation clips.
- Class balance and per-landmark normalization are not explicitly handled; verify label distribution and consider normalization.
- Overlapping windows (stride 5) inflate sample count; document this in dataset description.
- Consider INT8 quantization for further speed if accuracy holds; ensure SELECT_TF_OPS constraints are met.

## Suggested Reporting Angles
1) Motivation: Pi-friendly, CPU-only, 20–30 FPS, privacy-preserving skeletons.
2) Features: 33×4 landmarks, 30-frame temporal window, stride 5.
3) Architecture: two-layer LSTM with dropout; exported to TFLite float16.
4) Deployment: rpicam-vid → MediaPipe Pose → 30-frame buffer → TFLite LSTM → alert at 0.85 with cooldown.
5) Future work: subject-wise evaluation, threshold calibration, optional quantization, on-device latency/throughput measurements.
