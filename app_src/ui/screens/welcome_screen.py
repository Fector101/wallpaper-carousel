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
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel, MDIcon

from ui.widgets.layouts import MyMDScreen

from ui.widgets.buttons import MyRoundButton
from ui.widgets.android import toast
from utils.helper import load_kv_file, appFolder
from kivy.graphics import Color, Line

from utils.model import get_app


load_kv_file(py_file_absolute_path=__file__)

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


class NotificationRequestLayout(MDGridLayout):
    text_color_primary_light = ListProperty([0, 0, 0, 1])
    text_color_primary_dark = get_color_from_hex("#FFFFFF")
    text_color_secondary_light = ListProperty([88 / 255, 85 / 255, 85 / 255, 1])
    text_color_secondary_dark = get_color_from_hex("#F2F2F2")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()

    def enable_notifications(self, *_):
        print("Enable notifications pressed")

        def change_screen(_):
            try:
                self.app.sm.current = "thumbs"
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
        self.app.sm.current = "thumbs"
        print("Skip feature pressed")


class WelcomeScreen(MyMDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name = "welcome"
        self.add_widget(NotificationRequestLayout())
