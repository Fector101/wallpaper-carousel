from kivy.graphics import Color, RoundedRectangle
from kivy.graphics.boxshadow import BoxShadow
from kivy.uix.button import Button
from kivy.metrics import dp

# import os
# from kivy.core.text import LabelBase

# class Font:
#     def __init__(self, name, base_folder):
#         self.base_folder = base_folder
#         self.name = name
#
#     def get_type_path(self, fn_type):
#         """
#         Formats font type path
#         :param fn_type:
#         :return:
#         """
#         return os.path.join(self.base_folder, self.name + '-'+fn_type + '.ttf')
#
# # This work but i like the normal, bold,italic config better title.font_name = "app_src/assets/fonts/Roboto_Mono/RobotoMono-VariableFont_wght.ttf"
# robot_mono = Font(name='RobotoMono',base_folder="app_src/assets/fonts/Roboto_Mono/static")
# LabelBase.register(
#     name="RobotoMono",
#     fn_regular=robot_mono.get_type_path('Regular'),
#     fn_italic=robot_mono.get_type_path('Italic'),
#     fn_bold=robot_mono.get_type_path('Bold'),
# )

#
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
    def __init__(self,bg_color,inset_color, **kwargs):
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        self.font_name = "RobotoMono"
        r = 25

        with self.canvas.before:
            self.bg_color_instr = Color(*bg_color)
            self.rect = RoundedRectangle(radius=[r,r,r,r])

            Color(0,0,0,0.6)#*inset_color)
            # Color(5 / 255, 1 / 255, 1, 1)
            self.bg = BoxShadow(
                offset=[-10, -10],
                inset=True,
                spread_radius=[-15, -15],
                border_radius=[r, r, r, r],
                blur_radius=20 if self.state == "normal" else 50
            )
        self.bind(size=self.update_rect, pos=self.update_rect,state=self.update_rect)

    def update_rect(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.bg.blur_radius = 20 if self.state == "normal" else 50
        self.rect.pos = self.pos
        self.rect.size = self.size





# Give btns better colour
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDFabButton
from kivymd.uix.label import MDIcon
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle

class BottomButtonBar(MDRelativeLayout):
    """Floating bottom bar with two buttons with centered icons only."""

    def __init__(self, on_camera=None, on_settings=None, width=dp(65), height=dp(65), **kwargs):
        super().__init__(**kwargs)
        self.on_camera = on_camera
        self.on_settings = on_settings
        # self.md_bg_color = [1,0,1,1]
        self.button_box = MDBoxLayout(
            orientation="horizontal",
            spacing=0,
            size_hint=(None, None),
            pos_hint={"center_x": 0.5, "y": 0.05},
        )
        # button_box.md_bg_color=[1,.2,0,1]
        # button_box.size = (width * 2, height)

        # Camera button
        self.btn_camera = MDIconButton(
            icon="image-multiple",
            style="tonal",
            on_release=self._camera_pressed,
        )
        size = [dp(80), dp(45)]
        radius = 12
        # self.btn_camera.md_bg_color=[0.2, 0, 1, 1]
        self.btn_camera.size_hint=[None,None]
        self.btn_camera.size=size
        self.btn_camera.radius = [radius, 0, 0, radius]
        # theme_text_color = "Custom",
        # text_color=[1, 1, 1, 1]


        # Settings button
        self.btn_settings = MDIconButton(
            icon="cog",
            style="tonal",
            size_hint=(None, None),
            size=(width, height),
            on_release=self._settings_pressed,
        )
        self.btn_settings.size_hint = [None, None]
        self.btn_settings.size = size
        self.btn_settings.radius = [0, radius, radius, 0]


        # size = 18
        # icon_camera.font_size = sp(size)
        # icon_settings.font_size = sp(size)

        self.button_box.add_widget(self.btn_camera)
        self.button_box.add_widget(self.btn_settings)
        #
        self.button_box.bind(minimum_width=self.button_box.setter("width"))
        self.button_box.bind(minimum_height=self.button_box.setter("height"))

        self.add_widget(self.button_box)

    def hide(self):
        self.button_box.pos_hint = {"center_x": 0.5, "y": -1}

    def show(self):
        self.button_box.pos_hint = {"center_x": 0.5, "y": 0.05}

    def _camera_pressed(self, *args):
        if callable(self.on_camera):
            self.on_camera(*args)

    def _settings_pressed(self, *args):
        if callable(self.on_settings):
            self.on_settings(*args)