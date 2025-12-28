import os
import traceback
from pathlib import Path

from kivy.uix.image import AsyncImage, Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.carousel import Carousel

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout

try:
    from kivymd.toast import toast
except TypeError:
    def toast(*args):
        print('Fallback toast:', args)

from utils.helper import Service, makeDownloadFolder, start_logging, smart_convert_minutes
from utils.config_manager import ConfigManager


class FullscreenScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / ".wallpapers"

        self.name = "fullscreen"
        self.md_bg_color = [0, 0, 0, 1]
        self.bottom_height = 0.15
        self.is_fullscreen = False

        # Main layout container
        self.layout = MDFloatLayout(md_bg_color=[0, 0, 0, 1])
        self.add_widget(self.layout)

        # === SWIPE CAROUSEL ===
        self.carousel = Carousel(direction="right", loop=True,
                                 size_hint=(1, 1 - self.bottom_height),
                                 pos_hint={'x': 0, 'y': self.bottom_height})
        self.layout.add_widget(self.carousel)

        # === BOTTOM BUTTONS ===
        self.btn_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint=(1, self.bottom_height),
            pos_hint={'x': 0, 'y': 0},
            spacing=dp(5),
            padding=dp(5),
            md_bg_color=[0, 0, 0, 1]
        )

        self.btn_delete = Button(text="Delete")
        self.btn_info = Button(text="Info")
        self.btn_fullscreen = Button(text="Fullscreen")

        self.btn_layout.add_widget(self.btn_delete)
        self.btn_layout.add_widget(self.btn_info)
        self.btn_layout.add_widget(self.btn_fullscreen)
        self.layout.add_widget(self.btn_layout)

        # === BACK / EXIT FULLSCREEN ===
        self.btn_toggle = Button(
            text="Back",
            size_hint=(None, None),
            size=(dp(70), dp(70)),
            pos_hint={'x': 0.02, 'y': 0.9}
        )
        self.layout.add_widget(self.btn_toggle)

        # Bind events
        self.btn_delete.bind(on_release=self.delete_current)
        self.btn_info.bind(on_release=self.show_info)
        self.btn_fullscreen.bind(on_release=self.toggle_fullscreen)
        self.btn_toggle.bind(on_release=self.toggle_top_button)

    # ====================================================================
    #               FULLSCREEN TOGGLE BEHAVIOR
    # ====================================================================
    def toggle_fullscreen(self, *args):
        print(self.carousel.children[0].children)
        self.is_fullscreen = True

        self.carousel.size_hint = (1, 1)
        self.carousel.pos_hint = {'center_x': .5, 'center_y': .5}

        self.btn_layout.opacity = 0
        self.btn_layout.disabled = True

        self.btn_toggle.text = "Exit"
        for img in self.carousel.slides:
            img.fit_mode = "cover"

        self.layout.do_layout()

    def toggle_top_button(self, *args):
        # If in fullscreen mode → restore controls
        if self.btn_toggle.text == "Exit":
            self.carousel.size_hint = (1, 1 - self.bottom_height)
            self.carousel.pos_hint = {'x': 0, 'y': self.bottom_height}

            self.btn_layout.opacity = 1
            self.btn_layout.disabled = False

            self.btn_toggle.text = "Back"
            self.is_fullscreen = False

            for img in self.carousel.slides:
                img.fit_mode = "contain"

        # If not fullscreen → go back to thumbnails screen
        else:
            self.manager.current = "thumbs"

    # ====================================================================
    #               DELETE IMAGE
    # ====================================================================
    def delete_current(self, *args):
        gallery_screen = self.manager.gallery_screen
        wallpapers = gallery_screen.wallpapers
        if not wallpapers:
            return

        idx = self.carousel.index
        path = wallpapers.pop(idx)

        if path and os.path.exists(path):
            os.remove(path)
            # remove its low-res thumbnail (if exists)
            try:
                thumb = Path(path).parent / "thumbs" / f"{Path(path).stem}_thumb.jpg"
                if thumb.exists():
                    thumb.unlink()
            except Exception:
                pass

        app_dir = Path(makeDownloadFolder())
        ConfigManager().remove_wallpaper(path)

        if not wallpapers:
            gallery_screen.update_thumbnails_method(wallpapers)
            self.manager.current = "thumbs"
            return

        gallery_screen.update_thumbnails_method(wallpapers)
        self.update_images()
        self.carousel.index = max(0, min(idx, len(wallpapers) - 1))

    # ====================================================================
    #               IMAGE INFO POPUP
    # ====================================================================
    def show_info(self, *args):
        gallery_screen = self.manager.gallery_screen

        if not gallery_screen.wallpapers:
            return

        idx = self.carousel.index
        path = gallery_screen.wallpapers[idx]

        popup = Popup(
            title="Image Info",
            content=Label(text=f"Path:\n{path}"),
            size_hint=(0.8, 0.4)
        )
        popup.open()

    # ====================================================================
    #               REBUILD CAROUSEL IMAGES
    # ====================================================================
    def update_images(self):
        """Rebuild carousel anytime wallpapers change."""
        gallery_screen = self.manager.gallery_screen
        self.carousel.clear_widgets()

        for p in gallery_screen.wallpapers:
            img = AsyncImage(
                source=p,
                # allow_stretch=True,
                # keep_ratio=True,
                fit_mode="contain"
            )
            self.carousel.add_widget(img)
