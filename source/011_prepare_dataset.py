import os
import json
import numpy as np
import librosa
import pretty_midi
import sys

# --- CONFIG ---
BASE_DIR = os.path.expanduser("~/ai_music")
DATASET_DIR = os.path.join(BASE_DIR, "dataset_npz")
SETUP_DIR = os.path.join(BASE_DIR, "setup")
SR = 22050
HOP_LENGTH = 512
CQT_BINS = 84
BINS_PER_OCTAVE = 12
MIN_NOTE = 24

def load_alignment_map(category):
    dtw_path = os.path.join(SETUP_DIR, f"alignment_dtw_{category}.json")
    dtw_data = {}
    if os.path.exists(dtw_path):
        with open(dtw_path, 'r') as f: dtw_data = json.load(f)
        
    manual_path = os.path.join(SETUP_DIR, f"alignment_manual_{category}.json")
    manual_data = {}
    if os.path.exists(manual_path):
        with open(manual_path, 'r') as f: manual_data = json.load(f)
    return dtw_data, manual_data

def get_aligned_midi_roll(midi_path, duration_frames, alignment_info):
    try:
        pm = pretty_midi.PrettyMIDI(midi_path)
    except:
        return np.zeros(duration_frames)

    targets = np.zeros(duration_frames, dtype=np.int16)
    mode = alignment_info.get('mode', 'none')
    
    # Calculate normalization only if needed for Manual mode
    first_note_time = 0.0
    if mode == 'manual':
        start_times = [n.start for i in pm.instruments for n in i.notes if not i.is_drum]
        if start_times: first_note_time = min(start_times)
    
    def time_to_frame(t_midi_raw):
        t_audio = 0.0
        
        if mode == 'dtw':
            # Direct Mapping: Raw Midi -> Raw Audio
            points = alignment_info['points']
            t_audio = np.interp(t_midi_raw, [p[0] for p in points], [p[1] for p in points])
            
        elif mode == 'manual':
            # Normalized Mapping: (Raw - Start) -> Audio
            t_norm = t_midi_raw - first_note_time
            t_audio = (t_norm * alignment_info['speed']) + alignment_info['offset']
            
        else:
            t_audio = t_midi_raw # Fallback
            
        return int(t_audio * SR / HOP_LENGTH)

    for instrument in pm.instruments:
        if instrument.is_drum: continue
        for note in instrument.notes:
            start_frame = max(0, time_to_frame(note.start))
            end_frame = min(duration_frames, time_to_frame(note.end))
            if start_frame < end_frame:
                targets[start_frame:end_frame] = note.pitch

    return targets

def process_track(category, key, dtw_entry, manual_entry):
    wav_path = os.path.join(BASE_DIR, "mp3", category, "wav", f"{key}.wav")
    midi_path = os.path.join(BASE_DIR, "mid/cleaned", f"{key}.mid")
    save_path = os.path.join(DATASET_DIR, category, f"{key}.npz")
    
    if not os.path.exists(wav_path) or not os.path.exists(midi_path): return

    try:
        y, _ = librosa.load(wav_path, sr=SR)
        C = librosa.cqt(y, sr=SR, hop_length=HOP_LENGTH, n_bins=CQT_BINS, bins_per_octave=BINS_PER_OCTAVE, fmin=librosa.note_to_hz('C1'))
        C_db = librosa.amplitude_to_db(np.abs(C), ref=np.max)
        C_norm = np.clip((C_db + 80.0) / 80.0, 0, 1)
        X = C_norm.T  

        # --- UPDATED PRIORITY: DTW FIRST ---
        align_info = {'mode': 'none'}
        tag = "RAW"
        
        if dtw_entry:
            align_info = {'mode': 'dtw', 'points': dtw_entry['points']}
            tag = "DTW"
        elif manual_entry:
            align_info = {'mode': 'manual', 'offset': manual_entry['offset'], 'speed': manual_entry['speed']}
            tag = "MANUAL"

        Y = get_aligned_midi_roll(midi_path, X.shape[0], align_info)
        np.savez_compressed(save_path, x=X.astype(np.float32), y=Y)
        return tag

    except Exception as e:
        print(f"  Error {key}: {e}")
        return None

def run_batch():
    os.makedirs(DATASET_DIR, exist_ok=True)
    for cat in ["first", "one_kor", "one_kor_sgl"]:
        print(f"\n--- Generating: {cat} ---")
        out_dir = os.path.join(DATASET_DIR, cat)
        os.makedirs(out_dir, exist_ok=True)
        dtw_map, manual_map = load_alignment_map(cat)
        
        files = [f.replace(".wav","") for f in os.listdir(os.path.join(BASE_DIR, "mp3", cat, "wav")) if f.endswith(".wav")]
        count = 0
        for i, key in enumerate(files):
            dtw = dtw_map.get(key)
            man = manual_map.get(key)
            tag = process_track(cat, key, dtw, man)
            if tag:
                count += 1
                if count % 10 == 0: print(f"[{count}/{len(files)}] Last: {key} -> {tag}", end="\r")
    print("\nDone.")

if __name__ == "__main__":
    run_batch()