from kivy.graphics.boxshadow import BoxShadow
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.button import Button

from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton

# class RoundedButton(Button):
#     def __init__(self, bg_color, **kwargs):
#         super().__init__(**kwargs)
#
#         # Disable default button background
#         self.background_normal = ""
#         self.background_down = ""
#         self.background_color = (0, 0, 0, 0)
#
#         with self.canvas.before:
#             self.bg_color_instr = Color(*bg_color)
#             self.rect = RoundedRectangle(radius=[dp(14)])
#
#         self.bind(pos=self.update_rect, size=self.update_rect)
#
#     def update_rect(self, *args):
#         self.rect.pos = self.pos
#         self.rect.size = self.size


class MyRoundButton(Button):    # (RoundedButton):
    def __init__(self,bg_color, **kwargs):
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        self.font_name = "RobotoMono"
        r = 25

        with self.canvas.before:
            self.bg_color_instr = Color(*bg_color)
            self.rect = RoundedRectangle(radius=[r,r,r,r])

            Color(0,0,0,0.6)
            # Color(5 / 255, 1 / 255, 1, 1)
            self.bg = BoxShadow(
                offset=[-10, -10],
                inset=True,
                spread_radius=[-15, -15],
                border_radius=[r, r, r, r],
                blur_radius=20 if self.state == "normal" else 50
            )
        self.bind(size=self.update_rect, pos=self.update_rect,state=self.update_rect)

    def update_rect(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.bg.blur_radius = 20 if self.state == "normal" else 50
        self.rect.pos = self.pos
        self.rect.size = self.size



class BottomButtonBar(MDRelativeLayout):
    """Floating bottom bar with two buttons with centered icons only."""

    def __init__(self, on_camera=None, on_settings=None, **kwargs):
        super().__init__(**kwargs)

        self.on_camera = on_camera
        self.on_settings = on_settings
        self.size_hint = (1, None)
        self.height = dp(140)

        with self.canvas.before:
            self._gradient_rects = []
            steps = 30  # smoother gradient
            self._gradient_colors = []

            for i in range(steps):
                alpha = 1 - (i / steps)
                c = Color(0.1, 0.1, 0.1, alpha)
                rect = Rectangle()
                self._gradient_rects.append(rect)
                self._gradient_colors.append(c)

        self.bind(pos=self._update_gradient, size=self._update_gradient)

        # Button container
        radius = dp(12)
        self.button_box = MDBoxLayout(
            orientation="horizontal",
            spacing=0,
            size_hint=(None, None),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            md_bg_color=[1,1,1,1],
            radius=radius,
        )

        size = [dp(80), dp(45)]

        self.btn_camera = MDIconButton(
            icon="image-multiple",
            style="tonal",
            on_release=self._camera_pressed,
        )
        self.btn_camera.size_hint = [None, None]
        self.btn_camera.size = size
        self.btn_camera.radius = [radius, 0, 0, radius]

        self.btn_settings = MDIconButton(
            icon="cog",
            style="tonal",
            on_release=self._settings_pressed,
        )
        self.btn_settings.size_hint = [None, None]
        self.btn_settings.size = size
        self.btn_settings.radius = [0, radius, radius, 0]

        self.button_box.add_widget(self.btn_camera)
        self.button_box.add_widget(self.btn_settings)

        self.button_box.adaptive_size=True
        # self.button_box.bind(minimum_width=self.button_box.setter("width"))
        # self.button_box.bind(minimum_height=self.button_box.setter("height"))

        self.add_widget(self.button_box)

    def _update_gradient(self, *_):
        step_height = self.height / len(self._gradient_rects)

        for i, rect in enumerate(self._gradient_rects):
            rect.pos = (self.x, self.y + i * step_height)
            rect.size = (self.width, step_height)

    def hide(self):
        self.button_box.pos_hint = {"center_x": 0.5, "y": -1}
        for c in self._gradient_colors:
            c.a = 0

    def show(self):
        self.button_box.pos_hint = {"center_x": 0.5, "center_y": 0.5}

        steps = len(self._gradient_colors)
        for i, c in enumerate(self._gradient_colors):
            c.a = 1 - (i / steps)

    def _camera_pressed(self, *args):
        if callable(self.on_camera):
            self.on_camera(*args)

    def _settings_pressed(self, *args):
        if callable(self.on_settings):
            self.on_settings(*args)
