from kivymd.app import MDApp
from kivy.properties import BooleanProperty, ListProperty
from kivymd.uix.boxlayout import MDBoxLayout

class Row(MDBoxLayout):
    my_widgets = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for each_widget in self.my_widgets:
            self.add_widget(each_widget)


class Column(MDBoxLayout):
    my_widgets = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        for each_widget in self.my_widgets:
            self.add_widget(each_widget)



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
