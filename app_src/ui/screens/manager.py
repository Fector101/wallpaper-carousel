import traceback

from android_notify.internal.java_classes import autoclass

from android_notify.config import get_python_activity_context, on_android_platform
from kivy.uix.screenmanager import SlideTransition, NoTransition
from kivymd.uix.screenmanager import MDScreenManager

from android_notify import NotificationHandler
from ui.widgets.layouts import MyMDScreen
from utils.android import DisplayListener
from utils.logger import app_logger

from utils.model import get_app
from ui.screens.gallery_screen import GalleryScreen
from ui.screens.settings_screen import SettingsScreen
from ui.screens.full_screen import FullscreenScreen
from ui.screens.welcome_screen import WelcomeScreen
from ui.screens.logs_screen import LogsScreen
from ui.screens.download_apk_screen import DownloadApkScreen



class ScreenManager(MDScreenManager):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.welcome_screen = WelcomeScreen()
        self.gallery_screen = GalleryScreen()
        self.full_screen = FullscreenScreen()
        self.settings_screen = SettingsScreen()
        self.log_screen = LogsScreen()
        self.download_apk_screen = DownloadApkScreen()

        self.add_widget(self.gallery_screen)
        self.add_widget(self.full_screen)
        self.add_widget(self.settings_screen)
        self.add_widget(self.welcome_screen)
        self.add_widget(self.log_screen)
        self.add_widget(self.download_apk_screen)
        self.__register_rotate_listener()
        # self.__run_rotate_method_for_each_screen("BOTTOM")

        if not NotificationHandler.has_permission():
            self.current = "welcome"
        else:
            self.current = "thumbs"
        # self.current = "update_screen"
    def __register_rotate_listener(self):
        if on_android_platform():
            try:
                Context = autoclass('android.content.Context')
                activity = get_python_activity_context()
                self.dm = activity.getSystemService(Context.DISPLAY_SERVICE)

                # Register listener
                self.listener = DisplayListener(self.on_rotation)
                self.dm.registerDisplayListener(self.listener, None)

                # self.listener = DisplayListener(self.run_rotate_method_for_each_screen)
                # self.activity = get_python_activity_context()
                # self.activity.registerComponentCallbacks(self.listener)
            except Exception as error_registering_rotate_listener:
                print(error_registering_rotate_listener)
                traceback.print_exc()

    def on_current(self,*args):
        screen_name = args[1]
        is_fullscreen = screen_name in ["welcome","fullscreen","logs","update_screen"]
        if is_fullscreen and self.app.bottom_bar:
            self.app.bottom_bar.hide()
        elif self.app.bottom_bar:
            self.app.bottom_bar.show()
        super().on_current(instance=args[0],value=args[1])

    def go_to_settings(self, _=None):
        self.transition = SlideTransition(direction="left")
        self.current = "settings"

    def go_to_thumbs(self, _=None):
        self.transition = SlideTransition(direction="right")
        self.current = "thumbs"

    def open_image_in_full_screen(self, index):
        self.transition = NoTransition()
        self.current = "fullscreen"
        self.full_screen.update_images(index)
        self.full_screen.carousel.index = index

    def on_rotation(self, rotation):
        rotation=self.__get_rotation_name(rotation)
        for each_screen in self.screens:
            if isinstance(each_screen,MyMDScreen):
                try:
                    status_bar_height=each_screen.status_bar_height
                    nav_bar_height=each_screen.nav_bar_height
                    if rotation == "RIGHT":
                        each_screen.set_widget_left_and_right_padding(status_bar_height,nav_bar_height)
                    elif rotation == "LEFT":
                        each_screen.set_widget_left_and_right_padding(nav_bar_height, status_bar_height)
                    elif rotation in ["TOP", "BOTTOM"]:
                        each_screen.set_widget_left_and_right_padding(0,0)
                    each_screen.adjust_padding(rotation)
                except Exception as e:
                    print(e)
            else:
                app_logger.error("Impossible stuff")

    @staticmethod
    def __get_rotation_name(rotation):
        Surface = autoclass('android.view.Surface')

        if rotation == Surface.ROTATION_0:
            text = "TOP"
        elif rotation == Surface.ROTATION_90:
            text = "RIGHT"
        elif rotation == Surface.ROTATION_180:
            text = "BOTTOM"
        elif rotation == Surface.ROTATION_270:
            text = "LEFT"
        else:
            text = "UNKNOWN"
        return text