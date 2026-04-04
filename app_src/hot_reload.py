import os
from kaki.app import App
from kivy.factory import Factory
from kivymd.app import MDApp
# from main import WallpaperCarouselApp
from kivy.core.window import Window
from kivy.properties import BooleanProperty, StringProperty

from kivy import Config
from kivy.core.text import LabelBase
from kivy.clock import Clock
from utils.android import is_device_on_light_mode

#Linux has some weirdness with the touchpad by default... remove it
options = Config.options('input')
for option in options:
    if Config.get('input', option) == 'probesysfs':
        Config.remove_option('input', option)
Window.size = (390, 740)



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
    device_theme = StringProperty("dark")
    theme_widgets = []
    KV_FILES=[
        "ui.screens.welcome_screen".replace(".","/") + ".kv",
        "ui.screens.gallery_screen".replace(".","/") + ".kv",
        "ui.screens.settings_screen".replace(".","/") + ".kv",
        "ui.widgets.modals".replace(".","/") + ".kv",

    ]
    CLASSES = {
        # "MDScreenManager":"main",
        "SettingsScreen":"ui.screens.settings_screen",
        "DownloadApkScreen":"ui.screens.download_apk_screen",
        "HomeScreenWidgetControllerUI":"ui.screens.settings_screen",
        "LogsScreen":"ui.screens.logs_screen",
        "FullscreenScreen":"ui.screens.full_screen",
        "GalleryScreen":"ui.screens.gallery_screen",
        "MyBtmSheet":"ui.screens.gallery_screen",
        # "NotificationScreen": "important",
        "WelcomeScreen": "ui.screens.welcome_screen",
        # "MyRoundButton": "ui.widgets.buttons",
        "BottomNavigationBar": "ui.widgets.buttons",
        "LoadingLayout": "ui.widgets.layouts",
    }
    AUTORELOADER_PATHS = [
        ("./ui", {"recursive": True})
    ]

    def build_app(self, *args):
        # return Factory.MyPopUp()
        return Factory.GalleryScreen()

    def on_start(self):
        # self.theme_cls.theme_style = "Light"
        # self.theme_cls.primary_palette = "Blue"
        # Clock.schedule_interval(lambda dt: self.monitor_dark_and_light_device_change(), 1)
        pass

    def monitor_dark_and_light_device_change(self):
        on_light_mode = False #is_device_on_light_mode()
        if on_light_mode:
            for each_widget in self.theme_widgets:
                each_widget.lightMode()
        else:
            for each_widget in self.theme_widgets:
                each_widget.lightDark()

MDLive().run()

