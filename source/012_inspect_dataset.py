import numpy as np
import matplotlib.pyplot as plt
import os
import random
import glob

BASE_DIR = os.path.expanduser("~/ai_music")
DATASET_DIR = os.path.join(BASE_DIR, "dataset_npz")

def inspect_random():
    # Find all .npz files
    files = glob.glob(os.path.join(DATASET_DIR, "*", "*.npz"))
    if not files:
        print("No .npz files found. Run 011_prepare_dataset.py first.")
        return

    path = random.choice(files)
    filename = os.path.basename(path)
    print(f"Inspecting: {path}")

    # Load
    data = np.load(path)
    X = data['x'] # (Time, Freq)
    Y = data['y'] # (Time,) - Pitch values

    # Plot
    plt.figure(figsize=(12, 6))
    
    # 1. Plot CQT Heatmap
    # X is (Time, Freq), we want (Freq, Time) for plotting
    plt.imshow(X.T, aspect='auto', origin='lower', cmap='magma', interpolation='nearest')
    
    # 2. Plot Labels
    # Y contains MIDI pitch (e.g. 60).
    # CQT Bins start at C1 (approx midi 24).
    # We need to map MIDI pitch to CQT Bin Index.
    # Bin = Pitch - 24 (If BINS_PER_OCTAVE=12 and starting at C1)
    
    # Filter out silence (0)
    time_indices = np.arange(len(Y))
    mask = Y > 0
    
    midi_cqt_bins = Y[mask] - 24 
    
    plt.scatter(time_indices[mask], midi_cqt_bins, color='cyan', s=5, label='Aligned MIDI Label')
    
    plt.title(f"Dataset Inspection: {filename}")
    plt.xlabel("Time Frames")
    plt.ylabel("CQT Frequency Bins")
    plt.colorbar(label="Magnitude (dB)")
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    inspect_random()