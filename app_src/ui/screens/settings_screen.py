import time
import traceback
from pathlib import Path

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField

from android_notify.core import asks_permission_if_needed
from android_notify import NotificationHandler

try:
    from kivymd.toast import toast
    from jnius import autoclass
except TypeError:
    def toast(*args):
        print('Fallback toast:',args)


from utils.helper import Service, makeDownloadFolder, start_logging, smart_convert_minutes
from utils.config_manager import ConfigManager


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name="settings"
        self.md_bg_color = [0.1, 0.1, 0.1, 1]
        print('manager',self.manager)
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager(self.app_dir)
        self.wallpapers_dir = self.app_dir / ".wallpapers"
        self.interval = self.myconfig.get_interval()
        self.i = 1
        root = MDBoxLayout(orientation="vertical", padding=dp(20), spacing=dp(15))

        # ---------- HEADER ----------
        root.add_widget(Label(
            text="Settings",
            font_size="22sp",
            size_hint_y=None,
            height=dp(40)
        ))

        # ---------- INTERVAL SECTION ----------
        root.add_widget(Label(
            text="Wallpaper Change Interval (minutes)",
            size_hint_y=None,
            height=dp(30)
        ))

        input_row = MDBoxLayout(orientation="horizontal", spacing=dp(10),
                                size_hint_y=None, height=dp(50))

        self.interval_input = MDTextField(
            text=str(self.interval),
            hint_text="mins",
            size_hint_x=0.55,
            mode="outlined"
            )
        self.interval_input.input_filter="float"

        save_btn = Button(text="Save", size_hint_x=0.35)
        save_btn.bind(on_release=self.save_interval)

        input_row.add_widget(self.interval_input)
        input_row.add_widget(save_btn)
        root.add_widget(input_row)

        self.interval_label = Label(
            text=f"Saved: {smart_convert_minutes(self.interval)}",
            size_hint_y=None,
            height=dp(30)
        )
        root.add_widget(self.interval_label)

        # ---------- FLEXIBLE SPACER ----------
        root.add_widget(Widget(size_hint_y=1))

        # ---------- SERVICE BOOSTER (BOTTOM SITS HERE) ----------
        root.add_widget(Label(
            text="Carousel Tools",
            size_hint_y=None,
            height=dp(30)
        ))

        restart_btn = Button(
            text="Restart Carousel Worker",
            size_hint_y=None,
            height=dp(50)
        )
        restart_btn.bind(on_release=self.restart_service)
        root.add_widget(restart_btn)

        #------STOP SERVICE -------
        stop_btn = Button(
            text="Stop Carousel Worker",
            size_hint_y=None,
            height=dp(50)
        )
        stop_btn.bind(on_release=self.terminate_carousel)
        root.add_widget(stop_btn)

        # ---------- BACK ----------
        back_btn = Button(
            text="Back",
            size_hint_y=None,
            height=dp(50),
            on_release=lambda *_: setattr(self.manager, 'current', 'thumbs')
        )
        root.add_widget(back_btn)

        # Tests

        ai_btn = Button(
            text="test",
            size_hint_y=None,
            height=dp(50),
            on_release=lambda widget: self.open_notify_settings()
        )
        root.add_widget(ai_btn)
        self.add_widget(root)
    def open_notify_settings(self):
        print('Hello world')
        if self.i == 1:
            try:
                asks_permission_if_needed()
            except Exception as e:
                print('1error', e)
                traceback.print_exc()
            self.i = 0
            return
        try:
            NotificationHandler.asks_permission()
        except Exception as e:
            print('1error',e)

        self.i = 1


    def terminate_carousel(self,*args):
        try:
            Service(name="Wallpapercarousel").stop()
            toast("Successfully Terminated")
        except Exception as e:
            toast("Stop failed",e)

    # SAVE ONLY
    def save_interval(self, *args):
        try:
            new_val = float(self.interval_input.text)
        except:
            toast("Enter a valid number")
            return

        if new_val < 0.17:
            toast("Min allowed is 0.17 mins")
            return

        # app.interval = new_val
        self.myconfig.set_interval(new_val)
        self.interval_label.text = f"Saved: {smart_convert_minutes(new_val)}"
        toast("Saved")

    # RESTART SERVICE ONLY
    def restart_service(self, *args):

        def after_stop(*_):
            try:
                Service(name="Wallpapercarousel").start()
                toast("Service boosted!")
            except:
                toast("Start failed")

        try:
            Service(name="Wallpapercarousel").stop()
            Clock.schedule_once(after_stop, 1.2)
        except:
            toast("Stop failed")
