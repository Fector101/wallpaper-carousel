import traceback
from pathlib import Path

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
# from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField

from android_notify.core import asks_permission_if_needed
from android_notify import NotificationHandler
from ui.widgets.android import toast  # type: ignore

DEV = 0

from utils.helper import Service, makeDownloadFolder, start_logging, smart_convert_minutes  # type: ignore
from utils.config_manager import ConfigManager  # type: ignore
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp, sp
from kivy.uix.scrollview import ScrollView


class MyLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.on_release = self.tapped
        self.size_hint = [1, None]
        self.height = 100


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self.md_bg_color = [0.1, 0.1, 0.1, 1]
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"
        self.interval = self.myconfig.get_interval()
        self.times_tapped = 0

        # ---------- SCROLLVIEW ----------
        scroll = ScrollView(size_hint=(1, 1))

        root = MDBoxLayout(
            orientation="vertical",
            padding=[dp(20), dp(30), dp(20), dp(100)],
            spacing=dp(15),
            size_hint_y=None
        )
        root.bind(minimum_height=root.setter("height"))  # makes height dynamic based on content

        # ---------- HEADER ----------
        root.add_widget(Label(
            text="Settings",
            font_size="22sp",
            size_hint_y=None,
            height=dp(40),font_name="RobotoMono"
        ))

        # ---------- INTERVAL SECTION ----------
        root.add_widget(Label(
            text="Wallpaper Change Interval (minutes)",
            size_hint_y=None,
            height=dp(30),font_name="RobotoMono",font_size=sp(13)
        ))

        input_row = MDBoxLayout(orientation="horizontal", spacing=dp(10),
                                size_hint_y=None, height=dp(50))

        self.interval_input = MDTextField(
            text=str(self.interval),
            hint_text="mins",
            size_hint_x=0.55,
        )
        self.interval_input.theme_text_color = "Custom"
        self.interval_input.text_color_focus = [1, 1, 1, 1]
        self.interval_input.text_color_normal = [.8, .8, .8, 1]
        self.interval_input.hint_text_color_normal = [.8, .8, .8, 1]
        self.interval_input.hint_text_color_focus = [1, 1, 1, 1]
        self.interval_input.input_filter = "float"

        save_btn = Button(text="Save", size_hint_x=0.35,font_name="RobotoMono")
        save_btn.bind(on_release=self.save_interval)

        input_row.add_widget(self.interval_input)
        input_row.add_widget(save_btn)
        root.add_widget(input_row)

        self.interval_label = Label(
            text=f"Saved: {smart_convert_minutes(self.interval)}",
            size_hint_y=None,
            height=dp(30),font_name="RobotoMono"
        )
        root.add_widget(self.interval_label)

        # ---------- FLEXIBLE SPACER ----------
        root.add_widget(Widget(size_hint_y=1))

        root.add_widget(Label(
            text="Carousel Tools",
            size_hint_y=None,
            height=dp(30)
        ))

        restart_btn = Button(
            text="Restart Carousel",
            size_hint_y=None,
            height=dp(50)
        )
        restart_btn.bind(on_release=self.restart_service)
        root.add_widget(restart_btn)

        stop_btn = Button(
            text="Stop Carousel",
            size_hint_y=None,
            height=dp(50)
        )
        stop_btn.bind(on_release=self.terminate_carousel)
        root.add_widget(stop_btn)

        # ---------- TEST BUTTON ----------
        ai_btn = Button(
            text="export_waller_folder",
            size_hint_y=None,
            height=dp(50),
            on_release=lambda widget: self.export_waller_folder()
        )
        root.add_widget(ai_btn)



        if DEV:
            root.add_widget(Button(
                text="test android_notify",
                size_hint_y=None,
                height=dp(50),
                on_release=lambda widget: self.android_notify_tests()
            ))
        text = MyLabel(
            text="--- v1.0.2 ---",
            size_hint_y=None,
            height=dp(50),font_name="RobotoMono",
            on_release=self.open_logs_screen
        )
        root.add_widget(text)
        scroll.add_widget(root)
        self.add_widget(scroll)
    def open_logs_screen(self,widget=None):
        self.times_tapped += 1
        if self.times_tapped == 3:
            self.manager.current = "logs"
            self.times_tapped = 0

    def android_notify_tests(self):
        try:
            from tests.android_notify_test import TestAndroidNotifyFull
            import unittest

            suite = unittest.TestLoader().loadTestsFromTestCase(TestAndroidNotifyFull)
            unittest.TextTestRunner(verbosity=2).run(suite)

        except Exception as e:
            print("Error testing android_notify:", e)
            traceback.print_exc()

    def basic_side(self):
        try:
            asks_permission_if_needed()
        except Exception as e:
            print('Permission error:', e)
            traceback.print_exc()

    def open_notify_settings(self):

        try:
            NotificationHandler.asks_permission()
        except Exception as e:
            print('Notify error:', e)

    def terminate_carousel(self, *args):
        try:
            Service(name="Wallpapercarousel").stop()
            toast("Successfully Terminated")
        except Exception as e:
            toast("Stop failed", e)

    def save_interval(self, *args):
        try:
            new_val = float(self.interval_input.text)
        except:
            toast("Enter a valid number")
            return

        if new_val < 0.17:
            toast("Min allowed is 0.17 mins")
            return

        self.myconfig.set_interval(new_val)
        self.interval_label.text = f"Saved: {smart_convert_minutes(new_val)}"
        toast("Saved")

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

    def export_waller_folder(self, instance=None):
        """
        Export all images from app-private 'wallpapers' folder
        to public Pictures/Waller/ folder.

        API 29+  : MediaStore + IS_PENDING
        API < 29 : Direct filesystem write + MediaScanner

        Returns:
            list[str]: content:// URIs (29+) or file paths (<29)
        """

        from jnius import autoclass
        import os
        from android_notify.config import get_python_activity_context

        # Android core
        MediaStoreImages = autoclass("android.provider.MediaStore$Images$Media")
        ContentValues = autoclass("android.content.ContentValues")
        Environment = autoclass("android.os.Environment")
        BuildVersion = autoclass("android.os.Build$VERSION")
        Integer = autoclass("java.lang.Integer")

        # Fast native copy (safe)
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
        folder_path = os.path.join(makeDownloadFolder(), 'wallpapers')
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
            values.put(MediaStoreImages.DISPLAY_NAME, filename)
            values.put(MediaStoreImages.MIME_TYPE, mime)
            values.put(
                MediaStoreImages.RELATIVE_PATH,
                Environment.DIRECTORY_PICTURES + "/Waller"
            )
            values.put(MediaStoreImages.IS_PENDING, Integer(1))

            uri = resolver.insert(
                MediaStoreImages.EXTERNAL_CONTENT_URI,
                values
            )

            if not uri:
                continue

            try:
                out = resolver.openOutputStream(uri)

                # Fast, safe native copy
                Files.copy(
                    Paths.get(source_path),
                    out
                )

                out.flush()
                out.close()

                values.clear()
                values.put(MediaStoreImages.IS_PENDING, Integer(0))
                resolver.update(uri, values, None, None)

                exported_uris.append(str(uri))

            except Exception as e:
                print("MediaStore export error:", e)
                resolver.delete(uri, None, None)

        print("exported_uris:", exported_uris)
        return exported_uris
