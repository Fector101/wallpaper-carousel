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




# from jnius import PythonJavaClass, java_method


# from android.config import ACTIVITY_CLASS_NAME, ACTIVITY_CLASS_NAMESPACE
# ACTIVITY_CLASS_NAME = os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")
# ACTIVITY_CLASS_NAMESPACE = ACTIVITY_CLASS_NAME.replace('.','/')
# ACTIVITY_CLASS_NAME, ACTIVITY_CLASS_NAMESPACE = ['','']
# print(ACTIVITY_CLASS_NAME,"||",ACTIVITY_CLASS_NAMESPACE)
#
#
#
# def android_print(text):
#     print(text)
#
# class _onRequestPermissionsCallback(PythonJavaClass):
#     """Callback class for registering a Python callback from
#     onRequestPermissionsResult in PythonActivity.
#     """
#     __javainterfaces__ = [ACTIVITY_CLASS_NAMESPACE + '$PermissionsCallback']
#     __javacontext__ = 'app'
#
#     def __init__(self, func):
#         self.func = func
#         android_print("one_ring_to_rule_them_all3 self.func = func")
#         super().__init__()
#         android_print("one_ring_to_rule_them_all3 self.func = func super")
#
#     @java_method('(I[Ljava/lang/String;[I)V')
#     def onRequestPermissionsResult(self, requestCode,
#                                    permissions, grantResults):
#         self.func(requestCode, permissions, grantResults)
#
# def my_ask_with_callback(python_callback):
#     android_print("one_ring_to_rule_them_all0")
#     _java_callback = _onRequestPermissionsCallback(python_callback)
#     android_print("one_ring_to_rule_them_all1")
#     mActivity = autoclass(ACTIVITY_CLASS_NAME).mActivity
#     android_print("one_ring_to_rule_them_all2")
#     mActivity.addPermissionsCallback(_java_callback)
#     android_print("one_ring_to_rule_them_all3")
#     mActivity.requestPermissionsWithRequestCode(
#         ["android.permission.POST_NOTIFICATIONS"], 202)
#     android_print("one_ring_to_rule_them_all4")
#










# from kivy.app import App
# from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.progressbar import ProgressBar
# from kivy.uix.button import Button
# from kivy.uix.label import Label
# from utils.helper import fix_input_on_linux
# from utils.constants import DEFAULT_UPDATE_DOWNLOADER_UI_PORT, DEFAULT_UPDATE_DOWNLOADER_SERVICE_PORT, \
#     UpdateDownloaderServiceServerAddress,UpdateDownloaderUIListenerAddress
#
# import threading
# import json
#
# from pythonosc import dispatcher, osc_server, udp_client
#
# # 🔧 CONFIG (match your service)
# SERVICE_PORT = DEFAULT_UPDATE_DOWNLOADER_SERVICE_PORT   # service listens here
# UI_PORT = DEFAULT_UPDATE_DOWNLOADER_UI_PORT        # UI listens here
# fix_input_on_linux()
#
#
# class DownloaderUI(BoxLayout):
#
#     def __init__(self, **kwargs):
#         super().__init__(orientation='vertical', spacing=10, padding=10, **kwargs)
#
#         self.progress = ProgressBar(max=100, value=0)
#         self.label = Label(text="Waiting...", size_hint=(1, 0.3))
#
#         self.pause_btn = Button(text="Pause")
#         self.cancel_btn = Button(text="Cancel")
#
#         self.add_widget(self.label)
#         self.add_widget(self.progress)
#         self.add_widget(self.pause_btn)
#         self.add_widget(self.cancel_btn)
#
#         # OSC client → send commands to service
#         self.client = udp_client.SimpleUDPClient("127.0.0.1", SERVICE_PORT)
#
#         self.pause_btn.bind(on_press=self.toggle_pause)
#         self.cancel_btn.bind(on_press=self.cancel_download)
#
#         # Start OSC server (listener)
#         self.start_osc_server()
#
#     # -------------------------
#     # OSC SERVER (RECEIVE)
#     # -------------------------
#     def start_osc_server(self):
#         disp = dispatcher.Dispatcher()
#
#         disp.map(UpdateDownloaderUIListenerAddress.PROGRESS.value, self.on_progress)
#         disp.map(UpdateDownloaderUIListenerAddress.DONE.value, self.on_done)
#         disp.map(UpdateDownloaderUIListenerAddress.PAUSED.value, self.on_paused)
#         disp.map(UpdateDownloaderUIListenerAddress.RESUMED.value, self.on_resumed)
#         disp.map(UpdateDownloaderUIListenerAddress.CANCELLED.value, self.on_cancelled)
#         disp.map(UpdateDownloaderUIListenerAddress.ERROR.value, self.on_error)
#
#         def run():
#             server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", UI_PORT), disp)
#             print(f"UI listening on {UI_PORT}")
#             server.serve_forever()
#
#         threading.Thread(target=run, daemon=True).start()
#
#     # -------------------------
#     # RECEIVE HANDLERS
#     # -------------------------
#     def on_progress(self, addr, data):
#         data = json.loads(data)
#         percent = data.get("percent", 0)
#
#         self.progress.value = percent
#         self.label.text = f"Downloading... {percent}%"
#
#     def on_done(self, addr, data):
#         self.progress.value = 100
#         self.label.text = "Download Complete ✅"
#
#     def on_paused(self, addr, data):
#         self.label.text = "Paused ⏸"
#
#     def on_resumed(self, addr, data):
#         self.label.text = "Resumed ▶"
#
#     def on_cancelled(self, addr, data):
#         self.label.text = "Cancelled ❌"
#         self.progress.value = 0
#
#     def on_error(self, addr, data):
#         data = json.loads(data)
#         self.label.text = f"Error: {data.get('error')}"
#
#     # -------------------------
#     # SEND COMMANDS
#     # -------------------------
#     def toggle_pause(self, instance):
#         self.client.send_message(UpdateDownloaderServiceServerAddress.TOGGLE_PAUSE_ND_RESUME.value, "")
#         if self.pause_btn.text == "Pause":
#             self.pause_btn.text = "Resume"
#         else:
#             self.pause_btn.text = "Pause"
#
#     def cancel_download(self, instance):
#         self.client.send_message(UpdateDownloaderServiceServerAddress.CANCEL.value, "")
#
#
# class TestApp(App):
#     def build(self):
#         return DownloaderUI()
#
#
# if __name__ == "__main__":
#     TestApp().run()