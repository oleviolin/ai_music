import os
import glob
import sys
import numpy as np
import librosa
import librosa.display
import pretty_midi
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURATION ---
BASE_DIR = os.path.expanduser("~/ai_music")
MIDI_DIR = os.path.join(BASE_DIR, "mid/cleaned")

class AlignmentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spillefolk Alignment Workbench")
        self.root.geometry("1200x850")

        # Handle the "X" button properly
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Data placeholders
        self.midi_audio = None
        self.rec_audio = None
        self.sr = 22050
        self.current_key = ""
        
        # --- GUI LAYOUT ---
        control_frame = tk.Frame(root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # 1. Category Selector (Moved first as it determines the file list)
        tk.Label(control_frame, text="Recording Type:").pack(side=tk.LEFT, padx=(0, 5))
        self.cat_var = tk.StringVar(value="first")
        self.cat_combo = ttk.Combobox(control_frame, textvariable=self.cat_var, 
                                      values=["first", "one_kor", "one_kor_sgl"], width=12, state="readonly")
        self.cat_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.cat_combo.bind("<<ComboboxSelected>>", self.refresh_file_list)

        # 2. File Selector
        tk.Label(control_frame, text="Select Melody:").pack(side=tk.LEFT, padx=(0, 5))
        self.file_combo = ttk.Combobox(control_frame, width=30, state="readonly")
        self.file_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.file_combo.bind("<<ComboboxSelected>>", self.load_data)

        # 3. Speed Control
        tk.Label(control_frame, text="Speed:").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = tk.Scale(control_frame, from_=0.5, to=1.5, resolution=0.01, 
                                    orient=tk.HORIZONTAL, variable=self.speed_var, length=150)
        self.speed_scale.pack(side=tk.LEFT, padx=(0, 15))
        
        # 4. Buttons
        btn_refresh = tk.Button(control_frame, text="Apply Speed", command=self.update_processing)
        btn_refresh.pack(side=tk.LEFT, padx=5)

        btn_play = tk.Button(control_frame, text="Play Mix", command=self.play_mix, bg="#dddddd")
        btn_play.pack(side=tk.LEFT, padx=5)

        btn_stop = tk.Button(control_frame, text="Stop Audio", command=sd.stop, fg="red")
        btn_stop.pack(side=tk.LEFT, padx=5)

        # --- PLOT AREA ---
        self.fig, self.ax = plt.subplots(nrows=3, sharex=True, figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Initialize list
        self.refresh_file_list()

    def refresh_file_list(self, event=None):
        """Scans the currently selected MP3 folder and updates the file dropdown."""
        category = self.cat_var.get()
        mp3_dir = os.path.join(BASE_DIR, "mp3", category)
        
        # glob mp3s in that folder
        files = glob.glob(os.path.join(mp3_dir, "*.mp3"))
        
        # Extract keys (filename without extension)
        keys = sorted([os.path.splitext(os.path.basename(f))[0] for f in files])
        
        self.file_combo['values'] = keys
        if keys:
            self.file_combo.current(0)
            # Automatically load the first file
            self.load_data()
        else:
            self.file_combo.set('')
            messagebox.showwarning("Empty Folder", f"No MP3 files found in {category}")

    def load_data(self, event=None):
        sd.stop()
        key = self.file_combo.get()
        category = self.cat_var.get()
        
        if not key: return

        self.current_key = key
        print(f"Loading {key} from {category}...")

        midi_path = os.path.join(MIDI_DIR, f"{key}.mid")
        mp3_path = os.path.join(BASE_DIR, "mp3", category, f"{key}.mp3")

        if not os.path.exists(midi_path):
            messagebox.showerror("Missing MIDI", f"Could not find matching MIDI: {midi_path}")
            return

        # 1. Load MIDI
        try:
            pm = pretty_midi.PrettyMIDI(midi_path)
            self.midi_audio = pm.synthesize(fs=self.sr)
        except Exception as e:
            print(f"Error parsing MIDI: {e}")
            return

        # 2. Load Audio
        try:
            # Load only first 30 seconds to be fast
            self.rec_audio, _ = librosa.load(mp3_path, sr=self.sr, duration=30)
        except Exception as e:
            print(f"Error loading MP3: {e}")
            return
        
        # Reset speed
        self.speed_var.set(1.0)
        self.update_processing()

    def update_processing(self):
        sd.stop()
        if self.midi_audio is None or self.rec_audio is None:
            return

        # 1. Speed Correction
        speed = self.speed_var.get()
        if speed != 1.0:
            rec_processed = librosa.effects.time_stretch(self.rec_audio, rate=speed)
        else:
            rec_processed = self.rec_audio

        # 2. Align Lengths
        min_len = min(len(self.midi_audio), len(rec_processed))
        midi_crop = self.midi_audio[:min_len]
        rec_crop = rec_processed[:min_len]

        # 3. Compute CQT (CPB-like features)
        # hop_length=512 -> ~23ms time resolution
        C_midi = librosa.feature.chroma_cqt(y=midi_crop, sr=self.sr, hop_length=512)
        C_rec = librosa.feature.chroma_cqt(y=rec_crop, sr=self.sr, hop_length=512)

        # 4. Plot
        self.plot_results(C_midi, C_rec, midi_crop, rec_crop)
        
        # Store for playback
        self.playback_audio_midi = midi_crop
        self.playback_audio_rec = rec_crop

    def plot_results(self, C_midi, C_rec, audio_midi, audio_rec):
        # Clear axes
        for ax in self.ax: ax.clear()

        # Plot MIDI Chroma
        librosa.display.specshow(C_midi, y_axis='chroma', x_axis='time', ax=self.ax[0], cmap='coolwarm')
        self.ax[0].set_title(f'MIDI Reference: {self.current_key}')
        self.ax[0].set_xlabel('') # Hide x label for top plot

        # Plot Recording Chroma
        librosa.display.specshow(C_rec, y_axis='chroma', x_axis='time', ax=self.ax[1], cmap='coolwarm')
        self.ax[1].set_title(f'Recording: {self.cat_var.get()}')
        self.ax[1].set_xlabel('')

        # Plot Waveforms
        time_axis = np.linspace(0, len(audio_midi)/self.sr, len(audio_midi))
        # Normalize for display
        m_disp = audio_midi / (np.max(np.abs(audio_midi)) + 1e-9)
        r_disp = audio_rec / (np.max(np.abs(audio_rec)) + 1e-9)
        
        self.ax[2].plot(time_axis, m_disp, alpha=0.6, label='MIDI (Blue)', color='blue', linewidth=1)
        self.ax[2].plot(time_axis, r_disp, alpha=0.6, label='Rec (Orange)', color='orange', linewidth=1)
        self.ax[2].set_title('Waveform Alignment')
        self.ax[2].legend(loc="upper right")
        self.ax[2].set_xlabel('Time (s)')

        self.canvas.draw()

    def play_mix(self):
        if not hasattr(self, 'playback_audio_midi'): return
        
        # Create Stereo Mix (Left=Midi, Right=Rec)
        m = self.playback_audio_midi / (np.max(np.abs(self.playback_audio_midi)) + 1e-9) * 0.4
        r = self.playback_audio_rec / (np.max(np.abs(self.playback_audio_rec)) + 1e-9) * 0.4
        stereo_mix = np.vstack((m, r)).T
        
        sd.play(stereo_mix, self.sr)

    def on_closing(self):
        """Force clean shutdown"""
        print("Shutting down...")
        sd.stop()
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AlignmentApp(root)
        root.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)