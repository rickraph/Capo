import librosa
import numpy as np 
import os
from typing import Tuple, Optional

class AudioEngine:
    """
    Handles loading, processing and analyzing audio files.
    """

    def __int__(self):
        self.filepath: Optional[str] = None
        self.y: Optional[np.ndarray] = None
        self.sr: Optional[int] = None
        self.duration: float = 0.0

    def get_chords(self):
        """
        Analyzes pitch content to guess chords.
        Returns a list of chords corresponding to each second of audio
        """
        if self.y is None:
            return []
            
        print("Analyzing chords...")
        # 1. Extract Chroma Features (The 12 pitch classes)
        # hop_length=512 is standard for audio analysis
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr, hop_length=512)
        
        # 2. Match Chroma Vectors to Templates
        # We look at each time slice and see which chord template it matches best
        # (This is a simplified version; real chord recognition is very complex math!)
        
        # Create standard chord templates (Major and Minor for all 12 keys)
        # We will use a library helper if available, or simple logic
        # For this step, let's keep it simple: just identifying the strongest chroma note
        # A more advanced version would use template matching.
        
        # Sum chroma over 1 second windows to get stable chords
        frames_per_sec = self.sr / 512
        num_seconds = int(self.duration)
        detected_chords = []
        
        # Pitch names mapping
        pitches = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        for i in range(num_seconds):
            # Get the start and end frame for this second
            start_frame = int(i * frames_per_sec)
            end_frame = int((i + 1) * frames_per_sec)
            
            # Average the chroma vectors in this window
            segment = chroma[:, start_frame:end_frame]
            average_chroma = np.mean(segment, axis=1)
            
            # Find the strongest note (Root note assumption)
            root_index = np.argmax(average_chroma)
            root_note = pitches[root_index]
            
            # Simple heuristic: guessing Major for now
            detected_chords.append(f"{root_note} Maj")
            
        return detected_chords
    
    def load_track(self, filepath: str) -> bool:
        """
        Loads an  audio file safely.
        Returns True if successful, False otherwise.
        """

        if not os.path.exists(filepath):
            print(f"Error: File not found at {filepath}")
            return False
        
        try:
            print(f"Loading {os.path.basename(filepath)}") 
            
            self.y, self.sr = librosa.load(filepath)
            self.duration = librosa.get_duration(y=self.y, sr=self.sr)
            self.filepath = filepath
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
        
    def get_tempo(self) -> float:
        """
        Analyzes the audio to estimate the tempo (BPM).
        """

        if self.y is None:
            return 0.0
        
        print("Analyzing tempo...")

        onset_env = librosa.onset.onset_strength(y= self.y, sr=self.sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=self.sr)
        
        return float(tempo) if np.ndim(tempo) == 0 else float(tempo[0])

if __name__ == "__main__":
    engine = AudioEngine()
    # REPLACE THIS with a path to a real MP3 or WAV file on your Ubuntu machine
    test_file = "/home/rickson-raphel/Desktop/Riffstation/Maroon 5 - Sugar (Lyrics).mp3" 
    
    if engine.load_track(test_file):
        chords = engine.get_chords()
        print(f"First 10 detected chords: {chords[:10]}")
        bpm = engine.get_tempo()
        print(f"Success! Detected Tempo: {bpm:.2f} BPM")
        print(f"Duration: {engine.duration:.2f} seconds")