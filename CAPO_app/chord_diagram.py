from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtCore import Qt

# Dictionary for Standard Open Chords (Beginner)
CHORD_SHAPES_BEGINNER = {
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
    
    # Minors
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
}

# Dictionary for Barre Chords (Advanced)
CHORD_SHAPES_ADVANCED = {
    # Major Chords (E-shape or A-shape)
    "F":  [(6, 1), (5, 3), (4, 3), (3, 2), (2, 1), (1, 1)], 
    "F#": [(6, 2), (5, 4), (4, 4), (3, 3), (2, 2), (1, 2)], 
    "G":  [(6, 3), (5, 5), (4, 5), (3, 4), (2, 3), (1, 3)], 
    "G#": [(6, 4), (5, 6), (4, 6), (3, 5), (2, 4), (1, 4)], 
    "A":  [(6, 5), (5, 7), (4, 7), (3, 6), (2, 5), (1, 5)], 
    "A#": [(6, 6), (5, 8), (4, 8), (3, 7), (2, 6), (1, 6)], 
    "B":  [(5, 2), (4, 4), (3, 4), (2, 4), (1, 2)],         
    "C":  [(5, 3), (4, 5), (3, 5), (2, 5), (1, 3)],         
    "C#": [(5, 4), (4, 6), (3, 6), (2, 6), (1, 4)],         
    "D":  [(5, 5), (4, 7), (3, 7), (2, 7), (1, 5)],         
    "D#": [(5, 6), (4, 8), (3, 8), (2, 8), (1, 6)],         
    "E":  [(5, 7), (4, 9), (3, 9), (2, 9), (1, 7)],         

    # Minor Chords (Em-shape or Am-shape)
    "Fm":  [(6, 1), (5, 3), (4, 3), (3, 1), (2, 1), (1, 1)], 
    "F#m": [(6, 2), (5, 4), (4, 4), (3, 2), (2, 2), (1, 2)], 
    "Gm":  [(6, 3), (5, 5), (4, 5), (3, 3), (2, 3), (1, 3)], 
    "G#m": [(6, 4), (5, 6), (4, 6), (3, 4), (2, 4), (1, 4)], 
    "Am":  [(6, 5), (5, 7), (4, 7), (3, 5), (2, 5), (1, 5)], 
    "A#m": [(6, 6), (5, 8), (4, 8), (3, 6), (2, 6), (1, 6)], 
    "Bm":  [(5, 2), (4, 4), (3, 4), (2, 3), (1, 2)],         
    "Cm":  [(5, 3), (4, 5), (3, 5), (2, 4), (1, 3)],         
    "C#m": [(5, 4), (4, 6), (3, 6), (2, 5), (1, 4)],         
    "Dm":  [(5, 5), (4, 7), (3, 7), (2, 6), (1, 5)],         
    "D#m": [(5, 6), (4, 8), (3, 8), (2, 7), (1, 6)],         
    "Em":  [(5, 7), (4, 9), (3, 9), (2, 8), (1, 7)],         
}

class ChordDiagramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(220, 280) 
        self.current_chord = "" 
        self.mode = "beginner" 

    def set_mode(self, mode):
        self.mode = mode
        self.update() 

    def set_chord(self, chord_name):
        if not chord_name or not chord_name.strip():
            self.current_chord = ""
        else:
            parts = chord_name.split()
            if parts:
                self.current_chord = parts[0]
            else:
                self.current_chord = ""
        self.update() 

    def get_shape(self):
        if not self.current_chord:
            return []
        if self.mode == 'advanced':
            return CHORD_SHAPES_ADVANCED.get(self.current_chord, [])
        else:
            return CHORD_SHAPES_BEGINNER.get(self.current_chord, [])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # --- FIX 1: ADJUSTED MARGINS FOR TEXT SPACE ---
        margin_left = 25   
        margin_right = 60  # Increased to prevent number overlap
        margin_top = 25  
        margin_bottom = 55 
        
        board_w = w - margin_left - margin_right
        board_h = h - margin_top - margin_bottom 
        
        positions = self.get_shape()
        
        base_fret = 1
        if positions:
            frets_used = [p[1] for p in positions if p[1] > 0]
            if frets_used:
                max_fret_in_chord = max(frets_used)
                min_fret_in_chord = min(frets_used)
                if max_fret_in_chord > 5: 
                    base_fret = min_fret_in_chord
        
        num_frets_shown = 6 # Showing 6 frets is standard
        
        # 1. Fretboard Background
        painter.setBrush(QBrush(QColor("#1a100c")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(margin_left - 5, margin_top - 5, board_w + 10, board_h + 10, 5, 5)

        # 2. Nut (The White Line Fix)
        # Only draw the white nut if we are at fret 1 AND in beginner mode.
        # Advanced/Barre chords look better with just fret lines.
        is_beginner_at_start = (base_fret == 1 and self.mode == 'beginner')
        
        if is_beginner_at_start:
            nut_pen = QPen(QColor("#e0e0e0"), 6)
            painter.setPen(nut_pen)
            painter.drawLine(margin_left, margin_top, margin_left + board_w, margin_top)
        else:
            # Draw normal fret line for top
            top_pen = QPen(QColor("#8d6e63"), 2)
            painter.setPen(top_pen)
            painter.drawLine(margin_left, margin_top, margin_left + board_w, margin_top)

        # 3. Frets
        fret_pen = QPen(QColor("#8d6e63"), 2) 
        painter.setPen(fret_pen)
        fret_spacing = board_h / num_frets_shown
        
        for i in range(1, num_frets_shown + 1):
            y = margin_top + (i * fret_spacing)
            painter.drawLine(margin_left, int(y), margin_left + board_w, int(y))

        # 4. Strings
        string_pen = QPen(QColor("#5d4037"), 2)
        painter.setPen(string_pen)
        num_strings = 6
        string_spacing = board_w / (num_strings - 1)
        string_x_pos = []
        
        for i in range(num_strings):
            x = margin_left + (i * string_spacing)
            string_x_pos.append(x)
            painter.drawLine(int(x), margin_top, int(x), margin_top + int(board_h))

        # 5. Fingers
        painter.setBrush(QBrush(QColor("#00E676"))) 
        painter.setPen(Qt.PenStyle.NoPen)
        
        if positions:
            for string_num, fret_num in positions:
                s_idx = 6 - string_num 
                
                if 0 <= s_idx < 6:
                    x = string_x_pos[s_idx]
                    
                    if fret_num == 0:
                        # Open String
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.setPen(QPen(QColor("#00E676"), 2))
                        painter.drawEllipse(int(x) - 6, margin_top - 18, 12, 12)
                        painter.setBrush(QBrush(QColor("#00E676"))) 
                        painter.setPen(Qt.PenStyle.NoPen)
                    else:
                        # Fretted Note
                        rel_fret = fret_num - base_fret + 1
                        if 1 <= rel_fret <= num_frets_shown:
                            y = margin_top + (rel_fret * fret_spacing) - (fret_spacing / 2)
                            painter.drawEllipse(int(x) - 9, int(y) - 9, 18, 18)

        # 6. Fret Label (e.g. "5fr")
        if base_fret > 1:
            painter.setPen(QColor("#8d6e63"))
            font = QFont("Segoe UI", 12, QFont.Weight.Bold)
            painter.setFont(font)
            # Draw well outside the board now that we have margin_right=60
            painter.drawText(margin_left + board_w + 15, margin_top + int(fret_spacing/2) + 5, f"{base_fret}fr")

        # 7. Chord Name
        if self.current_chord:
            painter.setPen(QColor("#e09f53"))
            font = QFont("Segoe UI", 18, QFont.Weight.Bold)
            painter.setFont(font)
            
            text_rect_y = margin_top + board_h + 5
            painter.drawText(0, int(text_rect_y), w, 40, Qt.AlignmentFlag.AlignCenter, self.current_chord)