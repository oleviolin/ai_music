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
#HOP_LENGTH = 512
#from 013_make_one_DTW
HOP_LENGTH = 128
ERROR_THRESHOLD_SEC = 2.0 
DTW_METRIC = 'seuclidean' 
DTW_BAND_WIDTH = 0.06
OUTPUT_RESOLUTION_SEC = 0.25
DTW_SUBSEQUENCE = False
DTW_STEP_SIZES = np.array([[1, 1], [1, 0], [0, 1]]) 


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
            y_rec, _ = librosa.load(wav_path, sr=SR)
            pm = pretty_midi.PrettyMIDI(midi_path)
            y_midi = pm.synthesize(fs=SR)
            
            c_rec = librosa.feature.chroma_cqt(y=y_rec, sr=SR, hop_length=HOP_LENGTH)
            c_midi = librosa.feature.chroma_cqt(y=y_midi, sr=SR, hop_length=HOP_LENGTH)
            
            #D, wp = librosa.sequence.dtw(X=c_midi, Y=c_rec, metric='cosine')  OQ:Orig
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
            
            wp = wp[::-1] 
            midi_frames = wp[:, 0]
            audio_frames = wp[:, 1]
            
            frames_to_sec = HOP_LENGTH / SR
            path_midi_abs = midi_frames * frames_to_sec
            path_audio = audio_frames * frames_to_sec
            
            # --- CHANGE: KEEP ABSOLUTE TIME (No Normalization) ---
            # This maps the exact timestamp in the .mid file to the exact timestamp in the .wav
            
            # Error Checking (Still needs normalization to compare with Manual sliders)
            first_note_time = get_midi_start_time(pm)
            path_midi_norm = path_midi_abs - first_note_time
            
            error_score = 0.0
            if key in manual_data:
                m = manual_data[key]
                # Human: Audio = (MidiNorm * Speed) + Offset
                human_est = (path_midi_norm * float(m['speed'])) + float(m['offset'])
                diff = np.abs(path_audio - human_est)
                error_score = np.mean(diff)
                if error_score > ERROR_THRESHOLD_SEC:
                    errors_found.append(f"{key}: Avg Deviation {error_score:.2f}s")

            # --- DOWNSAMPLING ---
            # Interpolate raw midi time -> raw audio time
            # Range: from 0 to end of MIDI
            midi_duration = pm.get_end_time()
            lookup_times = np.arange(0, midi_duration, 0.25) 
            
            u_midi, u_indices = np.unique(path_midi_abs, return_index=True)
            u_audio = path_audio[u_indices]
            
            if len(u_midi) > 1:
                f_interp = interp1d(u_midi, u_audio, kind='linear', fill_value="extrapolate")
                simplified_audio = f_interp(lookup_times)
            else:
                simplified_audio = lookup_times 
            
            points = np.column_stack((lookup_times, simplified_audio)).round(3).tolist()
            
            dtw_output[key] = {
                "points": points, 
                "error": round(error_score, 3)
            }

        except Exception as e:
            print(f"\nError {key}: {e}")

    with open(os.path.join(SETUP_DIR, f"alignment_dtw_{cat}.json"), 'w') as f:
        json.dump(dtw_output, f)
        
    if errors_found:
        with open(os.path.join(SETUP_DIR, f"dtw_errors_{cat}.txt"), 'w') as f:
            f.write("\n".join(errors_found))

if __name__ == "__main__":
    for cat in CATEGORIES:
        process_category(cat)