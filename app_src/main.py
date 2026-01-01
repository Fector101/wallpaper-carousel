import os
import traceback


from kivy.uix.screenmanager import NoTransition
from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.utils import platform

from android_notify import NotificationHandler
from utils.helper import Service, start_logging, get_free_port, save_existing_file_to_public_pictures
from ui.screens.gallery_screen import GalleryScreen
from ui.screens.settings_screen import SettingsScreen
from ui.screens.full_screen import FullscreenScreen
from ui.screens.welcome_screen import WelcomeScreen
from ui.screens.logs_screen import LogsScreen
from ui.widgets.buttons import BottomButtonBar
from ui.widgets.android import toast

from kivymd.uix.relativelayout import MDRelativeLayout
from kivy.metrics import dp

try:
    start_logging()
except Exception as error_saving_logs:
    print('Error directing logs:', error_saving_logs)
if platform == 'linux':
    from kivy import Config
    #Linux has some weirdness with the touchpad by default... remove it
    options = Config.options('input')
    for option in options:
        if Config.get('input', option) == 'probesysfs':
            Config.remove_option('input', option)
    Window.size = (370, 700)

elif platform == 'android':
    try:
        from android.permissions import request_permissions, Permission  # type: ignore


        def check_permissions():
            # List the permissions you need to ask the user for
            permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_MEDIA_IMAGES  # Kivy's latest master/buildozer handles this
            ]
            request_permissions(permissions)


        check_permissions()
    except Exception as error_call_service_on_start:
        print('Fallback toast:', error_call_service_on_start)



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



class MyScreenManager(ScreenManager):
    go_to_settings = go_to_thumbs = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = MDApp.get_running_app()
        # Screens
        self.gallery_screen = GalleryScreen()
        self.full_screen = FullscreenScreen()
        self.settings_screen = SettingsScreen()
        self.welcome_screen = WelcomeScreen()
        self.log_screen = LogsScreen()

        self.add_widget(self.gallery_screen)
        self.add_widget(self.full_screen)
        self.add_widget(self.settings_screen)
        self.add_widget(self.welcome_screen)
        self.add_widget(self.log_screen)


    def on_current(self,*args):
        screen_name = args[1]
        is_fullscreen = screen_name == "fullscreen" or screen_name == "welcome" or screen_name == "logs"
        if is_fullscreen and self.app.bottom_bar:
            self.app.bottom_bar.hide()
        elif self.app.bottom_bar:
            self.app.bottom_bar.show()
        super().on_current(instance=args[0],value=args[1])

    def go_to_settings(self, wigdet=None):
        self.transition = SlideTransition(direction="left")
        self.current = "settings"

    def go_to_thumbs(self, wigdet=None):
        self.transition = SlideTransition(direction="right")
        self.current = "thumbs"

    def open_image_in_full_screen(self, index):
        self.full_screen.update_images()
        self.full_screen.carousel.index = index
        self.transition = NoTransition()
        self.current = "fullscreen"



class WallpaperCarouselApp(MDApp):
    interval = 2  # default rotation interval

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('init... app')
        self.root_layout = None
        self.sm = None
        self.bottom_bar = None

    def build(self):
        print('building app..')

        # Create a root layout to hold ScreenManager + BottomButtonBar
        self.root_layout = MDRelativeLayout()

        # ScreenManager
        self.sm = MyScreenManager()
        self.sm.gallery_screen.load_saved()
        self.root_layout.add_widget(self.sm)

        # Add global BottomButtonBar
        self.bottom_bar = BottomButtonBar(
            on_camera=self.sm.go_to_thumbs,
            on_settings=self.sm.go_to_settings,
            width=dp(120),
            height=dp(500)
        )
        self.root_layout.add_widget(self.bottom_bar)

        if not NotificationHandler.has_permission():
            self.sm.current = "welcome"

        return self.root_layout

    def on_start(self):
        print('starting app...')

        def android_service():
            try:
                Service(name='Wallpapercarousel', args_str=get_free_port()).start()
            except Exception as error_call_service_on_start:
                toast(error_call_service_on_start)
                traceback.print_exc()

        Clock.schedule_once(lambda dt: android_service(), 2)

    def on_resume(self):
        try:
            name=NotificationHandler.get_name()
            print("name:",name)
        except Exception as error_getting_notify_name:
            print("Error getting notify name:",error_getting_notify_name)
        try:
            print('resuming app..')
            self.sm.gallery_screen.load_saved()
        except Exception as error_loading_saved:
            traceback.print_exc()
            print("Error loading saved:",error_loading_saved)
            toast("Error loading saved: "+str(error_loading_saved))


if __name__ == '__main__':
    WallpaperCarouselApp().run()
