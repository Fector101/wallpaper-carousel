from android_notify.config import on_android_platform, autoclass
from kivy.metrics import dp, sp
from kivymd.app import MDApp
from kivy.properties import ListProperty, DictProperty, BooleanProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.popup import Popup
from kivymd.uix.label import MDLabel
from kivymd.uix.relativelayout import MDRelativeLayout

from kivymd.uix.screen import MDScreen


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
        print(999,widget, *args, **kwargs)
        super().add_widget(widget, *args, **kwargs)
    def adjust_height(self,widget,height):
        self.height = dp(height) + dp(56)#sp(self.popup_title_label.height)


from kivy.core.window import Window
from kivy.properties import ObjectProperty
from kivymd.uix.floatlayout import MDFloatLayout


def get_dimensions():
    status_bar_height = 0
    nav_bar_height = 0
    if not on_android_platform():
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


class MyMDScreen(MDScreen):
    status_bar_box = ObjectProperty()
    navigation_buttons_box = ObjectProperty()
    screen_content = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def add_widget(self, widget, *args, **kwargs):
        status_bar_height = 0
        nav_bar_height = 0

        if on_android_platform():
            dimensions = get_dimensions()
            status_bar_height = dimensions[0]
            nav_bar_height = dimensions[1]

        if self.status_bar_box is None:
            self.status_bar_box = MDBoxLayout(size_hint=[1, None], height=status_bar_height, md_bg_color=[26/255, 27/255, 27/255, 1],
                                              pos_hint={"top": 1})
            super().add_widget(self.status_bar_box)

        if self.screen_content is None:
            # MDFloatLayout
            self.screen_content = MDRelativeLayout(size_hint=[1, None],
                                                height=Window.height - (status_bar_height + nav_bar_height),
                                                md_bg_color=[0, 0, 0, 0])
            self.screen_content.orientation = "vertical"
            self.screen_content.y = nav_bar_height
            super().add_widget(self.screen_content)

        if self.navigation_buttons_box is None:
            self.navigation_buttons_box = MDBoxLayout(size_hint=[1, None], height=nav_bar_height,
                                                      md_bg_color=[26/255, 27/255, 27/255, 1])
            super().add_widget(self.navigation_buttons_box)

        if self.screen_content:
            self.screen_content.add_widget(widget, *args, **kwargs)
