from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtCore import Qt

# Chord shapes: (string_number 1-6, fret_number 1-7)
# 1 = high E (right), 6 = low E (left)
CHORD_SHAPES = {
    # --- MAJOR ---
    "C":  [(5, 3), (4, 2), (2, 1)],
    "C#": [(4, 3), (3, 1), (2, 2), (1, 1)],
    "D":  [(3, 2), (1, 2), (2, 3)],
    "D#": [(4, 1), (3, 3), (2, 4), (1, 3)],
    "E":  [(5, 2), (4, 2), (3, 1)],
    "F":  [(4, 3), (3, 2), (2, 1), (1, 1)],
    "F#": [(4, 4), (3, 3), (2, 2)],
    "G":  [(6, 3), (5, 2), (1, 3)],
    "G#": [(4, 6), (3, 5), (2, 4), (1, 4)],
    "A":  [(4, 2), (3, 2), (2, 2)],
    "A#": [(4, 3), (3, 3), (2, 3), (1, 1)],
    "B":  [(4, 4), (3, 4), (2, 4)],

    # --- MINOR ---
    "Cm":  [(5, 3), (4, 5), (3, 5), (2, 4)],
    "C#m": [(5, 4), (4, 6), (3, 6), (2, 5)],
    "Dm":  [(3, 2), (2, 3), (1, 1)],
    "D#m": [(4, 1), (3, 3), (2, 4), (1, 2)],
    "Em":  [(5, 2), (4, 2)],
    "Fm":  [(4, 3), (3, 1), (2, 1), (1, 1)],
    "F#m": [(4, 4), (3, 2), (2, 2)],
    "Gm":  [(4, 5), (3, 3), (2, 3), (1, 3)],
    "G#m": [(4, 6), (3, 4), (2, 4)],
    "Am":  [(4, 2), (3, 2), (2, 1)],
    "A#m": [(4, 3), (3, 1), (2, 2), (1, 1)],
    "Bm":  [(3, 4), (2, 3), (1, 2)],

    # --- 7th ---
    "C7": [(5, 3), (4, 2), (3, 3), (2, 1)],
    "D7": [(3, 2), (2, 1), (1, 2)],
    "E7": [(5, 2), (3, 1)],
    "F7": [(4, 3), (3, 2), (2, 4), (1, 1)],
    "G7": [(6, 3), (5, 2), (1, 1)],
    "A7": [(4, 2), (2, 2)],
    "B7": [(5, 2), (4, 1), (3, 2), (1, 2)],
}


class ChordDiagramWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Taller + can expand vertically
        self.setMinimumWidth(180)
        self.setMinimumHeight(260)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )
        self.current_chord = "A"

    def set_chord(self, chord_name):
        clean_name = chord_name.split()[0]
        self.current_chord = clean_name
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        painter.fillRect(rect, QColor("#263238"))

        margin_x = 30
        margin_y = 40
        width = rect.width() - (margin_x * 2)
        height = rect.height() - (margin_y * 2)

        # nut
        pen_nut = QPen(QColor("#455a64"), 8)
        painter.setPen(pen_nut)
        painter.drawLine(margin_x, margin_y, margin_x + width, margin_y)

        # 7 frets
        pen_fret = QPen(QColor("#455a64"), 2)
        painter.setPen(pen_fret)
        num_frets = 7
        fret_spacing = height / num_frets

        for i in range(1, num_frets + 1):
            y = margin_y + (i * fret_spacing)
            painter.drawLine(margin_x, int(y), margin_x + width, int(y))

        # 6 strings
        pen_string = QPen(QColor("#90a4ae"), 1)
        painter.setPen(pen_string)
        num_strings = 6
        string_spacing = width / (num_strings - 1)
        string_x_positions = []

        for i in range(num_strings):
            x = margin_x + (i * string_spacing)
            string_x_positions.append(x)
            painter.drawLine(int(x), margin_y, int(x), margin_y + int(height))

        # fingers
        if self.current_chord in CHORD_SHAPES:
            positions = CHORD_SHAPES[self.current_chord]
            painter.setBrush(QBrush(QColor("#fff176")))
            painter.setPen(Qt.PenStyle.NoPen)

            for string_num, fret_num in positions:
                # 6 = low E (left), 1 = high E (right)
                string_idx = 6 - string_num
                x = string_x_positions[string_idx]
                y = margin_y + (fret_num * fret_spacing) - (fret_spacing / 2)
                painter.drawEllipse(int(x) - 8, int(y) - 8, 16, 16)

        # chord name
        painter.setPen(QColor("#fff176"))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            self.current_chord,
        )
