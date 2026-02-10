import os
import glob
from pydub import AudioSegment

# Install pydub if missing: pip install pydub
# Ensure ffmpeg is installed: sudo apt install ffmpeg

BASE_DIR = os.path.expanduser("~/ai_music/mp3")
CATEGORIES = ["first", "one_kor", "one_kor_sgl"]

def convert_mp3s():
    print("--- Starting MP3 to WAV Conversion ---")
    
    for cat in CATEGORIES:
        source_dir = os.path.join(BASE_DIR, cat)
        target_dir = os.path.join(source_dir, "wav")
        
        # Create wav subdirectory if it doesn't exist
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            print(f"Created directory: {target_dir}")
            
        files = glob.glob(os.path.join(source_dir, "*.mp3"))
        
        print(f"Processing {cat}: {len(files)} files...")
        
        for f in files:
            filename = os.path.basename(f)
            name_only = os.path.splitext(filename)[0]
            wav_path = os.path.join(target_dir, f"{name_only}.wav")
            
            # Skip if already exists to save time
            if os.path.exists(wav_path):
                continue
                
            try:
                sound = AudioSegment.from_mp3(f)
                # Export as standard WAV (16-bit PCM)
                sound.export(wav_path, format="wav")
            except Exception as e:
                print(f"Failed to convert {filename}: {e}")

    print("--- Conversion Complete ---")

if __name__ == "__main__":
    convert_mp3s()