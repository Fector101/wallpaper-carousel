import os
import traceback

from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.image import Image
from kivy.utils import get_color_from_hex

from android_notify import NotificationHandler
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.properties import ListProperty, BooleanProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.screen import MDScreen

from ui.widgets.buttons import MyRoundButton
from ui.widgets.android import toast, ThemedWidget
from utils.helper import load_kv_file, appFolder
from kivy.graphics import Color, Line

# load_kv_file(module_name=__name__)
load_kv_file(py_file_absolute_path=__file__)
#

from kivy.lang import Builder


# kv_file_path = os.path.join(appFolder(), "ui","screens", "welcome_screen.kv")
# # with open(kv_file_path, encoding="utf-8") as kv_file:
# Builder.unload_file(kv_file_path)
# Builder.load_file(kv_file_path)
# Builder.load_string(kv_file.read(), filename="welcome_screen.kv")

class RotatedLayout(MDFloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(
                angle=0,
                origin=self.center
            )

        with self.canvas.after:
            PopMatrix()

        # keep rotation centered
        self.bind(pos=self.update_origin, size=self.update_origin)

        self.rotate()
        # animate rotation
        # Clock.schedule_interval(self.rotate, 1 / 60)

    def update_origin(self, *args):
        self.rot.origin = self.center

    def rotate(self, dt=None):
        self.rot.angle = -19


class Row(MDBoxLayout):
    my_widgets = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for each_widget in self.my_widgets:
            self.add_widget(each_widget)


class Column(MDBoxLayout):
    my_widgets = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        for each_widget in self.my_widgets:
            self.add_widget(each_widget)



class MyLabel(MDLabel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    #     Clock.schedule_interval(self.omo,1)
    # def omo(self,dt):
    #     self.theme_font_name= "Custom"
    #     self.theme_font_size= "Custom"
    #     self.theme_bg_color= "Custom"
    #     self.font_name= "RobotoMono"
    #     # self.adaptive_size= True
    #     self.md_bg_color= [1, 0, 0, 1]
    #     self.bg_color= [1, 0, 0, 1]

class BorderMDBoxLayout(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.after:
            c = 1
            self.bg_color_instr = Color(c, 0, c, .8)
            self.border = Line(width=1, rounded_rectangle=self.round_rect_args)
        self.bind(pos=self.update_border, size=self.update_border)

    @property
    def round_rect_args(self):
        return self.x, self.y, self.width, self.height, self.radius[0]

    def update_border(self, *_):
        self.border.rounded_rectangle = self.round_rect_args  # (self.x,self.y,self.width,self.height,16)


class NotificationRequestLayout(MDGridLayout,ThemedWidget):
    text_color_primary_light = ListProperty([0, 0, 0, 1])
    text_color_primary_dark = get_color_from_hex("#FFFFFF")
    text_color_secondary_light = ListProperty([88 / 255, 85 / 255, 85 / 255, 1])
    text_color_secondary_dark = get_color_from_hex("#F2F2F2")

    is_device_theme_light=BooleanProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.rows = 4
        # self.md_bg_color = [.9, .9, .9, 1]
        # p = 25
        # self.padding = [dp(p), dp(60), dp(p), dp(20)]
        # self.spacing = dp(50)
        #
        # header_layout = MDBoxLayout(orientation="vertical", adaptive_height=1)
        # # header_layout.md_bg_color = [1,.3,0,1]
        # title = MDLabel(
        #     text="Turn On\nNotifications?",
        #     bold=True,
        # )
        #
        # # title._md_bg_color=[1,1,0,1]
        # title.font_size = sp(36)
        # title.font_name = "RobotoMono"
        # title.adaptive_height = 1
        #
        # body = MDLabel(
        #     text=(
        #         "To keep Carousel running in the\n"
        #         "background, Android requires a\n"
        #         "foreground notification"
        #     ),
        # )
        # body.font_size = sp(14)
        # body.font_name = "RobotoMono"
        # body.adaptive_height = 1
        # # header_layout.md_bg_color=[1,.6,0,1]
        # header_layout.add_widget(title)
        # header_layout.add_widget(body)
        #
        # bell_layout = Column(
        #     adaptive_height=1,
        #
        # )
        # bell_layout.spacing = dp(10)
        # bell_layout.padding = dp(10)
        # bell_layout.md_bg_color = [183 / 255, 212 / 255, 227 / 255, 1]
        # bell_layout.radius = [dp(8)]
        #
        # size = 100
        # bell_image_layout = RotatedLayout()
        # bell_image_layout.pos_hint = {"center_x": .9}
        # # bell_image_layout.adaptive_size=1
        # bell_image_layout.md_bg_color = [1, 0, 1, 1]
        #
        # bell = Image(
        #     # source="ui/screens/group.png",
        #     source="assets/icons/bell.png",
        #     # size_hint=(1,1),
        #     size_hint=(None, None),
        #     size=(dp(size), dp(size)),
        #     # allow_stretch=False,
        #     # keep_ratio=False,
        # )
        # # bell.
        # bell.pos_hint = {'center_x': .5, 'center_y': .5}
        # bell_image_layout.add_widget(bell)
        # bell_layout.add_widget(bell_image_layout)
        #
        # bell_layout.add_widget(
        #     MDLabel(
        #         text="Additional Features",
        #         bold=True,
        #         theme_font_name="Custom",
        #         font_name="RobotoMono",
        #         adaptive_size=1,
        #     )
        # )
        #
        # bell_layout.add_widget(
        #     MDLabel(
        #         text="See what’s coming and skip images without opening app",
        #         # bold=True,
        #         font_size=sp(14),
        #         theme_font_size="Custom",
        #         theme_font_name="Custom",
        #         font_name="RobotoMono",
        #         adaptive_height=1,
        #         size_hint_x=1
        #     )
        # )
        # p = 10
        # notify_card = MDBoxLayout(
        #     md_bg_color=[1, 1, 1, 1],
        #     radius=[dp(20)],
        #     spacing=dp(10),
        #     padding=[dp(p), dp(p), dp(p), dp(p)],
        #     size_hint_x=1,
        #     adaptive_height=1,
        # )
        # s = 40
        # blue_circle = MDBoxLayout(
        #     pos_hint={'top': 1},
        #     radius=[50],
        #     size_hint=[None, None],
        #     md_bg_color=[116 / 255, 155 / 255, 215 / 255, 1],
        #     size=[s, s],
        # )
        #
        # second_section = Column(
        #     adaptive_size=1,
        #     # md_bg_color=[0, 0, 0, 1],
        #     pos_hint={'top': 1},
        #     size_hint_x=1,
        #     spacing=dp(10),
        #     my_widgets=[
        #         Row(
        #             my_widgets=[
        #                 MDLabel(
        #                     text="Waller",
        #                     theme_text_color="Custom",
        #                     text_color=[88 / 255, 85 / 255, 85 / 255, 1],
        #                     adaptive_size=1,
        #                     theme_font_name="Custom",
        #                     font_name="RobotoMono",
        #                     theme_font_size="Custom",
        #                     font_size=sp(14)
        #                 ),
        #                 MDIcon(
        #                     icon='checkbox-blank-circle',
        #                     theme_text_color="Custom",
        #                     text_color=[88 / 255, 85 / 255, 85 / 255, 1],
        #                     adaptive_size=1,
        #                     pos_hint={'center_y': .5},
        #                     theme_font_size="Custom",
        #                     font_size=sp(6)
        #                 ),
        #                 MDLabel(
        #                     text="20",
        #                     theme_text_color="Custom",
        #                     text_color=[88 / 255, 85 / 255, 85 / 255, 1],
        #                     adaptive_size=1,
        #                     theme_font_name="Custom",
        #                     font_name="RobotoMono",
        #                     theme_font_size="Custom",
        #                     font_size=sp(14)
        #                 )
        #             ],
        #             # md_bg_color=[1,1, 0.255, 1],
        #             spacing=dp(5),
        #             adaptive_size=1,
        #         ),
        #         MDLabel(
        #             text="Next in 1:26",
        #             theme_font_name="Custom",
        #             font_name="RobotoMono",
        #             theme_text_color="Custom",
        #             # text_color=[88 / 255, 85 / 255, 85 / 255, 1],
        #             adaptive_size=1,
        #             theme_font_size="Custom",
        #             font_size=sp(14)
        #         ),
        #         MDLabel(
        #             text="Skip",
        #             theme_text_color="Custom",
        #             text_color=[46 / 255, 95 / 255, 169 / 255, 1],
        #             adaptive_size=1,
        #             theme_bg_color="Custom",
        #             md_bg_color=[234 / 255, 233 / 255, 233 / 255, 1],
        #             padding=[dp(6), dp(4)],
        #             radius=[dp(4)],
        #             theme_font_name="Custom",
        #             font_name="RobotoMono",
        #             theme_font_size="Custom",
        #             font_size=sp(14)
        #         )
        #     ]
        # )
        #
        #
        #
        # t = 60
        # notify_card.add_widget(blue_circle)
        # notify_card.add_widget(second_section)
        # image_con = MDBoxLayout(pos_hint={'top': .95},adaptive_size = 1,md_bg_color = [161 / 255, 163 / 255, 172 / 255, 1])
        #
        # r = 5
        # image_con.radius = [dp(r)]
        # image_con.add_widget(FitImage(
        #     source="assets/icons/mountain.png",
        #     size_hint=(None, None),
        #     size=(dp(t), dp(t)),
        #     radius=[dp(r)]
        # ))
        # notify_card.add_widget(
        #     image_con
        # )
        #
        #
        # my_icon_box = MDBoxLayout(md_bg_color=(226 / 255, 223 / 255, 223 / 255, 1),
        #                           adaptive_size=1, pos_hint={'top': 1})
        # print(my_icon_box.height, "my_icon_box.height")
        # my_icon_box.radius = [dp(50)]
        # drop_down_icon = MDIcon(
        #     icon='chevron-up',
        #     theme_text_color="Custom",
        #     text_color='black',
        #     pos_hint={'top': 1, 'right': 1},
        # )
        # my_icon_box.add_widget(drop_down_icon)
        # notify_card.add_widget(my_icon_box)
        #
        # bell_layout.add_widget(notify_card)
        #
        # btns_layout = Column(
        #     my_widgets=[
        #         MyRoundButton(
        #             text="Enable notifications",
        #             bg_color=(55 / 255, 151 / 255, 252 / 255, 1),
        #             size_hint_y=None,
        #             height=dp(48),
        #             font_size=sp(16),
        #             on_release=self.enable_notifications,
        #         ),
        #         MyRoundButton(
        #             text="Skip Feature",
        #             bg_color=(243 / 255, 170 / 255, 170 / 255, 1),
        #             color=(0, 0, 0, 1),
        #             size_hint=[None, None],
        #             height=dp(44),
        #             width=sp(248),
        #             font_size=dp(14),
        #             pos_hint={'center_x': .5},
        #             on_release=self.skip_feature,
        #         )
        #     ]
        #     , spacing=dp(10)
        # )
        #
        # self.add_widget(header_layout)
        # self.add_widget(bell_layout)
        # self.add_widget(btns_layout)
        #



        # self.rows=4
        # self.size_hint=[None,None]
        # self.size=[Window.width-100,Window.height-10]
        # pass

        # self.lightMode()

    def darkMode(self):
        self.is_device_theme_light=False

    def lightMode(self):
        self.is_device_theme_light=True

    def enable_notifications(self, *_):
        print("Enable notifications pressed")

        def change_screen(_):
            try:
                self.parent.manager.current = "thumbs"
            except Exception as e:
                print(e)
                traceback.print_exc()

        def callback_func(state):
            Clock.schedule_once(change_screen)
            if state:
                toast("Notifications enabled")
            else:
                toast("Notifications disabled")

        try:
            NotificationHandler.asks_permission(callback_func)
        except Exception as error_asking_permission:
            print("error_asking_permission", error_asking_permission)
            traceback.print_exc()

    def skip_feature(self, *_):
        self.parent.manager.current = "thumbs"
        print("Skip feature pressed")


class WelcomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "welcome"
        self.add_widget(NotificationRequestLayout())
