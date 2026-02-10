import os
import glob
import json
import librosa
import pretty_midi

BASE_DIR = os.path.expanduser("~/ai_music")
SETUP_DIR = os.path.join(BASE_DIR, "setup")
CATEGORIES = ["first", "one_kor", "one_kor_sgl"]

# Silence Threshold (dB) - adjusted for synth vs recording
TOP_DB = 30 

def measure_all():
    print("--- Measuring Margins (Smart Heuristics) ---")
    os.makedirs(SETUP_DIR, exist_ok=True)

    # Load frozen list
    frozen_map = {}
    frozen_path = os.path.join(SETUP_DIR, "frozen_files.json")
    if os.path.exists(frozen_path):
        with open(frozen_path, 'r') as f: frozen_map = json.load(f)

    for cat in CATEGORIES:
        print(f"Processing category: {cat}")
        alignment_data = {}
        
        wav_dir = os.path.join(BASE_DIR, "mp3", cat, "wav")
        midi_dir = os.path.join(BASE_DIR, "mid/cleaned")
        wav_files = glob.glob(os.path.join(wav_dir, "*.wav"))
        
        for i, wav_path in enumerate(wav_files):
            key = os.path.splitext(os.path.basename(wav_path))[0]
            midi_path = os.path.join(midi_dir, f"{key}.mid")
            
            if not os.path.exists(midi_path): continue
            if i % 10 == 0: print(f"  {i}/{len(wav_files)}...", end="\r")

            # 1. Measure WAV (Silence Detection)
            try:
                # Load with default SR for speed
                y, sr = librosa.load(wav_path, sr=22050)
                # Trim silence
                yt, index = librosa.effects.trim(y, top_db=TOP_DB)
                
                wav_start_sec = index[0] / sr
                wav_end_sec = index[1] / sr
                wav_active_dur = wav_end_sec - wav_start_sec
            except:
                wav_start_sec = 0.0
                wav_active_dur = 0.0

            # 2. Measure MIDI
            try:
                pm = pretty_midi.PrettyMIDI(midi_path)
                start_times = [n.start for i in pm.instruments for n in i.notes]
                end_times = [n.end for i in pm.instruments for n in i.notes]
                
                if start_times:
                    midi_start = min(start_times)
                    midi_end = max(end_times)
                    midi_active_dur = midi_end - midi_start
                else:
                    midi_active_dur = 0.0
            except:
                midi_active_dur = 0.0

            # 3. Apply Heuristics
            calc_offset = 0.0
            calc_speed = 1.0

            if cat == "first":
                # Synth: Perfect speed, just need to find where audio starts
                calc_offset = wav_start_sec
                calc_speed = 1.0
            else:
                # Orchestra: Assume starts at 0, calculate speed stretch
                calc_offset = 0.0
                if midi_active_dur > 0.5 and wav_active_dur > 0.5:
                    # Ratio of Audio Length to MIDI Length
                    calc_speed = wav_active_dur / midi_active_dur
                else:
                    calc_speed = 1.0

            alignment_data[key] = {
                "calc_offset": round(calc_offset, 3),
                "calc_speed": round(calc_speed, 3),
                "is_frozen": (key in frozen_map.get(cat, []))
            }

        out_file = os.path.join(SETUP_DIR, f"alignment_{cat}.json")
        with open(out_file, 'w') as f:
            json.dump(alignment_data, f, indent=2)
            
        print(f"\n  Saved {len(alignment_data)} records to {out_file}")

if __name__ == "__main__":
    measure_all()