import os
import traceback

from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, ListProperty, ObjectProperty, NumericProperty, BooleanProperty

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDIconButton, MDButtonIcon, MDButtonText
from kivymd.uix.label import MDLabel, MDIcon

from ui.screens.full_screen import BorderMDBoxLayout
from ui.widgets.android import toast
from ui.widgets.layouts import LoadingLayout, Column, MyMDScreen, AdaptiveLabel, Row

from utils.android import add_home_screen_widget
from utils.config_manager import ConfigManager
from utils.constants import DEV, theme_colors, VERSION
from utils.helper import Service, appFolder, smart_convert_minutes, is_running_debug_build
from utils.logger import app_logger
from utils.model import get_app

my_config = ConfigManager()


class MyLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def start_short_task_service():
    from android import mActivity  # type: ignore
    from jnius import autoclass
    context = mActivity.getApplicationContext()
    service_name = "Shorttask"
    service = autoclass(context.getPackageName() + '.Service' + service_name.capitalize())
    service.start(mActivity, "")


def schedule_workmanager(seconds=20, message="Arg from Python"):
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


value__ = 100


def schedule_alarm():
    import time
    from android_widgets import get_package_name
    from android_notify.config import get_python_activity_context, autoclass
    from android_notify.internal.java_classes import PendingIntent, Intent
    time_in_secs = value__ * 60
    ##p("time_in_secs", time_in_secs)
    from android_notify.internal.java_classes import String
    Context = autoclass('android.content.Context')
    AlarmManager = autoclass('android.app.AlarmManager')
    context = get_python_activity_context()
    alarm = context.getSystemService(Context.ALARM_SERVICE)

    intent = Intent(context, autoclass(f"{get_package_name()}.TheReceiver"))
    intent.setAction(String("ALARM_ACTION"))
    intent.putExtra(String("message"), String("Arg from Python!"))

    pending = PendingIntent.getBroadcast(
        context, 12334, intent, PendingIntent.FLAG_IMMUTABLE
    )

    trigger_time = int((time.time() + time_in_secs) * 1000)  # 10 seconds later
    alarm.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, trigger_time, pending)


def my_with_callback():
    def android_print(text):
       print(text)

    try:

        def the_caller(*args):
            android_print("Wisdom")
            for each in args:
                android_print(str(each))

        ##p("got here")
        from android_notify.internal.permissions import my_ask_with_callback
        ##p("got here1")
        my_ask_with_callback(the_caller)
        ##p("got here2")

    except Exception as e:
        app_logger.exception(f'Notify error: {e}')


def show_home_screen_widget_popup1():
    from jnius import autoclass
    from android_widgets import get_package_name
    from android_notify.internal.java_classes import PendingIntent, Intent
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
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT  # type: ignore
            )

            # Request widget pin
            appWidgetManager.requestPinAppWidget(
                myProvider,
                None,
                successCallback
            )
    except Exception as error_from_my_way:
        app_logger.exception(f"error_from_my_way: {error_from_my_way}")
        traceback.print_exc()


# from android_notify.internal.permissions import open_notification_settings_screen
dev_object = {}
if DEV:
    dev_object = {
        # "check update": lambda widget: check_update()
        # "schedule_alarm": lambda widget: schedule_alarm(),
        # "start_short_task_service": lambda widget: start_short_task_service(),
        # "schedule_workmanager": lambda widget: schedule_workmanager(),
        # "open_notification_settings_screen": lambda widget: open_notification_settings_screen(),
        # "show_home_screen_widget_popup1": lambda widget: show_home_screen_widget_popup1(),
    }


def get_current_wallpaper():
    try:
        current_wallpaper_store_path = os.path.join(appFolder(), 'wallpaper.txt')
        with open(current_wallpaper_store_path, "r") as f:
            path = f.read()
    except FileNotFoundError:
        path = "assets/icons/icon.png"
    return path or "assets/icons/icon.png"


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
        from kivymd.uix.fitimage import FitImage
        from kivymd.uix.label import MDLabel
        self.orientation = "vertical"
        self.adaptive_size = True
        self.spacing = dp(5)
        # self.size_hint = (None, None)

        title_label = MDLabel(text=self.title, adaptive_size=True, theme_font_name="Custom", font_name="Roboto",
                              bold=True)
        title_label.theme_font_size = "Custom"
        title_label.font_size = sp(14)
        title_label.theme_text_color = "Custom"
        # title_label.text_color = 'white'
        title_label.color = theme_colors.PRIMARY
        title_label.padding = [dp(5), dp(2)]
        title_label.radius = [dp(5)]
        title_label.md_bg_color = theme_colors.SECONDARY
        self.image = FitImage(
            source=self.source,
            size_hint=(1, 1),
            fit_mode="cover",

        )
        self.image.radius = [10]
        self.image.size_hint = (None, None)
        self.image.size = self.image_size

        self.add_widget(title_label)
        self.add_widget(self.image)


class IconTextButton(MDButton):
    icon = StringProperty()
    text = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivymd.uix.button import MDButtonText, MDButtonIcon
        self.app = get_app()
        self.theme_bg_color = "Custom"
        self.md_bg_color = kwargs["md_bg_color"] if "md_bg_color" in kwargs else [.2, .2, .2, 1]
        self.radius = [5]
        self.icon_object = MDButtonIcon(icon=self.icon)
        self.add_widget(self.icon_object)
        self.text_object = MDButtonText(text="self.text",
                                        theme_text_color='Custom',
                                        text_color='white'
                                        )
        self.add_widget(self.text_object)
        self.app.bind(device_theme=self._set_theme_color)

        Clock.schedule_once(self.fix_width)

    def _set_theme_color(self, _, theme):
        is_dark = theme == "dark"
        self.md_bg_color = [.2, .2, .2, 1] if is_dark else [.85, .85, .85, 1]
        self.text_object.text_color = 'white' if is_dark else 'black'

    def fix_width(self, *_):
        self.adjust_width()


class QuickSetButton(MDButton):
    text = StringProperty("")
    line_color = [.25, .25, .25, 1]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivymd.uix.button import MDButtonText
        self.app = get_app()

        self.radius = 20
        self.theme_bg_color = "Custom"
        self.theme_height = "Custom"
        self.theme_width = "Custom"
        self.line_color = [.25, .25, .25, 1]
        self.clicked_bg_color = [.15, .15, .15, 1]
        self.un_clicked_bg_color = [.1, .1, .1, 1]
        self.md_bg_color = self.un_clicked_bg_color
        self.size_hint = [None, None]
        self.height = dp(40)
        self.width = dp(80)

        self.text_widget = MDButtonText(
            text=self.text,
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            theme_text_color="Custom",
            font_name="RobotoMono"
        )
        self.bind(text=self.set_text)
        self.app.bind(device_theme=self.set_theme_color)
        # Something Weird is happening when I add text widget in __init__
        # It gets added under Buttons Background Color, test with transparent color to see [0,0,0,0]
        Clock.schedule_once(self.add_thing)

    def add_thing(self, dt):
        self.set_theme_color()
        self.add_widget(self.text_widget)

    def set_theme_color(self, *args):
        is_dark = self.app.device_theme == "dark"
        self.text_widget.text_color = "black" if not is_dark else "white"
        self.clicked_bg_color = [.15, .15, .15, 1] if is_dark else [.75, .75, .75, 1]
        self.un_clicked_bg_color = [.1, .1, .1, 1] if is_dark else [.85, .85, .85, 1]
        self.md_bg_color = self.un_clicked_bg_color

    def set_text(self, instance, value):
        self.text_widget.text = value

    def on_release(self, *args) -> None:
        settings_screen = self.app.sm.settings_screen
        for each_button in settings_screen.ids.QuickSetButtonsBox.children:
            each_button.md_bg_color = self.un_clicked_bg_color
        self.md_bg_color = self.clicked_bg_color
        settings_screen.ids.interval_input_con.disabled = False
        settings_screen.ids.interval_input.text = settings_screen.interval
        settings_screen.ids.save_btn_text.text = "Save"
        # p("self.clicked_bg_color", self.clicked_bg_color)
        settings_screen.ids.interval_input.text = self.__get_mins()

    def __get_mins(self):
        mins_text = "Failed"
        try:
            # TODO fix me for larger mins
            mins_text = self.text.split(":")[0]
            if mins_text[0] == "0":
                mins_text = mins_text[1:]


        except Exception as error_getting_mins_text_from_quick_add:
            app_logger.exception(error_getting_mins_text_from_quick_add)
            traceback.print_exc()

        return mins_text


class BorderInput(BorderMDBoxLayout):
    input = ObjectProperty(None)
    line_width = NumericProperty(1.5)
    disabled_color = ListProperty((1, 1, 1, .3))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.radius = dp(20)
        self.disabled_color = [1, 1, 1, .3]
        self.app.bind(device_theme=self._set_theme_color)

    def _set_theme_color(self, _, theme):
        is_dark = theme == "dark"
        self.disabled_color = [1, 1, 1, .3] if is_dark else [.5, .5, .5, .5]
        if self.input and not self.input.focus:
            self.bg_color_instr.rgba = [.7, .7, .7, .6] if not is_dark else [.5, .5, .5, .8]

    def on_disabled(self, instance, value):
        self.bg_color_instr.rgba = self.disabled_color

    def doing_focus(self, _, state):
        if state:
            self.bg_color_instr.rgba = theme_colors.INPUT_FOCUS_BORDER
        else:
            theme = self.app.device_theme if hasattr(self.app, "device_theme") else "dark"
            is_dark = theme == "dark"
            self.bg_color_instr.rgba = [.5, .5, .5, .8] if is_dark else [.7, .7, .7, .6]

    def add_widget(self, widget, *args, **kwargs):
        self.input = widget
        self.input.bind(focus=self.doing_focus)

        super().add_widget(widget, *args, **kwargs)


class ToggleSliderRow(Row):
    title_text = StringProperty("")
    sub_title_text = StringProperty("")
    active = BooleanProperty(False)
    change_function = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivymd.uix.selectioncontrol import MDSwitch
        self.app = get_app()
        self.sub_text_widget = None
        self.adaptive_height = True
        self.spacing = dp(3)
        self.__is_subtitle_added = False

        self.text_layout = Column(
            adaptive_height=1,
            spacing=dp(1),
            pos_hint={"center_y": .5})  # ,md_bg_color=[1,0,0,.5])
        title_widget = AdaptiveLabel(text=self.title_text, size_hint=[None, None], color=[1, 1, 1, 1])

        self.title_widget_ref = title_widget
        self.text_layout.add_widget(title_widget)
        self.add_widget(self.text_layout)

        self.switch = MDSwitch(pos_hint={"center_y": .5}, track_color_active=theme_colors.PRIMARY,
                               thumb_color_active=theme_colors.SECONDARY, on_active=self.do_thing,
                               on_release=self.set_from_user_key)
        self.switch.title_text = self.title_text
        self.add_widget(self.switch)
        self.bind(active=self.switch.setter("active"))
        # self.switch.bind(on_active=self.on_active)

        self.bind(sub_title_text=self.add_subtitle, title_text=title_widget.setter("text"))
        self.app.bind(device_theme=self._set_theme_color)
        # self.bind(title_text=title_widget.setter("text"))

    #
    def add_subtitle(self, _, v):
        if v and not self.__is_subtitle_added:
            self.__is_subtitle_added = True
            self.sub_text_widget = AdaptiveLabel(text=self.sub_title_text, size_hint=[None, None], color="grey",
                                                 font_size=sp(14))
            self.text_layout.bind(width=self.wrap_text_width)
            self.text_layout.add_widget(self.sub_text_widget)
            self.bind(sub_title_text=self.sub_text_widget.setter("text"))

    def set_from_user_key(self, instance):
        instance.from_user = True

    def _set_theme_color(self, _, theme):
        is_dark = theme == "dark"
        if hasattr(self, 'title_widget_ref'):
            self.title_widget_ref.color = [1, 1, 1, 1] if is_dark else [0, 0, 0, 1]

    def do_thing(self, instance, *args):
        if self.change_function:
            self.change_function(instance, self.switch.active,
                                 instance.from_user if hasattr(instance, "from_user") else False)
            instance.from_user = False

    def wrap_text_width(self, i, v):
        # p(f"self.text_layout {self.text_layout.width}, dp:{dp(self.text_layout.width)}") # self.text_layout 470.0, dp:940.0
        self.sub_text_widget.text_size = [self.text_layout.width, None]

    def on_title_text(self, widget, value):
        self.switch.title_text = value


class SettingsSection(Column):
    title_text = StringProperty()
    content_layout = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.adaptive_height = True
        self.padding = [0, dp(10)]
        self.spacing = dp(5)
        app = get_app()
        is_dark = app.device_theme == "dark" if hasattr(app, "device_theme") else True
        tc = [0.7, 0.7, 0.9, 1.0] if is_dark else [0.3, 0.3, 0.5, 1.0]
        c = .67 if is_dark else .85
        ca = .1 if is_dark else .35
        self.title_widget = AdaptiveLabel(text=self.title_text, size_hint=[None, None], color=tc,
                                          pos_hint={"left": 1})
        self.title_widget.main_container = True
        self.bind(title_text=self.title_widget.setter("text"))
        self.add_widget(self.title_widget)

        self.content_layout = Column(
            md_bg_color=[c, c, c, ca], radius=dp(5),
            adaptive_height=1, padding=[dp(10), dp(15)],
            spacing=dp(30))
        self.content_layout.main_container = True
        self.add_widget(self.content_layout)
        self.bind(minimum_height=self.setter("height"))
        app.bind(device_theme=self._set_theme)

        # ToggleSliderRow
        # interval = my_config.get_interval()
        # self.interval_label.text = f"Saved: {}"
        # t = ToggleSliderRow(title_text="Use On-wake",sub_title_text='Get a new wallpaper each time you "turn on screen".')
        # t1 = ToggleSliderRow(title_text="Use interval",sub_title_text=f'Get a new wallpaper every "{smart_convert_minutes(interval)}".')
        #
        #
        # self.content_layout.add_widget(t)
        # self.content_layout.add_widget(t1)

    # [0.596078431372549, 0.9450980392156862, 0.8666666666666667, 1.0]
    def add_widget(self, widget, *args, **kwargs):
        if hasattr(widget, "main_container"):
            super().add_widget(widget, *args, **kwargs)
        elif self.content_layout:
            self.content_layout.add_widget(widget)

    def _set_theme(self, _, theme):
        is_dark = theme == "dark"
        tc = [0.7, 0.7, 0.9, 1.0] if is_dark else [0.3, 0.3, 0.5, 1.0]
        c = .67 if is_dark else .85
        ca = .1 if is_dark else .35
        self.title_widget.color = tc
        self.content_layout.md_bg_color = [c, c, c, ca]


class MyMDButton(MDButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.theme_bg_color = "Custom"
        self.md_bg_color = theme_colors.BUTTON_BG
        self.app.bind(device_theme=self._set_theme_color)

    def _set_theme_color(self, *_):
        self.md_bg_color = theme_colors.BUTTON_BG


class ThemeOptionCard(ButtonBehavior, MDBoxLayout):
    icon = StringProperty("moon-waning-crescent")
    label = StringProperty("Dark")
    preference_value = StringProperty("dark")
    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.orientation = "vertical"
        self.adaptive_size = True
        self.spacing = dp(4)
        self.padding = [dp(12), dp(10)]
        self.radius = [12]
        self.width = dp(90)
        self.bind(minimum_height=self.setter("height"))

        with self.canvas.after:
            self._card_border_color = Color(rgba=(0, 0, 0, 0))
            self._card_border = Line(width=dp(1.5))
        self.bind(pos=self._update_card_border, size=self._update_card_border)
        self._update_card_border()

        self.icon_widget = MDIcon(
            icon=self.icon,
            pos_hint={"center_x": 0.5},
            theme_text_color="Custom",
            theme_bg_color="Custom",
            md_bg_color=(0, 0, 0, 0),
        )
        self.label_widget = MDLabel(
            text=self.label,
            halign="center",
            theme_text_color="Custom",
            font_size=sp(12),
            adaptive_size=True,
        )
        self.add_widget(self.icon_widget)
        self.add_widget(self.label_widget)

        self.bind(icon=self.icon_widget.setter("icon"),
                  label=self.label_widget.setter("text"))
        self.bind(active=self._set_theme_color)
        self.app.bind(device_theme=self._set_theme_color)
        self._set_theme_color()

    def _update_card_border(self, *_):
        self._card_border.rounded_rectangle = [self.x, self.y, self.width, self.height, 12]

    def _set_theme_color(self, *_):
        if self.active:
            md_bg = theme_colors.THEME_SELECTOR_ACCENT
            text_color = (0.1, 0.1, 0.1, 1)
            border_color = theme_colors.THEME_SELECTOR_ACCENT
        else:
            md_bg = theme_colors.THEME_SELECTOR_INACTIVE
            text_color = "black" if self.app.device_theme == "light" else "white"
            border_color = (0, 0, 0, 0)
        self.md_bg_color = md_bg
        self.icon_widget.text_color = text_color
        self.label_widget.text_color = text_color
        self.label_widget.bold = self.active
        self._card_border_color.rgba = border_color


class CarouselTools(Column):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.spacing = dp(15)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))

        settings_screen = self.app.sm.get_screen("settings")

        button_box = MDBoxLayout(
            spacing=dp(10),
            size_hint_x=1,
            adaptive_size=True,
            pos_hint={"center_x": 0.5},
        )
        restart_btn = MyMDButton(radius=[5], theme_bg_color="Custom",
                                 on_release=settings_screen.restart_service)
        restart_text = MDButtonText(text="Restart Carousel", size_hint_y=None,
                                    theme_text_color="Custom", height=dp(50))
        restart_btn.add_widget(restart_text)
        self._restart_text = restart_text

        stop_btn = MyMDButton(theme_bg_color="Custom", md_bg_color=theme_colors.BUTTON_BG,
                              radius=[5], pos_hint={"center_x": 0.5},
                              on_release=settings_screen.terminate_carousel)
        stop_text = MDButtonText(text="Stop Carousel", theme_text_color="Custom")
        stop_btn.add_widget(stop_text)
        self._stop_text = stop_text

        button_box.add_widget(restart_btn)
        button_box.add_widget(stop_btn)
        self.add_widget(button_box)

        self.app.bind(device_theme=self._set_theme_color)
        self._set_theme_color()

    def _set_theme_color(self, *_):
        text_color = "black" if self.app.device_theme == "light" else "white"
        self._restart_text.text_color = text_color
        self._stop_text.text_color = text_color


class SettingsScreen(MyMDScreen):
    current_image_source = StringProperty()
    next_image_source = StringProperty()
    interval = StringProperty()
    displayed_interval_value = StringProperty()  # "2 mins"
    is_using_on_wake = BooleanProperty(ConfigManager.get_on_wake_state())
    start_on_app_launch = BooleanProperty(ConfigManager.get_start_on_app_launch())
    start_on_boot = BooleanProperty(ConfigManager.get_start_on_boot())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from pathlib import Path
        from kivymd.app import MDApp
        self.interval_input = None
        self.name = "settings"
        self.app = MDApp.get_running_app()
        self.status_bar_bg = [0.82, 0.82, 0.82, 1] if self.app.device_theme == "light" else [0.23, 0.23, 0.23, 1]
        self.app.bind(device_theme=self.set_theme_color)

        # b=.1
        # self.md_bg_color = [b,b,b, 1]
        self.app_dir = Path(appFolder())
        self.wallpapers_dir = self.app_dir / "wallpapers"
        v = my_config.get_interval()
        self.displayed_interval_value = smart_convert_minutes(v)
        self.interval = str(v)
        self.times_tapped = 0
        self.built_ui = False

    def on_enter(self, *args):
        super().on_enter(*args)
        if not self.built_ui:
            Clock.schedule_once(self._timer_set)
            self.built_ui = True

    def _timer_set(self, _):
        Clock.schedule_once(self.build_ui)

    def build_ui(self, _=None):
        if self.built_ui:
            return
        self.built_ui = True

        from kivy.uix.button import Button
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.textinput import TextInput
        from kivymd.uix.fitimage import FitImage
        from kivymd.uix.gridlayout import MDGridLayout
        from ui.widgets.modals import DialogScreen

        app = self.app

        self.md_bg_color = theme_colors.BG

        root = Column(pos_hint={"top": 1})

        title_text_case = MDBoxLayout(
            padding=[dp(25), dp(self.status_bar_height - 20 if self.status_bar_height > 20 else self.status_bar_height + 20), dp(0), dp(20)],
            size_hint_y=None,
            md_bg_color=theme_colors.BG_ELEVATED,
        )
        title_text_case.bind(minimum_height=title_text_case.setter("height"))
        title_label = MDLabel(
            text="Settings",
            theme_text_color="Custom",
            bold=True,
            color=theme_colors.TEXT_PRIMARY,
            adaptive_size=True,
            theme_font_size="Custom",
            font_name="RobotoMono",
            font_size="22sp",
        )
        title_text_case.add_widget(title_label)
        root.add_widget(title_text_case)

        scroll = ScrollView(size_hint=(1, 1))

        main_container = Column(
            size_hint_y=None,
            padding=[dp(25), dp(25), dp(25), dp(100)],
            spacing=dp(15),
        )
        main_container.bind(minimum_height=main_container.setter("height"))

        interval_heading = MDLabel(
            text="Wallpaper Change Interval (minutes)",
            size_hint_y=None,
            height=dp(30),
            font_name="RobotoMono",
            font_size=sp(13),
            color=theme_colors.TEXT_PRIMARY,
        )
        main_container.add_widget(interval_heading)

        interval_row = Row(spacing=dp(10), size_hint_y=None, height=dp(50))
        interval_input_con = BorderInput(
            padding=[dp(2)],
            size_hint_y=1,
            pos_hint={"center_y": 0.5},
        )
        interval_input_con.disabled = 1
        interval_input = TextInput(
            text=f"Set to {self.displayed_interval_value}",
            multiline=False,
            background_color=[0, 0, 0, 0],
            input_filter="float",
            cursor_color="blue",
            input_type="number",
        )
        interval_input_con.add_widget(interval_input)

        save_btn = MDButton(
            radius=20,
            theme_bg_color="Custom",
            
            theme_line_color="Custom",
            on_release=self.save_interval,
        )
        save_btn.theme_height="Custom"
        save_btn.theme_width="Custom"
        save_btn.width=dp(80)
        save_btn.size_hint_y=.9
        save_btn.pos_hint={"center_y": 0.5}
        save_btn_text = MDButtonText(
            text="Edit",
            size_hint_y=None,
            theme_text_color="Custom",
            height=dp(50),
            font_name="RobotoMono",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        save_btn.add_widget(save_btn_text)

        interval_row.add_widget(interval_input_con)
        interval_row.add_widget(save_btn)
        main_container.add_widget(interval_row)

        quick_set_box = MDGridLayout(
            cols=3,
            adaptive_size=True,
            spacing=dp(10),
            pos_hint={"center_x": 0.5},
        )
        quick_set_box.add_widget(QuickSetButton(text="01:00"))
        quick_set_box.add_widget(QuickSetButton(text="05:00"))
        quick_set_box.add_widget(QuickSetButton(text="15:00"))
        quick_set_box.add_widget(QuickSetButton(disabled=True, opacity=0))
        quick_set_box.add_widget(QuickSetButton(text="60:00"))
        main_container.add_widget(quick_set_box)

        home_widget_section = Column(adaptive_height=True, padding=[dp(10), 0, dp(10), 0])
        home_widget_header = MDBoxLayout(
            size_hint_y=None,
            height=dp(50),
            md_bg_color=theme_colors.BG_ELEVATED,
            radius=[dp(10), dp(10), 0, 0],
            padding=[dp(10), 0, dp(10), 0],
        )
        home_widget_header_label = MDLabel(
            text="Home Screen Carousel Widget",
            theme_font_size="Custom",
            font_size=sp(14),
            pos_hint={"center_y": 0.5},
            adaptive_size=True,
            color=theme_colors.TEXT_PRIMARY,
        )
        home_widget_header.add_widget(home_widget_header_label)

        home_widget_body = Column(
            md_bg_color=theme_colors.BG_CARD,
            adaptive_size=True,
            size_hint_x=1,
            spacing=dp(10),
            padding=[dp(10)],
            radius=[0, 0, dp(10), dp(10)],
        )
        countdown_label = MDLabel(
            text="OnNext Wake" if my_config.get_on_wake_state() else "--:--",
            pos_hint={"right": 1},
            adaptive_size=True,
            theme_text_color="Custom",
            theme_font_name="Custom",
            font_name="Roboto",
            bold=True,
        )
        home_widget_body.add_widget(countdown_label)

        self.current_image_source = get_current_wallpaper()
        self.next_image_source = "assets/icons/icon.png"

        images_row = Row(adaptive_height=True, size_hint_x=1, spacing=dp(10))
        current_col = Column(adaptive_size=True, spacing=dp(5))
        current_label = MDLabel(
            text="Current",
            adaptive_size=True,
            theme_font_name="Custom",
            font_name="Roboto",
            bold=True,
            theme_font_size="Custom",
            font_size=sp(14),
            theme_text_color="Custom",
            text_color=theme_colors.PRIMARY,
            padding=[dp(5), dp(2)],
            radius=[dp(5)],
            md_bg_color=theme_colors.SECONDARY,
        )
        current_image = FitImage(
            source=self.current_image_source,
            fit_mode="cover",
            size_hint=(None, None),
            size=(dp(120), dp(120)),
            radius=[10],
        )
        current_col.add_widget(current_label)
        current_col.add_widget(current_image)

        next_col = Column(adaptive_size=True, spacing=dp(5))
        next_label = MDLabel(
            text="Next",
            adaptive_size=True,
            theme_font_name="Custom",
            font_name="Roboto",
            bold=True,
            theme_font_size="Custom",
            font_size=sp(14),
            theme_text_color="Custom",
            text_color=theme_colors.PRIMARY,
            padding=[dp(5), dp(2)],
            radius=[dp(5)],
            md_bg_color=theme_colors.SECONDARY,
        )
        next_image = FitImage(
            source=self.next_image_source,
            fit_mode="cover",
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            radius=[10],
        )
        next_col.add_widget(next_label)
        next_col.add_widget(next_image)

        images_row.add_widget(current_col)
        images_row.add_widget(next_col)
        self.bind(current_image_source=current_image.setter("source"),
                  next_image_source=next_image.setter("source"))
        home_widget_body.add_widget(images_row)

        skip_row = Row(adaptive_size=True, spacing=dp(10), pos_hint={"right": 1})
        skip_btn = MyMDButton(radius=[5], theme_bg_color="Custom")
        skip_btn_text = MDButtonText(text="Skip Next", theme_text_color="Custom")
        skip_btn.add_widget(skip_btn_text)
        skip_row.add_widget(skip_btn)

        pause_row = Row(adaptive_size=True, spacing=dp(10), pos_hint={"right": 1})
        pause_btn = MDIconButton(
            icon="pause",
            pos_hint={"right": 1},
            on_release=lambda: self.toggle_home_screen_widget_loop(pause_btn),
        )
        add_btn = MyMDButton(
            theme_bg_color="Custom",
            md_bg_color=theme_colors.BUTTON_BG,
            radius=[5],
            on_release=add_home_screen_widget,
        )
        add_icon = MDButtonIcon(icon="plus")
        add_text = MDButtonText(text="Add to Home Screen", theme_text_color="Custom")
        add_btn.add_widget(add_icon)
        add_btn.add_widget(add_text)
        pause_row.add_widget(pause_btn)
        pause_row.add_widget(add_btn)

        home_widget_body.add_widget(skip_row)
        home_widget_body.add_widget(pause_row)

        home_widget_section.add_widget(home_widget_header)
        home_widget_section.add_widget(home_widget_body)
        main_container.add_widget(home_widget_section)

        carousel_section = SettingsSection(title_text="Carousel")
        on_wake_toggle = ToggleSliderRow(change_function=self.set_using_on_wake_config)
        on_wake_toggle.title_text = "Use On-wake"
        on_wake_toggle.sub_title_text = 'Get a new wallpaper each time you "turn on screen".'
        on_wake_toggle.active = self.is_using_on_wake
        carousel_section.content_layout.add_widget(on_wake_toggle)

        interval_toggle = ToggleSliderRow(change_function=self.set_using_on_wake_config)
        interval_toggle.title_text = "Use interval"
        interval_toggle.sub_title_text = f'Get a new wallpaper every "{self.displayed_interval_value}".'
        interval_toggle.active = not self.is_using_on_wake
        carousel_section.content_layout.add_widget(interval_toggle)
        carousel_section.content_layout.add_widget(CarouselTools())
        self._on_wake_toggle = on_wake_toggle
        self._interval_toggle = interval_toggle
        main_container.add_widget(carousel_section)

        autostart_section = SettingsSection(title_text="Auto Start")
        launch_toggle = ToggleSliderRow(change_function=self.set_start_on_app_launch_config)
        launch_toggle.title_text = "On App Launch"
        launch_toggle.sub_title_text = "Automatically start the carousel when you open the app."
        launch_toggle.active = self.start_on_app_launch
        autostart_section.content_layout.add_widget(launch_toggle)

        restart_toggle = ToggleSliderRow(change_function=self.set_start_on_boot_config)
        restart_toggle.title_text = "On Restart"
        restart_toggle.sub_title_text = "Automatically start the carousel when your phone restarts."
        restart_toggle.active = self.start_on_boot
        autostart_section.content_layout.add_widget(restart_toggle)
        main_container.add_widget(autostart_section)

        theme_section = SettingsSection(title_text="Theme")
        theme_row = Row(adaptive_size=True, spacing=dp(10), pos_hint={"center_x": 0.5})
        theme_dark_card = ThemeOptionCard(icon="moon-waning-crescent", label="Dark",
                                          preference_value="dark",
                                          active=self.app.theme_preference == "dark",
                                          on_release=lambda: self.set_theme_preference("dark"))
        theme_adaptive_card = ThemeOptionCard(icon="cellphone", label="Adaptive",
                                              preference_value="adaptive",
                                              active=self.app.theme_preference == "adaptive",
                                              on_release=lambda: self.set_theme_preference("adaptive"))
        theme_light_card = ThemeOptionCard(icon="white-balance-sunny", label="Light",
                                           preference_value="light",
                                           active=self.app.theme_preference == "light",
                                           on_release=lambda: self.set_theme_preference("light"))
        theme_row.add_widget(theme_dark_card)
        theme_row.add_widget(theme_adaptive_card)
        theme_row.add_widget(theme_light_card)
        theme_section.content_layout.add_widget(theme_row)
        main_container.add_widget(theme_section)

        export_section = SettingsSection(title_text="Uninstalling?")
        export_btn = MyMDButton(
            theme_bg_color="Custom",
            md_bg_color=theme_colors.BUTTON_BG,
            radius=[5],
            pos_hint={"center_x": 0.5},
            on_release=self.show_export_dialog,
        )
        export_icon = MDButtonIcon(icon="export-variant")
        export_text = MDButtonText(text="export wallpapers", theme_text_color="Custom")
        export_btn.add_widget(export_icon)
        export_btn.add_widget(export_text)
        export_section.content_layout.add_widget(export_btn)
        main_container.add_widget(export_section)

        version_btn = Button(
            text=f'v{VERSION}{"-debug" if is_running_debug_build() else ""}',
            pos_hint={"right": 1},
            background_color=[0, 0, 0, 0],
            size_hint=[None, None],
            font_name="RobotoMono",
            font_size=sp(14),
            padding=[dp(10), dp(10)],
            on_release=self.open_logs_screen,
        )
        version_btn.size = [version_btn.texture_size[0], dp(50)]
        version_btn.bind(texture_size=self._update_version_btn_size)
        main_container.add_widget(version_btn)

        if DEV:
            for each in dev_object:
                main_container.add_widget(
                    Button(text=f"test {each}", on_release=dev_object[each], size_hint_y=None, height=dp(50)))

        check_update_btn = Button(text="Check For New Version", on_release=self.check_for_update,
                                  size_hint_y=None, height=dp(50))
        check_update_btn.background_normal = ''
        check_update_btn.background_color = theme_colors.BUTTON_BG
        check_update_btn.color = theme_colors.TEXT_PRIMARY
        self._check_update_btn = check_update_btn
        main_container.add_widget(check_update_btn)

        self.export_dialog = DialogScreen(
            icon_name="export-variant",
            header_text="Export Wallpapers?",
            subtitle_text="All wallpapers will be copied to your public Pictures/Waller folder",
            ok_callback=self._export_in_thread,
            ok_button_text="Yes, Copy",
            ok_button_color=[0.2, 0.7, 0.3, 1.0],
        )

        scroll.add_widget(main_container)
        root.add_widget(scroll)
        self.add_widget(root)

        self.ids["title_text_case"] = title_text_case
        self.ids["settings_scroll_view_widget"] = scroll
        self.ids["main_container"] = main_container
        self.ids["interval_input_con"] = interval_input_con
        self.ids["interval_input"] = interval_input
        self.ids["save_btn"] = save_btn
        self.ids["save_btn_text"] = save_btn_text
        self.ids["QuickSetButtonsBox"] = quick_set_box
        self.ids["countdown_label"] = countdown_label
        self.ids["skip_upcoming_wallpaper_button"] = skip_btn
        self.ids["pause_home_screen_widget_loop_button"] = pause_btn
        self.ids["theme_dark_card"] = theme_dark_card
        self.ids["theme_adaptive_card"] = theme_adaptive_card
        self.ids["theme_light_card"] = theme_light_card
        self.ids["btn_icon"] = export_icon
        self.ids["btn_text"] = export_text

        self.interval_input = interval_input
        self.title_label = title_label
        self.interval_heading = interval_heading
        self.home_widget_header = home_widget_header
        self.home_widget_header_label = home_widget_header_label
        self.home_widget_body = home_widget_body
        self.countdown_label = countdown_label
        self.current_label = current_label
        self.next_label = next_label
        self.version_btn = version_btn
        self._bw_widgets = [skip_btn_text, add_text, export_text]
        self._bw_icon_widgets = [add_icon, export_icon]
        self._bw_misc = [pause_btn, countdown_label]
        self._theme_cards = (theme_dark_card, theme_adaptive_card, theme_light_card)

        interval_input.bind(height=self._update_interval_input_padding,
                            line_height=self._update_interval_input_padding,
                            focus=self._update_interval_input_colors)
        interval_input.disabled_foreground_color = interval_input_con.disabled_color
        interval_input_con.bind(disabled_color=interval_input.setter("disabled_foreground_color"))

        save_btn_text.bind(text=self._update_save_btn_theme)
        self.bind(displayed_interval_value=self._on_displayed_interval_value_changed)
        self.bind(is_using_on_wake=self._sync_toggles)
        app.bind(theme_preference=self._sync_theme_cards)

        self._update_interval_input_padding()
        self._update_interval_input_colors()
        self._update_save_btn_theme()
        self._sync_toggles()
        self.set_theme_color(None, app.device_theme)

    def _update_interval_input_padding(self, *_):
        if not self.built_ui or not self.interval_input:
            return
        self.interval_input.padding = [dp(10), (self.interval_input.height - self.interval_input.line_height) / 2]

    def _update_interval_input_colors(self, *_):
        if not self.built_ui or not self.interval_input:
            return
        is_dark = self.app.device_theme == "dark"
        if self.interval_input.focus:
            self.interval_input.foreground_color = [1, 1, 1, 1] if is_dark else [0, 0, 0, 1]
        else:
            self.interval_input.foreground_color = [.8, .8, .8, 1] if is_dark else [.3, .3, .3, 1]

    def _update_save_btn_theme(self, *_):
        if not self.built_ui or not self.ids.save_btn_text:
            return
        is_dark = self.app.device_theme == "dark"
        editing = self.ids.save_btn_text.text == "Edit"
        if editing:
            self.ids.save_btn.md_bg_color = [0.3, 0.3, 0.3, 1] if is_dark else [0.75, 0.75, 0.75, 1]
        else:
            self.ids.save_btn.md_bg_color = theme_colors.PRIMARY
        self.ids.save_btn.line_color = [1, 1, 1, 1] if is_dark else [.7, .7, .7, 1]
        self.ids.save_btn_text.text_color = ("black" if not is_dark else "white") if editing else theme_colors.SECONDARY

    def _update_version_btn_size(self, instance, value):
        instance.width = value[0]

    def _on_displayed_interval_value_changed(self, *_):
        if not self.built_ui:
            return
        self.ids.interval_input.text = f"Set to {self.displayed_interval_value}"
        if getattr(self, "_interval_toggle", None):
            self._interval_toggle.sub_title_text = f'Get a new wallpaper every "{self.displayed_interval_value}".'

    def _sync_toggles(self, *_):
        if not self.built_ui:
            return
        self._on_wake_toggle.active = self.is_using_on_wake
        self._interval_toggle.active = not self.is_using_on_wake

    def _sync_theme_cards(self, *_):
        if not self.built_ui:
            return
        preference = self.app.theme_preference
        for card in self._theme_cards:
            card.active = card.preference_value == preference

    def show_export_dialog(self):
        if hasattr(self.app, "bottom_bar") and self.app.bottom_bar:
            self.app.bottom_bar.hide(animation=False, hidden_by="export")
        self.export_dialog.dialog_box.cancel_btn.bind(on_release=lambda *_: self._restore_bottom_nav())
        self.export_dialog.show(img_texture=None)

    def _restore_bottom_nav(self):
        if hasattr(self.app, "bottom_bar") and self.app.bottom_bar:
            self.app.bottom_bar.show(animation=False, hidden_by="export")

    def _export_in_thread(self):
        spinner_layout = LoadingLayout()
        import threading
        def _run():
            try:
                self.export_waller_folder()
            except Exception as error_exporting_wallpapers:
                app_logger.exception(f"Export failed: {error_exporting_wallpapers}")
            finally:
                Clock.schedule_once(lambda dt: spinner_layout.remove())
                Clock.schedule_once(lambda dt: self._restore_bottom_nav())
        threading.Thread(target=_run, daemon=True).start()

    def toggle_home_screen_widget_loop(self, widget=None):
        if not self.built_ui:
            return
        widget.icon = "play" if widget.icon == "pause" else "pause"

        if widget.icon == "pause":
            text = "OnNext Wake" if my_config.get_on_wake_state() else "Resuming.."
        else:
            text = "Paused"
        self.ids.countdown_label.text = text

    def open_logs_screen(self, _=None):
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

    def save_interval(self, widget):
        ##p("saving interval")
        # app = MDApp.get_running_app()
        # # app.device_theme = "dark"
        # app.device_theme = "light" if app.device_theme == "dark" else "dark"
        ##p(app.device_theme)
        what_to_do = self.ids.save_btn_text.text
        if what_to_do == "Edit":
            self.ids.interval_input_con.disabled = False
            self.ids.interval_input.text = self.interval
            self.ids.save_btn_text.text = "Save"
            return
        elif what_to_do == "Save":
            self.ids.interval_input_con.disabled = True
            self.ids.save_btn_text.text = "Edit"

        global value__
        self.interval_input = self.ids.interval_input

        try:
            new_val = float(self.interval_input.text)
        except Exception as error_changing_input_to_float:
           #p(error_changing_input_to_float)
            traceback.print_exc()
            toast("Enter a valid number")
            return

        if new_val < 0.17:
            toast("Min allowed is 0.17 mins")
            return
        value__ = new_val
        my_config.set_interval(new_val)
        self.interval = str(new_val)
        self.displayed_interval_value = smart_convert_minutes(new_val)
        self.ids.interval_input.text = f"Saved: {self.displayed_interval_value}"
        toast("Saved")

    def update_label(self, seconds):
        if not self.built_ui:
            return
        if self.ids.pause_home_screen_widget_loop_button.icon == "play":
            self.ids.countdown_label.text = "Paused"
        elif my_config.get_on_wake_state():
            self.ids.countdown_label.text = "OnNext Wake"
        elif self.ids.pause_home_screen_widget_loop_button.icon == "pause":
            self.ids.countdown_label.text = seconds

    def restart_service(self, *_):

        def after_stop(*_):
            try:
                self.app.start_service()
                # Service(name="Wallpapercarousel").start()
                toast("Service boosted!")
            except Exception as error_starting_service:
               #p(error_starting_service)
                traceback.print_exc()
                toast("Start failed")

        try:
            # TODO call service server to stop, so it an end thread and avoid SECURITY ERROR when starting service
            Service(name="Wallpapercarousel").stop()
            Clock.schedule_once(after_stop, 1.2)
        except Exception as error_stoping_service:
           #p(error_stoping_service)
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
        from android_notify.config import get_python_activity_context, autoclass
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
                   app_logger.exception(f"Pre-29 export error:{e}")

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
               #p("MediaStore export error:", e)
                resolver.delete(uri, None, None)

       #p("exported_uris:", exported_uris)
        toast("Exported: To Pictures/Waller")
        return exported_uris

    def on_changed_homescreen_widget(self, current_wallpaper, next_wallpaper):
        self.current_image_source = current_wallpaper or self.current_image_source
        self.next_image_source = next_wallpaper or self.next_image_source

    def set_theme_color(self, _, value):
        self.status_bar_bg = [0.82, 0.82, 0.82, 1] if value == "light" else [0.23, 0.23, 0.23, 1]
        if not self.built_ui:
            return
        is_dark = value == "dark"
        self.md_bg_color = theme_colors.BG
        self.ids.title_text_case.md_bg_color = theme_colors.BG_ELEVATED
        self.title_label.color = theme_colors.TEXT_PRIMARY
        self.interval_heading.color = theme_colors.TEXT_PRIMARY
        self.home_widget_header.md_bg_color = theme_colors.BG_ELEVATED
        self.home_widget_header_label.color = theme_colors.TEXT_PRIMARY
        self.home_widget_body.md_bg_color = theme_colors.BG_CARD
        self.current_label.text_color = theme_colors.PRIMARY
        self.current_label.md_bg_color = theme_colors.SECONDARY
        self.next_label.text_color = theme_colors.PRIMARY
        self.next_label.md_bg_color = theme_colors.SECONDARY

        bw = "black" if not is_dark else "white"
        for widget in self._bw_widgets:
            widget.text_color = bw
        for widget in self._bw_icon_widgets:
            widget.text_color = bw
        for widget in self._bw_misc:
            widget.text_color = bw
        self.version_btn.color = bw if not is_dark else "grey"

        self._update_interval_input_colors()
        self._update_save_btn_theme()
        self._set_check_update_btn_theme(None, value)

    def set_theme_preference(self, preference):
        self.app.set_theme_preference(preference)

    def _set_check_update_btn_theme(self, _, theme):
        if not getattr(self, "_check_update_btn", None):
            return
        is_dark = theme == "dark"
        self._check_update_btn.background_color = theme_colors.BUTTON_BG
        self._check_update_btn.color = theme_colors.TEXT_PRIMARY

    def set_using_on_wake_config(self, instance, value, from_user):
        ##p("instance.title_text",instance, value)
        ##p('onrelease value',value,instance)
        if not from_user:
            return
        ##p(f'{instance.title_text} from_user')
        if instance.title_text == "Use On-wake":
            ConfigManager.set_on_wake_state(value)
            self.is_using_on_wake = value
            if value:
                self.app.ui_messenger_to_service.tell_service_server_to_use_on_wake()
                ##p(self.ids.countdown_label.text,111)
                self.ids.countdown_label.text = "OnNext Wake" if self.ids.countdown_label.text != "Paused" else self.ids.countdown_label.text
            else:
                self.app.ui_messenger_to_service.tell_service_server_to_use_interval_loop()

        elif instance.title_text == "Use interval":
            ConfigManager.set_on_wake_state(not value)
            self.is_using_on_wake = not value
            if value:
                self.app.ui_messenger_to_service.tell_service_server_to_use_interval_loop()
            else:
                self.app.ui_messenger_to_service.tell_service_server_to_use_on_wake()
                ##p(self.ids.countdown_label.text,22)
                self.ids.countdown_label.text = "OnNext Wake" if self.ids.countdown_label.text != "Paused" else self.ids.countdown_label.text

    def set_start_on_app_launch_config(self, instance, value, from_user):
        if not from_user:
            return
        ConfigManager.set_start_on_app_launch(value)
        self.start_on_app_launch = value

    def set_start_on_boot_config(self, instance, value, from_user):
        if not from_user:
            return
        ConfigManager.set_start_on_boot(value)
        self.start_on_boot = value

    def check_for_update(self, *args):
        from ui.screens.download_apk_screen import thread_check_for_update
        spinner_layout = LoadingLayout()

        def DownloadApkScreen__show(new_version, release_notes, apk_size):
            spinner_layout.remove()
            self.app.sm.download_apk_screen.show(new_version, release_notes, apk_size)

        def DownloadApkScreen__do_not_show(msg):
            toast(msg)
            spinner_layout.remove()

        Clock.schedule_once(
            lambda dt: thread_check_for_update(dt, DownloadApkScreen__show, DownloadApkScreen__do_not_show))

    def set_widget_left_and_right_padding(self,left_padding, right_padding,rotation):
        if not self.built_ui:
            return
        self.ids.main_container.padding=[dp(left_padding+25), dp(25), dp(right_padding+25), dp(100)]
        self.ids.title_text_case.padding=[dp(left_padding+25), dp(self.status_bar_height-20 if self.status_bar_height>20 else self.status_bar_height+20 ), dp(0), dp(20)]

    def handle_going_back(self,*_):
        self.manager.go_to_thumbs()

#
#
# import requests
# import os
# import traceback
# from utils.constants import VERSION
#
# def download_apk(url, filename="waller.apk"):
#     """Download APK from URL"""
#     try:
#         if on_android_platform():  # Android will be detected via pyjnius
#             from android import mActivity
#             context = mActivity.getApplicationContext()
#             files_dir = context.getFilesDir().getAbsolutePath()
#         else:
#             files_dir = "./"
#
#         apk_path = os.path.join(files_dir, filename)
#         r = requests.get(url, stream=True)
#         r.raise_for_status()
#
#         with open(apk_path, "wb") as f:
#             for chunk in r.iter_content(8192):
#                 if chunk:
#                     f.write(chunk)
#
#        #p("APK saved to:", apk_path)
#         return apk_path
#
#     except Exception as e:
#        #p("Download failed:", e)
#         traceback.print_exc()
#         return None
#
# def install_apk15(apk_path):
#     """Install APK using FileProvider (Android 15+)"""
#     import os
#     from jnius import autoclass
#     from android import mActivity
#
#     if not os.path.exists(apk_path):
#        #p("APK not found:", apk_path)
#         return
#
#     context = mActivity.getApplicationContext()
#     Intent = autoclass('android.content.Intent')
#     File = autoclass('java.io.File')
#     FileProvider = autoclass('androidx.core.content.FileProvider')
#     Uri = autoclass('android.net.Uri')
#
#     apk_file = File(apk_path)
#     authority = context.getPackageName() + ".fileprovider"
#     uri = FileProvider.getUriForFile(context, authority, apk_file)
#
#     intent = Intent(Intent.ACTION_VIEW)
#     intent.setDataAndType(uri, "application/vnd.android.package-archive")
#     intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
#     intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
#     mActivity.startActivity(intent)
#
# def install_apk(apk_path):
#     """Fallback installer for older Android versions"""
#     import os
#     from jnius import autoclass
#     from android import mActivity
#
#     if not os.path.exists(apk_path):
#        #p("APK not found:", apk_path)
#         return
#
#     Intent = autoclass('android.content.Intent')
#     Uri = autoclass('android.net.Uri')
#     File = autoclass('java.io.File')
#
#     intent = Intent(Intent.ACTION_VIEW)
#     apk_file = File(apk_path)
#     uri = Uri.fromFile(apk_file)
#     intent.setDataAndType(uri, "application/vnd.android.package-archive")
#     intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
#     mActivity.startActivity(intent)
#
# def check_update(*args):
#     """Check GitHub latest release version"""
#     repo_owner="Fector101"
#     repo_name="wallpaper-carousel"
#     api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
#     try:
#         r = requests.get(api_url, timeout=10)
#         r.raise_for_status()
#         data = r.json()
#        #p("Here's data:",data)
#         latest_version = data["tag_name"].lstrip("v")  # strip v prefix if any
#        #p("latest_version:", latest_version)
#         # apk_url = data["assets"][0]["browser_download_url"]
#         apk_url = "https://github.com/Fector101/wallpaper-carousel/releases/latest/download/waller.apk"
#        #p("Current version:", VERSION, "Latest version:", latest_version)
#
#         if latest_version != VERSION:
#             toast("Update available!")
#             apk_path = download_apk(apk_url)
#             if apk_path:
#                 try:
#                     install_apk15(apk_path)
#                 except Exception as e:
#                    #p("install_apk15 failed:", e)
#                     try:
#                         install_apk(apk_path)
#                     except Exception as e1:
#                        #p("install_apk failed:", e1)
#         else:
#             toast("Already up to date.")
#
#     except Exception as e:
#        #p("Failed to check updates:", e)
#         traceback.print_exc()
