import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel,
    QVBoxLayout, QHBoxLayout, QGridLayout, QWidget,
    QPushButton, QFileDialog, QFrame, QStyle,
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QKeySequence, QShortcut

# NOTE: relative imports because this file is inside the kelvi_app package
from .audio_engine import AudioEngine
from .waveform_view import WaveformView
from .chord_diagram import ChordDiagramWidget


# ---------- Worker for background loading / analysis ----------

class AudioLoaderWorker(QThread):
    finished_loading = pyqtSignal()

    def __init__(self, engine, file_path):
        super().__init__()
        self.engine = engine
        self.file_path = file_path
        self.success = False
        self.detected_bpm = 0.0
        self.detected_chords = []

    def run(self):
        print("Worker: Loading track...")
        self.success = self.engine.load_track(self.file_path)

        if self.success:
            print("Worker: Analyzing tempo/chords...")
            self.detected_bpm = self.engine.get_tempo()
            self.detected_chords = self.engine.get_chords()

        print("Worker: Done!")
        self.finished_loading.emit()


# ---------- Main Window ----------

class RiffStationWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Engine / audio state
        self.engine = AudioEngine()
        self.loader_thread = None

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)

        self.playback_rate = 1.0
        self.original_bpm = 0.0
        self.key_shift = 0
        self.capo = 0
        self.notes = ['C', 'C#', 'D', 'D#', 'E', 'F',
                      'F#', 'G', 'G#', 'A', 'A#', 'B']

        self.original_file_path = None
        self.chords = []
        self.display_chords = []

        # Playhead timer
        self.timer = QTimer()
        self.timer.setInterval(50)  # ~20 FPS
        self.timer.timeout.connect(self.update_game_loop)

        # Window setup
        self.setWindowTitle("My Riffstation Clone")
        self.setFixedSize(1200, 650)  # lock size
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Studio Professional palette
        self.setStyleSheet("""
            QMainWindow {
                background-color: #19232d;
                font-family: "Segoe UI", "Arial";
                color: #ffffff;
            }

            QFrame[class="panel"] {
                background-color: #263238;
                border: 1px solid #37474f;
                border-radius: 10px;
            }

            QLabel#SectionTitle {
                color: #fff176;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 1px;
            }

            QFrame[class="panel"] QLabel {
                color: #ffffff;
                font-size: 13px;
            }

            QLabel#ControlLabel {
                color: #eceff1;
                font-weight: 500;
                font-size: 13px;
            }

            QLabel#ValueLabel {
                color: #fff176;
                font-weight: bold;
                font-size: 16px;
            }

            QLabel#InfoLabel {
                color: #fff176;
                font-size: 12px;
            }

            QPushButton {
                background-color: #263238;
                color: #ffffff;
                border: 1px solid #455a64;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #fff176;
                border-color: #fff9c4;
                color: #263238;
            }
            QPushButton:pressed {
                background-color: #ffe082;
                border-color: #fff59d;
                color: #263238;
            }

            QPushButton#TransportButton {
                background-color: #263238;
                border-radius: 18px;
                min-width: 36px;
                min-height: 36px;
                border: 1px solid #455a64;
            }
            QPushButton#TransportButton:hover {
                background-color: #fff176;
                border-color: #fff9c4;
                color: #263238;
            }

            QPushButton#ZoomButton {
                background-color: #263238;
                border-radius: 6px;
                border: 1px solid #455a64;
                font-weight: bold;
            }
            QPushButton#ZoomButton:hover {
                background-color: #fff176;
                color: #263238;
            }

            QWidget#waveformContainer {
                border-radius: 8px;
                border: 1px solid #4fc3f7;
                background-color: #19232d;
            }

            QWidget QLabel.chord-chip {
                background-color: #29434e;
                border-radius: 6px;
                border: 1px solid #4fc3f7;
                padding: 6px 10px;
                color: #fff176;
                font-weight: 600;
            }
        """)

        self.init_ui()

    # ---------- UI setup ----------

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        main_widget.setLayout(self.main_layout)

        # TOP: waveform
        self.top_frame = QFrame()
        self.top_frame.setProperty("class", "panel")
        self.top_frame.setFixedHeight(200)

        top_container = QHBoxLayout()
        top_container.setContentsMargins(0, 0, 0, 0)
        self.top_frame.setLayout(top_container)

        waveform_container = QWidget()
        waveform_container.setObjectName("waveformContainer")
        wc_layout = QVBoxLayout()
        wc_layout.setContentsMargins(0, 0, 0, 0)
        waveform_container.setLayout(wc_layout)

        self.waveform_widget = WaveformView()
        self.waveform_widget.time_clicked.connect(self.seek_track)
        wc_layout.addWidget(self.waveform_widget)

        top_container.addWidget(waveform_container)

        zoom_layout = QVBoxLayout()
        zoom_layout.setContentsMargins(4, 4, 4, 4)
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(30, 30)
        self.btn_zoom_in.setObjectName("ZoomButton")
        self.btn_zoom_in.clicked.connect(self.waveform_widget.zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(30, 30)
        self.btn_zoom_out.setObjectName("ZoomButton")
        self.btn_zoom_out.clicked.connect(self.waveform_widget.zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)

        zoom_layout.addStretch()
        top_container.addLayout(zoom_layout)

        self.main_layout.addWidget(self.top_frame)

        # MIDDLE: two boxes
        self.middle_frame = QFrame()
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_frame.setLayout(self.middle_layout)

        # LEFT BIG BOX: chords detected + controls
        self.left_combo_panel = QFrame()
        self.left_combo_panel.setProperty("class", "panel")
        left_combo_layout = QHBoxLayout()
        left_combo_layout.setContentsMargins(20, 20, 20, 20)
        left_combo_layout.setSpacing(30)
        self.left_combo_panel.setLayout(left_combo_layout)

        # --- Chords detected
        chords_container = QWidget()
        chords_layout = QVBoxLayout()
        chords_layout.setContentsMargins(0, 0, 20, 0)
        chords_container.setLayout(chords_layout)
        chords_container.setFixedWidth(320)

        lbl_detected = QLabel("CHORDS DETECTED")
        lbl_detected.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_detected.setObjectName("SectionTitle")
        chords_layout.addWidget(lbl_detected)

        self.chord_grid = QGridLayout()
        chords_layout.addLayout(self.chord_grid)
        chords_layout.addStretch()

        left_combo_layout.addWidget(chords_container)

        # --- Controls
        controls_container = QWidget()
        controls_outer_layout = QVBoxLayout()
        controls_outer_layout.setContentsMargins(0, 0, 0, 0)
        controls_outer_layout.setSpacing(10)
        controls_container.setLayout(controls_outer_layout)

        center_layout = QGridLayout()
        center_layout.setVerticalSpacing(12)
        center_layout.setHorizontalSpacing(20)

        # KEY SHIFT
        key_label = QLabel("KEY SHIFT")
        key_label.setObjectName("ControlLabel")
        center_layout.addWidget(
            key_label, 0, 0, alignment=Qt.AlignmentFlag.AlignRight
        )

        key_container = QWidget()
        key_layout = QHBoxLayout()
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(8)
        key_container.setLayout(key_layout)

        btn_key_down = QPushButton("-")
        btn_key_down.setFixedSize(25, 25)
        btn_key_down.clicked.connect(self.key_down)
        key_layout.addWidget(btn_key_down)

        self.lbl_key = QLabel("0")
        self.lbl_key.setObjectName("ValueLabel")
        self.lbl_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        key_layout.addWidget(self.lbl_key)

        btn_key_up = QPushButton("+")
        btn_key_up.setFixedSize(25, 25)
        btn_key_up.clicked.connect(self.key_up)
        key_layout.addWidget(btn_key_up)

        center_layout.addWidget(key_container, 0, 1)

        # TEMPO
        tempo_label = QLabel("TEMPO")
        tempo_label.setObjectName("ControlLabel")
        center_layout.addWidget(
            tempo_label, 1, 0, alignment=Qt.AlignmentFlag.AlignRight
        )

        tempo_container = QWidget()
        tempo_layout = QHBoxLayout()
        tempo_layout.setContentsMargins(0, 0, 0, 0)
        tempo_layout.setSpacing(8)
        tempo_container.setLayout(tempo_layout)

        btn_slower = QPushButton("-")
        btn_slower.setFixedSize(25, 25)
        btn_slower.clicked.connect(self.slow_down)
        tempo_layout.addWidget(btn_slower)

        self.lbl_tempo = QLabel("0 BPM")
        self.lbl_tempo.setObjectName("ValueLabel")
        self.lbl_tempo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tempo_layout.addWidget(self.lbl_tempo)

        btn_faster = QPushButton("+")
        btn_faster.setFixedSize(25, 25)
        btn_faster.clicked.connect(self.speed_up)
        tempo_layout.addWidget(btn_faster)

        center_layout.addWidget(tempo_container, 1, 1)

        # CHORD TYPE
        chord_type_label = QLabel("CHORD TYPE")
        chord_type_label.setObjectName("ControlLabel")
        center_layout.addWidget(
            chord_type_label, 2, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        center_layout.addWidget(
            QLabel("Open | Power"), 2, 1,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        # CAPO
        capo_label = QLabel("CAPO")
        capo_label.setObjectName("ControlLabel")
        center_layout.addWidget(
            capo_label, 3, 0, alignment=Qt.AlignmentFlag.AlignRight
        )

        capo_container = QWidget()
        capo_layout = QHBoxLayout()
        capo_layout.setContentsMargins(0, 0, 0, 0)
        capo_layout.setSpacing(8)
        capo_container.setLayout(capo_layout)

        btn_capo_down = QPushButton("-")
        btn_capo_down.setFixedSize(25, 25)
        btn_capo_down.clicked.connect(self.capo_down)
        capo_layout.addWidget(btn_capo_down)

        self.lbl_capo = QLabel("0")
        self.lbl_capo.setObjectName("ValueLabel")
        self.lbl_capo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capo_layout.addWidget(self.lbl_capo)

        btn_capo_up = QPushButton("+")
        btn_capo_up.setFixedSize(25, 25)
        btn_capo_up.clicked.connect(self.capo_up)
        capo_layout.addWidget(btn_capo_up)

        center_layout.addWidget(capo_container, 3, 1)

        controls_outer_layout.addStretch()
        controls_outer_layout.addLayout(center_layout)
        controls_outer_layout.setAlignment(center_layout, Qt.AlignmentFlag.AlignHCenter)
        controls_outer_layout.addStretch()

        left_combo_layout.addWidget(controls_container)
        self.middle_layout.addWidget(self.left_combo_panel, stretch=2)

        # RIGHT BOX: chord finder
        self.right_panel = QFrame()
        self.right_panel.setProperty("class", "panel")
        self.right_panel.setFixedWidth(250)
        right_layout = QVBoxLayout()
        self.right_panel.setLayout(right_layout)

        lbl_finder = QLabel("CHORD FINDER")
        lbl_finder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_finder.setObjectName("SectionTitle")
        right_layout.addWidget(lbl_finder)

        self.diagram_widget = ChordDiagramWidget()
        right_layout.addWidget(self.diagram_widget)

        self.middle_layout.addWidget(self.right_panel, stretch=1)
        self.main_layout.addWidget(self.middle_frame)

        # BOTTOM: transport + info
        self.bottom_frame = QFrame()
        self.bottom_frame.setFixedHeight(80)
        self.bottom_frame.setProperty("class", "panel")
        bot_layout = QHBoxLayout()
        self.bottom_frame.setLayout(bot_layout)

        self.btn_load = QPushButton("Load Song 📂")
        self.btn_load.setFixedWidth(150)
        self.btn_load.clicked.connect(self.load_song)
        bot_layout.addWidget(self.btn_load)

        bot_layout.addStretch()

        self.btn_play = QPushButton()
        self.btn_play.setObjectName("TransportButton")
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.play_audio)
        bot_layout.addWidget(self.btn_play)

        self.btn_pause = QPushButton()
        self.btn_pause.setObjectName("TransportButton")
        self.btn_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.btn_pause.clicked.connect(self.pause_audio)
        bot_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton()
        self.btn_stop.setObjectName("TransportButton")
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.btn_stop.clicked.connect(self.stop_audio)
        bot_layout.addWidget(self.btn_stop)

        bot_layout.addStretch()

        self.label_info = QLabel("No song loaded")
        self.label_info.setObjectName("InfoLabel")
        bot_layout.addWidget(self.label_info)

        self.main_layout.addWidget(self.bottom_frame)

        # Global arrow-key shortcuts
        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_left.activated.connect(lambda: self.nudge_playhead(-1.0))

        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_right.activated.connect(lambda: self.nudge_playhead(1.0))

    # ---------- Chord helpers ----------

    def transpose_chord(self, chord_name, semitone_shift):
        root = chord_name.split()[0]
        suffix = chord_name[len(root):]
        if root in self.notes:
            idx = self.notes.index(root)
            new_idx = (idx + semitone_shift) % 12
            return self.notes[new_idx] + suffix
        return chord_name

    def get_display_chord(self, chord_name):
        semitone_shift = self.key_shift - self.capo
        return self.transpose_chord(chord_name, semitone_shift)

    def refresh_display_chords(self):
        if not self.chords:
            return
        self.display_chords = [self.get_display_chord(ch) for ch in self.chords]
        self.waveform_widget.plot_chords(self.display_chords)
        self.populate_chord_grid(self.display_chords)

    # ---------- Load / analysis ----------

    def load_song(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio", "", "Audio (*.mp3 *.wav)"
        )
        if file_path:
            self.label_info.setText(f"Loading {os.path.basename(file_path)}...")
            self.loader_thread = AudioLoaderWorker(self.engine, file_path)
            self.loader_thread.finished_loading.connect(self.on_load_complete)
            self.loader_thread.start()

    def on_load_complete(self):
        if not self.loader_thread:
            return

        if self.loader_thread.success:
            print("Main: Worker finished. UI updating...")
            self.chords = self.loader_thread.detected_chords
            self.original_bpm = self.loader_thread.detected_bpm
            self.original_file_path = self.loader_thread.file_path

            self.playback_rate = 1.0
            self.key_shift = 0
            self.capo = 0
            self.lbl_key.setText("0")
            self.lbl_capo.setText("0")
            self.update_tempo_display()

            if self.engine.y is not None:
                self.waveform_widget.plot_audio(self.engine.y, self.engine.sr)

            self.refresh_display_chords()

            self.player.setSource(QUrl.fromLocalFile(self.original_file_path))
            self.player.setPlaybackRate(self.playback_rate)
            self.label_info.setText("Track Loaded Successfully")
        else:
            self.label_info.setText("Error loading file.")

    def populate_chord_grid(self, all_chords):
        unique_chords = sorted(set(all_chords))
        for i in reversed(range(self.chord_grid.count())):
            item = self.chord_grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        row, col = 0, 0
        max_cols = 4
        for chord in unique_chords:
            lbl = QLabel(chord)
            lbl.setProperty("class", "chord-chip")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chord_grid.addWidget(lbl, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    # ---------- Tempo ----------

    def change_speed(self, bpm_change):
        if self.original_bpm <= 0:
            return
        current_bpm = self.original_bpm * self.playback_rate
        new_bpm = current_bpm + bpm_change
        self.playback_rate = new_bpm / self.original_bpm
        self.playback_rate = max(0.2, min(2.0, self.playback_rate))
        self.player.setPlaybackRate(self.playback_rate)
        self.update_tempo_display()

    def update_tempo_display(self):
        if self.original_bpm > 0:
            current_bpm = self.original_bpm * self.playback_rate
            self.lbl_tempo.setText(f"{current_bpm:.0f} BPM")
        else:
            self.lbl_tempo.setText("0 BPM")

    def speed_up(self):
        self.change_speed(1)

    def slow_down(self):
        self.change_speed(-1)

    # ---------- Key / Capo ----------

    def key_up(self):
        self.key_shift += 1
        self.lbl_key.setText(f"{self.key_shift:+d}")
        self.apply_audio_shift()
        self.refresh_display_chords()

    def key_down(self):
        self.key_shift -= 1
        self.lbl_key.setText(f"{self.key_shift:+d}")
        self.apply_audio_shift()
        self.refresh_display_chords()

    def capo_up(self):
        if self.capo < 11:
            self.capo += 1
            self.lbl_capo.setText(str(self.capo))
            self.refresh_display_chords()

    def capo_down(self):
        if self.capo > 0:
            self.capo -= 1
            self.lbl_capo.setText(str(self.capo))
            self.refresh_display_chords()

    # ---------- Pitch shift audio switching ----------

    def apply_audio_shift(self):
        """
        key_shift == 0  -> original file
        key_shift != 0  -> temp pitch-shifted WAV
        For now: restart from beginning so you clearly hear the change.
        """
        if not self.original_file_path:
            self.label_info.setText("No track loaded")
            return

        if self.key_shift == 0:
            # back to original
            print("Reverting to original audio file (no pitch processing).")
            self.engine.cleanup_temp_file()
            new_source_path = self.original_file_path
            self.label_info.setText("Back to original key")
        else:
            # use shifted temp file
            self.label_info.setText(
                f"Shifting audio by {self.key_shift:+d} semitones..."
            )
            temp_file_path = self.engine.generate_shifted_file(self.key_shift)
            if not temp_file_path:
                self.label_info.setText("Error shifting audio.")
                return
            new_source_path = temp_file_path
            print(f"Using shifted audio: {new_source_path}")
            self.label_info.setText(f"Key shifted to {self.key_shift:+d}")

        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(new_source_path))
        self.player.setPlaybackRate(self.playback_rate)
        self.player.setPosition(0)
        self.player.play()

    # ---------- Playback / navigation ----------

    def play_audio(self):
        self.player.play()
        self.timer.start()

    def pause_audio(self):
        self.player.pause()
        self.timer.stop()

    def stop_audio(self):
        self.player.stop()
        self.timer.stop()
        self.waveform_widget.move_playhead(0.0)

    def seek_track(self, time_sec):
        self.player.setPosition(int(time_sec * 1000))
        self.waveform_widget.move_playhead(time_sec)

    def nudge_playhead(self, delta_sec):
        if self.player.duration() <= 0:
            return
        current_ms = self.player.position()
        target_ms = current_ms + int(delta_sec * 1000)
        target_ms = max(0, min(target_ms, self.player.duration()))
        self.player.setPosition(target_ms)
        self.waveform_widget.move_playhead(target_ms / 1000.0)
        self.update_game_loop()

    def update_game_loop(self):
        current_ms = self.player.position()
        current_sec = current_ms / 1000.0
        self.waveform_widget.move_playhead(current_sec)

        if self.chords:
            idx = int(current_sec)
            if 0 <= idx < len(self.chords):
                raw = self.chords[idx]
                self.diagram_widget.set_chord(self.get_display_chord(raw))

    # ---------- Cleanup ----------

    def closeEvent(self, event):
        try:
            self.engine.cleanup_temp_file()
        except Exception as e:
            print(f"Error during cleanup on close: {e}")
        super().closeEvent(event)


# ---------- entry point for top-level main.py ----------

def run_app():
    app = QApplication(sys.argv)
    window = RiffStationWindow()
    window.show()
    sys.exit(app.exec())
