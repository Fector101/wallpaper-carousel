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
        r = 10

        with self.canvas.before:
            self.bg_color_instr = Color(*bg_color)
            self.rect = RoundedRectangle(radius=[dp(r)])

            Color(*inset_color)
            # Color(5 / 255, 1 / 255, 1, 1)
            self.bg = BoxShadow(
                offset=[0, -10],
                inset=True,
                spread_radius=[-20, -20],
                border_radius=[r, r, r, r],
                blur_radius=80 if self.state == "normal" else 20
            )
        self.bind(size=self.update_rect, pos=self.update_rect,state=self.update_rect)
        # Clock.schedule_once(self.update_bg_enable_btn)

    def update_rect(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.bg.blur_radius = 80 if self.state == "normal" else 50
        self.rect.pos = self.pos
        self.rect.size = self.size