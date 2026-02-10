import os
import json
import numpy as np
import librosa
import pretty_midi
from scipy.interpolate import interp1d

# --- CONFIG ---
BASE_DIR = os.path.expanduser("~/ai_music")
SETUP_DIR = os.path.join(BASE_DIR, "setup")
CATEGORIES = ["first", "one_kor", "one_kor_sgl"]
SR = 22050
HOP_LENGTH = 512

# Threshold: If AI differs from Human by more than this (average seconds), flag it.
ERROR_THRESHOLD_SEC = 2.0 

def load_manual_saves(cat):
    path = os.path.join(SETUP_DIR, f"alignment_manual_{cat}.json")
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return {}

def get_midi_start_time(pm):
    start_times = [n.start for i in pm.instruments for n in i.notes]
    return min(start_times) if start_times else 0.0

def process_category(cat):
    print(f"\n--- Processing {cat} ---")
    manual_data = load_manual_saves(cat)
    
    wav_dir = os.path.join(BASE_DIR, "mp3", cat, "wav")
    midi_dir = os.path.join(BASE_DIR, "mid/cleaned")
    
    # Files to process: All WAVs
    files = [f for f in os.listdir(wav_dir) if f.endswith('.wav')]
    
    dtw_output = {}
    errors_found = []

    for i, f in enumerate(files):
        key = f.replace(".wav", "")
        midi_path = os.path.join(midi_dir, f"{key}.mid")
        wav_path = os.path.join(wav_dir, f)
        
        if not os.path.exists(midi_path): continue
        print(f"[{i+1}/{len(files)}] {key}...", end="\r")

        try:
            # 1. Load Data
            y_rec, _ = librosa.load(wav_path, sr=SR)
            pm = pretty_midi.PrettyMIDI(midi_path)
            y_midi = pm.synthesize(fs=SR)
            
            # 2. Chroma & DTW
            c_rec = librosa.feature.chroma_cqt(y=y_rec, sr=SR, hop_length=HOP_LENGTH)
            c_midi = librosa.feature.chroma_cqt(y=y_midi, sr=SR, hop_length=HOP_LENGTH)
            
            # Standard DTW (Force alignment of ends? or Subsequence?)
            # For now, standard DTW is safest for structural checking
            D, wp = librosa.sequence.dtw(X=c_midi, Y=c_rec, metric='cosine')
            
            # wp is [midi_frame, audio_frame] (reverse order)
            wp = wp[::-1] 
            midi_frames = wp[:, 0]
            audio_frames = wp[:, 1]
            
            # 3. Convert to Seconds
            # Adjust MIDI time: The Player normalizes MIDI (Start=0). 
            # But Synthesis includes start silence.
            # We need the path to map Normalized_Midi_Time -> Audio_Time
            
            first_note_time = get_midi_start_time(pm)
            
            # Current mapping: Absolute_Midi_Sec -> Audio_Sec
            frames_to_sec = HOP_LENGTH / SR
            path_midi_abs = midi_frames * frames_to_sec
            path_audio = audio_frames * frames_to_sec
            
            # Normalize MIDI path (remove start silence)
            path_midi_norm = path_midi_abs - first_note_time
            
            # 4. Error Checking (If manual save exists)
            error_score = 0.0
            if key in manual_data:
                m = manual_data[key]
                m_offset = float(m['offset'])
                m_speed = float(m['speed'])
                
                # Human Prediction: Audio = (Midi_Norm * Speed) + Offset
                human_audio_est = (path_midi_norm * m_speed) + m_offset
                
                # Calculate difference
                diff = np.abs(path_audio - human_audio_est)
                error_score = np.mean(diff)
                
                if error_score > ERROR_THRESHOLD_SEC:
                    msg = f"{key}: Avg Deviation {error_score:.2f}s (Structural Mismatch?)"
                    errors_found.append(msg)

            # 5. Simplify Path for JSON (Downsample)
            # We don't need 22000 points. 1 point every 0.1s of MIDI is enough.
            # We use interpolation to create a clean lookup table.
            
            # Create a query grid for MIDI time (every 0.25s)
            midi_duration = pm.get_end_time() - first_note_time
            if midi_duration <= 0: midi_duration = 1.0
            
            lookup_times = np.arange(0, midi_duration, 0.25) # 4 points per second
            
            # Interpolator: given Midi_Norm, find Audio
            # We must handle duplicates in X (vertical segments in DTW)
            # standard interp1d requires unique X. We can average duplicates or just take first.
            # Simplest: use numpy.unique
            u_midi, u_indices = np.unique(path_midi_norm, return_index=True)
            u_audio = path_audio[u_indices]
            
            if len(u_midi) > 1:
                f_interp = interp1d(u_midi, u_audio, kind='linear', fill_value="extrapolate")
                simplified_audio = f_interp(lookup_times)
            else:
                simplified_audio = lookup_times # Fallback
            
            # Round for JSON size
            points = np.column_stack((lookup_times, simplified_audio)).round(3).tolist()
            
            dtw_output[key] = {
                "points": points, # [[midi_norm_time, audio_time], ...]
                "error": round(error_score, 3)
            }

        except Exception as e:
            print(f"\nError processing {key}: {e}")

    # Save Results
    out_json = os.path.join(SETUP_DIR, f"alignment_dtw_{cat}.json")
    with open(out_json, 'w') as f:
        json.dump(dtw_output, f)
        
    # Save Error Report
    if errors_found:
        err_path = os.path.join(SETUP_DIR, f"dtw_errors_{cat}.txt")
        with open(err_path, 'w') as f:
            f.write("\n".join(errors_found))
        print(f"\nSaved {len(errors_found)} error flags to {err_path}")

if __name__ == "__main__":
    for cat in CATEGORIES:
        process_category(cat)