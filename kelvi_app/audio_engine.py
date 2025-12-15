# kelvi_app/audio_engine.py

import os
import numpy as np
import librosa
import soundfile as sf


class AudioEngine:
    def __init__(self):
        # Always keep the ORIGINAL audio here (stereo if available)
        self.y_stereo = None
        self.sr = None
        self.duration = 0.0

        self.original_path = None
        self.temp_path = None  # path to temp_shifted.wav

    # ----------------- LOADING -----------------

    def load_track(self, file_path: str) -> bool:
        """
        Load audio, keep full-quality stereo, no resampling.
        """
        try:
            print(f"Loading {file_path}...")
            y, sr = librosa.load(file_path, sr=None, mono=False)
            self.y_stereo = y
            self.sr = sr
            self.duration = librosa.get_duration(y=y, sr=sr)
            self.original_path = file_path
            self.cleanup_temp_file()

            print(f"Loaded: sr={sr}, duration={self.duration:.2f}s")
            return True
        except Exception as e:
            print(f"Error loading track: {e}")
            return False

    # ----------------- TEMPO / CHORDS -----------------

    def get_tempo(self) -> float:
        if self.y_stereo is None:
            return 0.0

        print("Analyzing tempo...")
        if self.y_stereo.ndim > 1:
            y_mono = librosa.to_mono(self.y_stereo)
        else:
            y_mono = self.y_stereo

        onset_env = librosa.onset.onset_strength(y=y_mono, sr=self.sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=self.sr)
        tempo = float(np.atleast_1d(tempo)[0])
        print(f"Detected tempo: {tempo:.1f} BPM")
        return tempo

    def get_chords(self):
        if self.y_stereo is None:
            return []

        print("Analyzing chords...")
        if self.y_stereo.ndim > 1:
            y_analyze = librosa.to_mono(self.y_stereo)
        else:
            y_analyze = self.y_stereo

        hop = 512
        chroma = librosa.feature.chroma_cqt(y=y_analyze, sr=self.sr, hop_length=512)
        frames_per_sec = self.sr / hop
        num_seconds = int(self.duration)

        pitches = ['C', 'C#', 'D', 'D#', 'E', 'F',
                   'F#', 'G', 'G#', 'A', 'A#', 'B']

        detected = []
        for i in range(num_seconds):
            start = int(i * frames_per_sec)
            end = int((i + 1) * frames_per_sec)
            segment = chroma[:, start:end]
            if segment.size == 0:
                detected.append("N.C.")
                continue
            avg = np.mean(segment, axis=1)
            idx = int(np.argmax(avg))
            root = pitches[idx]
            detected.append(f"{root} Maj")

        return detected

    # ----------------- PITCH SHIFTING -----------------

    def generate_shifted_file(self, semitones: int) -> str | None:
        """
        Create a stereo temp WAV with pitch shifted by `semitones`.
        Returns path to the new file (or original file if semitones==0),
        or None on error.
        """
        if self.y_stereo is None or self.original_path is None:
            return None

        if semitones == 0:
            # No shift requested – just use the original file
            return self.original_path

        try:
            print(f"Shifting pitch by {semitones} semitones (stereo)...")
            y = self.y_stereo

            if y.ndim > 1:
                # y: (channels, samples)
                left = librosa.effects.pitch_shift(y[0], sr=self.sr, n_steps=semitones)
                right = librosa.effects.pitch_shift(y[1], sr=self.sr, n_steps=semitones)
                min_len = min(len(left), len(right))
                data = np.stack([left[:min_len], right[:min_len]], axis=1)  # (samples, 2)
            else:
                shifted = librosa.effects.pitch_shift(y, sr=self.sr, n_steps=semitones)
                data = shifted

            folder = os.path.dirname(self.original_path)
            self.temp_path = os.path.join(folder, "temp_shifted.wav")
            sf.write(self.temp_path, data, self.sr)
            print(f"Temp shifted file written to {self.temp_path}")
            return self.temp_path
        except Exception as e:
            print(f"Error during pitch shifting: {e}")
            return None

    # ----------------- CLEANUP -----------------

    def cleanup_temp_file(self):
        if self.temp_path and os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
                print(f"Removed temp file: {self.temp_path}")
            except Exception as e:
                print(f"Could not remove temp file: {e}")
        self.temp_path = None
