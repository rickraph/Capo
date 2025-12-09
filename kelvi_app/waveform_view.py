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

        self.figure = Figure(figsize=(5, 2), dpi=100, facecolor="#19232d")
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor("#19232d")
        self.ax.axis("off")
        # full area: no margins
        self.ax.set_position([0.0, 0.0, 1.0, 1.0])

        self.canvas.mpl_connect("button_press_event", self.on_click)

        self.duration = 0.0
        self.visible_duration = 10.0
        self.current_start = 0.0
        self.chord_artists = []
        self.playhead = None

    # ---------- audio plotting ----------

    def plot_audio(self, y, sr):
        if y is None:
            return

        # mix stereo to mono for drawing only
        if hasattr(y, "ndim") and y.ndim > 1:
            y_plot = np.mean(y, axis=0)
        else:
            y_plot = y

        total_samples = len(y_plot)
        print(f"DEBUG: Plotting {total_samples} samples.")
        if total_samples == 0:
            return

        self.ax.clear()
        self.ax.set_facecolor("#19232d")
        self.ax.axis("off")
        self.ax.set_position([0.0, 0.0, 1.0, 1.0])

        self.duration = total_samples / float(sr)
        self.visible_duration = self.duration
        self.current_start = 0.0

        target_points = 5000
        step = max(1, total_samples // target_points)
        y_fast = y_plot[::step]
        times = np.linspace(0.0, self.duration, num=len(y_fast), endpoint=False)

        # Studio accent color
        self.ax.plot(times, y_fast, color="#4fc3f7", linewidth=1.0)

        self.playhead, = self.ax.plot(
            [0, 0], [-1, 1], color="#ffffff", linewidth=1.5
        )

        self.ax.set_xlim(0.0, self.duration)
        self.ax.set_ylim(-1.0, 1.0)
        self.ax.margins(x=0.0)

        self.canvas.draw_idle()

    # ---------- chord overlays ----------

    def plot_chords(self, chords):
        for artist in self.chord_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self.chord_artists.clear()

        if not chords:
            self.canvas.draw_idle()
            return

        segments = self.group_chords(chords)

        for chord_name, start, duration in segments:
            width = max(0.05, duration - 0.05)
            center_x = start + (duration / 2.0)

            box = mpatches.FancyBboxPatch(
                (start, -0.9), width, 0.2,
                boxstyle="round,pad=0.02,rounding_size=0.1",
                facecolor="#fff176",
                edgecolor="#fff176",
                mutation_scale=1,
            )
            self.ax.add_patch(box)
            self.chord_artists.append(box)

            text = self.ax.text(
                center_x, -0.8, chord_name,
                color="#263238", fontsize=9, fontweight="bold",
                ha="center", va="center",
            )
            self.chord_artists.append(text)

        self.canvas.draw_idle()

    def group_chords(self, chords):
        if not chords:
            return []
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

    # ---------- playhead / zoom ----------

    def move_playhead(self, current_time_sec):
        if self.playhead is not None:
            self.playhead.set_data(
                [current_time_sec, current_time_sec], [-1, 1]
            )

            if self.visible_duration < self.duration:
                half_view = self.visible_duration / 2.0
                target_start = current_time_sec - half_view

                if target_start < 0:
                    self.current_start = 0
                elif target_start > self.duration - self.visible_duration:
                    self.current_start = self.duration - self.visible_duration
                else:
                    self.current_start = target_start

                self.ax.set_xlim(
                    self.current_start,
                    self.current_start + self.visible_duration,
                )

            self.canvas.draw_idle()

    def zoom_in(self):
        self.visible_duration *= 0.8
        if self.visible_duration < 1.0:
            self.visible_duration = 1.0
        self.update_view()

    def zoom_out(self):
        self.visible_duration *= 1.2
        if self.visible_duration > self.duration:
            self.visible_duration = self.duration
        self.update_view()

    def update_view(self):
        self.ax.set_xlim(self.current_start, self.current_start + self.visible_duration)
        self.canvas.draw_idle()

    # ---------- mouse ----------

    def on_click(self, event):
        if event.xdata is not None:
            self.time_clicked.emit(float(event.xdata))
