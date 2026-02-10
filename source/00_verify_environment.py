import os
import glob

# Define paths relative to where the script is run, or absolute
BASE_DIR = os.path.expanduser("~/ai_music")
MIDI_DIR = os.path.join(BASE_DIR, "mid/cleaned")
MP3_DIRS = {
    "First (Synth)": os.path.join(BASE_DIR, "mp3/first"),
    "Solo (Single Inst)": os.path.join(BASE_DIR, "mp3/one_kor_sgl"),
    "Orchestra (One Kor)": os.path.join(BASE_DIR, "mp3/one_kor")
}

def check_pairs():
    print(f"--- Checking Environment in {BASE_DIR} ---")
    
    # Get all MIDI files (stripped of path and extension for matching)
    # We use a set for O(1) lookups
    midi_files = glob.glob(os.path.join(MIDI_DIR, "*.mid"))
    midi_keys = {os.path.splitext(os.path.basename(f))[0] for f in midi_files}
    
    print(f"Found {len(midi_keys)} unique MIDI keys in {MIDI_DIR}")
    
    if len(midi_keys) == 0:
        print("WARNING: No MIDI files found. Please populate 'mid/cleaned' before proceeding.")
        return

    # Check each MP3 category
    for category, path in MP3_DIRS.items():
        mp3_files = glob.glob(os.path.join(path, "*.mp3"))
        
        if not mp3_files:
            print(f"\n{category}: No files found in {path}")
            continue
            
        matches = 0
        mismatches = []
        
        for f in mp3_files:
            # Extract key: /path/to/song_name.mp3 -> song_name
            key = os.path.splitext(os.path.basename(f))[0]
            if key in midi_keys:
                matches += 1
            else:
                mismatches.append(key)
        
        print(f"\n{category}:")
        print(f"  Total MP3s: {len(mp3_files)}")
        print(f"  Matches found in MIDI: {matches}")
        if mismatches:
            print(f"  MISSING MIDIs for ({len(mismatches)} files): {mismatches[:3]}...")
        else:
            print("  OK: 100% Match coverage.")

if __name__ == "__main__":
    check_pairs()