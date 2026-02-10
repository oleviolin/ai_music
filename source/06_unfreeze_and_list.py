import os
import glob
import shutil
import json

BASE_DIR = os.path.expanduser("~/ai_music")
CATEGORIES = ["first", "one_kor", "one_kor_sgl"]
SETUP_DIR = os.path.join(BASE_DIR, "setup")

def unfreeze_data():
    print("--- Unfreezing Data & Creating List ---")
    os.makedirs(SETUP_DIR, exist_ok=True)
    
    frozen_files_map = {}

    for cat in CATEGORIES:
        frozen_files_map[cat] = []
        
        # Paths
        source_dir = os.path.join(BASE_DIR, "mp3", cat)
        wav_dir = os.path.join(source_dir, "wav")
        
        frozen_base = os.path.join(source_dir, "frozen")
        frozen_wav = os.path.join(frozen_base, "wav")
        
        if not os.path.exists(frozen_base):
            print(f"No frozen folder for {cat}, skipping.")
            continue

        # 1. Find all files in frozen directory
        mp3s = glob.glob(os.path.join(frozen_base, "*.mp3"))
        
        print(f"Restoring {len(mp3s)} files in {cat}...")

        for mp3_path in mp3s:
            filename = os.path.basename(mp3_path)
            key = os.path.splitext(filename)[0]
            
            # Record this key as frozen
            frozen_files_map[cat].append(key)
            
            # Move MP3 back
            shutil.move(mp3_path, os.path.join(source_dir, filename))
            
            # Move WAV back
            wav_src = os.path.join(frozen_wav, f"{key}.wav")
            if os.path.exists(wav_src):
                shutil.move(wav_src, os.path.join(wav_dir, f"{key}.wav"))
                
            # Move JSON Analysis back
            json_src = os.path.join(frozen_wav, f"{key}.json")
            if os.path.exists(json_src):
                shutil.move(json_src, os.path.join(wav_dir, f"{key}.json"))

        # Clean up empty directories
        if os.path.exists(frozen_wav): os.rmdir(frozen_wav)
        if os.path.exists(frozen_base): os.rmdir(frozen_base)

    # Save the list
    list_path = os.path.join(SETUP_DIR, "frozen_files.json")
    with open(list_path, 'w') as f:
        json.dump(frozen_files_map, f, indent=2)
        
    print(f"Saved frozen file list to: {list_path}")

if __name__ == "__main__":
    unfreeze_data()