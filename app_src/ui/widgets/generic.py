from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex


class LineDivider(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.graphics import Color, Line
        self.size_hint_y = None
        self.height = 2  # Set line thickness space area

        with self.canvas:
            Color(*get_color_from_hex("#5E5E5E"))
            self.line = Line(points=[], width=0.5)

        # Bind it to its own size/position changes
        self.bind(pos=self.update_line, size=self.update_line)

    def update_line(self, *_):
        # Keeps the line perfectly straight along its own layout position
        self.line.points = [self.x, self.y, self.x + self.width, self.y]
