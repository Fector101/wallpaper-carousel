from kaki.app import App
from kivy.factory import Factory
from kivymd.app import MDApp
# from app_src.main import WallpaperCarouselApp


class MDLive(App,MDApp):
    CLASSES = {
        # "MDScreenManager":"app_src.main",
        "SettingsScreen":"app_src.ui.screens.settings_screen",
        "GalleryScreen":"app_src.ui.screens.gallery_screen",
        # "NotificationScreen": "app_src.important",
        # "NotificationScreen": "app_src.ui.screens.welcome_screen",
        # "MyRoundButton": "app_src.ui.widgets.buttons",
        "BottomButtonBar": "app_src.ui.widgets.buttons",
    }
    AUTORELOADER_PATHS = [
        ("./app_src", {"recursive": True})
    ]

    def build_app(self, *args):
        print("Inside Build App Auto Reload")
        return Factory.GalleryScreen()

MDLive().run()