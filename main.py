import sys
import os # We need this to check file paths
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, 
                             QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, 
                             QPushButton, QFileDialog, QFrame, QStyle) # Added QStyle for standard icons
from PyQt6.QtCore import Qt, QUrl, QTimer # Added QUrl and QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput # <--- NEW AUDIO IMPORTS
from audio_engine import AudioEngine
from waveform_view import WaveformView



class RiffStationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = AudioEngine()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Default volume (0.0 to 1.0)
        self.audio_output.setVolume(0.7)
        self.timer = QTimer()
        self.timer.setInterval(16) # Update every 100ms (0.1 seconds)
        self.timer.timeout.connect(self.update_game_loop) # Call this function repeatedly
        self.setWindowTitle("My Riffstation Clone")
        self.setGeometry(100, 100, 1100, 750) 
        
        # --- THEME SETUP ---
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: #00d4ff; font-family: Arial; font-size: 14px; }
            QPushButton {
                background-color: #1e1e1e;
                color: #00d4ff;
                border: 2px solid #00d4ff;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #00d4ff; color: #121212; }
            QFrame { border: none; }
            .panel { 
                background-color: #1e1e1e; 
                border: 1px solid #333333; 
                border-radius: 8px; 
            }
        """)
        
        self.init_ui()

    def populate_chord_grid(self, all_chords):
        """ Clears the grid and fills it with unique detected chords """
        # 1. Get Unique Chords using a SET
        unique_chords = sorted(list(set(all_chords)))
        
        # 2. Clear previous items in the grid
        # (We loop backwards to safely remove items)
        for i in reversed(range(self.chord_grid.count())): 
            self.chord_grid.itemAt(i).widget().setParent(None)
            
        # 3. Add new boxes
        # We'll use a simple counter to handle rows/columns
        row = 0
        col = 0
        max_cols = 4 # How many chords per row?
        
        for chord in unique_chords:
            # Create a simple box for the chord
            lbl = QLabel(chord)
            lbl.setStyleSheet("""
                background-color: #333; 
                color: #00d4ff; 
                border: 1px solid #555; 
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            """)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Add to the grid layout
            self.chord_grid.addWidget(lbl, row, col)
            
            # Move to next cell
            col += 1
            if col >= max_cols:
                col = 0
                row += 1    

    def play_audio(self):
        self.player.play()
        self.timer.start() # Start syncing the graph
        
    def pause_audio(self):
        self.player.pause()
        self.timer.stop() # Stop wasting CPU
        
    def stop_audio(self):
        self.player.stop()
        self.timer.stop()
        self.waveform_widget.move_playhead(0) # Reset line to start
        
    def update_game_loop(self):
        """ This runs 10 times a second while music plays """
        current_ms = self.player.position()
        current_sec = current_ms / 1000
        
        # 1. Move the White Line
        self.waveform_widget.move_playhead(current_sec)
        
        # 2. Update the Current Chord --- NEW ---
        # We check if we have chords loaded, and if the current second is valid
        if hasattr(self, 'chords') and self.chords:
            index = int(current_sec) # e.g., 1.5 seconds -> index 1
            
            # Make sure we don't go past the end of the list
            if index < len(self.chords):
                current_chord = self.chords[index]
                self.lbl_big_chord.setText(current_chord)


    def seek_track(self, time_sec):
        """ Jumps the player to the specific time """
        # The player works in milliseconds, so we multiply by 1000
        self.player.setPosition(int(time_sec * 1000))
        # Update the visual line immediately so it feels snappy
        self.waveform_widget.move_playhead(time_sec)

    def init_ui(self):
        # Main Container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        main_widget.setLayout(self.main_layout)
        
        # --- ZONE 1: TOP (Waveform) ---
        self.top_frame = QFrame()
        self.top_frame.setProperty("class", "panel")
        self.top_frame.setFixedHeight(200)
        
        # We use a Horizontal layout now to put buttons next to the graph
        top_container = QHBoxLayout()
        top_container.setContentsMargins(0, 0, 0, 0)
        self.top_frame.setLayout(top_container)
        
        # The Waveform Graph
        self.waveform_widget = WaveformView()
        self.waveform_widget.time_clicked.connect(self.seek_track)
        top_container.addWidget(self.waveform_widget)
        
        # Zoom Controls (Vertical strip on the right)
        zoom_layout = QVBoxLayout()
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(30, 30)
        self.btn_zoom_in.clicked.connect(self.waveform_widget.zoom_in) # <--- Connect to class
        zoom_layout.addWidget(self.btn_zoom_in)
        
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(30, 30)
        self.btn_zoom_out.clicked.connect(self.waveform_widget.zoom_out) # <--- Connect to class
        zoom_layout.addWidget(self.btn_zoom_out)
        
        zoom_layout.addStretch() # Push buttons to the top
        top_container.addLayout(zoom_layout)
        
        self.main_layout.addWidget(self.top_frame)
        
        # --- ZONE 2: MIDDLE (The Dashboard) ---
        self.middle_frame = QFrame()
        self.middle_layout = QHBoxLayout()
        self.middle_frame.setLayout(self.middle_layout)
        
        # 2A. LEFT COLUMN: CHORDS DETECTED
        self.left_panel = QFrame()
        self.left_panel.setProperty("class", "panel")
        self.left_panel.setFixedWidth(320)
        
        left_layout = QVBoxLayout()
        self.left_panel.setLayout(left_layout)
        
        lbl_detected = QLabel("CHORDS DETECTED")
        lbl_detected.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(lbl_detected)
        
        # Placeholder grid for small chord boxes
        self.chord_grid = QGridLayout()
        for i in range(4): # Create 4 dummy chord slots
            box = QLabel("Cm") 
            box.setStyleSheet("border: 1px solid #555; padding: 10px;")
            box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chord_grid.addWidget(box, 0, i)
        left_layout.addLayout(self.chord_grid)
        left_layout.addStretch() # Push everything up
        
        self.middle_layout.addWidget(self.left_panel)

        # 2B. CENTER COLUMN: CONTROLS (Jam Master)
        self.center_panel = QFrame()
        self.center_panel.setProperty("class", "panel")
        
        center_layout = QGridLayout()
        self.center_panel.setLayout(center_layout)
        
        # Controls Row 1: Key Shift
        center_layout.addWidget(QLabel("KEY SHIFT"), 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        center_layout.addWidget(QLabel("0"), 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        # Controls Row 2: Tempo
        center_layout.addWidget(QLabel("TEMPO"), 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self.lbl_tempo = QLabel("0 BPM")
        self.lbl_tempo.setStyleSheet("font-weight: bold; font-size: 16px;")
        center_layout.addWidget(self.lbl_tempo, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        # Controls Row 3: Chord Type
        center_layout.addWidget(QLabel("CHORD TYPE"), 2, 0, alignment=Qt.AlignmentFlag.AlignRight)
        center_layout.addWidget(QLabel("Open | Power"), 2, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        self.middle_layout.addWidget(self.center_panel)

        # 2C. RIGHT COLUMN: CHORD FINDER
        self.right_panel = QFrame()
        self.right_panel.setProperty("class", "panel")
        self.right_panel.setFixedWidth(250)
        
        right_layout = QVBoxLayout()
        self.right_panel.setLayout(right_layout)
        
        lbl_finder = QLabel("CHORD FINDER")
        lbl_finder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(lbl_finder)
        
        # Big chord placeholder
        self.lbl_big_chord = QLabel("A Major")
        self.lbl_big_chord.setStyleSheet("font-size: 20px; border: 2px solid #00d4ff; padding: 20px;")
        self.lbl_big_chord.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.lbl_big_chord)
        
        self.middle_layout.addWidget(self.right_panel)
        
        self.main_layout.addWidget(self.middle_frame)
        
        # --- ZONE 3: BOTTOM (Playback Controls) ---
        self.bottom_frame = QFrame()
        self.bottom_frame.setFixedHeight(80)
        self.bottom_frame.setProperty("class", "panel")
        
        bot_layout = QHBoxLayout()
        self.bottom_frame.setLayout(bot_layout)
        
        # Load Button
        self.btn_load = QPushButton("Load Song 📂")
        self.btn_load.setFixedWidth(120)
        self.btn_load.clicked.connect(self.load_song)
        bot_layout.addWidget(self.btn_load)
        
        # Separator (Spacer)
        bot_layout.addStretch()
        
        # --- PLAYER CONTROLS ---
        # We use standard icons for a professional look
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.play_audio) # <--- CHANGED
        bot_layout.addWidget(self.btn_play)
        
        self.btn_pause = QPushButton()
        self.btn_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.btn_pause.clicked.connect(self.pause_audio) # <--- CHANGED
        bot_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton()
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.btn_stop.clicked.connect(self.stop_audio) # <--- CHANGED
        bot_layout.addWidget(self.btn_stop)
        
        # Separator
        bot_layout.addStretch()
        
        # Info Label
        self.label_info = QLabel("No song loaded")
        bot_layout.addWidget(self.label_info)
        
        self.main_layout.addWidget(self.bottom_frame)

    def load_song(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Audio", "", "Audio (*.mp3 *.wav)")
        if file_path:
            self.label_info.setText(f"Loading {file_path}...")
            QApplication.processEvents()
            
            if self.engine.load_track(file_path):
                # 1. Get Tempo
                bpm = self.engine.get_tempo()
                self.lbl_tempo.setText(f"{bpm:.0f} BPM")
                
                # 2. Get Chords --- NEW ---
                self.chords = self.engine.get_chords() # Save the list of chords
                
                # 3. Setup Visuals
                self.waveform_widget.plot_audio(self.engine.y, self.engine.sr)
                self.waveform_widget.plot_chords(self.chords)
                self.populate_chord_grid(self.chords)
                self.player.setSource(QUrl.fromLocalFile(file_path))
                
                self.label_info.setText("Track Loaded Successfully")
            else:
                self.label_info.setText("Error loading file.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RiffStationWindow()
    window.show()
    sys.exit(app.exec())