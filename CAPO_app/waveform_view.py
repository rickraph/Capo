import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

class WaveformView(QWidget):
    time_clicked = pyqtSignal(float) 

    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Dark Almost-Black background
        self.bg_color = '#0b0a08'
        self.line_color = '#00ffcc' # Bright Cyan
        
        self.figure = Figure(figsize=(5, 2), dpi=100, facecolor=self.bg_color)
        
        # Remove margins
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet(f"background-color: {self.bg_color};")
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(self.bg_color)
        self.ax.axis('off') 
        
        self.canvas.mpl_connect('button_press_event', self.on_click)

        self.duration = 0 
        self.visible_duration = 10 
        self.current_start = 0 
        self.chord_artists = [] 
        self.playhead = None
        
        self.canvas.draw()

    def show_placeholder(self):
        pass

    def plot_audio(self, y, sr):
        self.ax.clear()
        self.ax.set_facecolor(self.bg_color)
        self.ax.axis('off')
        
        if y.ndim > 1:
            y = np.mean(y, axis=0)
            
        self.duration = len(y) / sr
        self.visible_duration = self.duration 
        self.current_start = 0
        
        # Downsample
        target_points = 10000 
        step = max(1, len(y) // target_points)
        y_fast = y[::step] 
        
        # --- FIX: NORMALIZE SMALLER TO PREVENT OVERLAP ---
        # Scale to 0.75 so the bottom of the wave doesn't touch the chords
        max_val = np.max(np.abs(y_fast)) if len(y_fast) > 0 else 0
        if max_val > 0:
            y_fast = y_fast / max_val * 0.75
            
        times = np.arange(len(y_fast)) * step / sr
        
        self.line, = self.ax.plot(times, y_fast, color=self.line_color, linewidth=1.2)
        
        # Playhead (Full height)
        self.playhead, = self.ax.plot([0, 0], [-1.5, 1.5], color='white', linewidth=2)
        
        # --- FIX: EXPAND Y LIMITS ---
        # By setting bottom to -1.5, we create 'empty space' below -0.75 for the chords
        self.ax.set_xlim(0, self.visible_duration)
        self.ax.set_ylim(-1.5, 1.0) 
        
        self.canvas.draw()

    def plot_chords(self, chords):
        for artist in self.chord_artists:
            try: artist.remove()
            except: pass
        self.chord_artists.clear() 

        if not chords:
            self.canvas.draw()
            return

        segments = self.group_chords(chords)
        
        for chord_name, start, duration in segments:
            width = duration - 0.05 
            center_x = start + (duration / 2)
            
            # --- FIX: MOVE CHORDS LOWER ---
            # y = -1.35 puts them safely in the margin we created
            box = mpatches.FancyBboxPatch(
                (start, -1.45), width, 0.35, 
                boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor="#e0b168", 
                edgecolor="#d2ad61",
                mutation_scale=1
            )
            self.ax.add_patch(box)
            self.chord_artists.append(box) 
            
            text = self.ax.text(center_x, -1.28, chord_name, 
                         color='#1a0e05', fontsize=9, fontweight='bold',
                         ha='center', va='center')
            self.chord_artists.append(text) 
        
        self.canvas.draw()

    def move_playhead(self, current_time_sec):
        if self.playhead:
            self.playhead.set_data([current_time_sec, current_time_sec], [-1.5, 1.5])
            
            if self.visible_duration < self.duration:
                half_view = self.visible_duration / 2
                target_start = current_time_sec - half_view
                
                if target_start < 0: self.current_start = 0
                elif target_start > self.duration - self.visible_duration:
                    self.current_start = self.duration - self.visible_duration
                else: self.current_start = target_start
                    
                self.ax.set_xlim(self.current_start, self.current_start + self.visible_duration)
                
            self.canvas.draw()

    def group_chords(self, chords):
        if not chords: return []
        grouped = []
        current_chord = chords[0]
        current_start = 0
        for i in range(1, len(chords)):
            if chords[i] != current_chord:
                duration = i - current_start
                grouped.append((current_chord, current_start, duration))
                current_chord = chords[i]
                current_start = i
        grouped.append((current_chord, current_start, len(chords) - current_start))
        return grouped
    
    def zoom_in(self):
        self.visible_duration *= 0.8
        if self.visible_duration < 1: self.visible_duration = 1
        self.update_view()
        
    def zoom_out(self):
        self.visible_duration *= 1.2
        if self.visible_duration > self.duration: self.visible_duration = self.duration
        self.update_view()
        
    def update_view(self):
        self.ax.set_xlim(self.current_start, self.current_start + self.visible_duration)
        self.canvas.draw()

    def on_click(self, event):
        if event.xdata is not None:
            self.time_clicked.emit(event.xdata)