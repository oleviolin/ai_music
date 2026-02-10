import os
import glob
import json
import numpy as np
import librosa
import pretty_midi
import sys
from scipy.spatial.distance import cdist

# Configuration
BASE_DIR = os.path.expanduser("~/ai_music")
SR = 22050
HOP_LENGTH = 512

def analyze_track(category, key):
    # Paths
    mp3_path = os.path.join(BASE_DIR, "mp3", category, f"{key}.mp3")
    # Also check if a WAV exists directly (since you might have updated the WAV but not the MP3)
    wav_source_path = os.path.join(BASE_DIR, "mp3", category, "wav", f"{key}.wav")
    
    midi_path = os.path.join(BASE_DIR, "mid/cleaned", f"{key}.mid")
    output_json = os.path.join(BASE_DIR, "mp3", category, "wav", f"{key}.json")
    
    # Prefer loading from WAV if available (it's faster and might be the updated file)
    load_path = wav_source_path if os.path.exists(wav_source_path) else mp3_path
    
    if not os.path.exists(load_path):
        print(f"Error: Audio file not found: {load_path}")
        return
    if not os.path.exists(midi_path):
        print(f"Error: MIDI file not found: {midi_path}")
        return

    print(f"Analyzing {key} ({category})...")

    # --- 1. Load Audio ---
    y_rec, _ = librosa.load(load_path, sr=SR)
    duration = len(y_rec) / SR

    # --- 2. Generate Waveform ---
    pixels_per_second = 50
    target_length = int(duration * pixels_per_second)
    hop = max(1, len(y_rec) // target_length)
    waveform = []
    for i in range(0, len(y_rec), hop):
        chunk = y_rec[i:i+hop]
        if len(chunk) > 0:
            waveform.append(float(np.max(np.abs(chunk))))
    
    # --- 3. AUTO-SYNC ---
    try:
        pm = pretty_midi.PrettyMIDI(midi_path)
        y_midi = pm.synthesize(fs=SR)
        
        chroma_rec = librosa.feature.chroma_cqt(y=y_rec, sr=SR, hop_length=HOP_LENGTH)
        chroma_midi = librosa.feature.chroma_cqt(y=y_midi, sr=SR, hop_length=HOP_LENGTH)
        
        # Analyze first 30s
        frames_to_check = int(30 * SR / HOP_LENGTH)
        c_rec_short = chroma_rec[:, :frames_to_check]
        c_midi_short = chroma_midi[:, :frames_to_check]
        
        dist = cdist(c_rec_short.T, c_midi_short.T, metric='cosine')
        
        frames_per_sec = SR / HOP_LENGTH
        search_range = int(6 * frames_per_sec)
        
        diagonals = []
        for lag in range(-int(2 * frames_per_sec), search_range):
            d_cost = np.trace(dist, offset=lag)
            overlap = dist.shape[0] - abs(lag)
            if overlap > 0:
                diagonals.append((lag, d_cost / overlap))
        
        best_lag, _ = min(diagonals, key=lambda x: x[1])
        calculated_offset = -(best_lag * HOP_LENGTH / SR)
    except Exception as e:
        print(f"Sync calculation failed: {e}")
        calculated_offset = 0.0

    # --- 4. Export ---
    data = {
        "waveform": waveform,
        "duration": duration,
        "auto_offset": calculated_offset
    }
    
    with open(output_json, 'w') as f:
        json.dump(data, f)
    print(f"Success: Updated {output_json}")

def run_batch():
    for cat in ["first", "one_kor", "one_kor_sgl"]:
        files = glob.glob(os.path.join(BASE_DIR, "mp3", cat, "*.mp3"))
        for f in files:
            key = os.path.splitext(os.path.basename(f))[0]
            analyze_track(cat, key)

if __name__ == "__main__":
    # If arguments provided: python script.py [category] [key]
    if len(sys.argv) > 2:
        analyze_track(sys.argv[1], sys.argv[2])
    else:
        run_batch()