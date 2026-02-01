import traceback

from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.screen import MDScreen

from kivymd.uix.label import MDLabel, MDIcon
from kivy.uix.image import Image
from kivy.metrics import dp, sp
from kivy.clock import Clock

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.relativelayout import MDRelativeLayout
from android_notify import NotificationHandler

from ui.widgets.buttons import MyRoundButton

try:
    from kivymd.toast import toast
except TypeError:
    def toast(*args):
        print('Fallback toast:', args)

from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock


class RotatedLayout(MDFloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(
                angle=0,
                origin=self.center
            )

        with self.canvas.after:
            PopMatrix()

        # keep rotation centered
        self.bind(pos=self.update_origin, size=self.update_origin)

        self.rotate()
        # animate rotation
        # Clock.schedule_interval(self.rotate, 1 / 60)

    def update_origin(self, *args):
        self.rot.origin = self.center

    def rotate(self, dt=None):
        self.rot.angle = -19

class NotificationRequestLayout(MDGridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.orientation = "vertical"
        self.rows = 4
        self.md_bg_color = [.9, .9, .9, 1]
        p=25
        self.padding = [dp(p), dp(60), dp(p), dp(20)]
        self.spacing = dp(50)

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

        bell_layout = MDBoxLayout(
            adaptive_height=1,

        )  # MDRelativeLayout()  # anchor_x="center",anchor_y="center")#orientation="vertical")
        bell_layout.orientation = "vertical"
        bell_layout.spacing = dp(10)
        bell_layout.padding = dp(10)
        bell_layout.md_bg_color = [183 / 255, 212 / 255, 227 / 255, 1]
        bell_layout.radius = [dp(8)]
        # bell_layout.size_hint = [1, 1]
        size = 100
        bell_image_layout= RotatedLayout()
        bell_image_layout.pos_hint={"center_x":.9}
        # bell_image_layout.adaptive_size=1
        bell_image_layout.md_bg_color = [1, 0,1, 1]

        bell = Image(
            # source="ui/screens/group.png",
            source="assets/icons/bell.png",
            # size_hint=(1,1),
            size_hint=(None, None),
            size=(dp(size), dp(size)),
            # allow_stretch=False,
            # keep_ratio=False,
        )
        # bell.
        bell.pos_hint = {'center_x': .5, 'center_y': .5}
        bell_image_layout.add_widget(bell)
        bell_layout.add_widget(bell_image_layout)

        bell_layout.add_widget(
            MDLabel(
                text="Additional Features",
                bold=True,
                theme_font_name="Custom",
                font_name="RobotoMono",
                adaptive_size=1,
            )
        )

        bell_layout.add_widget(
            MDLabel(
                text="See what’s coming and skip images without opening app",
                # bold=True,
                font_size=sp(14),
                theme_font_size="Custom",
                theme_font_name="Custom",
                font_name="RobotoMono",
                adaptive_height=1,
                size_hint_x=1
            )
        )
        p = 10
        notify_card = MDBoxLayout(
            md_bg_color=[1, 1, 1, 1],
            radius=[dp(20)],
            spacing=dp(10),
            padding=[dp(p), dp(p), dp(p), dp(p)],
            size_hint_x=1,
            adaptive_height=1,
        )
        s = 40
        first_section = MDBoxLayout(
                                    pos_hint={'top': 1},
                                    radius=[50],
                                    size_hint=[None, None],
                                    md_bg_color=[116 / 255, 155 / 255, 215 / 255, 1],
                                    size=[s, s],
                                    )

        second_section = MDBoxLayout(
            adaptive_size=1,
            # md_bg_color=[0, 0, 0, 1],
            pos_hint={'top': 1},
            orientation="vertical",
            size_hint_x=1,
        spacing=dp(10),
        )
        title_nd_mins = MDBoxLayout(
            # md_bg_color=[1,1, 0.255, 1],
            spacing=dp(5),
            adaptive_size=1,
        )

        title_nd_mins.add_widget(
            MDLabel(
                text="Waller",
                theme_text_color="Custom",
                text_color=[88 / 255, 85 / 255, 85 / 255, 1],
                adaptive_size=1,
                theme_font_name="Custom",
                font_name="RobotoMono",
                theme_font_size="Custom",
                font_size=sp(14)
            )
        )

        title_nd_mins.add_widget(
            MDIcon(
                icon='checkbox-blank-circle',
                theme_text_color="Custom",
                text_color=[88 / 255, 85 / 255, 85 / 255, 1],
                adaptive_size=1,
                pos_hint={'center_y': .5},
                theme_font_size="Custom",
                font_size=sp(6)
            )
        )
        title_nd_mins.add_widget(
            MDLabel(
                text="20m",
                theme_text_color="Custom",
                text_color=[88 / 255, 85 / 255, 85 / 255, 1],
                adaptive_size=1,
                theme_font_name="Custom",
                font_name="RobotoMono",
                theme_font_size="Custom",
                font_size = sp(14)
            )
        )
        second_section.add_widget(title_nd_mins)
        second_section.add_widget(MDLabel(
            text="Next in 1:26",
            theme_font_name="Custom",
            font_name="RobotoMono",
            theme_text_color="Custom",
            # text_color=[88 / 255, 85 / 255, 85 / 255, 1],
            adaptive_size=1,
            theme_font_size="Custom",
            font_size=sp(14)
        ))
        second_section.add_widget(MDLabel(
            text="Skip",
            theme_text_color="Custom",
            text_color=[46 / 255, 95 / 255, 169 / 255, 1],
            adaptive_size=1,
            theme_bg_color="Custom",
            md_bg_color=[234 / 255, 233 / 255, 233 / 255, 1],
            padding=[dp(6), dp(4)],
            radius=[dp(4)],
            theme_font_name="Custom",
            font_name="RobotoMono",
            theme_font_size="Custom",
            font_size=sp(14)
        ))
        t = 60

        notify_card.add_widget(first_section)
        notify_card.add_widget(second_section)
        image_con = MDBoxLayout(
            pos_hint={'top': .95},

        )
        image_con.adaptive_size = 1
        image_con.md_bg_color = [161/255,163/255,172/255, 1]
        r=5
        image_con.radius = [dp(r)]
        image_con.add_widget(FitImage(
            source="assets/icons/mountain.png",
            size_hint=(None, None),
            size=(dp(t), dp(t)),
            radius=[dp(r)]
        ))
        notify_card.add_widget(
            image_con
        )

        my_icon_box = MDBoxLayout(md_bg_color=(226 / 255, 223 / 255, 223 / 255, 1),
                                  adaptive_size=1, pos_hint={'top': 1})
        print(my_icon_box.height, "my_icon_box.height")
        my_icon_box.radius = [dp(50)]
        drop_down_icon = MDIcon(
            icon='chevron-up',
            theme_text_color="Custom",
            text_color='black',
            pos_hint={'top': 1, 'right': 1},
        )
        my_icon_box.add_widget(drop_down_icon)
        notify_card.add_widget(
            my_icon_box
        )

        bell_layout.add_widget(
            notify_card
        )

        btns_layout = MDBoxLayout(orientation="vertical", spacing=dp(10))#, adaptive_height=1)

        self.enable_btn = MyRoundButton(
            text="Enable notifications",
            bg_color=(55 / 255, 151 / 255, 252 / 255, 1),
            size_hint_y=None,
            height=dp(48),
            font_size=sp(16),
            on_release=self.enable_notifications,
        )

        skip_btn = MyRoundButton(
            text="Skip Feature",
            bg_color=(243 / 255, 170 / 255, 170 / 255, 1),
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

    def enable_notifications(self, *_):
        print("Enable notifications pressed")

        def change_screen(_):
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
            print("error_asking_permission", error_asking_permission)
            traceback.print_exc()

    def skip_feature(self, *_):
        self.parent.manager.current = "thumbs"
        print("Skip feature pressed")


class WelcomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "welcome"
        self.add_widget(NotificationRequestLayout())
