import traceback, logging, os

from kivy.uix.screenmanager import NoTransition
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import SlideTransition
from kivy.core.window import Window
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.relativelayout import MDRelativeLayout

from android_notify.config import on_android_platform, autoclass
from android_notify import NotificationHandler, logger as android_notify_logger
from kivymd.uix.screenmanager import MDScreenManager

from utils.model import get_app
from utils.permissions import ask_permission_to_images
from utils.image_operations import ImageOperation
from utils.constants import SERVICE_PORT_ARGUMENT_KEY, SERVICE_UI_PORT_ARGUMENT_KEY, DEV
from utils.helper import Service, write_logs_to_file, get_free_port, Font, appFolder, toInt
from utils.android import is_device_on_light_mode
from utils.ui_service_bridge import UIServiceListener, UIServiceMessenger

from ui.screens.gallery_screen import GalleryScreen
from ui.screens.settings_screen import SettingsScreen
from ui.screens.full_screen import FullscreenScreen
from ui.screens.welcome_screen import WelcomeScreen
from ui.screens.logs_screen import LogsScreen
from ui.widgets.buttons import BottomButtonBar
from ui.widgets.android import toast


android_notify_logger.setLevel(logging.DEBUG if on_android_platform() else logging.ERROR)

write_logs_to_file()
if platform == 'linux':
    from kivy import Config
    # Linux has some weirdness with the touchpad by default... remove it
    options = Config.options('input')
    for option in options:
        if Config.get('input', option) == 'probesysfs':
            Config.remove_option('input', option)
    Window.size = (390, 740)

elif platform == 'android':
    ask_permission_to_images()


robot_mono = Font(name='RobotoMono', base_folder="assets/fonts/Roboto_Mono/static")
LabelBase.register(
    name="RobotoMono",
    fn_regular=robot_mono.get_type_path('Regular'),
    fn_italic=robot_mono.get_type_path('Italic'),
    fn_bold=robot_mono.get_type_path('Bold'),
)


class MyScreenManager(MDScreenManager):
    go_to_settings = go_to_thumbs = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        # Screens
        self.welcome_screen = WelcomeScreen()
        self.gallery_screen = GalleryScreen()
        self.full_screen = FullscreenScreen()
        self.settings_screen = SettingsScreen()
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

    def go_to_settings(self, widget=None):
        self.transition = SlideTransition(direction="left")
        self.current = "settings"

    def go_to_thumbs(self, widget=None):
        self.transition = SlideTransition(direction="right")
        self.current = "thumbs"

    def open_image_in_full_screen(self, index):
        self.transition = NoTransition()
        self.current = "fullscreen"
        self.full_screen.update_images(index)
        self.full_screen.carousel.index = index
        # print("done....")


class WallpaperCarouselApp(MDApp):
    interval = 2  # default rotation interval

    device_theme = StringProperty("light")
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service_port = None
        self.ui_messenger_to_service = None
        self.file_operation = None
        self.ui_service_listener=None
        self.root_layout = None
        self.sm = None
        self.bottom_bar = None

    def build(self):
        # Create a root layout to hold ScreenManager + BottomButtonBar
        self.root_layout = MDRelativeLayout()

        # ScreenManager
        self.sm = MyScreenManager()
        # self.sm.gallery_screen.load_saved()
        self.root_layout.add_widget(self.sm)

        # Add global BottomButtonBar
        self.bottom_bar = BottomButtonBar(
            on_camera=self.sm.go_to_thumbs,
            on_settings=self.sm.go_to_settings,
        )
        self.root_layout.add_widget(self.bottom_bar)
        # self.monitor_dark_and_light_device_change()
        self.bottom_bar.bind_change()# needs theme from monitor_dark_and_light_device_change
        if not NotificationHandler.has_permission():
            self.sm.current = "welcome"

        self.file_operation = ImageOperation(self.sm.gallery_screen.initialize_tabs)
        self.bind_plyer_fix()
        return self.root_layout

    def on_start(self):
        self.debug()
        def android_service():
            try:
                self.setup_service()
            except Exception as error_call_service_on_start:
                toast(str(error_call_service_on_start))
                traceback.print_exc()
        # self.debug1()
        Clock.schedule_once(lambda dt: android_service(), 2)
        Clock.schedule_interval(lambda dt: self.monitor_dark_and_light_device_change(), 1)

    def setup_service(self):
        service = Service(name='Wallpapercarousel')
        service_port = ui_port = None
        if service.is_running():
            # read ui and service port from .txt file
            # TODO EMPTY FILES WHEN SERVICE ENDS
            ui_port_store_path = os.path.join(appFolder(), "ui_port.txt")
            service_port_store_path = os.path.join(appFolder(), "port.txt")

            if os.path.exists(ui_port_store_path):
                with open(ui_port_store_path,"r") as f:
                    ui_port = toInt(f.read())
            if os.path.exists(service_port_store_path):
                with open(service_port_store_path,"r") as f:
                    service_port = toInt(f.read())

        self.service_port = service_port or get_free_port()
        self.ui_messenger_to_service = UIServiceMessenger(self.service_port)
        self.sm.settings_screen.ids.skip_upcoming_wallpaper_button.on_release = self.ui_messenger_to_service.change_next
        self.sm.settings_screen.ids.pause_home_screen_widget_loop_button.on_release = self.ui_messenger_to_service.toggle_home_screen_widget_changes

        self.ui_service_listener = UIServiceListener(ui_port)
        self.ui_service_listener.start()
        self.ui_service_listener.on_countdown_change = self.sm.settings_screen.update_label
        self.ui_service_listener.on_changed_homescreen_widget = self.sm.settings_screen.on_changed_homescreen_widget
        self.start_service()

    def start_service(self):

        Service(
            name='Wallpapercarousel',
            args_str={
                SERVICE_PORT_ARGUMENT_KEY: self.service_port,
                SERVICE_UI_PORT_ARGUMENT_KEY: self.ui_service_listener.UI_PORT,
            },

        ).start()

    def on_resume(self):
        if NotificationHandler.has_permission() and self.sm and self.sm.current == "welcome":
            self.sm.current = "thumbs"
        try:
            n_data = NotificationHandler.data_object
            if DEV:
                print("resume",n_data)
        except Exception as error_getting_data_object:
            print(error_getting_data_object)
            traceback.print_exc()

        try:
            name = NotificationHandler.get_name()
            print("name:",name)
            if DEV:
                toast(text=f"name: {name}", length_long=True)
        except Exception as error_getting_notify_name:
            print("Error getting notify name:",error_getting_notify_name)
        try:
            name=NotificationHandler.get_name()
            if DEV:
                print("name1:",name)
        except Exception as e:
            print("Error getting notify name:", e)

    def bind_plyer_fix(self):
        if platform == 'android':
            from android import activity # type: ignore
            def set_intent_for_file_operation_class(activity_id,some_int,intent):
                try:
                    print("intent must be before chooser callback",activity_id,some_int,intent)
                    if intent:
                        self.file_operation.intent = intent
                except Exception as error_getting_path:
                    print("error_getting_path",error_getting_path)
            activity.bind(on_activity_result=set_intent_for_file_operation_class) # handling permission error in image path

    @staticmethod
    def debug():
        if not DEV:
            return None
        try:
            n_data = NotificationHandler.data_object
            print("start",n_data)
        except Exception as error_getting_data_object:
            print(error_getting_data_object)
            traceback.print_exc()
        try:
            name = NotificationHandler.get_name(on_start=True)
            toast(text=f"name: {name}", length_long=True)
        except Exception as e:
            print("Error getting notify namex:", e)
        print('on_start','-'*33)
        return None

    def monitor_dark_and_light_device_change(self):
        self.device_theme = is_device_on_light_mode()
        # self.device_theme = "light" #if self.device_theme == "dark" else "dark"
        # self.bottom_bar.color_tab_buttons(self.sm.current)
        return self.device_theme

if __name__ == '__main__':
    WallpaperCarouselApp().run()
