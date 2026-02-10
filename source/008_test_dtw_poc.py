import os
import json
import random
import numpy as np
import librosa
import librosa.display
import pretty_midi
import matplotlib.pyplot as plt
import sys

# --- CONFIGURATION ---
BASE_DIR = os.path.expanduser("~/ai_music")
SETUP_DIR = os.path.join(BASE_DIR, "setup")
SR = 22050
HOP_LENGTH = 512

def load_manual_saves():
    """Aggregates all manual saves into a single list."""
    saves = []
    for cat in ["first", "one_kor", "one_kor_sgl"]:
        path = os.path.join(SETUP_DIR, f"alignment_manual_{cat}.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                for key, val in data.items():
                    saves.append({
                        "category": cat,
                        "key": key,
                        "manual_offset": float(val['offset']),
                        "manual_speed": float(val['speed'])
                    })
    return saves

def get_midi_start_time(pm):
    """Finds the start time of the very first note in the MIDI."""
    start_times = []
    for instrument in pm.instruments:
        for note in instrument.notes:
            start_times.append(note.start)
    if start_times:
        return min(start_times)
    return 0.0

def test_dtw(track_info):
    cat = track_info['category']
    key = track_info['key']
    m_offset = track_info['manual_offset']
    m_speed = track_info['manual_speed']
    
    print(f"\n--- Testing: {key} ({cat}) ---")
    print(f"Human says: Offset={m_offset:.3f}, Speed={m_speed:.3f}")

    # 1. Load Audio
    wav_path = os.path.join(BASE_DIR, "mp3", cat, "wav", f"{key}.wav")
    if not os.path.exists(wav_path):
        print(f"Audio file missing: {wav_path}")
        return

    y_rec, _ = librosa.load(wav_path, sr=SR)
    
    # 2. Load MIDI & Synthesize
    midi_path = os.path.join(BASE_DIR, "mid/cleaned", f"{key}.mid")
    if not os.path.exists(midi_path):
        print(f"MIDI file missing: {midi_path}")
        return

    try:
        pm = pretty_midi.PrettyMIDI(midi_path)
        y_midi = pm.synthesize(fs=SR)
        
        # KEY FIX: Get the start time of the first note
        first_note_time = get_midi_start_time(pm)
        print(f"MIDI First Note Time: {first_note_time:.3f}s")
        
    except Exception as e:
        print(f"Error loading MIDI: {e}")
        return

    # 3. Compute Chroma
    print("Computing Chroma...")
    c_rec = librosa.feature.chroma_cqt(y=y_rec, sr=SR, hop_length=HOP_LENGTH)
    c_midi = librosa.feature.chroma_cqt(y=y_midi, sr=SR, hop_length=HOP_LENGTH)

    # 4. Run DTW
    D, wp = librosa.sequence.dtw(X=c_midi, Y=c_rec, metric='cosine')
    
    # 5. Visualize Comparison
    plt.figure(figsize=(12, 8))
    
    # Plot Cost Matrix
    librosa.display.specshow(D, x_axis='frames', y_axis='frames', cmap='gray_r', 
                             hop_length=HOP_LENGTH, sr=SR)
    
    # Plot AI Path (Cyan)
    plt.plot(wp[:, 1], wp[:, 0], label='AI (DTW Path)', color='cyan', linewidth=2, alpha=0.8)
    
    # Plot Human Path (Red Dashed)
    # Corrected Logic: 
    # Player: AudioTime = ((MidiTime - FirstNote) * Speed) + Offset
    # Inverse: MidiTime = ((AudioTime - Offset) / Speed) + FirstNote
    
    audio_frames = np.arange(c_rec.shape[1])
    offset_frames = m_offset * SR / HOP_LENGTH
    first_note_frames = first_note_time * SR / HOP_LENGTH
    
    # Apply the shift to match the Player's logic + MIDI absolute time
    predicted_midi_frames = ((audio_frames - offset_frames) / m_speed) + first_note_frames
    
    plt.plot(audio_frames, predicted_midi_frames, label='Human (Manual Save)', 
             color='red', linestyle='--', linewidth=2)

    plt.title(f"DTW Consensus Check: {key}\n(Cyan=AI, Red=You)")
    plt.xlabel("Audio Frames (Recording)")
    plt.ylabel("MIDI Frames (Synthesized)")
    plt.legend()
    
    plt.xlim([0, c_rec.shape[1]])
    plt.ylim([0, c_midi.shape[1]])
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    saves = load_manual_saves()
    
    if not saves:
        print("No manual saves found! Please use the player to save some alignments first.")
        sys.exit()
        
    print(f"Found {len(saves)} manually validated files.")
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
        found = next((x for x in saves if x['key'] == target), None)
        if found:
            test_dtw(found)
        else:
            print(f"Key '{target}' not found in manual saves.")
    else:
        choice = random.choice(saves)
        test_dtw(choice)
        print("\nTip: Run 'python3 source/08_test_dtw_poc.py [filename]' to test a specific song.")