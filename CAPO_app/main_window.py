import sys
import os
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel,
    QVBoxLayout, QHBoxLayout, QGridLayout, QWidget,
    QPushButton, QFrame, QStyle, QButtonGroup, QFileDialog, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QFont, QColor, QPalette

# relative imports inside package
from .audio_engine import AudioEngine
from .waveform_view import WaveformView
from .chord_diagram import ChordDiagramWidget


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS

        # CRITICAL FIX:
        # In your build.yml, you mapped "CAPO_app/assets" to just "assets".
        # So if the code asks for "CAPO_app/assets/...", we must change it to "assets/..."
        if "CAPO_app/assets" in relative_path:
            relative_path = relative_path.replace("CAPO_app/assets", "assets")

    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

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
    def __init__(self, custom_font_name="Segoe UI"):
        super().__init__()

        # --- 1. DEFINE COMMON ASSETS PATH (The Fix) ---
        # This logic handles the difference between "dev mode" and "installed app"
        if hasattr(sys, '_MEIPASS'):
            # If running as a compiled app (PyInstaller), assets are in the temp folder
            base_dir = os.path.join(sys._MEIPASS, "assets")
        else:
            # If running locally on your computer, assets are in "CAPO_app/assets"
            base_dir = os.path.abspath("CAPO_app/assets")
            
        # Store it as a class variable (self.assets_path) to use everywhere
        self.assets_path = base_dir.replace("\\", "/")

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
        self.chord_type_mode = "beginner"
        self.notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.original_file_path = None
        self.chords = []
        self.display_chords = []
        
        self.timer = QTimer()
        self.timer.setInterval(50) 
        self.timer.timeout.connect(self.update_game_loop)

        # --- WINDOW SETUP ---
        self.setWindowTitle("Capo | Unlock the Music")
        
        # 1. SET INITIAL SIZE (Starts at this size, but is resizable)
        self.resize(1333, 937)
        self.setMinimumSize(1000, 720) # Prevents shrinking too small
        
        # 2. WINDOW FLAGS
        # We MUST include WindowMaximizeButtonHint to allow resizing borders on Windows.
        # We can still manually disable Minimize if you prefer.
        flags = Qt.WindowType.Window
        flags |= Qt.WindowType.WindowCloseButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint # Required for manual resizing
        flags |= Qt.WindowType.CustomizeWindowHint
        flags |= Qt.WindowType.WindowTitleHint
        
        self.setWindowFlags(flags)

        # Optional: Disable Minimize only (if you still want that hidden)
        # self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # --- STYLESHEET ---
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #0c0704;
                background-image: url({self.assets_path}/border_shell.png);
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover;
                font-family: "Segoe UI", "Helvetica", sans-serif;
            }}

            QWidget#CentralWidget {{
                background-color: #b86e28;
                background-image: url({self.assets_path}/bg_main_wood.jpg);
                background-position: center;
                background-repeat: no-repeat;
                background-size: 100% 100%;
                border: 5px solid #d9b15c; /* Gold Border back */
                border-radius: 30px;
            }}

            QFrame[class="panel"] {{
                background-image: url({self.assets_path}/panel_wood.png);
                background-position: center;
                background-repeat: no-repeat;
                background-size: 100% 100%;
                border: 3px solid #d2ad61;
                border-radius: 15px;
                padding: 4px;
            }}

            QFrame#ControlsPanel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f4c979, stop:0.45 #e0b168, stop:1 #b7773b);
                border: 3px solid #d2ad61;
                border-radius: 15px;
                padding: 10px;
            }}

            QFrame#WaveformFrame {{
                background-color: #0b0a08;
                border: 4px solid #d2ad61;
                border-radius: 12px;
                padding: 0px; 
            }}

            /* --- TEXT --- */
            QLabel {{
                color: #f2d48a; /* GOLD */
                font-weight: 900;
                background: transparent;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
            }}

            QLabel#WindowTitle {{
                font-family: "{custom_font_name}";
                color: #331912; /* Back to GOLD */
                font-size: 38px; /* Back to larger size */
                font-weight: 900;
                letter-spacing: 1px;
                text-shadow: 1px 1px 3px #000;
            }}
            
            QLabel#SectionTitle {{
                color: #f2d48a;
                font-size: 18px;  /* <--- CHANGED FROM 12px TO 18px */
                font-weight: 900; /* Added bold weight */
                text-transform: uppercase;
                letter-spacing: 2px;
                border-bottom: 2px solid #f2d48a;
                padding-bottom: 8px; /* Increased padding slightly */
                margin-bottom: 8px;
                text-shadow: 1px 1px 2px #000;
            }}
            
            QLabel#ValueLabel {{
                color: #f2d48a;
                font-size: 20px;
                font-family: "Arial";
                font-weight: 900;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
            }}

            QLabel[class="ChordChip"] {{
                background-image: url({self.assets_path}/chord_chip.png);
                background-position: center;
                background-size: 100% 100%;
                background-repeat: no-repeat;
                color: #f2d48a;
                font-weight: 900;
                font-size: 13px;
                padding: 10px 8px;
                min-width: 80px;
                qproperty-alignment: AlignCenter;
                text-shadow: 0px 0px 1px rgba(255,255,255,0.4);
            }}

            /* --- CIRCLE BUTTONS --- */
            QPushButton.circle-btn {{
                background-color: #d9b15c; /* Gold Color */
                color: #3e2723;            /* Dark Brown Text */
                border: 2px solid #f2d48a; /* Light Gold Border */
                border-radius: 15px;       /* CURVED EDGES (Matches Pill) */
                min-width: 40px;
                min-height: 35px;
                font-size: 18px;
                font-weight: 900;
                padding: 0px;
            }}
            QPushButton.circle-btn:hover {{
                background-color: #f2d48a; /* Lighter on hover */
            }}
            QPushButton.circle-btn:pressed {{
                background-color: #b8860b; /* Darker on press */
                padding-top: 2px;
                padding-left: 2px;
            }}

            /* --- PILL BUTTONS (Curved Edges) --- */
            QPushButton.pill-btn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f4ec, stop:1 #d8cdb8);
                border: 2px solid #8D6E63;
                border-radius: 15px;       /* CURVED EDGES */
                color: #1a0e05;
                font-weight: 900;
                padding: 6px 15px;
                font-size: 12px;
                min-width: 90px;
            }}
            QPushButton.pill-btn:pressed {{
                padding-top: 3px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9dfcc, stop:1 #cbbda3);
            }}
            QPushButton.pill-btn:checked {{
                color: #000;
                border: 2px solid #D4AF37;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8e7b0, stop:1 #dfc37f);
            }}

            /* --- PILL BUTTONS --- */
            QPushButton.pill-btn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f4ec, stop:1 #d8cdb8);
                border: 1px solid #8D6E63;
                border-radius: 20px;
                color: #1a0e05;
                font-weight: 900;
                padding: 6px 15px;
                font-size: 15px;
                min-width: 90px;
            }}
            QPushButton.pill-btn:pressed {{
                padding-top: 3px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9dfcc, stop:1 #cbbda3);
            }}
            QPushButton.pill-btn:checked {{
                color: #000;
                border: 2px solid #D4AF37;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8e7b0, stop:1 #dfc37f);
            }}

            /* --- TRANSPORT BRIDGE --- */
            QFrame#BridgeFrame {{
                background-image: url({self.assets_path}/transport_bar.png);
                background-position: center;
                background-size: 100% 100%;
                background-repeat: no-repeat;
                border: none;
            }}

            QPushButton#TransportButton {{
                background-color: #f5f1e7;
                border: 2px solid #5D4037;
                border-radius: 25px;
                min-width: 50px;
                min-height: 50px;
                color: #1a0e05;
                qproperty-iconSize: 26px 26px;
            }}
            QPushButton#TransportButton:hover {{
                background-color: #ffffff;
                border-color: #D4AF37;
            }}
        """)

        self.init_ui()

    # ---------- UI setup ----------

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setObjectName("CentralWidget")
        self.setCentralWidget(main_widget)
        
        self.main_layout = QVBoxLayout()
        # Restore original margins
        self.main_layout.setContentsMargins(20, 15, 20, 15) 
        self.main_layout.setSpacing(10)
        main_widget.setLayout(self.main_layout)

        # Title Label (Back inside the main layout)
        title_lbl = QLabel("Capo") 
        title_lbl.setObjectName("WindowTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.main_layout.addWidget(title_lbl)

        # ── MAIN CONTENT AREA (Waveform, Chords, Controls) ────────────────
        
        # Waveform Frame
        self.top_frame = QFrame()
        self.top_frame.setObjectName("WaveformFrame")
        self.top_frame.setFixedHeight(170) 
        
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 10, 0)
        top_layout.setSpacing(5)
        self.top_frame.setLayout(top_layout)

        self.waveform_widget = WaveformView()
        self.waveform_widget.time_clicked.connect(self.seek_track)
        top_layout.addWidget(self.waveform_widget, stretch=1)

        zoom_col = QVBoxLayout()
        zoom_col.setContentsMargins(0, 10, 0, 10)
        zoom_col.setSpacing(5)
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setProperty("class", "circle-btn")
        self.btn_zoom_in.setFixedSize(30, 30)
        self.btn_zoom_in.clicked.connect(self.waveform_widget.zoom_in)
        zoom_col.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setProperty("class", "circle-btn")
        self.btn_zoom_out.setFixedSize(30, 30)
        self.btn_zoom_out.clicked.connect(self.waveform_widget.zoom_out)
        zoom_col.addWidget(self.btn_zoom_out)
        
        zoom_col.addStretch()
        top_layout.addLayout(zoom_col)
        
        self.main_layout.addWidget(self.top_frame)

        # MIDDLE AREA
        middle_container = QHBoxLayout()
        middle_container.setSpacing(15)

        # --- LEFT COLUMN (Chord Diagram - Nudged Right) ---
        left_col = QVBoxLayout()
        left_col.setSpacing(0) 
        
        self.finder_frame = QFrame()
        self.finder_frame.setProperty("class", "panel")
        find_layout = QVBoxLayout()
        find_layout.setContentsMargins(15, 12, 15, 15)
        self.finder_frame.setLayout(find_layout)
        
        find_layout.addStretch(1)
        
        # Heading (Centered)
        lbl_find = QLabel("CHORD DIAGRAM")
        lbl_find.setObjectName("SectionTitle")
        lbl_find.setAlignment(Qt.AlignmentFlag.AlignCenter)
        find_layout.addWidget(lbl_find)
        
        # -- CONTENT WRAPPER --
        shift_h = QHBoxLayout()
        
        # *** FIX: Added 40px padding to the LEFT.
        # This pushes the content slightly to the RIGHT.
        # Format: (Left, Top, Right, Bottom)
        shift_h.setContentsMargins(40, 0, 0, 0)
        
        content_v = QVBoxLayout()
        content_v.setSpacing(10)

        # Diagram
        self.diagram_widget = ChordDiagramWidget()
        self.diagram_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.diagram_widget.setMinimumHeight(300)
        self.diagram_widget.set_chord("") 
        content_v.addWidget(self.diagram_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Buttons
        type_layout = QHBoxLayout()
        type_layout.setSpacing(20)  # Increased spacing slightly for better looks
        
        # 1. Beginner Button
        self.btn_beginner = QPushButton("Beginner")
        self.btn_beginner.setProperty("class", "pill-btn")  # Connects to CSS for rounded edges
        self.btn_beginner.setCheckable(True)
        self.btn_beginner.setChecked(True)
        self.btn_beginner.setCursor(Qt.CursorShape.PointingHandCursor) # Hand cursor on hover
        self.btn_beginner.clicked.connect(lambda: self.set_chord_type_mode("beginner"))
        type_layout.addWidget(self.btn_beginner)
        
        # 2. Advanced Button
        self.btn_advanced = QPushButton("Advanced")
        self.btn_advanced.setProperty("class", "pill-btn") # <--- THIS LINE WAS LIKELY MISSING BEFORE
        self.btn_advanced.setCheckable(True)
        self.btn_advanced.setCursor(Qt.CursorShape.PointingHandCursor) # Hand cursor on hover
        self.btn_advanced.clicked.connect(lambda: self.set_chord_type_mode("advanced"))
        type_layout.addWidget(self.btn_advanced)
        
        # 3. Group them (Exclusive selection)
        grp = QButtonGroup(self)
        grp.addButton(self.btn_beginner)
        grp.addButton(self.btn_advanced)
        grp.setExclusive(True)
        
        content_v.addLayout(type_layout)
        
        shift_h.addLayout(content_v)
        
        find_layout.addLayout(shift_h)
        find_layout.addStretch(1)
        
        left_col.addWidget(self.finder_frame)
        middle_container.addLayout(left_col, stretch=4)

        # Right Column
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Detected Chords
        self.detected_frame = QFrame()
        self.detected_frame.setProperty("class", "panel")
        det_layout = QVBoxLayout()
        det_layout.setContentsMargins(15, 12, 15, 12)
        self.detected_frame.setLayout(det_layout)
        
        lbl_det = QLabel("CHORDS DETECTED")
        lbl_det.setObjectName("SectionTitle")
        lbl_det.setAlignment(Qt.AlignmentFlag.AlignCenter)
        det_layout.addWidget(lbl_det)
        
        self.chord_grid = QGridLayout()
        self.chord_grid.setSpacing(6)
        det_layout.addLayout(self.chord_grid)
        det_layout.addStretch()
        right_col.addWidget(self.detected_frame, stretch=3) 

        # 2. Performance Controls (Centralized)
        # 2. Performance Controls (Centralized & Shifted Left)
        self.controls_frame = QFrame()
        self.controls_frame.setProperty("class", "panel")
        
        ctrl_layout = QVBoxLayout()
        ctrl_layout.setSpacing(15) 
        # Keep these margins symmetric so the underline looks good
        ctrl_layout.setContentsMargins(30, 20, 30, 20)
        self.controls_frame.setLayout(ctrl_layout)

        # --- MAIN SECTION HEADING ---
        lbl_perf = QLabel("PERFORMANCE CONTROLS")
        lbl_perf.setObjectName("SectionTitle")
        lbl_perf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(lbl_perf)

        # -- CONTENT LAYOUT --
        # We use a separate layout for the buttons so we can squeeze it
        center_h = QHBoxLayout()
        
        # *** FIX: Add 80px padding to the RIGHT side only.
        # This pushes the "visual center" of the controls to the LEFT.
        # Format: (Left, Top, Right, Bottom)
        center_h.setContentsMargins(0, 0, 80, 0)
        
        grid = QGridLayout()
        grid.setVerticalSpacing(20)
        grid.setHorizontalSpacing(20)
        
        row_heading_style = "font-size: 15px; font-weight: 900; color: #f2d48a;"

        # --- Row 0: KEY SHIFT ---
        lbl_k = QLabel("KEY SHIFT")
        lbl_k.setStyleSheet(row_heading_style)
        grid.addWidget(lbl_k, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.btn_key_down = QPushButton("-")
        self.btn_key_down.setProperty("class", "circle-btn")
        self.btn_key_down.clicked.connect(self.key_down)
        grid.addWidget(self.btn_key_down, 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_key = QLabel("0")
        self.lbl_key.setObjectName("ValueLabel")
        self.lbl_key.setFixedWidth(100)
        self.lbl_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.lbl_key, 0, 2)
        
        self.btn_key_up = QPushButton("+")
        self.btn_key_up.setProperty("class", "circle-btn")
        self.btn_key_up.clicked.connect(self.key_up)
        grid.addWidget(self.btn_key_up, 0, 3, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Row 1: TEMPO ---
        lbl_t = QLabel("TEMPO")
        lbl_t.setStyleSheet(row_heading_style)
        grid.addWidget(lbl_t, 1, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.btn_slow = QPushButton("-")
        self.btn_slow.setProperty("class", "circle-btn")
        self.btn_slow.clicked.connect(self.slow_down)
        grid.addWidget(self.btn_slow, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_tempo = QLabel("0 BPM")
        self.lbl_tempo.setObjectName("ValueLabel")
        self.lbl_tempo.setFixedWidth(120) 
        self.lbl_tempo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_tempo.setStyleSheet("font-size: 18px; color: #f2d48a; font-weight: 900;")
        grid.addWidget(self.lbl_tempo, 1, 2)
        
        self.btn_fast = QPushButton("+")
        self.btn_fast.setProperty("class", "circle-btn")
        self.btn_fast.clicked.connect(self.speed_up)
        grid.addWidget(self.btn_fast, 1, 3, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Row 2: CAPO ---
        lbl_c = QLabel("CAPO")
        lbl_c.setStyleSheet(row_heading_style)
        grid.addWidget(lbl_c, 2, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.btn_capo_down = QPushButton("-")
        self.btn_capo_down.setProperty("class", "circle-btn")
        self.btn_capo_down.clicked.connect(self.capo_down)
        grid.addWidget(self.btn_capo_down, 2, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_capo = QLabel("0")
        self.lbl_capo.setObjectName("ValueLabel")
        self.lbl_capo.setFixedWidth(100) 
        self.lbl_capo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.lbl_capo, 2, 2)
        
        self.btn_capo_up = QPushButton("+")
        self.btn_capo_up.setProperty("class", "circle-btn")
        self.btn_capo_up.clicked.connect(self.capo_up)
        grid.addWidget(self.btn_capo_up, 2, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add normal stretches to keep it centered within the new margin-constrained area
        center_h.addStretch(1)
        center_h.addLayout(grid)
        center_h.addStretch(1)

        ctrl_layout.addStretch() 
        ctrl_layout.addLayout(center_h)
        ctrl_layout.addStretch() 
        
        right_col.addWidget(self.controls_frame, stretch=5)
        
        middle_container.addLayout(right_col, stretch=6)
        self.main_layout.addLayout(middle_container)

        # BOTTOM: The "Guitar Bridge"
        self.bridge_frame = QFrame()
        self.bridge_frame.setObjectName("BridgeFrame")
        self.bridge_frame.setFixedHeight(80) 
        
        bridge_layout = QHBoxLayout()
        bridge_layout.setContentsMargins(40, 10, 40, 10)
        bridge_layout.setSpacing(32)
        self.bridge_frame.setLayout(bridge_layout)

        # Load Button
        self.btn_load = QPushButton("Load Song")
        self.btn_load.setProperty("class", "pill-btn")
        self.btn_load.setFixedSize(130, 36)
        self.btn_load.clicked.connect(self.load_song)
        bridge_layout.addWidget(self.btn_load)
        
        bridge_layout.addStretch()

        # Playback Controls
        self.btn_play = QPushButton()
        self.btn_play.setObjectName("TransportButton")
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.play_audio)
        
        self.btn_pause = QPushButton()
        self.btn_pause.setObjectName("TransportButton")
        self.btn_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.btn_pause.clicked.connect(self.pause_audio)
        
        self.btn_stop = QPushButton()
        self.btn_stop.setObjectName("TransportButton")
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.btn_stop.clicked.connect(self.stop_audio)
        
        bridge_layout.addWidget(self.btn_play)
        bridge_layout.addWidget(self.btn_pause)
        bridge_layout.addWidget(self.btn_stop)
        
        bridge_layout.addStretch()
        
        # Status Label
        self.label_info = QLabel("No Song Loaded")
        self.label_info.setStyleSheet("color: #f2e7d0; font-size: 11px; font-style: italic;")
        bridge_layout.addWidget(self.label_info)

        self.main_layout.addWidget(self.bridge_frame)

        # Global Shortcuts
        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_left.activated.connect(lambda: self.nudge_playhead(-1.0))

        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_right.activated.connect(lambda: self.nudge_playhead(1.0))
        

    # ---------- Chord helpers ----------

    def set_chord_type_mode(self, mode: str):
        self.chord_type_mode = mode
        self.diagram_widget.set_mode(mode)

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

            # reset state
            self.playback_rate = 1.0
            self.key_shift = 0
            self.capo = 0
            self.lbl_key.setText("0")
            self.lbl_capo.setText("0")
            self.update_tempo_display()

            # ✅ use y_stereo now (WaveformView can handle stereo)
            if self.engine.y_stereo is not None:
                self.waveform_widget.plot_audio(self.engine.y_stereo, self.engine.sr)

            # chords (already in original key)
            self.refresh_display_chords()

            # audio player uses the ORIGINAL file path
            self.player.setSource(QUrl.fromLocalFile(self.original_file_path))
            self.player.setPlaybackRate(self.playback_rate)
            self.label_info.setText("Ready to Rock")
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
            lbl.setProperty("class", "ChordChip")
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
        if not self.original_file_path:
            self.label_info.setText("No track loaded")
            return

        # key_shift 0 => original audio
        if self.key_shift == 0:
            print("Reverting to original audio file (no pitch processing).")
            self.engine.cleanup_temp_file()
            new_source_path = self.original_file_path
            self.label_info.setText("Back to original key")
        else:
            self.label_info.setText(
                f"Shifting audio by {self.key_shift:+d} semitones..."
            )
            QApplication.processEvents() # Force UI update before heavy lift
            temp_file_path = self.engine.generate_shifted_file(self.key_shift)
            if not temp_file_path:
                self.label_info.setText("Error shifting audio.")
                return
            new_source_path = temp_file_path
            print(f"Using shifted audio: {new_source_path}")
            self.label_info.setText(f"Key shifted to {self.key_shift:+d}")

        # reload into QMediaPlayer
        current_pos = self.player.position()
        was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(new_source_path))
        self.player.setPlaybackRate(self.playback_rate)
        self.player.setPosition(current_pos)
        
        if was_playing:
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


def run_app():
    app = QApplication(sys.argv)

    # --- 1. DETERMINE ASSETS PATH ---
    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.join(sys._MEIPASS, "assets")
    else:
        base_dir = os.path.abspath("CAPO_app/assets")
        
    assets_path = base_dir.replace("\\", "/")

    # --- 2. LOAD FONT (Fixed Filename: .otf instead of .ttf) ---
    font_path = f"{assets_path}/fonts/Rosaline-Regular.otf"  # <--- UPDATED THIS LINE
    font_id = QFontDatabase.addApplicationFont(font_path)
    
    # Default fallback
    rosaline_family = "Segoe UI" 

    if font_id < 0:
        print(f"Error: Could not load font at {font_path}")
    else:
        # CAPTURE THE EXACT INTERNAL NAME
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            rosaline_family = families[0]
            print(f"Success! Font loaded as: '{rosaline_family}'")

    app.setStyle("Fusion")
    
    # --- 3. PASS THE FONT NAME TO THE WINDOW ---
    window = RiffStationWindow(custom_font_name=rosaline_family)
    window.show()
    
    sys.exit(app.exec())