import os
import tempfile

import librosa
import numpy as np
import soundfile as sf


class AudioEngine:
    def __init__(self):
        self.y = None
        self.sr = None
        self.duration = 0.0
        self.temp_file_path = None

    def load_track(self, file_path):
        """Loads an audio file, preserving original sample rate and stereo."""
        try:
            print(f"Loading {file_path}...")
            # Keep original sample rate (e.g. 44100), keep stereo
            self.y, self.sr = librosa.load(file_path, sr=None, mono=False)
            self.duration = librosa.get_duration(y=self.y, sr=self.sr)
            print(f"Loaded: sr={self.sr}, duration={self.duration:.2f}s")
            return True
        except Exception as e:
            print(f"Error loading track: {e}")
            self.y = None
            self.sr = None
            self.duration = 0.0
            return False

    def get_tempo(self):
        if self.y is None:
            return 0.0

        print("Analyzing tempo...")
        if self.y.ndim > 1:
            y_mono = librosa.to_mono(self.y)
        else:
            y_mono = self.y

        onset_env = librosa.onset.onset_strength(y=y_mono, sr=self.sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=self.sr)

        if isinstance(tempo, (np.ndarray, list)):
            tempo_val = float(tempo[0])
        else:
            tempo_val = float(tempo)

        print(f"Detected tempo: {tempo_val:.1f} BPM")
        return tempo_val

    def get_chords(self):
        if self.y is None:
            return []

        print("Analyzing chords...")

        if self.y.ndim > 1:
            y_analyze = librosa.to_mono(self.y)
        else:
            y_analyze = self.y

        chroma = librosa.feature.chroma_cqt(y=y_analyze, sr=self.sr, hop_length=512)

        frames_per_sec = self.sr / 512
        num_seconds = int(self.duration)
        detected_chords = []
        pitches = ['C', 'C#', 'D', 'D#', 'E', 'F',
                   'F#', 'G', 'G#', 'A', 'A#', 'B']

        for i in range(num_seconds):
            start_frame = int(i * frames_per_sec)
            end_frame = int((i + 1) * frames_per_sec)
            segment = chroma[:, start_frame:end_frame]

            if segment.size == 0:
                detected_chords.append("N.C.")
                continue

            average_chroma = np.mean(segment, axis=1)
            root_index = int(np.argmax(average_chroma))
            root_note = pitches[root_index]
            detected_chords.append(f"{root_note} Maj")

        return detected_chords

    # ---------- pitch shift / temp file ----------

    def generate_shifted_file(self, semitones):
        """
        Shifts pitch while preserving stereo quality.
        Returns absolute path to temp file, or None on failure.
        """
        if self.y is None:
            return None

        print(f"Shifting pitch by {semitones} semitones...")

        # delete previous temp, if any
        self.cleanup_temp_file()

        try:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"kelvi_shift_{semitones:+d}.wav")

            if self.y.ndim > 1:
                # stereo: process each channel separately
                y_left = librosa.effects.pitch_shift(
                    self.y[0],
                    sr=self.sr,
                    n_steps=semitones,
                    res_type="kaiser_best",
                )
                y_right = librosa.effects.pitch_shift(
                    self.y[1],
                    sr=self.sr,
                    n_steps=semitones,
                    res_type="kaiser_best",
                )
                y_shifted = np.vstack((y_left, y_right)).T  # shape: (samples, 2)
                sf.write(output_path, y_shifted, self.sr)
            else:
                y_shifted = librosa.effects.pitch_shift(
                    self.y,
                    sr=self.sr,
                    n_steps=semitones,
                    res_type="kaiser_best",
                )
                sf.write(output_path, y_shifted, self.sr)

            self.temp_file_path = output_path
            print(f"Temp shifted file written to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error generating shifted file: {e}")
            return None

    def cleanup_temp_file(self):
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.remove(self.temp_file_path)
                print(f"Deleted temp file: {self.temp_file_path}")
            except Exception as e:
                print(f"Failed to delete temp file: {e}")
        self.temp_file_path = None
