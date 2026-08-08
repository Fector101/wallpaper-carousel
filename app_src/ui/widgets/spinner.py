from kivy.clock import Clock
from kivy.graphics import Color, Line, Rotate
from kivy.uix.widget import Widget

from utils.constants import theme_colors


class SpinningArcWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set a fixed size for the spinner widget
        self.size = (100, 100)
        # Draw spinner on the canvas
        with self.canvas:
            # Create a rotation instruction; note the origin will be updated as the widget size changes
            self.rotation = Rotate(angle=0, origin=self.center)
            # Set a visible color; here white is typical for many spinners, but you can adjust as needed.
            Color(*theme_colors.PRIMARY)
            # Draw an arc: (center_x, center_y, radius, start_angle, end_angle)
            # A partial circle (e.g. 270°) gives a "spinner" look.
            self.arc = Line(circle=(self.center_x, self.center_y, 40, 0, 270), width=4)
        # Ensure that the rotation origin updates when the widget is resized or repositioned.
        self.bind(pos=self._update_origin, size=self._update_origin)
        # Schedule an update at roughly 60 frames per second.
        Clock.schedule_interval(self.update_arc, 0.016)

    def _update_origin(self, *args):
        # Update the rotation's origin to keep it centered
        self.rotation.origin = self.center
        self.arc.circle = (self.center_x, self.center_y, 40, 0, 270)

    def update_arc(self, dt):
        # Increase the rotation angle to create the spinning effect.
        self.rotation.angle += 5
