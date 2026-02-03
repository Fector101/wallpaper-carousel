from android_notify.config import on_android_platform, from_service_file
from kivy.properties import BooleanProperty

if on_android_platform() and not from_service_file():
    from kivymd.toast import toast # type: ignore

else:
    def toast(text=None,length_long=0):
        print(f'Fallback toast - text: {text}, length_long: {length_long}')

if not from_service_file():
    from kivymd.app import MDApp

current_theme = None
class ThemedWidget:
    current_theme = BooleanProperty(None)
    def __init__(self):
        self.app = MDApp.get_running_app()
        self.app.bind(device_light_mode_state=self.setTheme)
        self.setTheme()

    def setTheme(self,app=None,value=None):
        global current_theme
        if current_theme == value:
            return
        current_theme = value
        if self.app.device_light_mode_state:
            self.lightMode()
        else:
            self.darkMode()

    def darkMode(self):
        raise NotImplementedError

    def lightMode(self):
        raise NotImplementedError

