import sys
import os
import shutil
import traceback
from pathlib import Path

from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.uix.widget import Widget

from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast

from plyer import filechooser
from android_notify import NotificationHandler
from utils.helper import Service, makeDownloadFolder, start_logging, convert_minutes_to_time_units
from utils.config_manager import ConfigManager

try:
    from utils.permissions import PermissionHandler
    PermissionHandler().requestStorageAccess()
except Exception as e:
    traceback.print_exc()


try:
    start_logging()
except:
    pass

# ---------- CLICKABLE THUMBNAIL IMAGE ----------

class Thumb(ButtonBehavior, AsyncImage):
    source_path = StringProperty()

# ---------- THUMBNAIL LIST SCREEN ----------

class ThumbListScreen(MDScreen):  # Changed to MDScreen
    wallpapers = ListProperty([])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = [0.1, 0.1, 0.1, 1]  # Now you can set md_bg_color!

# ---------- FULLSCREEN VIEWER ----------

class FullscreenScreen(MDScreen):  # Changed to MDScreen
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = [0, 0, 0, 1]  # Black background for fullscreen
        self.bottom_height = 0.15
        self.is_fullscreen = False
        
        
        self.layout = MDFloatLayout(md_bg_color= [0, 0, 0, 1])
        self.add_widget(self.layout)
        
        # Image
        self.full_img = AsyncImage(
            allow_stretch=True,fit_mode="contain",
            size_hint=(1, 1 - self.bottom_height),
            pos_hint={'x': 0, 'y': self.bottom_height}
        )
        self.layout.add_widget(self.full_img)
        
        # Bottom buttons
        self.btn_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint=(1, self.bottom_height),
            pos_hint={'x': 0, 'y': 0},
            spacing=5,
            padding=dp(5),
            md_bg_color= [0, 0,0, 1]  
        )
        self.btn_delete = Button(text="Delete")
        self.btn_info = Button(text="Info")
        self.btn_fullscreen = Button(text="Fullscreen")
        self.btn_layout.add_widget(self.btn_delete)
        self.btn_layout.add_widget(self.btn_info)
        self.btn_layout.add_widget(self.btn_fullscreen)
        self.layout.add_widget(self.btn_layout)
        
        # Top-left toggle button
        self.btn_toggle = Button(
            text="Back",
            size_hint=(None, None),
            size=(dp(70), dp(70)),
            pos_hint={'x': 0.02, 'y': 0.9}
        )
        self.layout.add_widget(self.btn_toggle)
        
        # Bind buttons
        self.btn_delete.bind(on_release=self.delete_current)
        self.btn_info.bind(on_release=self.show_info)
        self.btn_fullscreen.bind(on_release=self.toggle_fullscreen)
        self.btn_toggle.bind(on_release=self.toggle_top_button)
    
    # -------------------- FULLSCREEN --------------------
    def toggle_fullscreen(self, *args):
        self.is_fullscreen = True
        self.full_img.size_hint = (None, None)
        self.full_img.allow_stretch=True
        self.full_img.fit_mode="cover"
        
        self.full_img.width = Window.width
        self.full_img.height = Window.height
        self.full_img. pos_hint={'center_x': 0.5, 'center_y':0.5}
        
        self.btn_layout.opacity = 0
        self.btn_layout.disabled = True
        
        self.btn_toggle.text = "Exit"
        self.btn_toggle.opacity = 1
        self.btn_toggle.disabled = False
        
        self.layout.do_layout()
    
    def toggle_top_button(self, *args):
        if self.btn_toggle.text == "Exit":
            self.full_img.keep_ratio = True
            self.full_img.size_hint = (1, 1 - self.bottom_height)
            self.full_img.pos_hint = {'x': 0, 'y': self.bottom_height}
            self.full_img.fit_mode="contain"
            self.btn_layout.opacity = 1
            self.btn_layout.disabled = False
            self.btn_toggle.text = "Back"
            self.is_fullscreen = False
        else:
            MDApp.get_running_app().sm.current = "thumbs"
    
    # -------------------- DELETE IMAGE --------------------
    def delete_current(self, *args):
        app = MDApp.get_running_app()
        if app.wallpapers:
            idx = app.current_index
            path = app.wallpapers.pop(idx)
            app.config.remove_wallpaper(path)
            if os.path.exists(path):
                os.remove(path)
            app.update_thumbnails()
            MDApp.get_running_app().sm.current = "thumbs"
    
    # -------------------- SHOW IMAGE INFO --------------------
    def show_info(self, *args):
        app = MDApp.get_running_app()
        if app.wallpapers:
            path = app.wallpapers[app.current_index]
            popup = Popup(
                title="Image Info",
                content=Label(text=f"Path: {path}"),
                size_hint=(0.8, 0.4)
            )
            popup.open()

# ---------- SETTINGS SCREEN ----------

class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = [0.2, 0.2, 0.3, 1]

        app = MDApp.get_running_app()
        app.interval = float(app.config.get_interval())

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
            text=str(app.interval),
            hint_text="mins",
            size_hint_x=0.55,
            mode="outlined")
        self.interval_input.input_filter="float"
        
        save_btn = Button(text="Save", size_hint_x=0.35)
        save_btn.bind(on_release=self.save_interval)

        input_row.add_widget(self.interval_input)
        input_row.add_widget(save_btn)
        root.add_widget(input_row)

        self.interval_label = Label(
            text=f"Saved: {app.interval} mins",
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
            on_release=lambda *_: setattr(app.sm, 'current', 'thumbs')
        )
        root.add_widget(back_btn)
        self.add_widget(root)

    def terminate_carousel(self,*args):
        try:
            Service(name="Mycarousel").stop()
            toast("Successfully Terminated")
        except:
            toast("Stop failed")

    # SAVE ONLY
    def save_interval(self, *args):
        app = MDApp.get_running_app()
        try:
            new_val = float(self.interval_input.text)
        except:
            toast("Enter a valid number")
            return

        if new_val < 0.17:
            toast("Min allowed is 0.17 mins")
            return

        app.interval = new_val
        app.config.set_interval(new_val)
        self.interval_label.text = f"Saved: {new_val} mins"
        toast("Saved")

    # RESTART SERVICE ONLY
    def restart_service(self, *args):
        app = MDApp.get_running_app()

        def after_stop(*_):
            try:
                Service(name="Mycarousel").start()
                toast("Service boosted!")
            except:
                toast("Start failed")

        try:
            Service(name="Mycarousel").stop()
            Clock.schedule_once(after_stop, 1.2)
        except:
            toast("Stop failed")
# ---------- MAIN APP ----------

class WallpaperCarouselApp(MDApp):
    interval = 2  # default rotation interval
    
    def on_start(self):
        try:
            NotificationHandler.asks_permission()
        except:
            traceback.print_exc()
        def android_service():
            try:
                Service(name='Mycarousel').start()
            except:
                traceback.print_exc()
        Clock.schedule_once(lambda dt:android_service(),2)

    def on_resume(self):
        try:
            self.load_saved()
        except:
            toast("Error loading saved")

    def build(self):
        # Change to MDScreenManager
        self.sm = MDScreenManager()
        self.sm.md_bg_color = [0.05, 0.05, 0.05, 1]  # Manager background
        
        self.app_dir = Path(makeDownloadFolder())
        self.config = ConfigManager(self.app_dir)
        self.wallpapers_dir = self.app_dir / ".wallpapers"
        self.wallpapers_dir.mkdir(parents=True, exist_ok=True)
        
        # Screens
        self.build_thumbnails_screen()
        self.build_fullscreen_screen()
        self.build_settings_screen()
        
        # Load saved wallpapers
        
        self.load_saved()
        return self.sm
    
    # ---------- BUILD SCREENS ----------
    def build_thumbnails_screen(self):
        screen = ThumbListScreen(name="thumbs")
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        
        layout.add_widget(Label(text="Wallpapers", size_hint_y=0.1, font_size="22sp"))
        
        # RecycleView for thumbnails
        self.rv = RecycleView(size_hint_y=0.8)
        grid = RecycleGridLayout(cols=3,
                                 spacing=5,
                                 default_size=(None, dp(120)),
                                 default_size_hint=(1, None),
                                 size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        self.rv.add_widget(grid)
        self.rv.layout_manager = grid
        self.rv.viewclass = "Thumb"
        
        layout.add_widget(self.rv)
        
        # Buttons
        btns = BoxLayout(size_hint_y=0.1, spacing=10)
        btns.add_widget(Button(text="Add Images", on_release=self.open_filechooser))
        btns.add_widget(Button(text="Settings (WIP)", on_release=lambda *_: setattr(self.sm, 'current', 'settings')))
        layout.add_widget(btns)
        
        screen.add_widget(layout)
        self.sm.add_widget(screen)
    
    def build_fullscreen_screen(self):
        self.full_screen = FullscreenScreen(name="fullscreen")
        self.sm.add_widget(self.full_screen)
    
    def build_settings_screen(self):
        screen = SettingsScreen(name="settings")
        self.sm.add_widget(screen)
    
    # ---------- LOAD WALLPAPERS ----------
    def load_saved(self):
        self.wallpapers = [
            str(p) for p in self.wallpapers_dir.glob("*")
            if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        ]
        print("Loaded wallpapers:", self.wallpapers)
        self.config.set_wallpapers(self.wallpapers)
        self.update_thumbnails()
    
    def update_thumbnails(self):
        data = []
        for i, path in enumerate(self.wallpapers):
            data.append({
                "source": path,
                "source_path": path,
                "on_release": lambda p=path, idx=i: self.open_fullscreen(p, idx)
            })
        print("Thumbnail data length:", len(data))
        self.rv.data = data
    
    # ---------- FULLSCREEN ----------
    def open_fullscreen(self, path, index):
        self.full_screen.full_img.source = path
        self.current_index = index
        self.sm.current = "fullscreen"
    
    # ---------- ADD IMAGES ----------
    def open_filechooser(self, *args):
        filechooser.open_file(on_selection=self.copy_add, multiple=True)
    
    def copy_add(self, files):
        if not files:
            return
        new_images = []
        for src in files:
            if not os.path.exists(src):
                continue
            dest = self.unique(os.path.basename(src))
            try:
                shutil.copy2(src, dest)
            except:
                continue
            new_images.append(str(dest))
            self.wallpapers.append(str(dest))
        self.config.add_wallpaper(path)
        self.update_thumbnails()
    
    def unique(self, dest_name):
        dest = self.wallpapers_dir / dest_name
        base, ext = os.path.splitext(dest_name)
        i = 1
        while dest.exists():
            dest = self.wallpapers_dir / f"{base}_{i}{ext}"
            i += 1
        return dest
    

if __name__ == '__main__':
    WallpaperCarouselApp().run()
