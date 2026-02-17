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

from ui.widgets.layouts import get_dimensions
from utils.model import get_app
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
        self.app = get_app()

        self.old_setting_btn_color = None
        self.old_gallery_btn_color = None

        self.on_camera = on_camera
        self.on_settings = on_settings
        self.size_hint = (1, None)
        android_nav_bar_height = get_dimensions()[1]
        self.height = dp(android_nav_bar_height * 2) or dp(140)
        # self.md_bg_color = [1,1,0,1]


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

        self.app.bind(device_theme=self.changeBottomBtnsTheme)
        self.changeBottomBtnsTheme(None, self.app.device_theme)
        # self.color_tab_buttons("thumbs")

    def changeBottomBtnsTheme(self,app,theme):
        if hasattr(self.app,"sm") and self.app.sm:
            self.color_tab_buttons(screen=self.app.sm.current)
        else:
            self.color_tab_buttons(screen="thumbs")

        c = 55
        a = 52
        dark_theme_bg = [a/255, c/255, c/255, 1]# get_color_from_hex("#1A1B1B")
        light_theme_bg = [1,1,1, 1]
        self.btn_camera.md_bg_color = light_theme_bg if theme == "light" else dark_theme_bg
        self.btn_settings.md_bg_color = light_theme_bg if theme == "light" else dark_theme_bg
        self.button_box.md_bg_color = self.btn_camera.md_bg_color


    def hide(self):
        self.button_box.pos_hint = {"center_x": 0.5, "y": -1}


    def show(self):
        self.button_box.pos_hint = {"center_x": 0.5, "center_y": 0.5}



    def _camera_pressed(self, *args):
        if callable(self.on_camera):
            self.on_camera(*args)

    def _settings_pressed(self, *args):
        if callable(self.on_settings):
            self.on_settings(*args)
    def bind_change(self):
        self.app.sm.bind(current=self.color_tab_buttons)
        self.color_tab_buttons(screen=self.app.sm.current)
    def color_tab_buttons(self, screen_manager=None, screen=None):
        theme = self.app.monitor_dark_and_light_device_change()

        # print(theme,screen,'fff')

        if screen == "settings":
            self.btn_settings.text_color = [0,0,0,1] if theme == "light" else [1,1,1,1]
            self.btn_camera.text_color = [.4,.4,.4,1]
        elif screen == "thumbs":
            self.btn_camera.text_color = [0,0,0,1] if theme == "light" else [1,1,1,1]
            self.btn_settings.text_color = [.4,.4,.4,1]
