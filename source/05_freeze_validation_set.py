import os
import glob
import shutil
import random

# CONFIGURATION
BASE_DIR = os.path.expanduser("~/ai_music")
VALIDATION_PCT = 0.15  # 15% of files
CATEGORIES = ["first", "one_kor", "one_kor_sgl"]

def freeze_dataset():
    print("--- Freezing Validation Set ---")
    
    for cat in CATEGORIES:
        source_dir = os.path.join(BASE_DIR, "mp3", cat)
        wav_dir = os.path.join(source_dir, "wav")
        
        # Create 'frozen' subdirectory
        frozen_dir = os.path.join(source_dir, "frozen")
        frozen_wav_dir = os.path.join(frozen_dir, "wav")
        os.makedirs(frozen_wav_dir, exist_ok=True)
        
        # Get all MP3s
        files = glob.glob(os.path.join(source_dir, "*.mp3"))
        
        # Identify how many to move
        # We use a fixed seed so this is reproducible (if you ran it from scratch)
        random.seed(42) 
        
        # Check if we already have files there (don't move more if run twice)
        existing_frozen = glob.glob(os.path.join(frozen_dir, "*.mp3"))
        if len(existing_frozen) > 0:
            print(f"Skipping {cat}: {len(existing_frozen)} files already frozen.")
            continue
            
        # Select random files
        num_to_freeze = int(len(files) * VALIDATION_PCT)
        files_to_move = random.sample(files, num_to_freeze)
        
        print(f"Moving {num_to_freeze} files from {cat} to 'frozen'...")
        
        for file_path in files_to_move:
            filename = os.path.basename(file_path) # e.g., "song.mp3"
            key = os.path.splitext(filename)[0]    # e.g., "song"
            
            # 1. Move MP3
            dest_mp3 = os.path.join(frozen_dir, filename)
            shutil.move(file_path, dest_mp3)
            
            # 2. Move WAV (if exists)
            wav_src = os.path.join(wav_dir, f"{key}.wav")
            wav_dest = os.path.join(frozen_wav_dir, f"{key}.wav")
            if os.path.exists(wav_src):
                shutil.move(wav_src, wav_dest)
                
            # 3. Move JSON Analysis (if exists)
            json_src = os.path.join(wav_dir, f"{key}.json")
            json_dest = os.path.join(frozen_wav_dir, f"{key}.json")
            if os.path.exists(json_src):
                shutil.move(json_src, json_dest)

    print("--- Freeze Complete ---")

if __name__ == "__main__":
    freeze_dataset()