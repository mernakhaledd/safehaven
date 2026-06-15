import os

def check_dataset():
    # Expected path after user moves the folder
    dataset_path = "fall dataset"
    
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset folder '{dataset_path}' not found in current directory.")
        print("Please move the folder here.")
        return
    
    print(f"✅ Found dataset folder: {dataset_path}")
    
    # Check subjects
    subjects = [d for d in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, d))]
    print(f"Found {len(subjects)} subjects: {subjects}")
    
    # Check for video files (approximate check)
    total_videos = 0
    for subj in subjects:
        subj_path = os.path.join(dataset_path, subj)
        files = os.listdir(subj_path)
        videos = [f for f in files if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
        total_videos += len(videos)
        print(f"  - {subj}: {len(videos)} videos found.")
        
    if total_videos > 0:
        print(f"\nTotal videos found: {total_videos}. Dataset looks ready for processing!")
    else:
        print("\n⚠️ Usage Warning: No video files found in subject folders. Please check file extensions.")

if __name__ == "__main__":
    check_dataset()
