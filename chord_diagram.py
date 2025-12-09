from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtCore import Qt

# A simple dictionary mapping Chord Names to Finger Positions
# Format: "Chord": [(String 1-6, Fret 1-4), ...]
# Strings: 1=High E (Right), 6=Low E (Left)
CHORD_SHAPES = {
    "C":  [(5, 3), (4, 2), (2, 1)],      # C Major
    "G":  [(6, 3), (5, 2), (1, 3)],      # G Major
    "D":  [(3, 2), (1, 2), (2, 3)],      # D Major
    "A":  [(4, 2), (3, 2), (2, 2)],      # A Major
    "E":  [(5, 2), (4, 2), (3, 1)],      # E Major
    "Am": [(4, 2), (3, 2), (2, 1)],      # A Minor
    "Em": [(5, 2), (4, 2)],              # E Minor
    "Dm": [(3, 2), (2, 3), (1, 1)],      # D Minor
    # Add more as needed!
}

class ChordDiagramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(150, 200)
        self.current_chord = "A" # Default
        
    def set_chord(self, chord_name):
        """ Updates the chord and repaints the widget """
        # Strip " Maj" or " min" to match our dictionary keys
        clean_name = chord_name.split()[0] 
        self.current_chord = clean_name
        self.update() # Triggers paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Background
        rect = self.rect()
        painter.fillRect(rect, QColor("#1e1e1e"))
        
        # 2. Draw the Nut (Top thick bar)
        pen_nut = QPen(QColor("#555"), 8)
        painter.setPen(pen_nut)
        margin_x = 30
        margin_y = 40
        width = rect.width() - (margin_x * 2)
        height = rect.height() - (margin_y * 2)
        
        painter.drawLine(margin_x, margin_y, margin_x + width, margin_y)
        
        # 3. Draw Frets (Horizontal Lines)
        pen_fret = QPen(QColor("#555"), 2)
        painter.setPen(pen_fret)
        num_frets = 5
        fret_spacing = height / num_frets
        
        for i in range(1, num_frets + 1):
            y = margin_y + (i * fret_spacing)
            painter.drawLine(margin_x, int(y), margin_x + width, int(y))
            
        # 4. Draw Strings (Vertical Lines)
        # Strings are usually silver/grey
        pen_string = QPen(QColor("#888"), 1) 
        painter.setPen(pen_string)
        num_strings = 6
        string_spacing = width / (num_strings - 1)
        
        string_x_positions = []
        for i in range(num_strings):
            x = margin_x + (i * string_spacing)
            string_x_positions.append(x)
            painter.drawLine(int(x), margin_y, int(x), margin_y + int(height))
            
        # 5. Draw Fingers (Dots)
        if self.current_chord in CHORD_SHAPES:
            positions = CHORD_SHAPES[self.current_chord]
            
            painter.setBrush(QBrush(QColor("#ff7f00"))) # Orange
            painter.setPen(Qt.PenStyle.NoPen)
            
            for string_num, fret_num in positions:
                # Calculate X: String index (0-5). Input is 1-6, but 1 is High E (Right side)
                # Usually charts go Low E (Left) -> High E (Right). Let's assume Low E is index 0.
                # If Input 1 = High E (Right), then index is 5. 
                # Let's flip it: String 6 (Low E) -> Index 0 (Left)
                
                string_idx = 6 - string_num 
                x = string_x_positions[string_idx]
                
                # Calculate Y: Middle of the fret
                y = margin_y + (fret_num * fret_spacing) - (fret_spacing / 2)
                
                painter.drawEllipse(int(x) - 8, int(y) - 8, 16, 16)

        # 6. Draw Chord Name
        painter.setPen(QColor("#00d4ff"))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, self.current_chord)