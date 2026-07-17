import os
import traceback

from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.image import Image
from kivy.utils import get_color_from_hex

from android_notify import NotificationHandler
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.properties import ListProperty, BooleanProperty, ObjectProperty
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel, MDIcon

from ui.widgets.layouts import MyMDScreen,GenericStatusBarSpacer

from ui.widgets.buttons import MyRoundButton
from ui.widgets.android import toast
from utils.helper import load_kv_file, appFolder

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


class NotificationRequestLayout(MDGridLayout):
    text_color_primary_light = ListProperty([0, 0, 0, 1])
    text_color_primary_dark = get_color_from_hex("#FFFFFF")
    text_color_secondary_light = ListProperty([88 / 255, 85 / 255, 85 / 255, 1])
    text_color_secondary_dark = get_color_from_hex("#F2F2F2")
    answer_callback = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()

    def enable_notifications(self, *_):
        print("Enable notifications pressed")

        def callback_func(state):
            Clock.schedule_once(self.answer_callback)
            toast(f"Notifications {'enabled' if state else 'disabled'}")

        try:
            NotificationHandler.asks_permission(callback_func)
        except Exception as error_asking_permission:
            print("error_asking_permission", error_asking_permission)
            traceback.print_exc()

    def skip_feature(self, *_):
        self.answer_callback()
        print("Skip feature pressed")


class WelcomeScreen(MyMDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()

        self.name = "welcome"
        self.generic_status_bar_spacer = GenericStatusBarSpacer(
            status_bar_height=self.status_bar_height,
        md_bg_color=[0.8, 0.8, 0.8, 1] if self.app.device_theme == "light" else[.1, .1, .1, 1]
        )
        self.add_widget(self.generic_status_bar_spacer)
        self.add_widget(NotificationRequestLayout(answer_callback=self.handle_going_back))

    def handle_going_back(self, *_):
        self.app.sm.current = "thumbs"
        self.app.bottom_bar.show(hidden_by="notify_permission")