from utils.boot_log import boot_log
boot_log("[BOOT] main:-----------------imports started------------------------------")
from utils.helper import write_logs_to_file
write_logs_to_file()
boot_log("main: write_logs_to_file imports done")


import logging, threading, traceback # +0.024s

from kivy.properties import StringProperty, ObjectProperty # +0.997s
from kivy.utils import platform # +0.001s
from kivy.clock import Clock # +1.403s
from kivymd.app import MDApp # +0.955s
from kivymd.uix.navigationdrawer import MDNavigationLayout # +0.259s
boot_log("main: kivymd/MDApp imports done")


# +0.001s
from android_notify import NotificationHandler, logger as android_notify_logger
from android_notify.config import on_android_platform, on_pydroid_app
boot_log("main: android_notify imports done")

from ui.screens.manager import ScreenManager
boot_log("main: local imports done3")
from ui.widgets.android import toast
from ui.widgets.buttons import BottomNavigationBar
from ui.widgets.bottom_sheet import MyBtmSheet

from utils.android import is_device_on_light_mode
from utils.config_manager import ConfigManager
from utils.constants import SERVICE_PORT_ARGUMENT_KEY, SERVICE_UI_PORT_ARGUMENT_KEY, theme_colors as _theme_colors
boot_log("main: local imports done2")
from utils.helper import Service, get_free_port, register_fonts, fix_input_on_linux, \
    get_stored_running_ui_server_port, get_stored_running_service_server_port
boot_log("main: local imports done1")
from utils.image_operations import ImageOperation # JNI call — app_storage_path() - 0.697s
from utils.logger import app_logger
from utils.ui_service_bridge import UIListenToServicer, UIMessengerToService
boot_log("main: local imports done")

android_notify_logger.setLevel(logging.DEBUG if on_android_platform() else logging.ERROR)

fix_input_on_linux()
register_fonts()
boot_log("--------------main: module setup done--------------")

if platform == 'linux':
    from kivy.core.window import Window # +0.738s
    Window.size = (390, 740)


class WallpaperCarouselApp(MDApp):
    device_theme = StringProperty("dark")
    theme_preference = StringProperty(ConfigManager.get_theme_preference())
    theme_colors = ObjectProperty(_theme_colors)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        boot_log("app: __init__ done")
        self.btm_sheet = None
        self.service_port = None
        self.ui_messenger_to_service = None
        self.file_operation = None
        self.ui_service_listener = None
        self.root_layout = None
        self.sm = None
        self.bottom_bar = None

    def build_ui(self):
        from kivy.lang import Builder
        boot_log("build_ui: Builder.load_string start")
        Builder.load_string("""
<MDButton>:
    theme_elevation_level: "Custom"
    elevation_level: 0
    theme_shadow_softness: "Custom"
    shadow_softness: 0
<MDIconButton>:
    theme_elevation_level: "Custom"
    elevation_level: 0
    theme_shadow_softness: "Custom"
    shadow_softness: 0
""")
        boot_log("build_ui: Builder.load_string done")
        root_layout = MDNavigationLayout()
        # self.root_layout = MDRelativeLayout()

        boot_log("build_ui: ScreenManager() start")
        self.sm = ScreenManager()
        boot_log("build_ui: ScreenManager() done")
        root_layout.add_widget(self.sm)

        boot_log("build_ui: BottomNavigationBar start")
        self.bottom_bar = BottomNavigationBar(
            on_camera=self.sm.go_to_thumbs,
            on_settings=self.sm.go_to_settings,
            on_double_click_camera = self.sm.scroll_to_to_thumbs,
            on_double_click_settings = self.sm.scroll_to_to_settings
        )
        boot_log("build_ui: BottomNavigationBar done")

        boot_log("build_ui: has_permission() start")
        if not NotificationHandler.has_permission():
            self.sm._ensure_welcome_screen()
            self.sm.current = "welcome"
        else:
            boot_log("build_ui: moving to thumbs screen")
            self.sm.current = "thumbs"
            boot_log("build_ui: moved to thumbs screen")
        boot_log("build_ui: has_permission() done")

        root_layout.add_widget(self.bottom_bar)
        boot_log("build_ui: bind_change start")
        self.bottom_bar.bind_change()  # needs theme from monitor_dark_and_light_device_change
        boot_log("build_ui: bind_change done")

        # get_number_of_cols()
        boot_log("build_ui: MyBtmSheet start")
        self.btm_sheet = MyBtmSheet(change_number_or_cols=self.sm.gallery_screen.change_amount_of_columns)
        root_layout.add_widget(self.btm_sheet)
        boot_log("build_ui: MyBtmSheet done")

        return root_layout

    def build(self):
        self.bind(device_theme=self._sync_theme_colors)
        self._sync_theme_colors()
        boot_log("build: build_ui start")
        self.root_layout = self.build_ui()
        boot_log("build: build_ui done")
        threading.Thread(
            target=self._init_image_operation_on_background_thread,
            daemon=True,
            name="image_operation_thread",
        ).start()

        return self.root_layout

    def _init_image_operation_on_background_thread(self):
        try:
            boot_log("build: ImageOperation start")
            self.file_operation = ImageOperation(load_saved=self.sm.gallery_screen.initialize_tabs)
            boot_log("build: ImageOperation done")
            Clock.schedule_once(self._finish_image_operation_init, 0)
        except Exception as error_init_image_operation:
            traceback.print_exc()
            error_message = str(error_init_image_operation)
            Clock.schedule_once(lambda dt: toast(error_message))

    def _finish_image_operation_init(self, _):
        # jnius PythonJavaClass proxies (activity.bind) require app-dex classes
        # (org.kivy.android.PythonActivity$*) via FindClass, which only works on
        # the main thread -- so this must stay here, off the background thread.
        try:
            self.bind_plyer_fix()
            boot_log("build: bind_plyer_fix done")
            self.file_operation.setup_share_from_others_to_app_listener()
            boot_log("build: share listener done")
        except Exception as error_finish_image_operation_init:
            traceback.print_exc()
            error_message = str(error_finish_image_operation_init)
            Clock.schedule_once(lambda dt: toast(error_message))

    def on_start(self):
        boot_log("on_start: scheduling")
        Clock.schedule_once(lambda dt: self.setup_service(), 2)
        Clock.schedule_interval(lambda dt: self.monitor_dark_and_light_device_change(), 1)

    def setup_service(self):
        boot_log("setup_service: start")
        print(f"ConfigManager.get_start_on_app_launch(): {ConfigManager.get_start_on_app_launch()}")
        threading.Thread(
            target=self._setup_service_on_background_thread,
            daemon=True,
            name="setup_service_thread",
        ).start()

    def _setup_service_on_background_thread(self):
        try:
            service = Service(name='Wallpapercarousel')
            service_port = ui_port = None

            if service.is_running():
                ui_port = get_stored_running_ui_server_port()
                service_port = get_stored_running_service_server_port()

            self.service_port = service_port or get_free_port()
            boot_log("setup_service: service/ports done")
            self.ui_messenger_to_service = UIMessengerToService(self.service_port)

            self.ui_service_listener = UIListenToServicer(ui_port)
            self.ui_service_listener.start()
            boot_log("setup_service: messenger+listener started")
            Clock.schedule_once(self._finish_setup_service, 0)
        except Exception as error_call_service_on_start:
            traceback.print_exc()
            error_message = str(error_call_service_on_start)
            Clock.schedule_once(lambda dt: toast(error_message))

    def _finish_setup_service(self, _):
        try:
            self.sm.settings_screen.build_ui()
            self.sm.settings_screen.ids.skip_upcoming_wallpaper_button.on_release = self.ui_messenger_to_service.change_next
            self.sm.settings_screen.ids.pause_home_screen_widget_loop_button.on_release = self.ui_messenger_to_service.toggle_home_screen_widget_changes

            self.ui_service_listener.on_countdown_change = self.sm.settings_screen.update_label
            self.ui_service_listener.on_changed_homescreen_widget = self.sm.settings_screen.on_changed_homescreen_widget
            if ConfigManager.get_start_on_app_launch():
                self.start_service()
            boot_log("setup_service: done")
        except Exception as error_call_service_on_start:
            toast(str(error_call_service_on_start))
            traceback.print_exc()

    def start_service(self):

        Service(
            name='Wallpapercarousel',
            args_str={
                SERVICE_PORT_ARGUMENT_KEY: self.service_port,
                SERVICE_UI_PORT_ARGUMENT_KEY: self.ui_service_listener.UI_PORT,
            },

        ).start()

    def on_resume(self):
        if self.file_operation and self.file_operation.showing_loading_screen and not self.file_operation._file_picker_active:
            print("on_resume: cleaning up spinner left from permission settings redirect")
            self.file_operation.hide_spinner()
            self.bottom_bar.show(hidden_by="pic")
        if NotificationHandler.has_permission() and self.sm and self.sm.current == "welcome":
            self.sm.current = "thumbs"

    def bind_plyer_fix(self):
        if on_android_platform() and not on_pydroid_app():
            from android import activity  # type: ignore
            def set_intent_for_file_operation_class(activity_id, some_int, intent):
                if not some_int:
                    # Fix for Half Screen Popup When no file is picked.
                    # some_int is usually -1 when a file is chosen and 0 when no file is chosen
                    self.file_operation._file_picker_active = False
                    if self.file_operation.showing_loading_screen:
                        self.file_operation.hide_spinner()
                        self.bottom_bar.show(hidden_by="pic")
                    return
                try:
                    print("intent must be before chooser callback",activity_id,some_int,intent)
                    if intent:
                        # Fix for permission Error when choosing from Internal Storage section Android FileExplorer
                        self.file_operation.intent = intent
                        # Process URIs in background immediately, bypassing plyer's main-thread path resolution.
                        if self.file_operation._file_picker_active:
                            print("bind_plyer_fix: starting async import_from_intent")
                            self.file_operation.import_images_from_android()
                except Exception as error_getting_path:
                    app_logger.exception(f"error_getting_path: {error_getting_path}")

            activity.bind(
                on_activity_result=set_intent_for_file_operation_class)

    def monitor_dark_and_light_device_change(self):
        if self.theme_preference == "adaptive":
            self.device_theme = is_device_on_light_mode()
        else:
            self.device_theme = self.theme_preference
        return self.device_theme

    def set_theme_preference(self, preference):
        self.theme_preference = preference
        ConfigManager.set_theme_preference(preference)
        if preference == "adaptive":
            self.device_theme = is_device_on_light_mode()
        else:
            self.device_theme = preference

    def _sync_theme_colors(self, *args):
        _theme_colors.theme = self.device_theme


if __name__ == '__main__':
    WallpaperCarouselApp().run()
