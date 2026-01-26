import os.path,traceback
from kivymd.uix.screen import MDScreen

# from kivy.core.text import LabelBase
from kivymd.uix.label import MDLabel
from kivy.uix.image import Image
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import NoTransition

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.relativelayout import MDRelativeLayout
from android_notify import NotificationHandler
from android_notify.config import run_on_ui_thread

from ui.widgets.buttons import MyRoundButton


try:
    from kivymd.toast import toast
except TypeError:
    def toast(*args):
        print('Fallback toast:', args)
#
# class Font:
#     def __init__(self, name, base_folder):
#         self.base_folder = base_folder
#         self.name = name
#
#     def get_type_path(self, fn_type):
#         """
#         Formats font type path
#         :param fn_type:
#         :return:
#         """
#         return os.path.join(self.base_folder, self.name + '-'+fn_type + '.ttf')
#
# # This work but i like the normal, bold,italic config better title.font_name = "app_src/assets/fonts/Roboto_Mono/RobotoMono-VariableFont_wght.ttf"
# robot_mono = Font(name='RobotoMono',base_folder="app_src/assets/fonts/Roboto_Mono/static")
# LabelBase.register(
#     name="RobotoMono",
#     fn_regular=robot_mono.get_type_path('Regular'),
#     fn_italic=robot_mono.get_type_path('Italic'),
#     fn_bold=robot_mono.get_type_path('Bold'),
# )
from kivy.clock import Clock


class NotificationRequestLayout(MDGridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.orientation = "vertical"
        self.rows = 4
        self.md_bg_color = [.9, .9, .9, 1]
        self.padding = [dp(35),dp(60),dp(35),dp(35)]
        self.spacing = dp(18)

        header_layout = MDBoxLayout(orientation="vertical", adaptive_height=1)
        # header_layout.md_bg_color = [1,.3,0,1]
        title = MDLabel(
            text="Turn On\nNotifications?",
            bold=True,
        )

        # title._md_bg_color=[1,1,0,1]
        title.font_size = sp(36)
        title.font_name = "RobotoMono"
        title.adaptive_height = 1

        body = MDLabel(
            text=(
                "To keep Carousel running in the\n"
                "background, Android requires a\n"
                "foreground notification"
            ),
        )
        body.font_size = sp(14)
        body.font_name = "RobotoMono"
        body.adaptive_height = 1
        # header_layout.md_bg_color=[1,.6,0,1]
        header_layout.add_widget(title)
        header_layout.add_widget(body)

        bell_layout = MDRelativeLayout()  # anchor_x="center",anchor_y="center")#orientation="vertical")
        bell_layout.size_hint = [1, 1]
        size = 190
        bell = Image(
            source="assets/icons/bell.png",
            size_hint=(None, None),
            size=(dp(size), dp(size)),
            # allow_stretch=False,
            # keep_ratio=False,
        )
        bell.pos_hint = {'center_x': .5, 'center_y': .5}
        bell_layout.add_widget(bell)

        btns_layout = MDBoxLayout(orientation="vertical", spacing=dp(10), adaptive_height=1)
        self.enable_btn = MyRoundButton(
            text="Enable notifications",
            bg_color=(55/255, 151/255, 252/255, 1),
            inset_color=[5 / 255, 1 / 255, 1, 1],
            size_hint_y=None,
            height=dp(48),
            font_size=sp(16),
            on_release=self.enable_notifications,
        )

        skip_btn = MyRoundButton(
            text="Skip Feature",
            bg_color=(243/255,170/255,170/255, 1),
            inset_color=[255 / 255, 10 / 255, 50/255, 1],
            color=(0, 0, 0, 1),
            size_hint=[None, None],
            height=dp(44),
            width=sp(248),
            font_size=dp(14),
            pos_hint={'center_x': .5},
            on_release=self.skip_feature,
        )
        skip_btn.font_name = "RobotoMono"
        btns_layout.add_widget(self.enable_btn)
        btns_layout.add_widget(skip_btn)

        self.add_widget(header_layout)
        self.add_widget(bell_layout)
        self.add_widget(btns_layout)

    def enable_notifications(self, *args):
        print("Enable notifications pressed")

        def change_screen(dt):
            try:
                self.parent.manager.current = "thumbs"
            except Exception as e:
                print(e)
                traceback.print_exc()

        def callback_func(state):
            Clock.schedule_once(change_screen)
            if state:
                toast("Notifications enabled")
            else:
                toast("Notifications disabled")
        try:
            NotificationHandler.asks_permission(callback_func)
        except Exception as error_asking_permission:
            print("error_asking_permission",error_asking_permission)
            traceback.print_exc()

    def skip_feature(self, *args):
        self.parent.manager.current = "thumbs"
        print("Skip feature pressed")


class WelcomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "welcome"
        self.add_widget(NotificationRequestLayout())
