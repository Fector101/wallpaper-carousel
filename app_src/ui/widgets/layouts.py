import traceback

from kivymd.uix.widget import MDWidget

from android_notify.config import on_android_platform, autoclass
from kivy.metrics import dp
from kivy.properties import ListProperty, DictProperty, NumericProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.popup import Popup
from kivymd.uix.label import MDLabel
from kivymd.uix.relativelayout import MDRelativeLayout

from kivymd.uix.screen import MDScreen
from kivy.core.window import Window
from kivymd.uix.floatlayout import MDFloatLayout

from kivymd.app import MDApp

from kivy.clock import Clock
from kivy.graphics import Color, Line, Rotate
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

from android_notify.internal.java_classes import BuildVersion
from utils.logger import app_logger

# Add this before creating your main widget or in your build method
Window.softinput_mode = 'below_target' # or 'pan'


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


class MyPopUp(Popup):
    info = DictProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Image Info"

        # if not on_android_platform():
        # self.info = {
        #     "Pixels": "1920x1080",
        #     "Megapixels": "2.1 MP",
        #     "Size": "1.75 MB",
        #     "MIME": "image/jpeg"
        # }
        self.content = Column(
            pos_hint={"top": .95},
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(10),dp(20)],
            spacing=dp(10)
        )

        first_row = Row(
            adaptive_height=True,
            my_widgets=[self.__get_item("Pixels"),self.__get_item("Size")]
        )
        second_row = Row(
            adaptive_height=True,
            my_widgets=[self.__get_item("MIME")]
        )

        self.content.add_widget(first_row)
        self.content.add_widget(second_row)


        self.size_hint = (0.8, None)
        self.content.bind(height=self.adjust_height)
        self.pos_hint = {"center_x": .5, "center_y": .5}

    def __get_item(self,name):
        return Column(adaptive_height=True,my_widgets=[
            MDLabel(text=name, adaptive_height=True, theme_text_color="Custom", text_color="grey"),
            MDLabel(text=self.info[name], adaptive_height=True, theme_text_color="Custom", text_color="white")
        ])

    def add_widget(self, widget, *args, **kwargs):
        # print(999,widget, *args, **kwargs)
        super().add_widget(widget, *args, **kwargs)

    def adjust_height(self,widget,height):
        self.height = dp(height) + dp(56)#sp(self.popup_title_label.height)


from kivy.properties import ObjectProperty


def get_dimensions():
    status_bar_height = 0
    nav_bar_height = 0
    if not on_android_platform():
        return [50,50]
        return [status_bar_height, nav_bar_height]

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity

    # This First block works when user is using Buttons

    try:
        WindowInsetsType = autoclass("android.view.WindowInsets$Type")
        window = activity.getWindow()
        decor = window.getDecorView()

        insets = decor.getRootWindowInsets()
        if insets:
            status_bar_height = insets.getInsets(
                WindowInsetsType.statusBars()
            ).top

            nav_bar_height = insets.getInsets(
                WindowInsetsType.navigationBars()
            ).bottom
    except Exception as Error_using_first_method_to_get_Status_Bar_and_Nav_Bar_Height:
        print(Error_using_first_method_to_get_Status_Bar_and_Nav_Bar_Height)


    # This Block is a fallback when user is using Gestures
    if not status_bar_height:
        try:
            resources = activity.getResources()
            status_id = resources.getIdentifier("status_bar_height", "dimen", "android")
            status_bar_height = resources.getDimensionPixelSize(status_id)
        except Exception as Error_using_second_method_to_get_status_bar_height:
            print(Error_using_second_method_to_get_status_bar_height)

    if not nav_bar_height:
        try:
            resources = activity.getResources()
            nav_id = resources.getIdentifier("navigation_bar_height", "dimen", "android")
            nav_bar_height = resources.getDimensionPixelSize(nav_id)
        except Exception as Error_using_second_method_to_get_nav_bar_height:
            print(Error_using_second_method_to_get_nav_bar_height)

    return [status_bar_height, nav_bar_height]


def get_nav_bar_height():
    dimensions = get_dimensions()
    return dimensions[1]


def get_status_bar_height():
    dimensions = get_dimensions()
    return dimensions[0]

# For header use In python file self.status_bar_height. In kv file root.status_bar_height
# each subclass should implement set_widget_left_and_right_padding
class MyMDScreen(MDScreen):
    navigation_buttons_box = ObjectProperty()
    screen_content = ObjectProperty()

    dimensions = get_dimensions()
    status_bar_height = NumericProperty(get_status_bar_height())
    nav_bar_height = NumericProperty(get_nav_bar_height())
    status_bar_bg = ListProperty([26 / 255, 27 / 255, 27 / 255, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.change_layout_orientation_clock = None
        Window.bind(size=self.on_window_resize)
        self.on_window_resize(Window, (Window.width, Window.height))

    def add_widget(self, widget, *args, **kwargs):
        if self.screen_content is None:
            self.screen_content = MDBoxLayout(
                pos_hint={"top": 1}, padding = [0, 0, 0, self.nav_bar_height],orientation = "vertical"
                # md_bg_color=[1, 0, 0, 1],
            )
            super().add_widget(self.screen_content)

        if self.screen_content:
            self.screen_content.add_widget(widget, *args, **kwargs)

    def on_window_resize(self, _, size):
        if on_android_platform():
            return None
        if self.change_layout_orientation_clock:
            self.change_layout_orientation_clock.cancel()
        self.change_layout_orientation_clock = Clock.schedule_once(lambda x: self.do_thing(size), 1)
        return None

    def do_thing(self, size):
        width, height = size
        orientation = "portrait" if height > width else "landscape"
        if not self.screen_content or on_android_platform():
            return

        if orientation == "landscape":
            self.screen_content.padding = [0, 0, 0, 0]
            pos = self.__get_right_positioning()
            self.set_widget_left_and_right_padding(left_padding=pos[0],right_padding=pos[1])
            # self.set_widget_left_and_right_padding(left_padding=self.status_bar_height,right_padding=self.nav_bar_height)
        else:
            self.screen_content.padding = [0, 0, 0, self.nav_bar_height]
            self.set_widget_left_and_right_padding(left_padding=0,right_padding=0)

    def adjust_padding(self, rotation):
        if rotation == "TOP":
            self.screen_content.padding = [0, 0, 0, self.nav_bar_height]
        elif rotation == "BOTTOM":
            self.screen_content.padding = [0, 0, 0, self.nav_bar_height+self.status_bar_height]
        elif rotation in ["LEFT", "RIGHT"]:
            self.screen_content.padding = [0, 0, 0, 0]

    def set_widget_left_and_right_padding(self,left_padding, right_padding):
        pass
        # print("Mad Bread",left_padding,right_padding)
        # self.ids.main_container.padding=[dp(left_padding+25), dp(25), dp(right_padding+25), dp(0)]

    @staticmethod
    def __get_rotation():
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity

        try:
            # Modern method
            display = activity.getDisplay()
        except Exception as error_getting_rotation:
            app_logger.exception(error_getting_rotation)
            traceback.print_exc()
            # Fallback for older Android
            wm = activity.getSystemService(activity.WINDOW_SERVICE)
            display = wm.getDefaultDisplay()

        return display.getRotation()

    def __get_right_positioning(self):
        default = self.status_bar_height, self.nav_bar_height
        if not on_android_platform():
            return default
        Surface = autoclass('android.view.Surface')
        rotation = self.__get_rotation()

        print("rotation:", rotation)
        # Using status bar position
        # "TOP (Portrait)", "RIGHT (Landscape)", "BOTTOM (Upside Down)""
        if rotation in [Surface.ROTATION_0,Surface.ROTATION_90,Surface.ROTATION_180]:
            print(rotation)
            return default
        elif rotation == Surface.ROTATION_270: # "LEFT (Landscape)"
            print("Rotation: 270")
            return self.nav_bar_height,self.status_bar_height
        else:
            app_logger.error(f"Unknown rotation: {rotation}")
            return default

class GenericStatusBarSpacer(MDWidget):
    status_bar_height=NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint=[1, None]
        self.pos_hint={'center_x': .5, 'top': 1}
        self.height=self.status_bar_height
        self.bind(height=lambda _,value: setattr(self, 'height', value))
# NOTE this from kivymd.uix.button import MDButton has line color feature
# Still Useful for Element with No Button Behavior

class BorderMDRelativeLayout(MDRelativeLayout):
    line_color = ListProperty([1, 0, 0, 1])
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.after:
            self.bg_color_instr = Color(*self.line_color)
            self.border = Line(width=1, rounded_rectangle=self.round_rect_args)
        self.bind(pos=self.update_border, size=self.update_border)

    @property
    def round_rect_args(self):
        return self.x, self.y, self.width, self.height, self.radius[0]

    def update_border(self, *_):
        self.border.rounded_rectangle = self.round_rect_args  # (self.x,self.y,self.width,self.height,16)


class LoadingLayout1(MDFloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = MDApp.get_running_app()

        c=.1
        self.md_bg_color=[c,c,c, .5]
        from kivymd.uix.loadingindicator import MDLoadingIndicator
        self.spinner = MDLoadingIndicator()
        self.spinner.start()
        self.add_widget(self.spinner)
        # if isinstance(app, kaki.app.App):
        #     screen = app.root.children[0]
        #     if isinstance(screen, MyMDScreen):
        #         current_screen = screen
        # else:
        current_screen = app.sm.current_screen
        current_screen.add_widget(self)

    def remove(self,dt=None):
        self.spinner.stop()
        self.parent.remove_widget(self)


class SpinningArcWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set a fixed size for the spinner widget
        self.size = (100, 100)
        # Draw spinner on the canvas
        with self.canvas:
            # Create a rotation instruction; note the origin will be updated as the widget size changes
            self.rotation = Rotate(angle=0, origin=self.center)
            # Set a visible color; here white is typical for many spinners, but you can adjust as needed.
            Color(*get_color_from_hex("#98F1DD"))
            # Draw an arc: (center_x, center_y, radius, start_angle, end_angle)
            # A partial circle (e.g. 270°) gives a "spinner" look.
            self.arc = Line(circle=(self.center_x, self.center_y, 40, 0, 270), width=4)
        # Ensure that the rotation origin updates when the widget is resized or repositioned.
        self.bind(pos=self._update_origin, size=self._update_origin)
        # Schedule an update at roughly 60 frames per second.
        Clock.schedule_interval(self.update_arc, 0.016)

    def _update_origin(self, *args):
        # Update the rotation's origin to keep it centered
        self.rotation.origin = self.center
        self.arc.circle = (self.center_x, self.center_y, 40, 0, 270)

    def update_arc(self, dt):
        # Increase the rotation angle to create the spinning effect.
        self.rotation.angle += 5

# Act as BackDrop
class LoadingLayout(MDRelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.disabled=True
        c = .1
        self.md_bg_color = [c, c, c, .5]
        # Center the spinner by positioning it relative to the screen's center.
        self.spinner = SpinningArcWidget(size_hint=(None, None), size=(100, 100))
        # Position the spinner in the middle of the screen:
        self.spinner.pos = ((self.width - self.spinner.width) / 2, (self.height - self.spinner.height) / 2)
        self.add_widget(self.spinner)
        # Update the spinner's position when the screen size changes.
        self.bind(size=self._update_spinner_pos)

        app = MDApp.get_running_app()
        if hasattr(app,"root_layout"):
            current_screen = app.root_layout
            current_screen.add_widget(self)

    def _update_spinner_pos(self, *args):
        self.spinner.pos = ((self.width - self.spinner.width) / 2, (self.height - self.spinner.height) / 2)
    def remove(self,dt=None):
        if self.parent:
            self.parent.remove_widget(self)  # Hides the spinner by removing it
