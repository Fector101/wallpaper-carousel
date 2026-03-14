from kivy.uix.screenmanager import SlideTransition, NoTransition
from kivymd.uix.screenmanager import MDScreenManager

from android_notify import NotificationHandler

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

        if not NotificationHandler.has_permission():
            self.current = "welcome"
        else:
            self.current = "thumbs"
        # self.current = "update_screen"
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

