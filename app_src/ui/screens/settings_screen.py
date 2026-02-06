import traceback, time, os
from pathlib import Path

from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.uix.button import Button
# from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp, sp
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivymd.uix.button import MDButtonText, MDButton, MDIconButton, MDButtonIcon
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField

from android_notify.core import asks_permission_if_needed
from android_notify.config import get_python_activity_context,autoclass
from android_notify.internal.java_classes import PendingIntent,Intent
from android_notify import NotificationHandler,Notification
from android_widgets import get_package_name

from android_notify.internal.permissions import can_show_permission_request_popup
from ui.widgets.android import toast
from ui.widgets.layouts import Row, Column
from utils.constants import DEV, VERSION
from utils.helper import Service, appFolder, smart_convert_minutes
from utils.config_manager import ConfigManager
from utils.android import add_home_screen_widget
from kivymd.app import MDApp


from utils.helper import load_kv_file  # type

load_kv_file(py_file_absolute_path=__file__)

class MyLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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


def my_with_callback():
    def android_print(text):
        print(text)
    try:

        def the_caller(*args):
            android_print("Wisdom")
            for each in args:
                android_print(str(each))

        print("got here")
        from android_notify.internal.permissions import my_ask_with_callback
        print("got here1")
        my_ask_with_callback(the_caller)
        print("got here2")

    except Exception as e:
        print('Notify error:', e)



def show_home_screen_widget_popup1():
    from jnius import autoclass
    from android_widgets import get_package_name
    try:
        # Android classes
        AppWidgetManager = autoclass('android.appwidget.AppWidgetManager')
        ComponentName = autoclass('android.content.ComponentName')

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
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT # type: ignore
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


def regular_ask():
    NotificationHandler.asks_permission()


def regular_has():
    print(f"Permission State: {NotificationHandler.has_permission()}")



from android_notify.internal.permissions import open_notification_settings_screen
dev_object={}
if DEV:
    dev_object = {
        "regular_has": lambda widget: regular_has(),
        "regular_ask": lambda widget: regular_ask(),
        "open_notification_settings_screen": lambda widget: open_notification_settings_screen(),
        "my_with_callback": lambda widget: my_with_callback(),
        "my pop up": lambda widget: show_home_screen_widget_popup1(),
        # "vibrate": lambda widget: test_vibration(),
        # "create vibes test channel": lambda widget: create_channel(),
        # "no vibrate": lambda widget: no_vibes(),
        # "delete_all_channels": lambda widget: delete_current_channel(),
        # "test_force_vibration": lambda widget: test_force_vibration(),
        # "ALARM": lambda widget: self.android_notify_tests(),
        # "schedule_notification": lambda widget: self.android_notify_tests(),
    }

def get_current_wallpaper():
    try:
        current_wallpaper_store_path = os.path.join(appFolder(), 'wallpaper.txt')
        with open(current_wallpaper_store_path, "r") as f:
            path= f.read()
    except FileNotFoundError:
        path= "assets/icons/icon.png"
    return path or "assets/icons/icon.png"

class TextButton(MDButton):
    text = StringProperty("")
    text_color = StringProperty("")
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.radius = [5]
        self.txt = MDButtonText(text=self.text,
                                theme_text_color='Custom'
                                )
        self.bind(text=self.set_val,text_color=self.set_text_color)
        self.add_widget(self.txt)
        Clock.schedule_once(self.fix_width)

    def set_val(self, instance, value):
        self.txt.text = value
    def set_text_color(self, instance, value):
        self.txt.text_color = value
        print("self.txt.text_color = value",self.txt.text_color)

    def fix_width(self,*_):
        self.adjust_width()

class ToggleButton(MDIconButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.icon = "pause"


    def on_release(self):
        self.icon = "play" if self.icon == "pause" else "pause"


class HomeScreenImageDisplay(MDBoxLayout):
    source = StringProperty()
    title = StringProperty()
    image_size = ListProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.adaptive_size=True
        self.spacing =dp(5)
        # self.size_hint = (None, None)

        title_label = MDLabel(text=self.title,adaptive_size=True,theme_font_name ="Custom",font_name="Roboto",bold=True)
        title_label.theme_font_size="Custom"
        title_label.font_size=sp(14)
        title_label.theme_text_color="Custom"
        # title_label.text_color = 'white'
        title_label.color = get_color_from_hex("#98F1DD")
        title_label.padding = [dp(5),dp(2)]
        title_label.radius = [dp(5)]
        title_label.md_bg_color = get_color_from_hex("#262C3A")
        self.image = FitImage(
            source=self.source,
            size_hint=(1, 1),
            fit_mode="cover",

        )
        self.image.radius=[10]
        self.image.size_hint = (None, None)
        self.image.size = self.image_size


        self.add_widget(title_label)
        self.add_widget(self.image)

class IconTextButton(MDButton):
    icon = StringProperty()
    text = StringProperty()

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.theme_bg_color = "Custom"
        self.md_bg_color = kwargs["md_bg_color"] if "md_bg_color" in kwargs else [.2, .2, .2, 1]
        self.radius = [5]
        self.icon_object = MDButtonIcon(icon=self.icon,
                                     # theme_text_color='Custom', text_color='white'
                                     )
        self.add_widget(self.icon_object)
        self.text_object = MDButtonText(text="self.text",
                                     theme_text_color='Custom', text_color='white'
                                     )
        self.add_widget(self.text_object)

        Clock.schedule_once(self.fix_width)


    def fix_width(self, *_):
        self.adjust_width()

class HomeScreenWidgetControllerUI(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.adaptive_height=True
        padding = [dp(10),0,dp(10),0]
        # d=.15
        # d=.55
        d=.75
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y = None,
            md_bg_color=[d,d,d,1],
            padding=padding,radius=[dp(10),dp(10),dp(0),0]
        )
        header.adaptive_width=True
        header.height=dp(50)

        header_text = MDLabel(text="Home Screen Widget")#,theme_font_name ="Custom",font_name="Roboto",bold=True)
        header_text.theme_font_size ="Custom"
        header_text.font_size =sp(14)
        header_text.pos_hint = {"center_y": 0.5}
        # header_text.theme_text_color = 'Custom'
        # header_text.theme_bg_color = 'Custom'
        # header_text.md_bg_color = [1,1,0,1]
        header_text.adaptive_size=True

        header.add_widget(header_text)


        main_content = MDBoxLayout(adaptive_size=True,size_hint_x=1,spacing=dp(10),padding=[dp(10)],radius=[0,dp(10),dp(10),dp(10)])
        main_content.orientation = "vertical"#height=True,size_hint_x=1,spacing=dp(10),padding=padding,md_bg_color= [.3,1,.3,1])
        s=.2
        main_content.md_bg_color= [s,s,s,.3]
        self.countdown_label =MDLabel(text="0:13",pos_hint = {"right": 1},adaptive_size=True,
                                      # theme_text_color = 'Custom',
                                      # text_color = 'white',
                                      theme_font_name ="Custom",font_name="Roboto",bold=True)
        main_content.add_widget(self.countdown_label)#,md_bg_color=[1,0,1,1]))

        images_layout = MDBoxLayout(adaptive_height=True,size_hint_x=1,spacing=dp(10))
        # images_layout.adaptive_width=True

        self.current_image_layout = HomeScreenImageDisplay(title="Current", source=get_current_wallpaper(), image_size=(dp(120), dp(120)))
        self.next_image_layout = HomeScreenImageDisplay(title="Next", source="assets/icons/icon.png", image_size=(dp(60), dp(60)))
        images_layout.add_widget(self.current_image_layout)
        images_layout.add_widget(self.next_image_layout)

        self.skip_upcoming_wallpaper_button = TextButton(text="Skip Next")
        btns_layout = Row(
            my_widgets = [
                TextButton(text="Change Current"),
                self.skip_upcoming_wallpaper_button
            ],
            adaptive_size=True,
            spacing=dp(10),
            pos_hint={"right": 1}
        )
        main_content.add_widget(images_layout)
        main_content.add_widget(btns_layout)

        last_btns_layout = Row(
            my_widgets = [
                ToggleButton(pos_hint={"right":1}),
                IconTextButton(icon="plus", text="Add to Home Screen",on_release=add_home_screen_widget)
            ],
            adaptive_size=True,
            spacing=dp(10),
            pos_hint={"right": 1}
        )
        main_content.add_widget(last_btns_layout)

        self.add_widget(header)
        self.add_widget(main_content)
        #
        # app = MDApp.get_running_app()
        # app.ui_service_listener.on_countdown_change =self.update_label


    # def update_label(self,seconds):
    #     self.countdown_label.text = seconds
    #
    # def on_changed_homescreen_widget(self,current_wallpaper,next_wallpaper):
    #     self.current_image_layout.image.source = current_wallpaper or self.current_image_layout.image.source
    #     self.next_image_layout.image.source = next_wallpaper or self.next_image_layout.image.source
    #

class SettingsScreen(MDScreen):
    current_image_source=StringProperty()
    next_image_source=StringProperty()
    interval=StringProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"

        self.app = MDApp.get_running_app()
        # b=.1
        # self.md_bg_color = [b,b,b, 1]
        self.app_dir = Path(appFolder())
        self.my_config = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"
        self.interval = str(self.my_config.get_interval())
        self.times_tapped = 0
        #
        # scroll = ScrollView(size_hint=(1, 1))
        #
        # root = Column(
        #     padding=[dp(20), dp(30), dp(20), dp(100)],
        #     spacing=dp(15),
        #     size_hint_y=None,
        #     my_widgets = [
        #         MDLabel(
        #             text="Settings",
        #             font_size="22sp",
        #             size_hint_y=None,
        #             height=dp(40), font_name="RobotoMono"
        #         ),
        #         MDLabel(
        #             text="Wallpaper Change Interval (minutes)",
        #             size_hint_y=None,
        #             height=dp(30), font_name="RobotoMono", font_size=sp(13)
        #         )
        #     ]
        #
        # )
        # root.bind(minimum_height=root.setter("height"))  # makes height dynamic based on content
        #
        # input_row = Row(
        #     spacing=dp(10),
        #     size_hint_y=None,
        #     height=dp(50),
        #     my_widgets=[
        #         MDTextField(
        #             text=str(self.interval),
        #             hint_text="mins",
        #             size_hint_x=0.55,
        #             # theme_text_color="Custom",
        #             text_color_focus=[1, 1, 1, 1],
        #             text_color_normal=[.8, .8, .8, 1],
        #             # hint_text_color_normal=[.8, .8, .8, 1],
        #             # hint_text_color_focus=[1, 1, 1, 1],
        #             input_filter="float"
        #         ),
        #         Button(text="Save", size_hint_x=0.35, font_name="RobotoMono", on_release=self.save_interval)
        #     ]
        # )
        #
        #
        # root.add_widget(input_row)
        #
        # self.interval_label = MDLabel(
        #     text=f"Saved: {smart_convert_minutes(self.interval)}",
        #     size_hint_y=None,
        #     height=dp(30),font_name="RobotoMono"
        # )
        # root.add_widget(self.interval_label)
        #
        # # ---------- FLEXIBLE SPACER ----------
        # # root.add_widget(Widget(size_hint_y=1))
        #
        # root.add_widget(MDLabel(
        #     text="Carousel Tools",
        #     size_hint_y=None,
        #     height=dp(30)
        # ))
        #
        # restart_btn = TextButton(
        #     text="Restart Carousel",
        #     size_hint_y=None,
        #     height=dp(50),
        #     on_release=self.restart_service
        # )
        # root.add_widget(restart_btn)
        #
        # stop_btn = TextButton(
        #     text="Stop Carousel",
        #     size_hint_y=None,
        #     height=dp(50),
        #     on_release=self.terminate_carousel
        # )
        # root.add_widget(stop_btn)
        #
        # export_folder_btn = TextButton(
        #     text="export wallpapers",
        #     size_hint_y=None,
        #     height=dp(50),
        #     on_release=lambda widget: self.export_waller_folder()
        # )
        # root.add_widget(export_folder_btn)
        #
        # # ---------- TEST BUTTONS ----------
        # if DEV:
        #     for each in dev_object:
        #         root.add_widget(Button(text = f"test {each}", on_release=dev_object[each],size_hint_y=None,height=dp(50)))
        #
        # self.homeScreenWidgetControllerUI = HomeScreenWidgetControllerUI()
        # root.add_widget(self.homeScreenWidgetControllerUI)
        #
        # text = MyLabel(
        #     text=f"--- v{VERSION} ---",
        #     size_hint_y=None,
        #     height=dp(50),font_name="RobotoMono",
        #     on_release=self.open_logs_screen
        # )
        # root.add_widget(text)
        #
        #
        # scroll.add_widget(root)
        # self.add_widget(scroll)


        # self.add_widget(root) for auto reload
        # self.save_interval()
        self.current_image_source = get_current_wallpaper()
        self.next_image_source =  "assets/icons/icon.png"

    @staticmethod
    def toggle_home_screen_widget_loop(widget=None):
        widget.icon = "play" if widget.icon == "pause" else "pause"
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
        # print("saving interval")
        # app = MDApp.get_running_app()
        # # app.device_theme = "dark"
        # app.device_theme = "light" if app.device_theme == "dark" else "dark"
        # print(app.device_theme)
        # return
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

        self.my_config.set_interval(new_val)
        self.interval_label.text = f"Saved: {smart_convert_minutes(new_val)}"
        toast("Saved")
    def update_label(self,seconds):
        if self.ids.pause_home_screen_widget_loop_button.icon == "pause":
            self.ids.countdown_label.text = seconds

    def restart_service(self,*_):

        def after_stop(*_):
            try:
                self.app.start_service()
                # Service(name="Wallpapercarousel").start()
                toast("Service boosted!")
            except Exception as error_starting_service:
                print(error_starting_service)
                traceback.print_exc()
                toast("Start failed")

        try:
            # TODO call service server to stop, so it an end thread and avoid SECURITY ERROR when starting service
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

        import os
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
        folder_path = os.path.join(appFolder(), "wallpapers")
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
    def on_changed_homescreen_widget(self,current_wallpaper,next_wallpaper):
        self.current_image_source = current_wallpaper or self.current_image_source
        self.next_image_source = next_wallpaper or self.next_image_source
