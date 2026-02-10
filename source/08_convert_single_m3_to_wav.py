import sys
import os
from pydub import AudioSegment

# Usage: python3 source/convert_single.py [path_to_mp3]
# Example: python3 source/convert_single.py ~/ai_music/mp3/one_kor_sgl/ha-mzzllevzzzng.mp3

def convert_single(file_path):
    file_path = os.path.expanduser(file_path)
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    # Determine Output Path
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    key = os.path.splitext(filename)[0]
    
    # Ensure 'wav' subdirectory exists
    wav_dir = os.path.join(directory, "wav")
    os.makedirs(wav_dir, exist_ok=True)
    
    out_path = os.path.join(wav_dir, f"{key}.wav")

    print(f"Converting: {filename}")
    print(f"Target: Mono, 22050Hz")

    try:
        # Load
        sound = AudioSegment.from_mp3(file_path)
        
        # TRANSFORMATION
        sound = sound.set_channels(1)       # Force Mono
        sound = sound.set_frame_rate(22050) # Force 22050Hz
        
        # Export
        sound.export(out_path, format="wav")
        print(f"Success! Saved to: {out_path}")
        
    except Exception as e:
        print(f"Conversion Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a filename.")
    else:
        convert_single(sys.argv[1])