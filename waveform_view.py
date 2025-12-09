import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

class WaveformView(QWidget):
    time_clicked = pyqtSignal(float) 

    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        self.figure = Figure(figsize=(5, 2), dpi=100, facecolor='#121212')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#121212')
        self.ax.axis('off') 
        
        # Connect click event
        self.canvas.mpl_connect('button_press_event', self.on_click)

        # --- STATE VARIABLES ---
        self.duration = 0 # Total song length
        self.visible_duration = 0 # How many seconds are currently shown (Zoom level)
        self.current_start = 0 # Where the view currently starts
        self.chord_artists = []
        
        # Initial empty plot
        self.line, = self.ax.plot([], [], color='#ff7f00', linewidth=0.5)
        self.playhead, = self.ax.plot([], [], color='white', linewidth=1.5)
        self.canvas.draw()

    def plot_audio(self, y, sr):
        self.ax.clear()
        self.ax.axis('off')
        self.ax.set_facecolor('#121212')
        
        # Save song stats
        self.duration = len(y) / sr
        self.visible_duration = self.duration # Start fully zoomed out
        self.current_start = 0
        
        # Downsample
        step = 100 
        y_fast = y[::step] 
        self.times = np.arange(len(y_fast)) * step / sr
        
        self.ax.plot(self.times, y_fast, color='#ff7f00', linewidth=0.5)
        self.playhead, = self.ax.plot([0, 0], [-1, 1], color='white', linewidth=1.5)
        
        self.canvas.draw()

    def move_playhead(self, current_time_sec):
        # 1. Update the vertical line position
        self.playhead.set_data([current_time_sec, current_time_sec], [-1, 1])
        
        # 2. CONTINUOUS SCROLL LOGIC
        # Only scroll if we are zoomed in
        if self.visible_duration < self.duration:
            # We want the playhead to be in the CENTER of the view
            half_view = self.visible_duration / 2
            target_start = current_time_sec - half_view
            
            # "Clamp" the view so we don't show empty space before 0s or after the end
            if target_start < 0:
                self.current_start = 0
            elif target_start > self.duration - self.visible_duration:
                self.current_start = self.duration - self.visible_duration
            else:
                self.current_start = target_start
                
            # Update the camera position (X-Axis limits)
            self.ax.set_xlim(self.current_start, self.current_start + self.visible_duration)
            
        self.canvas.draw()

    def group_chords(self, chords):
        """
        Merges consecutive identical chords into segments.
        Returns a list of tuples: (chord_name, start_time, duration)
        """
        if not chords:
            return []
            
        grouped = []
        current_chord = chords[0]
        current_start = 0
        
        # Loop starting from the second chord
        for i in range(1, len(chords)):
            # If the chord changes, save the previous group
            if chords[i] != current_chord:
                duration = i - current_start
                grouped.append((current_chord, current_start, duration))
                
                # Reset for the new chord
                current_chord = chords[i]
                current_start = i
                
        # Don't forget the very last group!
        grouped.append((current_chord, current_start, len(chords) - current_start))
        
        return grouped
    
    def plot_chords(self, chords):
        """ Draws merged chord bubbles using a tracker list for safe cleanup """
        
        # 1. Clear ONLY the old chords
        for artist in self.chord_artists:
            artist.remove()
        self.chord_artists.clear() # Empty the list

        # 2. Group the chords
        segments = self.group_chords(chords)
        
        # 3. Draw each segment
        for chord_name, start, duration in segments:
            width = duration - 0.05 
            center_x = start + (duration / 2)
            
            # Create the Bubble
            box = mpatches.FancyBboxPatch(
                (start, -0.9), width, 0.2,
                boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor="#ff7f00",
                edgecolor="#ff7f00",
                mutation_scale=1
            )
            self.ax.add_patch(box)
            self.chord_artists.append(box) # <--- Add to tracker
            
            # Draw the Text
            text = self.ax.text(center_x, -0.8, chord_name, 
                         color='black', 
                         fontsize=9, 
                         fontweight='bold',
                         ha='center', va='center')
            self.chord_artists.append(text) # <--- Add to tracker
        
        self.canvas.draw()

    def zoom_in(self):
        # Show 20% less audio (zoom in)
        self.visible_duration *= 0.8
        # Minimum zoom: 1 second
        if self.visible_duration < 1: self.visible_duration = 1
        self.update_view()
        
    def zoom_out(self):
        # Show 20% more audio (zoom out)
        self.visible_duration *= 1.2
        # Maximum zoom: don't see more than the whole song
        if self.visible_duration > self.duration: self.visible_duration = self.duration
        self.update_view()
        
    def update_view(self):
        """ Applies the current zoom and position to the graph """
        self.ax.set_xlim(self.current_start, self.current_start + self.visible_duration)
        self.canvas.draw()

    def on_click(self, event):
        if event.xdata is not None:
            self.time_clicked.emit(event.xdata)