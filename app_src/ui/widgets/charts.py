from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty
from kivy.utils import get_color_from_hex
from kivy.uix.widget import Widget


def format_bytes(size):
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{int(round(size / 1024))} KB"
    return f"{size} B"


class HorizontalBarChart(Widget):
    """Canvas-drawn horizontal bar chart.

    data: list of (label, value) tuples. Values are byte counts.
    """

    data = ListProperty([])
    bar_color = ListProperty(get_color_from_hex("98F1DD"))
    track_color = ListProperty(get_color_from_hex("2E2E2E"))
    grid_color = ListProperty(get_color_from_hex("4A4A4A"))
    label_color = ListProperty(get_color_from_hex("FFFFFF"))
    value_color = ListProperty(get_color_from_hex("999898"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._label_textures = {}
        self._value_textures = {}
        self.bind(pos=self._redraw, size=self._redraw, data=self._redraw,
                  bar_color=self._redraw, track_color=self._redraw,
                  grid_color=self._redraw, label_color=self._redraw,
                  value_color=self._redraw)

    def _texture(self, text, color, font_size, cache):
        tex = cache.get(text)
        if tex is None:
            label = CoreLabel(text=text, font_size=font_size, color=color,
                              font_name="RobotoMono", bold=True)
            label.refresh()
            tex = label.texture
            cache[text] = tex
        return tex

    def _redraw(self, *_):
        self.canvas.clear()
        data = self.data or []
        if not data:
            return
        width, height = self.width, self.height
        if width <= 0 or height <= 0:
            return

        label_w = dp(64)
        value_w = dp(58)
        plot_x = self.x + label_w
        plot_w = width - label_w - value_w
        if plot_w <= 0:
            return

        max_value = max(value for _, value in data)
        row_h = height / len(data)
        bar_h = row_h * 0.5

        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            grid_x = plot_x + plot_w * fraction
            with self.canvas:
                Color(*self.grid_color)
                Line(points=[grid_x, self.y, grid_x, self.y + height], width=1)

        for index, (label, value) in enumerate(data):
            row_center = self.y + height - row_h * (index + 0.5)
            bar_y = row_center - bar_h / 2
            fraction = value / max_value if max_value else 0.0
            bar_w = plot_w * fraction

            with self.canvas:
                Color(*self.track_color)
                RoundedRectangle(pos=(plot_x, bar_y), size=(plot_w, bar_h),
                                 radius=[4])
                Color(*self.bar_color)
                RoundedRectangle(pos=(plot_x, bar_y), size=(bar_w, bar_h),
                                 radius=[4])

            label_tex = self._texture(label, self.label_color, sp(13),
                                      self._label_textures)
            with self.canvas:
                Color(1, 1, 1, 1)
                Rectangle(texture=label_tex,
                          pos=(plot_x - label_tex.width - dp(6),
                               row_center - label_tex.height / 2),
                          size=label_tex.size)

            value_text = format_bytes(value)
            value_tex = self._texture(value_text, self.value_color, sp(12),
                                      self._value_textures)
            value_x = min(plot_x + bar_w + dp(8),
                          plot_x + plot_w - value_tex.width)
            with self.canvas:
                Color(1, 1, 1, 1)
                Rectangle(texture=value_tex,
                          pos=(value_x, row_center - value_tex.height / 2),
                          size=value_tex.size)
