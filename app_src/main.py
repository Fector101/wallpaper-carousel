import time, os
import traceback

from kivy.uix.screenmanager import NoTransition
from kivymd.app import MDApp
from kivy.uix.image import AsyncImage
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty
from kivy.uix.behaviors import ButtonBehavior

from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from android_notify import NotificationHandler

try:
    from kivymd.toast import toast
except TypeError:
    def toast(*args):
        print('Fallback toast:', args)

from utils.helper import Service, start_logging
from ui.screens.gallery_screen import GalleryScreen
from ui.screens.settings_screen import SettingsScreen
from ui.screens.full_screen import FullscreenScreen
from ui.screens.welcome_screen import WelcomeScreen
from kivy.core.window import Window
from kivy.utils import platform

try:
    from utils.permissions import PermissionHandler
    PermissionHandler().requestStorageAccess()
except Exception as e:
    traceback.print_exc()


if platform == 'android':
    try:
        start_logging()
    except:
        pass
else:
    Window.size = (400, 700)

try:
    from kivy.core.text import LabelBase


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


    # This work but i like the normal, bold,italic config better title.font_name = "app_src/assets/fonts/Roboto_Mono/RobotoMono-VariableFont_wght.ttf"
    robot_mono = Font(name='RobotoMono', base_folder="assets/fonts/Roboto_Mono/static")
    LabelBase.register(
        name="RobotoMono",
        fn_regular=robot_mono.get_type_path('Regular'),
        fn_italic=robot_mono.get_type_path('Italic'),
        fn_bold=robot_mono.get_type_path('Bold'),
    )
except Exception as e:
    print("Error loading fonts", e)
    traceback.print_exc()


class MyScreenManager(MDScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = [0.05, 0.05, 0.05, 1]  # Manager background
        self.gallery_screen = GalleryScreen()
        self.full_screen = FullscreenScreen()
        screen = SettingsScreen()
        self.welcome_screen = WelcomeScreen()
        self.add_widget(self.gallery_screen)
        self.add_widget(self.full_screen)
        self.add_widget(screen)
        self.add_widget(self.welcome_screen)
        # print(self.current_screen)
        if not NotificationHandler.has_permission():
            self.transition = NoTransition()
            self.current = "welcome"



    def open_image_in_full_screen(self, index):
        self.full_screen.update_images()
        self.full_screen.carousel.index = index
        self.current = "fullscreen"


class Thumb(ButtonBehavior, AsyncImage):
    source_path = StringProperty()


class ThumbListScreen(MDScreen):  # Changed to MDScreen
    wallpapers = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = [0.1, 0.1, 0.1, 1]  # Now you can set md_bg_color!


class WallpaperCarouselApp(MDApp):
    interval = 2  # default rotation interval

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('init... app')
        self.sm = None

    def on_start(self):
        print('starting app...')
        def android_service():
            try:
                Service(name='Wallpapercarousel').start()
            except Exception as error_call_service_on_start:
                toast(error_call_service_on_start)
                traceback.print_exc()

        Clock.schedule_once(lambda dt: android_service(), 2)

    def on_resume(self):
        try:
            print('resuming app..')
            self.sm.gallery_screen.load_saved()
        except:
            toast("Error loading saved")

    def build(self):
        print('building app..')
        # Change to MDScreenManager
        self.sm = MyScreenManager()
        self.sm.gallery_screen.load_saved()
        return self.sm


if __name__ == '__main__':
    WallpaperCarouselApp().run()
