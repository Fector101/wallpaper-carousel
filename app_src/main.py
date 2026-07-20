from utils.helper import write_logs_to_file
write_logs_to_file()
import materialyoucolor
from android_notify import Notification
m=f"materialyoucolor: {materialyoucolor.__version__}"
print(m)
Notification(
    title="Version",
    message=m).send()









import os
from jnius import autoclass
from android_notify import Notification

PythonActivity = autoclass("org.kivy.android.PythonActivity")
context = PythonActivity.mActivity

base = context.getFilesDir().getAbsolutePath()

matches = []

for root, dirs, files in os.walk(base):
    if "materialyoucolor" in root:
        matches.append(f"\n{root}")
        for d in sorted(dirs):
            matches.append(f"  📁 {d}")
        for f in sorted(files):
            matches.append(f"  📄 {f}")

text = "\n".join(matches) if matches else "materialyoucolor not found"
print(text)
n=Notification(
    title="materialyoucolor Files",
    message="Tap to expand"
)
n.setBigText(text[:4000])
n.send()












import logging
import traceback

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, ObjectProperty
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.navigationdrawer import MDNavigationLayout

from android_notify import NotificationHandler, logger as android_notify_logger
from android_notify.config import on_android_platform, on_pydroid_app

from ui.screens.manager import ScreenManager
from ui.widgets.android import toast
from ui.widgets.buttons import BottomNavigationBar
from ui.widgets.bottom_sheet import MyBtmSheet

from utils.android import is_device_on_light_mode
from utils.config_manager import ConfigManager
from utils.constants import SERVICE_PORT_ARGUMENT_KEY, SERVICE_UI_PORT_ARGUMENT_KEY, theme_colors as _theme_colors
from utils.helper import Service, write_logs_to_file, get_free_port, register_fonts, fix_input_on_linux, \
    get_stored_running_ui_server_port, get_stored_running_service_server_port
from utils.image_operations import ImageOperation
from utils.logger import app_logger
from utils.permissions import ask_permission_to_images
from utils.ui_service_bridge import UIListenToServicer, UIMessengerToService

android_notify_logger.setLevel(logging.DEBUG if on_android_platform() else logging.ERROR)

write_logs_to_file()
fix_input_on_linux()
register_fonts()

if platform == 'linux':
    Window.size = (390, 740)
elif on_android_platform() and not on_pydroid_app():
    ask_permission_to_images()


class WallpaperCarouselApp(MDApp):
    device_theme = StringProperty("dark")
    theme_preference = StringProperty(ConfigManager.get_theme_preference())
    theme_colors = ObjectProperty(_theme_colors)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        root_layout = MDNavigationLayout()
        # self.root_layout = MDRelativeLayout()

        self.sm = ScreenManager()
        root_layout.add_widget(self.sm)

        self.bottom_bar = BottomNavigationBar(
            on_camera=self.sm.go_to_thumbs,
            on_settings=self.sm.go_to_settings,
            on_double_click_camera = self.sm.scroll_to_to_thumbs,
            on_double_click_settings = self.sm.scroll_to_to_settings
        )

        if not NotificationHandler.has_permission():
            self.sm.current = "welcome"
        else:
            self.sm.current = "thumbs"

        root_layout.add_widget(self.bottom_bar)
        self.bottom_bar.bind_change()  # needs theme from monitor_dark_and_light_device_change

        # get_number_of_cols()
        self.btm_sheet = MyBtmSheet(change_number_or_cols=self.sm.gallery_screen.change_amount_of_columns)
        root_layout.add_widget(self.btm_sheet)

        return root_layout

    def build(self):
        self.bind(device_theme=self._sync_theme_colors)
        self._sync_theme_colors()
        self.root_layout = self.build_ui()
        self.file_operation = ImageOperation(load_saved=self.sm.gallery_screen.initialize_tabs)
        self.bind_plyer_fix()
        self.file_operation.setup_share_from_others_to_app_listener()

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
        self.ui_messenger_to_service = UIMessengerToService(self.service_port)
        self.sm.settings_screen.ids.skip_upcoming_wallpaper_button.on_release = self.ui_messenger_to_service.change_next
        self.sm.settings_screen.ids.pause_home_screen_widget_loop_button.on_release = self.ui_messenger_to_service.toggle_home_screen_widget_changes

        self.ui_service_listener = UIListenToServicer(ui_port)
        self.ui_service_listener.start()
        self.ui_service_listener.on_countdown_change = self.sm.settings_screen.update_label
        self.ui_service_listener.on_changed_homescreen_widget = self.sm.settings_screen.on_changed_homescreen_widget
        if ConfigManager.get_start_on_app_launch():
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
        if on_android_platform() and not on_pydroid_app():
            from android import activity  # type: ignore
            def set_intent_for_file_operation_class(activity_id, some_int, intent):
                if self.file_operation.showing_loading_screen and not some_int:
                    # Fix for Half Screen Popup When no file is picked.
                    # some_int is usually -1 when a file is chosen and 0 when no file is chosen
                    self.file_operation.hide_spinner()
                    self.bottom_bar.show(hidden_by="pic")
                try:
                    print("intent must be before chooser callback",activity_id,some_int,intent)
                    if intent:
                        # Fix for permission Error when choosing from Internal Storage section Android FileExplorer
                        self.file_operation.intent = intent
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
