import os
import traceback
from pathlib import Path

from kivy.uix.image import AsyncImage, Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.carousel import Carousel
from kivymd.uix.relativelayout import MDRelativeLayout

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout

try:
    from kivymd.toast import toast
except TypeError:
    def toast(*args):
        print('Fallback toast:', args)

from utils.helper import makeDownloadFolder, thumbnail_path_for
from utils.config_manager import ConfigManager
from kivymd.uix.button import MDIconButton

# from kivy.core.window import Window
# from kivy.utils import platform
#
# if platform == 'linux':
#     from kivy import Config
#     #Linux has some weirdness with the touchpad by default... remove it
#     options = Config.options('input')
#     for option in options:
#         if Config.get('input', option) == 'probesysfs':
#             Config.remove_option('input', option)
#     Window.size = (370, 700)

class FullscreenScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"

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
        self.carousel.bind(index=self.on_current_slide)

        self.layout.add_widget(self.carousel)

        # === BOTTOM BUTTONS ===
        self.btn_layout_x = MDRelativeLayout(
            size_hint=(1, self.bottom_height),
        )
        bg=.2
        self.btn_layout = MDBoxLayout(
            # orientation='horizontal',
            # size_hint=(1, self.bottom_height),
            pos_hint={'center_x': .5, 'center_y': .5},
            spacing=dp(20),
            padding=[dp(20),dp(10)],
            adaptive_size=True,
            radius=[10],
            md_bg_color=[bg, bg, bg, 1]
        )

        self.btn_delete = MDIconButton(icon="trash-can",style="tonal",)#ext="Delete")
        self.btn_info = MDIconButton(icon="information-outline",style="tonal",)#Button(text="Info")
        self.btn_fullscreen = MDIconButton(icon="fullscreen",style="tonal")


        self.btn_layout.add_widget(self.btn_delete)
        self.btn_layout.add_widget(self.btn_info)
        self.btn_layout.add_widget(self.btn_fullscreen)

        self.btn_layout_x.add_widget(self.btn_layout)
        self.layout.add_widget(self.btn_layout_x)

        # === BACK / EXIT FULLSCREEN ===

        self.btn_toggle = MDIconButton(
            icon="chevron-left",
            style="tonal",
            size=(dp(70), dp(70)),
            pos_hint={'x': 0.04, 'y': 0.9}
        )
        self.layout.add_widget(self.btn_toggle)

        # Bind events
        self.btn_delete.bind(on_release=self.delete_current)
        self.btn_info.bind(on_release=self.show_info)
        self.btn_fullscreen.bind(on_release=self.toggle_fullscreen)
        self.btn_toggle.bind(on_release=self.toggle_top_button)
        # self.update_images() for hot_reload

    def toggle_fullscreen(self, *args):
        # print(self.carousel.children[0].children)
        self.is_fullscreen = True

        self.carousel.size_hint = (1, 1)
        self.carousel.pos_hint = {'center_x': .5, 'center_y': .5}

        self.btn_layout.opacity = 0
        self.btn_layout.disabled = True

        self.btn_toggle.icon = "close"
        for img in self.carousel.slides:
            img.fit_mode = "cover"

        self.layout.do_layout()

    def toggle_top_button(self, *args):
        # If in fullscreen mode → restore controls
        if self.btn_toggle.icon == "close":
            self.carousel.size_hint = (1, 1 - self.bottom_height)
            self.carousel.pos_hint = {'x': 0, 'y': self.bottom_height}

            self.btn_layout.opacity = 1
            self.btn_layout.disabled = False

            self.btn_toggle.icon = "chevron-left"
            self.is_fullscreen = False

            for img in self.carousel.slides:
                img.fit_mode = "contain"

        # If not fullscreen → go back to thumbnails screen
        else:
            self.manager.current = "thumbs"

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

    def update_images(self):
        """Rebuild carousel anytime wallpapers change."""
        gallery_screen = self.manager.gallery_screen
        self.carousel.clear_widgets()

        # for hot_reload self.data=["/home/fabian/Documents/Laner/mobile/wallpapers/Anime Art Night Sky Scenery Wallpaper iPhone Phone 4k 1400f.jpg","/home/fabian/Documents/Laner/mobile/wallpapers/content.png","/home/fabian/Documents/Laner/mobile/wallpapers/Anime Girl Wallpaper.jpeg"]
        for p in gallery_screen.wallpapers:
            # print("thumbnail_path_for(p)", str(thumbnail_path_for(p)))
            img = AsyncImage(
                source=str(thumbnail_path_for(p)),#p,
                # allow_stretch=True,
                # keep_ratio=True,
                fit_mode="contain"
            )
            img.higher_format = p
            self.carousel.add_widget(img)

    def on_current_slide(self,carousel,index):
        current_slide = self.carousel.current_slide

        if current_slide:
            current_slide.source = str(current_slide.higher_format)
