import logging
import traceback

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.relativelayout import MDRelativeLayout

from android_notify import NotificationHandler, logger as android_notify_logger
from android_notify.config import on_android_platform

from ui.screens.manager import ScreenManager
from ui.widgets.android import toast
from ui.widgets.buttons import BottomNavigationBar

from utils.android import is_device_on_light_mode
from utils.constants import SERVICE_PORT_ARGUMENT_KEY, SERVICE_UI_PORT_ARGUMENT_KEY
from utils.helper import Service, write_logs_to_file, get_free_port, register_fonts, fix_input_on_linux, \
    get_stored_running_ui_server_port, get_stored_running_service_server_port
from utils.image_operations import ImageOperation
from utils.logger import app_logger
from utils.permissions import ask_permission_to_images
from utils.ui_service_bridge import UIServiceListener, UIMessengerTOService

android_notify_logger.setLevel(logging.DEBUG if on_android_platform() else logging.ERROR)

write_logs_to_file()
fix_input_on_linux()
register_fonts()

if platform == 'linux':
    Window.size = (390, 740)
elif on_android_platform():
    ask_permission_to_images()


class WallpaperCarouselApp(MDApp):
    device_theme = StringProperty("dark")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service_port = None
        self.ui_messenger_to_service = None
        self.file_operation = None
        self.ui_service_listener = None
        self.root_layout = None
        self.sm = None
        self.bottom_bar = None

    def build(self):
        self.root_layout = MDRelativeLayout()

        self.sm = ScreenManager()
        self.root_layout.add_widget(self.sm)

        self.bottom_bar = BottomNavigationBar(
            on_camera=self.sm.go_to_thumbs,
            on_settings=self.sm.go_to_settings,
        )
        self.root_layout.add_widget(self.bottom_bar)
        self.bottom_bar.bind_change()  # needs theme from monitor_dark_and_light_device_change

        self.file_operation = ImageOperation(load_saved=self.sm.gallery_screen.initialize_tabs)
        self.bind_plyer_fix()

        return self.root_layout

    def on_start(self):
        def android_service():
            try:
                self.setup_service()
            except Exception as error_call_service_on_start:
                toast(str(error_call_service_on_start))
                traceback.print_exc()

        Clock.schedule_once(lambda dt: android_service(), 2)
        Clock.schedule_interval(lambda dt: self.monitor_dark_and_light_device_change(), 1)

    def setup_service(self):
        service = Service(name='Wallpapercarousel')
        service_port = ui_port = None

        if service.is_running():
            ui_port = get_stored_running_ui_server_port()
            service_port = get_stored_running_service_server_port()


        self.service_port = service_port or get_free_port()
        self.ui_messenger_to_service = UIMessengerTOService(self.service_port)
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

    def bind_plyer_fix(self):
        if on_android_platform():
            from android import activity  # type: ignore
            def set_intent_for_file_operation_class(activity_id, some_int, intent):
                if self.file_operation.showing_loading_screen and not some_int:
                    # Fix for Half Screen Popup When no file is picked.
                    # some_int is usually -1 when a file is chosen and 0 when no file is chosen
                    self.file_operation.hide_spinner()
                try:
                    print("intent must be before chooser callback",activity_id,some_int,intent)
                    if intent:
                        # Fix for permission Error when choosing from Internal Storage section Android FileExplorer
                        self.file_operation.intent = intent
                except Exception as error_getting_path:
                    app_logger.exception("error_getting_path", error_getting_path)

            activity.bind(
                on_activity_result=set_intent_for_file_operation_class)

    def monitor_dark_and_light_device_change(self):
        self.device_theme = is_device_on_light_mode()
        # self.device_theme='light'
        return self.device_theme


if __name__ == '__main__':
    WallpaperCarouselApp().run()
