import traceback, time
from pathlib import Path

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField

from android_notify.core import asks_permission_if_needed
from android_notify.config import get_python_activity_context,autoclass
from android_notify.internal.java_classes import PendingIntent,Intent
from android_notify import NotificationHandler,Notification
from ui.widgets.android import toast  # type: ignore
from android_widgets import get_package_name
from utils.constants import DEV, VERSION

from utils.helper import Service, makeDownloadFolder, start_logging, smart_convert_minutes  # type: ignore
from utils.config_manager import ConfigManager  # type: ignore
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp, sp
from kivy.uix.scrollview import ScrollView
import logging
from android_notify.internal.logger import logger
logger.setLevel(logging.DEBUG)
class MyLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.on_release = self.tapped
        self.size_hint = [1, None]
        self.height = 100


def create_channel():
    Notification.createChannel(
        id='vibes',
        name="Vibes",
        vibrate=True
    )
    Notification.createChannel(
        id='no_vibes',
        name="No Vibes",
        vibrate=False
    )


def delete_current_channel():
    Notification.deleteAllChannel()


def schedule_notification(seconds=10, message="Hello from WorkManager"):
    from jnius import autoclass

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    WorkManager = autoclass('androidx.work.WorkManager')
    OneTimeWorkRequestBuilder = autoclass(
        'androidx.work.OneTimeWorkRequest$Builder'
    )
    DataBuilder = autoclass('androidx.work.Data$Builder')
    TimeUnit = autoclass('java.util.concurrent.TimeUnit')
    MyWorker = autoclass('org.wally.waller.MyWorker')
    context = PythonActivity.mActivity

    data = (
        DataBuilder()
        .putString("message", message)
        .build()
    )

    request = (
        OneTimeWorkRequestBuilder(MyWorker)
        .setInitialDelay(seconds, TimeUnit.SECONDS)
        .setInputData(data)
        .build()
    )

    WorkManager.getInstance(context).enqueue(request)


def no_vibes():
    n=Notification(title='no vibrate',channel_id='no_vibes')
    n.send()


def basic_side():
    try:
        asks_permission_if_needed()
    except Exception as e:
        print('Permission error:', e)
        traceback.print_exc()


def test_vibration():
    try:
        n=Notification(title='vibrate',channel_id='vibes')
        n.send()
        # from android_notify.tests.android_notify_test import TestAndroidNotifyFull
        # import unittest
        #
        # suite = unittest.TestLoader().loadTestsFromTestCase(TestAndroidNotifyFull)
        # unittest.TextTestRunner(verbosity=2).run(suite)

    except Exception as e:
        print("Error testing vibration:", e)
        traceback.print_exc()


def test_force_vibration():
    try:
        n=Notification(title='vibrate',channel_id='vibes')
        n.send()
        n.fVibrate()
    except Exception as e:
        print("Error test_force_vibration:", e)
        traceback.print_exc()


def schedule_alarm():
    Context = autoclass('android.content.Context')
    AlarmManager = autoclass('android.app.AlarmManager')
    context = get_python_activity_context()
    alarm = context.getSystemService(Context.ALARM_SERVICE)

    intent = Intent(context, autoclass(f"{get_package_name()}.TheReceiver"))
    intent.setAction("ALARM_ACTION")
    intent.putExtra("message", "Hello from Python!")

    pending = PendingIntent.getBroadcast(
        context, 0, intent, PendingIntent.FLAG_IMMUTABLE
    )

    trigger_time = int((time.time() + 10) * 1000)  # 10 seconds later
    alarm.setExact(AlarmManager.RTC_WAKEUP, trigger_time, pending)


def open_notify_settings():

    try:
        NotificationHandler.asks_permission()
    except Exception as e:
        print('Notify error:', e)


def show_home_screen_widget_popup():
    try:
        from jnius import autoclass
        from android_widgets import get_package_name

        # Android classes
        AppWidgetManager = autoclass('android.appwidget.AppWidgetManager')
        ComponentName = autoclass('android.content.ComponentName')
        Intent = autoclass('android.content.Intent')
        PendingIntent = autoclass('android.app.PendingIntent')

        # Your widget provider class (Java side)
        CarouselWidgetProvider = autoclass(
            f'{get_package_name()}.CarouselWidgetProvider'
        )

        # Get current Android activity context
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        context = PythonActivity.mActivity

        # AppWidgetManager instance
        appWidgetManager = AppWidgetManager.getInstance(context)

        # ComponentName for your widget provider
        myProvider = ComponentName(context, CarouselWidgetProvider)

        # Check if pinning is supported
        if appWidgetManager.isRequestPinAppWidgetSupported():
            # Optional: callback when widget is pinned
            intent = Intent(context, CarouselWidgetProvider)

            successCallback = PendingIntent.getBroadcast(
                context,
                0,
                intent,
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT

            )

            # Request widget pin
            appWidgetManager.requestPinAppWidget(
                myProvider,
                None,
                successCallback
            )
    except Exception as error_from_gpt_way:
        print("error_from_gpt_way",error_from_gpt_way)
        traceback.print_exc()

def show_home_screen_widget_popup1():
    from jnius import autoclass
    from android_widgets import get_package_name
    try:
        # Android classes
        AppWidgetManager = autoclass('android.appwidget.AppWidgetManager')
        ComponentName = autoclass('android.content.ComponentName')
        Intent = autoclass('android.content.Intent')
        PendingIntent = autoclass('android.app.PendingIntent')

        # Your widget provider class (Java side)
        package_name = get_package_name()
        CarouselWidgetProvider = autoclass(
            f'{package_name}.CarouselWidgetProvider'
        )

        # Get current Android activity context
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        context = PythonActivity.mActivity

        # AppWidgetManager instance
        appWidgetManager = AppWidgetManager.getInstance(context)

        # ComponentName for your widget provider
        myProvider = ComponentName(context, autoclass(f'{package_name}.CarouselWidgetProvider'))

        # Check if pinning is supported
        if appWidgetManager.isRequestPinAppWidgetSupported():
            # Optional: callback when widget is pinned
            intent = Intent(context, CarouselWidgetProvider)

            successCallback = PendingIntent.getBroadcast(
                context,
                0,
                intent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
            )

            # Request widget pin
            appWidgetManager.requestPinAppWidget(
                myProvider,
                None,
                successCallback
            )
    except Exception as error_from_my_way:
        print("error_from_my_way",error_from_my_way)
        traceback.print_exc()

if DEV:
    dev_object = {
        "gpt pop up": lambda widget: show_home_screen_widget_popup(),
        "my pop up": lambda widget: show_home_screen_widget_popup1(),
        # "vibrate": lambda widget: test_vibration(),
        # "create vibes test channel": lambda widget: create_channel(),
        # "no vibrate": lambda widget: no_vibes(),
        # "delete_all_channels": lambda widget: delete_current_channel(),
        # "test_force_vibration": lambda widget: test_force_vibration(),
        # "ALARM": lambda widget: self.android_notify_tests(),
        # "schedule_notification": lambda widget: self.android_notify_tests(),
    }

class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self.md_bg_color = [0.1, 0.1, 0.1, 1]
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"
        self.interval = self.myconfig.get_interval()
        self.times_tapped = 0

        scroll = ScrollView(size_hint=(1, 1))

        root = MDBoxLayout(
            orientation="vertical",
            padding=[dp(20), dp(30), dp(20), dp(100)],
            spacing=dp(15),
            size_hint_y=None
        )
        root.bind(minimum_height=root.setter("height"))  # makes height dynamic based on content

        # ---------- HEADER ----------
        root.add_widget(Label(
            text="Settings",
            font_size="22sp",
            size_hint_y=None,
            height=dp(40),font_name="RobotoMono"
        ))

        # ---------- INTERVAL SECTION ----------
        root.add_widget(Label(
            text="Wallpaper Change Interval (minutes)",
            size_hint_y=None,
            height=dp(30),font_name="RobotoMono",font_size=sp(13)
        ))

        input_row = MDBoxLayout(orientation="horizontal", spacing=dp(10),
                                size_hint_y=None, height=dp(50))

        self.interval_input = MDTextField(
            text=str(self.interval),
            hint_text="mins",
            size_hint_x=0.55,
        )
        self.interval_input.theme_text_color = "Custom"
        self.interval_input.text_color_focus = [1, 1, 1, 1]
        self.interval_input.text_color_normal = [.8, .8, .8, 1]
        self.interval_input.hint_text_color_normal = [.8, .8, .8, 1]
        self.interval_input.hint_text_color_focus = [1, 1, 1, 1]
        self.interval_input.input_filter = "float"

        save_btn = Button(text="Save", size_hint_x=0.35,font_name="RobotoMono")
        save_btn.bind(on_release=self.save_interval)

        input_row.add_widget(self.interval_input)
        input_row.add_widget(save_btn)
        root.add_widget(input_row)

        self.interval_label = Label(
            text=f"Saved: {smart_convert_minutes(self.interval)}",
            size_hint_y=None,
            height=dp(30),font_name="RobotoMono"
        )
        root.add_widget(self.interval_label)

        # ---------- FLEXIBLE SPACER ----------
        root.add_widget(Widget(size_hint_y=1))

        root.add_widget(Label(
            text="Carousel Tools",
            size_hint_y=None,
            height=dp(30)
        ))

        restart_btn = Button(
            text="Restart Carousel",
            size_hint_y=None,
            height=dp(50)
        )
        restart_btn.bind(on_release=self.restart_service)
        root.add_widget(restart_btn)

        stop_btn = Button(
            text="Stop Carousel",
            size_hint_y=None,
            height=dp(50)
        )
        stop_btn.bind(on_release=self.terminate_carousel)
        root.add_widget(stop_btn)

        # ---------- TEST BUTTON ----------
        ai_btn = Button(
            text="export_waller_folder",
            size_hint_y=None,
            height=dp(50),
            on_release=lambda widget: self.export_waller_folder()
        )
        root.add_widget(ai_btn)



        if DEV:
            for each in dev_object:
                root.add_widget(Button(text = f"test {each}", on_release=dev_object[each],size_hint_y=None,height=dp(50)))

        text = MyLabel(
            text=f"--- v{VERSION} ---",
            size_hint_y=None,
            height=dp(50),font_name="RobotoMono",
            on_release=self.open_logs_screen
        )
        root.add_widget(text)
        scroll.add_widget(root)
        self.add_widget(scroll)

    def open_logs_screen(self,_=None):
        self.times_tapped += 1
        if self.times_tapped == 3:
            self.manager.current = "logs"
            self.times_tapped = 0
    @staticmethod
    def terminate_carousel(*_):
        try:
            Service(name="Wallpapercarousel").stop()
            toast("Successfully Terminated")
        except Exception as e:
            toast("Stop failed", e)

    def save_interval(self, *_):
        try:
            new_val = float(self.interval_input.text)
        except Exception as error_changing_input_to_float:
            print(error_changing_input_to_float)
            traceback.print_exc()
            toast("Enter a valid number")
            return

        if new_val < 0.17:
            toast("Min allowed is 0.17 mins")
            return

        self.myconfig.set_interval(new_val)
        self.interval_label.text = f"Saved: {smart_convert_minutes(new_val)}"
        toast("Saved")

    @staticmethod
    def restart_service(*_):

        def after_stop(*_):
            try:
                Service(name="Wallpapercarousel").start()
                toast("Service boosted!")
            except Exception as error_starting_service:
                print(error_starting_service)
                traceback.print_exc()
                toast("Start failed")

        try:
            Service(name="Wallpapercarousel").stop()
            Clock.schedule_once(after_stop, 1.2)
        except Exception as error_stoping_service:
            print(error_stoping_service)
            traceback.print_exc()
            toast("Stop failed")

    @staticmethod
    def export_waller_folder(_=None):
        """
        Export all images from app-private 'wallpapers' folder
        to public Pictures/Waller/ folder.

        API 29+  : MediaStore + IS_PENDING
        API < 29 : Direct filesystem write + MediaScanner

        Returns:
            list[str]: content:// URIs (29+) or file paths (<29)
        """

        from jnius import autoclass
        import os
        from android_notify.config import get_python_activity_context

        # Android core
        MediaStoreImages = autoclass("android.provider.MediaStore$Images$Media")
        MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")
        ContentValues = autoclass("android.content.ContentValues")
        Environment = autoclass("android.os.Environment")
        BuildVersion = autoclass("android.os.Build$VERSION")
        Integer = autoclass("java.lang.Integer")

        # Fast native copy
        Files = autoclass("java.nio.file.Files")
        Paths = autoclass("java.nio.file.Paths")

        # Media scanner (pre-29)
        MediaScannerConnection = autoclass(
            "android.media.MediaScannerConnection"
        )

        context = get_python_activity_context()
        resolver = context.getContentResolver()
        exported_uris = []

        # Internal app folder
        folder_path = os.path.join(makeDownloadFolder(), "wallpapers")
        if not os.path.isdir(folder_path):
            return exported_uris

        for filename in os.listdir(folder_path):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue

            source_path = os.path.join(folder_path, filename)

            # MIME type
            if filename.lower().endswith(".png"):
                mime = "image/png"
            elif filename.lower().endswith(".webp"):
                mime = "image/webp"
            else:
                mime = "image/jpeg"

            # ─────────────────────────────────────────────
            # API < 29 → Direct filesystem + MediaScanner
            # ─────────────────────────────────────────────
            if BuildVersion.SDK_INT < 29:
                pictures = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_PICTURES
                ).getAbsolutePath()

                dest_dir = os.path.join(pictures, "Waller")
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, filename)

                try:
                    with open(source_path, "rb") as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())

                    MediaScannerConnection.scanFile(
                        context,
                        [dest_path],
                        [mime],
                        None
                    )

                    exported_uris.append(dest_path)

                except Exception as e:
                    print("Pre-29 export error:", e)

                continue

            # ─────────────────────────────────────────────
            # API 29+ → MediaStore (scoped storage)
            # ─────────────────────────────────────────────
            values = ContentValues()
            values.put(MediaColumns.DISPLAY_NAME, filename)
            values.put(MediaColumns.MIME_TYPE, mime)
            values.put(
                MediaColumns.RELATIVE_PATH,
                Environment.DIRECTORY_PICTURES + "/Waller"
            )
            values.put(MediaColumns.IS_PENDING, Integer(1))

            uri = resolver.insert(
                MediaStoreImages.EXTERNAL_CONTENT_URI,
                values
            )

            if not uri:
                continue

            try:
                out = resolver.openOutputStream(uri)

                # Fast, native copy
                Files.copy(
                    Paths.get(source_path),
                    out
                )

                out.flush()
                out.close()

                values.clear()
                values.put(MediaColumns.IS_PENDING, Integer(0))
                resolver.update(uri, values, None, None)

                exported_uris.append(str(uri))

            except Exception as e:
                print("MediaStore export error:", e)
                resolver.delete(uri, None, None)

        print("exported_uris:", exported_uris)
        toast("Exported: To Pictures/Waller")
        return exported_uris
