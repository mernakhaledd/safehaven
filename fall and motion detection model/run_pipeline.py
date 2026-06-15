import os
import subprocess
import sys
import time

def run_step(command, step_name):
    print(f"\n{'='*50}")
    print(f"STEP: {step_name}")
    print(f"{'='*50}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"❌ Error in step: {step_name}")
        sys.exit(1)
    print(f"✅ {step_name} completed successfully.")

def main():
    print("🚀 Starting Fall Detection System Setup Pipeline...")

    # 1. Install Requirements (just to be safe)
    # run_step(f"{sys.executable} -m pip install -r requirements.txt", "Install Dependencies")

    # 2. Preprocess Data
    if not os.path.exists("processed_data") or len(os.listdir("processed_data")) == 0:
        print("\n[Info] processed_data folder is empty or missing. Starting video processing...")
        run_step(f"{sys.executable} preprocess_data.py", "Data Preprocessing (Extracting Keypoints)")
    else:
        print("\n[Info] Data already processed. Skipping preprocessing.")

    # 3. Train Model
    if not os.path.exists("fall_detection_lstm.pth"):
        print("\n[Info] Model file not found. Starting training...")
        run_step(f"{sys.executable} train_model.py", "Model Training")
    else:
        print("\n[Info] Model found (fall_detection_lstm.pth). Skipping training to save time.")
        print("To retrain, delete the .pth file and run this script again.")

    # 4. Inference
    print("\n🎉 System is ready!")
    print("Launching Inference Demo...")
    # run_step(f"{sys.executable} inference.py", "Real-Time Inference") 
    # We don't auto-run inference to allow user to read the success msg.

if __name__ == "__main__":
    main()
