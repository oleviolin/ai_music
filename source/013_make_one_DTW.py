import os
import json
import numpy as np
import librosa
import pretty_midi
from scipy.interpolate import interp1d
import sys

# --- CONFIGURATION ---
BASE_DIR = os.path.expanduser("~/ai_music")
DEBUG_DIR = os.path.join(BASE_DIR, "setup", "debug")
SR = 22050
HOP_LENGTH = 128

# ==========================================
# --- 🎛️ EXPERIMENTAL PARAMETERS (TWEAK THESE) ---
# ==========================================

# 1. METRIC: How to compare frames.
# Options: 'cosine' (recommended for CQT), 'euclidean', 'seuclidean', 'cityblock'
DTW_METRIC = 'seuclidean' 

# 2. STEP SIZES: Constraints on the path (Slope).
# Default is np.array([[1, 1], [1, 0], [0, 1]]) which allows vertical/horizontal moves (stops time).
# Try creating a strict diagonal bias to prevent "stuttering" notes.
# Example Strict: np.array([[1, 1], [2, 1], [1, 2]])
DTW_STEP_SIZES = np.array([[1, 1], [1, 0], [0, 1]]) 

# 3. BAND WIDTH: Global constraint (Sakoe-Chiba).
# Limits how far the path can stray from the diagonal. 
# None = No limit. Int = Number of frames (e.g., 100 frames ~= 2.3 seconds)
# Set this if the AI is jumping to a completely wrong verse. OQ was none
DTW_BAND_WIDTH = 0.06

# 4. SUBSEQUENCE:
# True: Allows the MIDI to be a small part of a long Audio.
# False: Forces the ends to match (Standard DTW). OQ Was True
DTW_SUBSEQUENCE = False

# 5. BACKTRACK SMOOTHING:
# Sometimes the raw path is "stair-steppy". This simplifies it.
# 0.25 means "Save a point every 0.25 seconds of MIDI"
OUTPUT_RESOLUTION_SEC = 0.25

# ==========================================

def get_midi_start_time(pm):
    start_times = [n.start for i in pm.instruments for n in i.notes]
    return min(start_times) if start_times else 0.0

def run_experiment(category, key):
    print(f"--- Running DTW Experiment: {category}/{key} ---")
    
    # Paths
    wav_path = os.path.join(BASE_DIR, "mp3", category, "wav", f"{key}.wav")
    midi_path = os.path.join(BASE_DIR, "mid/cleaned", f"{key}.mid")
    
    if not os.path.exists(wav_path):
        print(f"Error: WAV not found: {wav_path}")
        return
    if not os.path.exists(midi_path):
        print(f"Error: MIDI not found: {midi_path}")
        return

    try:
        # 1. Load Data
        print("Loading Audio & MIDI...")
        y_rec, _ = librosa.load(wav_path, sr=SR)
        pm = pretty_midi.PrettyMIDI(midi_path)
        y_midi = pm.synthesize(fs=SR)
        
        # 2. Compute Features (CQT)
        print("Computing Chroma...")
        c_rec = librosa.feature.chroma_cqt(y=y_rec, sr=SR, hop_length=HOP_LENGTH)
        c_midi = librosa.feature.chroma_cqt(y=y_midi, sr=SR, hop_length=HOP_LENGTH)
        
        # 3. Run DTW with Experimental Parameters
        print(f"Running DTW (Metric={DTW_METRIC}, Subseq={DTW_SUBSEQUENCE})...")
        
        if DTW_SUBSEQUENCE:
            D, wp = librosa.sequence.dtw(X=c_midi, Y=c_rec, metric=DTW_METRIC, 
                                         step_sizes_sigma=DTW_STEP_SIZES, 
                                         global_constraints=DTW_SUBSEQUENCE,                                          
                                         band_rad=DTW_BAND_WIDTH)
        else:
            # Librosa Dtw standard
            D, wp = librosa.sequence.dtw(X=c_midi, Y=c_rec, metric=DTW_METRIC, 
                                         step_sizes_sigma=DTW_STEP_SIZES,
                                         band_rad=DTW_BAND_WIDTH)

        # 4. Post-Process Path
        wp = wp[::-1] # Reverse to be [Start -> End]
        midi_frames = wp[:, 0]
        audio_frames = wp[:, 1]
        
        frames_to_sec = HOP_LENGTH / SR
        path_midi_abs = midi_frames * frames_to_sec
        path_audio = audio_frames * frames_to_sec
        
        # 5. Downsample for Player
        midi_duration = pm.get_end_time()
        lookup_times = np.arange(0, midi_duration, OUTPUT_RESOLUTION_SEC)
        
        # Interpolate unique points
        u_midi, u_indices = np.unique(path_midi_abs, return_index=True)
        u_audio = path_audio[u_indices]
        
        if len(u_midi) > 1:
            f_interp = interp1d(u_midi, u_audio, kind='linear', fill_value="extrapolate")
            simplified_audio = f_interp(lookup_times)
        else:
            simplified_audio = lookup_times
            
        points = np.column_stack((lookup_times, simplified_audio)).round(3).tolist()
        
        # 6. Save to Debug Folder
        os.makedirs(DEBUG_DIR, exist_ok=True)
        # Format: Category.Key.json (Safe delimiter)
        filename = f"{category}.{key}.json"
        out_path = os.path.join(DEBUG_DIR, filename)
        
        output_data = {
            "points": points,
            "params": {
                "metric": DTW_METRIC,
                "subsequence": DTW_SUBSEQUENCE,
                "band_width": DTW_BAND_WIDTH
            }
        }
        
        with open(out_path, 'w') as f:
            json.dump(output_data, f)
            
        print(f"Success! Saved experiment to: {out_path}")
        print("-> Select 'Debug / Experimental' in the Player to verify.")

    except Exception as e:
        print(f"DTW Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 source/013_make_one_DTW.py [category] [key]")
    else:
        run_experiment(sys.argv[1], sys.argv[2])