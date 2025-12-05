# Complete Kivy Wallpaper Carousel App (Kivy FileChooser version)

import sys
import os, traceback
from datetime import datetime
import json
import shutil
from pathlib import Path
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.carousel import Carousel
from kivy.clock import Clock
#from kivy.uix.filechooser import FileChooserListView
from plyer import filechooser # pylint: disable=import-error

IMAGE_FILTERS = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']

try:
    from utils.permissions import PermissionHandler
    PermissionHandler().requestStorageAccess()
except Exception as e:
    traceback.print_exc()
from utils.helper import Service,makeDownloadFolder, makeFolder,start_logging



try:
    start_logging()
except Exception as e:
    traceback.print_exc()

class WallpaperCarouselApp(App):
    def on_start(self):
        try:
            NotificationHandler.asks_permission()
        except Exception as e:
            traceback.print_exc()
        
        def android_service():
            try: 
                Service(name='MyCarousel')
            except Exception as e:
                traceback.print_exc()
        Clock.schedule_once(lambda dt:android_service(),2)
    def build(self):
        self.sm = ScreenManager()
        self.app_dir = Path(makeDownloadFolder())#Path(self.user_data_dir)
        self.wallpapers_dir = self.app_dir / 'wallpapers'
        self.config_file = self.app_dir / 'config.json'
        self.setup_storage()

        main_screen = Screen(name='main')
        main_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        title = Label(text='Wallpaper Carousel', size_hint_y=0.1, font_size='24sp', bold=True)

        self.carousel = Carousel(direction='right', loop=True, size_hint_y=0.6)
        self.info_label = Label(text='Select images to begin', size_hint_y=0.1)

        btns = BoxLayout(size_hint_y=0.2, spacing=10)
        btn_add = Button(text='Add Images')
        btn_add.bind(on_release=self.open_filechooser)
        btn_del = Button(text='Remove Current')
        btn_del.bind(on_release=self.remove_current)
        btn_view = Button(text='Fullscreen View')
        btn_view.bind(on_release=lambda *_: self.sm.current.__set__('carousel'))
        btns.add_widget(btn_add)
        btns.add_widget(btn_del)
        btns.add_widget(btn_view)

        main_layout.add_widget(title)
        main_layout.add_widget(self.carousel)
        main_layout.add_widget(self.info_label)
        main_layout.add_widget(btns)
        main_screen.add_widget(main_layout)
        self.sm.add_widget(main_screen)

        carousel_screen = Screen(name='carousel')
        fs = BoxLayout(orientation='vertical')
        self.fullscreen_carousel = Carousel(direction='right', loop=True)
        btn_back = Button(text='Back', size_hint_y=0.1)
        btn_back.bind(on_release=lambda *_: self.sm.current.__set__('main'))
        fs.add_widget(self.fullscreen_carousel)
        fs.add_widget(btn_back)
        carousel_screen.add_widget(fs)
        self.sm.add_widget(carousel_screen)

        self.load_saved()
        Clock.schedule_interval(self.auto_next, 5)

        return self.sm

    def setup_storage(self):
        self.wallpapers_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            with open(self.config_file, 'w') as f:
                json.dump({'wallpapers': []}, f)

    def load_saved(self):
        try:
            with open(self.config_file) as f:
                data = json.load(f)
            self.wallpapers = [wp for wp in data.get('wallpapers', []) if os.path.exists(wp)]
            self.carousel.clear_widgets()
            for img in self.wallpapers:
                self.add_to_carousel(img)
            self.update_label()
        except:
            self.wallpapers = []
            self.update_label()

    def save_list(self):
        with open(self.config_file, 'w') as f:
            json.dump({'wallpapers': self.wallpapers}, f, indent=2)

    def open_filechooser(self, *_):
        def finish(files_list):
            if files_list:
                selected=[files_list] if isinstance(files_list,str) else files_list
                self.copy_and_add(selected)
                
        filechooser.open_file(on_selection=finish, multiple=True)
        
    def copy_and_add(self, files):
        for src in files:
            if not os.path.exists(src):
                continue
            name = os.path.basename(src)
            dest = self.wallpapers_dir / name
            base, ext = os.path.splitext(name)
            i = 1
            while dest.exists():
                dest = self.wallpapers_dir / f"{base}_{i}{ext}"
                i += 1
            try:
                shutil.copy2(src, dest)
                self.wallpapers.append(str(dest))
                self.add_to_carousel(str(dest))
            except Exception as e:
                print("Copy error:", e)
        self.save_list()
        self.update_label()

    def add_to_carousel(self, path):
        self.carousel.add_widget(Image(source=path, allow_stretch=True, keep_ratio=True))

    def remove_current(self, *_):
        if not self.wallpapers or not self.carousel.slides:
            return
        idx = self.carousel.index
        removed = self.wallpapers.pop(idx)
        if os.path.exists(removed): os.remove(removed)
        self.carousel.remove_widget(self.carousel.slides[idx])
        self.save_list()
        self.update_label()

    def update_label(self):
        if not self.wallpapers:
            self.info_label.text = "No wallpapers yet"
        else:
            idx = (self.carousel.index % len(self.wallpapers)) + 1
            self.info_label.text = f"Image {idx} of {len(self.wallpapers)}"

    def auto_next(self, dt):
        if len(self.wallpapers) > 1:
            self.carousel.load_next()
            self.update_label()

if __name__ == '__main__':
    WallpaperCarouselApp().run()
