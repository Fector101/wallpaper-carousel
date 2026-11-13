from utils.helper import write_logs_to_file
write_logs_to_file()

import logging, threading, traceback # +0.024s

from kivy.properties import BooleanProperty, StringProperty, ObjectProperty
from kivy.utils import platform
from kivy.clock import Clock
from kivy.lang import Builder

from kivymd.app import MDApp
from kivymd.uix.navigationdrawer import MDNavigationLayout


from android_notify import NotificationHandler, logger as android_notify_logger
from android_notify.config import on_android_platform, on_pydroid_app

from ui.screens.manager import ScreenManager
from ui.widgets.android import toast
from ui.widgets.buttons import BottomNavigationBar
from ui.widgets.bottom_sheet import MyBtmSheet

from utils.config_manager import ConfigManager
from utils.constants import SERVICE_PORT_ARGUMENT_KEY, SERVICE_UI_PORT_ARGUMENT_KEY
from ui.theming import theme_colors as _theme_colors, get_device_theme

from utils.helper import (Service, get_free_port, register_fonts, fix_input_on_linux, patch_kivymd_for_kivy3,
                          get_stored_running_ui_server_port, get_stored_running_service_server_port, register_connectivity_receiver)
from utils.image_operations import ImageOperation, warm_up_android_bitmap_stack, warm_scaled_down_cache
from utils.logger import app_logger
from utils.ui_service_bridge import UIListenToServicer, UIMessengerToService

android_notify_logger.setLevel(logging.DEBUG if 0 else logging.ERROR)

patch_kivymd_for_kivy3()
register_fonts()

if platform == 'linux':
    from kivy.core.window import Window # +0.738s
    fix_input_on_linux()
    Window.size = (390, 740)


class WallpaperCarouselApp(MDApp):
    device_theme = StringProperty("dark")
    theme_preference = StringProperty(ConfigManager.get_theme_preference())
    theme_colors = ObjectProperty(_theme_colors)
    # True only after file_operation is created AND bind_plyer_fix + share
    # listener are wired up; gates the picker entry point and early results.
    image_operation_ready = BooleanProperty(False)
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
        self._widget_pick_pending = None
        self._carousel_service = None

    def build_ui(self):
        Builder.load_string("""
<MDButton>:
    theme_elevation_level: "Custom"
    theme_shadow_softness: "Custom"
    theme_shadow_color: "Custom"
    elevation_level: 0
    shadow_color: [0,0,0,0]
    shadow_softness: 0
<MDIconButton>:
    theme_elevation_level: "Custom"
    theme_shadow_softness: "Custom"
    theme_shadow_color: "Custom"
    elevation_level: 0
    shadow_color: [0,0,0,0]
    shadow_softness: 0
""")
        root_layout = MDNavigationLayout()

        self.sm = ScreenManager()
        root_layout.add_widget(self.sm)

        self.bottom_bar = BottomNavigationBar(
            on_camera=self.sm.go_to_thumbs,
            on_settings=self.sm.go_to_settings,
            on_double_click_camera = self.sm.scroll_to_to_thumbs,
            on_double_click_settings = self.sm.scroll_to_to_settings
        )
        per = NotificationHandler.has_permission()
        if not per:
            self.sm.current = "welcome"
        else:
            self.sm.current = "thumbs"

        root_layout.add_widget(self.bottom_bar)
        self.bottom_bar.bind_change()

        self.sm.ensure_screen("thumbs")
        self.btm_sheet = MyBtmSheet(change_number_or_cols=self.sm.gallery_screen.change_amount_of_columns)
        root_layout.add_widget(self.btm_sheet)
        # Clock.schedule_once(self.on_startup_clock_scheduler, 1)

        return root_layout

    def build(self):
        self.bind(device_theme=self._sync_theme_colors)
        self._sync_theme_colors() # +0.439s

        self.root_layout = self.build_ui()

        # threading.Thread(
        #     target=self._init_image_operation_on_background_thread,
        #     daemon=True,
        #     name="image_operation_thread",
        # ).start()

        return self.root_layout

    def _init_image_operation_on_background_thread(self):
        try:
            warm_up_android_bitmap_stack()
            self.file_operation = ImageOperation(load_saved=self.sm.gallery_screen.initialize_tabs)
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
            self.image_operation_ready = True
        except Exception as error_finish_image_operation_init:
            traceback.print_exc()
            error_message = str(error_finish_image_operation_init)
            Clock.schedule_once(lambda dt: toast(error_message))

    def start_up_jobs(self, dt):
        Clock.schedule_once(lambda dt: self.setup_service(), 2)
        Clock.schedule_interval(lambda dt: self.monitor_dark_and_light_device_change(), 1)
        warm_scaled_down_cache()
        if on_android_platform():
            from utils.update_checker import schedule_update_check
            Clock.schedule_once(lambda dt: register_connectivity_receiver(), 0)
            Clock.schedule_once(lambda dt: self._bind_update_intent_listener(), 0)
            Clock.schedule_once(lambda dt: schedule_update_check(), 0)
            # Handle initial intent if app was launched via share/widget/update
            Clock.schedule_once(lambda dt: self._handle_initial_intent(), 1)

    def _bind_update_intent_listener(self):
        try:
            from android import activity
            from utils.update_checker import handle_update_intent
            from utils.widget_intent import handle_widget_intent

            def on_new_intent_handler(intent):
                app_logger.info(f"_bind_update_intent_listener: on_new_intent fired, intent={intent}")
                if intent is None:
                    return
                # Handle share intent first (ACTION_SEND / ACTION_SEND_MULTIPLE with image/*)
                share_handled = False
                if self.file_operation and self.image_operation_ready:
                    share_handled = self.file_operation.handle_image_sharing_from_others_app(intent)
                if share_handled:
                    return
                handle_update_intent(self, intent=intent)
                handle_widget_intent(self, intent=intent)

            activity.bind(on_new_intent=on_new_intent_handler)
            app_logger.info("_bind_update_intent_listener: bound successfully")
        except Exception as e:
            app_logger.exception(f"Failed to bind update intent listener: {e}")

    def _handle_initial_intent(self):
        """Handle initial intent if app was launched via share, widget, or update notification."""
        if not on_android_platform():
            return
        try:
            from android_notify.config import get_python_activity_context
            from android_notify.internal.java_classes import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            intent = activity.getIntent()
            if intent is None:
                return
            # Delegate to the same handler logic
            share_handled = False
            if self.file_operation and self.image_operation_ready:
                share_handled = self.file_operation.handle_image_sharing_from_others_app(intent)
            if share_handled:
                return
            from utils.update_checker import handle_update_intent
            from utils.widget_intent import handle_widget_intent
            handle_update_intent(self, intent=intent)
            handle_widget_intent(self, intent=intent)
        except Exception as e:
            app_logger.exception(f"Failed to handle initial intent: {e}")

    def setup_service(self):
        # print(f"ConfigManager.get_start_on_app_launch(): {ConfigManager.get_start_on_app_launch()}")
        threading.Thread(
            target=self._setup_service_on_background_thread,
            daemon=True,
            name="setup_service_thread",
        ).start()

    def _setup_service_on_background_thread(self):
        try:
            service = Service(name='Wallpapercarousel')
            service_port = ui_port = None
            self.service_was_running = False

            if service.is_running():
                ui_port = get_stored_running_ui_server_port()
                service_port = get_stored_running_service_server_port()
                self.service_was_running = True

            self.service_port = service_port or get_free_port()
            self.ui_messenger_to_service = UIMessengerToService(self.service_port)

            self.ui_service_listener = UIListenToServicer(ui_port)
            self.ui_service_listener.start()
            Clock.schedule_once(self._finish_setup_service, 0)
        except Exception as error_call_service_on_start:
            traceback.print_exc()
            error_message = str(error_call_service_on_start)
            Clock.schedule_once(lambda dt: toast(error_message))

    def _finish_setup_service(self, _):
        try:
            self.sm.ensure_screen("settings")
            self.sm.settings_screen.build_ui()
            self.sm.settings_screen.ids.skip_upcoming_wallpaper_button.on_release = lambda x=None, motion=None: self.ui_messenger_to_service.change_next()
            self.sm.settings_screen.ids.pause_home_screen_widget_loop_button.on_release = lambda x=None, motion=None: self.ui_messenger_to_service.toggle_home_screen_widget_changes()

            self.ui_service_listener.on_countdown_change = self.sm.settings_screen.update_label
            self.ui_service_listener.on_changed_homescreen_widget = self.sm.settings_screen.on_changed_homescreen_widget
            self.ui_service_listener.on_service_status = self.sm.settings_screen.on_service_status
            self.ui_service_listener.on_stopped_all = self.sm.settings_screen.on_service_stopped
            
            if ConfigManager.get_start_on_app_launch():
                self.start_service()
        except Exception as error_call_service_on_start:
            toast(str(error_call_service_on_start))
            traceback.print_exc()

    def self_settings_screen_service_state(self, status):
        if self.sm and getattr(self.sm, "settings_screen", None) is not None:
            self.sm.settings_screen.set_service_status(status)

    def start_service(self):
        """Build a Service with retry callbacks wired to the settings screen."""
        self.cancel_service_start_retry()

        settings_screen = self._settings_screen_or_none()
        on_retry = None
        on_give_up = None
        on_start_attempt = None
        on_attempt_failed = None
        if settings_screen is not None:
            on_retry = settings_screen.on_service_retry_tick
            on_give_up = settings_screen.on_service_start_gave_up
            on_start_attempt = settings_screen.on_service_start_attempt
            on_attempt_failed = settings_screen.on_service_attempt_failed

        try:
            self._carousel_service = Service(
                name='Wallpapercarousel',
                args_str={
                    SERVICE_PORT_ARGUMENT_KEY: self.service_port,
                    SERVICE_UI_PORT_ARGUMENT_KEY: self.ui_service_listener.UI_PORT,
                },
                on_finish=self.self_settings_screen_service_state,
                on_start_attempt=on_start_attempt,
                on_attempt_failed=on_attempt_failed,
                on_retry=on_retry,
                on_give_up=on_give_up,
            )
            return self._carousel_service.start_with_retry()
        except Exception as error_starting_service:
            app_logger.exception(
                f"start_service: error starting carousel service: "
                f"{error_starting_service}")
            self._carousel_service = None
            return False

    def cancel_service_start_retry(self):
        if self._carousel_service:
            self._carousel_service.cancel_retry()

    def service_retry_pending(self):
        return bool(
            self._carousel_service and self._carousel_service.retry_pending)

    def _settings_screen_or_none(self):
        return getattr(getattr(self, "sm", None), "settings_screen", None)

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
                if not self.image_operation_ready:
                    app_logger.warning("bind_plyer_fix: ignoring early activity result before image operation ready")
                    return
                if not some_int:
                    # Fix for Half Screen Popup When no file is picked.
                    # some_int is usually -1 when a file is chosen and 0 when no file is chosen
                    self.file_operation._file_picker_active = False
                    self._widget_pick_pending = None
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
        self.device_theme = get_device_theme(self.theme_preference)

    def set_theme_preference(self, preference):
        self.theme_preference = preference
        ConfigManager.set_theme_preference(preference)
        self.device_theme = get_device_theme(preference)

    def _sync_theme_colors(self, *args):
        _theme_colors.theme = self.device_theme


    def on_startup_clock_scheduler(self, dt):
        
        Clock.schedule_once(self._get_tabs_for_gallery_screen, 0.7)
        Clock.schedule_once(self.start_up_jobs, 1)

    def _get_tabs_for_gallery_screen(self, dt):
        self.sm.gallery_screen.initialize_tabs(no_clock=True)

if __name__ == '__main__':
    try:
        WallpaperCarouselApp().run()
    except Exception as startup_failure:
        # Log it, then let it crash: the traceback in Logcat and a nonzero exit
        # are how a broken startup gets noticed, so swallowing it here would hide
        # exactly the failure this is here to surface.
        print(f"main: app failed: {startup_failure}")
        traceback.print_exc()
        raise
