DATASET_ROOT = "fall dataset/fall dataset"
PROCESSED_DATA_ROOT = "processed_data"
FRAME_SEQUENCE_LENGTH = 30  # We will chunk videos into 30-frame sequences
INPUT_SHAPE = (30, 34) # 17 keypoints * 2 (x, y) - or 51 if using confidence
CLASSES = ["ADL", "Fall"]
