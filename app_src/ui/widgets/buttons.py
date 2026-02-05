from kivy.graphics.boxshadow import BoxShadow
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.properties import ListProperty
from kivy.uix.button import Button
from kivymd.app import MDApp
from kivy.utils import get_color_from_hex

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
    bg_color = ListProperty()
    bg_color_instr = None
    bg_color_instr1 = None
    back_layer_bg_color = ListProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        self.font_name = "RobotoMono"
        r = 25

        with self.canvas.before:
            # print("self.back_layer_bg_color",self.back_layer_bg_color)
            self.bg_color_instr1 = Color(*self.back_layer_bg_color)
            self.rect1 = RoundedRectangle(radius=[r, r, r, r])

            self.bg_color_instr = Color(*self.bg_color)
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

        # Clock.schedule_interval(self.peek,2)
    def on_back_layer_bg_color(self, widget, color_value):
        if self.bg_color_instr1 and hasattr(self.bg_color_instr1, "rgba"):
            self.bg_color_instr1.rgba = color_value
    def on_bg_color(self,widget, color_value):
        # .kv file patch
        if self.bg_color_instr and hasattr(self.bg_color_instr, "rgba"):
            self.bg_color_instr.rgba = color_value
    def update_rect(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.bg.blur_radius = 20 if self.state == "normal" else 50
        self.rect.pos = self.pos
        self.rect.size = self.size

        self.rect1.pos = self.pos
        self.rect1.size = self.size




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
            theme_text_color="Custom",
            theme_bg_color="Custom",
            on_release=self._camera_pressed,
        )
        self.btn_camera.size_hint = [None, None]
        self.btn_camera.size = size
        self.btn_camera.radius = [radius, 0, 0, radius]

        self.btn_settings = MDIconButton(
            icon="cog",
            style="tonal",
            theme_text_color="Custom",
            theme_bg_color="Custom",
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

        app = MDApp.get_running_app()
        app.bind(device_theme=self.changeBottomBtnsTheme)
        self.changeBottomBtnsTheme(None, app.device_theme)

    def changeBottomBtnsTheme(self,app,theme):
        w=.3
        dark_icon_color  = [w,w,.4,1]
        secondary_color  = [0.7,0.7, 0.7, 1]
        self.btn_camera.text_color = secondary_color if theme == "light" else dark_icon_color
        self.btn_settings.text_color = secondary_color if theme == "light" else dark_icon_color

        c = [1,1,1, 1]
        self.btn_camera.md_bg_color = get_color_from_hex("#1A1B1B") if theme == "light" else c
        self.btn_settings.md_bg_color = get_color_from_hex("#1A1B1B") if theme == "light" else c
        self.button_box.md_bg_color = self.btn_camera.md_bg_color
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

