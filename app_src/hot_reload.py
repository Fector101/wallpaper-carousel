import os
from kaki.app import App
from kivy.factory import Factory
from kivymd.app import MDApp
# from main import WallpaperCarouselApp
from kivy.core.window import Window

from kivy import Config
from kivy.core.text import LabelBase

#Linux has some weirdness with the touchpad by default... remove it
options = Config.options('input')
for option in options:
    if Config.get('input', option) == 'probesysfs':
        Config.remove_option('input', option)
Window.size = (370, 700)



class Font:
    def __init__(self, name, base_folder):
        self.base_folder = base_folder
        self.name = name

    def get_type_path(self, fn_type):
        """
        Formats font type path
        :param fn_type:
        :return:
        """
        return os.path.join(self.base_folder, self.name + '-' + fn_type + '.ttf')


robot_mono = Font(name='RobotoMono', base_folder="assets/fonts/Roboto_Mono/static")
LabelBase.register(
    name="RobotoMono",
    fn_regular=robot_mono.get_type_path('Regular'),
    fn_italic=robot_mono.get_type_path('Italic'),
    fn_bold=robot_mono.get_type_path('Bold'),
)


class MDLive(App,MDApp):
    CLASSES = {
        # "MDScreenManager":"main",
        "SettingsScreen":"ui.screens.settings_screen",
        "HomeScreenWidgetControllerUI":"ui.screens.settings_screen",
        # "LogsScreen":"ui.screens.logs_screen",
        # "FullscreenScreen":"ui.screens.full_screen",
        # "GalleryScreen":"ui.screens.gallery_screen",
        # "NotificationScreen": "important",
        # "NotificationScreen": "ui.screens.welcome_screen",
        # "MyRoundButton": "ui.widgets.buttons",
        # "BottomButtonBar": "ui.widgets.buttons",
    }
    AUTORELOADER_PATHS = [
        ("./ui", {"recursive": True})
    ]

    def build_app(self, *args):
        print("Inside Build App Auto Reload")
        return Factory.SettingsScreen()

MDLive().run()