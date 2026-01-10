import os
import traceback
from pathlib import Path

from kivy.clock import Clock
from kivy.uix.image import AsyncImage, Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.carousel import Carousel
from kivymd.uix.label import MDLabel
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

from kivy.graphics import Color, Rectangle, RoundedRectangle, Line



class BorderMDBoxLayout(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.after:
            c = .5
            self.bg_color_instr = Color(c, c, c, .8)
            self.border = Line(width=1, rounded_rectangle=self.round_rect_args)
        self.bind(pos=self.update_border, size=self.update_border)

    @property
    def round_rect_args(self):
        return self.x, self.y, self.width, self.height, self.radius[0]

    def update_border(self, *args):
        self.border.rounded_rectangle = self.round_rect_args  # (self.x,self.y,self.width,self.height,16)


class MyCarousel(Carousel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    #     r = 25
    #
    #     with self.canvas.before:
    #         self.bg_color_instr = Color([1,1,0,0.1])
    #         self.rect = RoundedRectangle(radius=[r, r, r, r])
    #     self.bind(size=self.update_rect, pos=self.update_rect)
    #
    # def update_rect(self, *args):
    #         self.rect.size = self.size
    #         self.rect.pos = self.pos


class MyMDIconButton(MDIconButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_bg_color = "Custom"
        self.bg_color = 'black'
        self.theme_text_color = 'Custom'
        self.text_color = 'white'


class FullscreenScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"

        self.name = "fullscreen"
        self.md_bg_color = [0, 0, 0, 1]
        self.bottom_height = 0.12
        self.is_fullscreen = False

        # Main layout container
        self.layout = MDFloatLayout(md_bg_color=[0, 0, 0, 1])
        # self.layout.orientation="vertical"
        self.add_widget(self.layout)

        self.original_carousel_pos_hint = {'x': 0, 'y': 0.125}
        self.original_carousel_size_hint = (1, 1 - .25)
        self.carousel = MyCarousel(direction="right", loop=True,
                                   size_hint=self.original_carousel_size_hint,
                                   pos_hint=self.original_carousel_pos_hint)
        self.carousel.bind(index=self.on_current_slide)

        self.layout.add_widget(self.carousel)


        self.header_layout = BorderMDBoxLayout(
            orientation="horizontal", radius=[25],
            size_hint=[.95, None], height=dp(60),
            pos_hint={'center_x': .5, 'top': .97},
            padding=[dp(10), dp(10)], spacing=dp(8))
        # self.header_layout.y=Window.height - dp(110)
        self.header_layout.md_bg_color = [.1, .1, .1, 1]
        self.btn_toggle = MDIconButton(
            icon="chevron-left",
            style="standard",
            size=(dp(70), dp(70)),
            pos_hint={'center_y': 0.5},
            theme_text_color='Custom',
            text_color=[1, 1, 1, 1]
        )

        self.btn_toggle.theme_bg_color = 'Custom'
        self.btn_toggle.md_bg_color = self.header_layout.md_bg_color

        self.header_title = MDLabel(text="",
                                    pos_hint={'center_y': .48})
        self.header_title.shorten = True
        self.header_title.shorten_from = "right"
        self.header_title.text_color = 'white'

        self.header_layout.add_widget(self.btn_toggle)
        self.header_layout.add_widget(self.header_title)
        self.layout.add_widget(self.header_layout)

        bg = .2
        self.btm_btn_layout_root = MDRelativeLayout(
            size_hint=(1, self.bottom_height),
            # md_bg_color=[.1, .1, .12, 1],
            pos_hint={"y": 0}
        )
        self.btn_layout = BorderMDBoxLayout(
            # orientation='horizontal',
            # size_hint=(1, self.bottom_height),
            pos_hint={'center_x': .5, 'center_y': .55},
            spacing=dp(20),
            padding=[dp(20), dp(5)],
            adaptive_size=True,
            radius=[25],
            md_bg_color=[.1, .1, .1, 1],
            # md_bg_color=[bg, bg, bg, 1]
        )

        self.btn_delete = MyMDIconButton(icon="trash-can", style="tonal", )  # ext="Delete")
        self.btn_info = MyMDIconButton(icon="information-outline", style="tonal", )  # Button(text="Info")
        self.btn_fullscreen = MyMDIconButton(icon="fullscreen", style="tonal")

        self.btn_layout.add_widget(self.btn_delete)
        self.btn_layout.add_widget(self.btn_info)
        self.btn_layout.add_widget(self.btn_fullscreen)

        self.btm_btn_layout_root.add_widget(self.btn_layout)
        self.layout.add_widget(self.btm_btn_layout_root)

        # Bind events
        self.btn_delete.bind(on_release=self.delete_current)
        self.btn_info.bind(on_release=self.show_info)
        self.btn_fullscreen.bind(on_release=self.toggle_fullscreen)
        self.btn_toggle.bind(on_release=self.toggle_top_button)
        # self.update_images()  # for hot_reload

    def toggle_fullscreen(self, *args):
        # print(self.carousel.children[0].children)
        self.is_fullscreen = True

        self.carousel.size_hint = (1, 1)
        self.carousel.pos_hint = {'center_x': .5, 'center_y': .5}
        self.header_layout.md_bg_color = [0, 0, 0, 0]
        self.header_title.text_color = [0, 0, 0, 0]
        self.header_layout.bg_color_instr.rgba = [0, 0, 0, 0]

        self.btn_toggle.text_color = [1, 1, 1, .9]
        self.btn_toggle.style = "outlined"

        self.btm_btn_layout_root.pos_hint = {"y": -2}
        # self.btn_layout.disabled = True

        self.btn_toggle.icon = "close"
        for img in self.carousel.slides:
            img.fit_mode = "cover"

        self.layout.do_layout()

    def toggle_top_button(self, *args):
        # If in fullscreen mode → restore controls
        if self.btn_toggle.icon == "close":
            self.carousel.size_hint = self.original_carousel_size_hint
            self.carousel.pos_hint = self.original_carousel_pos_hint
            self.header_layout.pos_hint = {'center_x': .5, 'top': .97}
            self.header_title.text_color = [1, 1, 1, 1]
            self.header_layout.bg_color_instr.rgba = [.5, .5, .5, .8]

            self.btm_btn_layout_root.pos_hint = {"y": 0}

            self.header_layout.md_bg_color = self.btn_toggle.md_bg_color
            self.btn_toggle.icon = "chevron-left"
            self.btn_toggle.style = "standard"
            self.btn_toggle.theme_text_color = 'Custom'
            self.btn_toggle.text_color = [1, 1, 1, 1]
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

        # for hot_reload
        # self.data = ["/home/fabian/Downloads/home screen.png",
        #              "/home/fabian/Downloads/stroage screen modal - Delete.png",
        #              "/home/fabian/Documents/Laner/mobile/wallpapers/Anime Art Night Sky Scenery Wallpaper iPhone Phone 4k 1400f.jpg",
        #              "/home/fabian/Documents/Laner/mobile/wallpapers/content.png",
        #              "/home/fabian/Documents/Laner/mobile/wallpapers/Anime Girl Wallpaper.jpeg"]
        for p in gallery_screen.wallpapers:
        # for p in self.data:
            # print("thumbnail_path_for(p)", str(thumbnail_path_for(p)))
            img = AsyncImage(
                source=str(thumbnail_path_for(p)),  # p,
                # allow_stretch=True,
                # keep_ratio=True,
                fit_mode="contain",
                # on_load=self.set_side_by_side1
            )
            img.higher_format = p
            self.carousel.add_widget(img)

    def on_current_slide(self, carousel, index):

        current_slide = self.carousel.current_slide

        if not current_slide:
            return None
        def change_img(dt):
            current_slide.source = str(current_slide.higher_format)

        self.header_title.text = os.path.basename(current_slide.source)
        Clock.schedule_once(change_img, 1)
        Clock.schedule_once(self.set_side_by_side, 1.5)
        return None

    def set_side_by_side1(self, widget):
        if os.path.basename(widget.source) != os.path.basename(self.carousel.current_slide.source):
            return None
        print(os.path.basename(widget.source), "on load:", os.path.basename(self.carousel.current_slide.source))
        current_slide_index = self.carousel.index
        first_img = self.carousel.slides[0]
        last_img = self.carousel.slides[-1]

        left_side_img = self.carousel.slides[current_slide_index - 1] if current_slide_index - 1 >= 0 else last_img
        right_side_img = self.carousel.slides[current_slide_index + 1] if current_slide_index + 1 < len(
            self.carousel.slides) else first_img

        print("left_side_img source:", os.path.basename(left_side_img.source), "left_side_img hf:",
              os.path.basename(left_side_img.higher_format))
        if left_side_img:
            if left_side_img.source != str(left_side_img.higher_format):
                print('left...')
                left_side_img.source = str(left_side_img.higher_format)
        if right_side_img:
            if right_side_img.source != str(right_side_img.higher_format):
                print('right...')
                right_side_img.source = str(right_side_img.higher_format)
        return None

    def set_side_by_side(self, *args):
        """
        Set High res img for left and right side.
        """
        # AsyncImage(on_load=self.set_side_by_side) not calling right
        # print(str(self.carousel.current_slide.higher_format) != str(self.carousel.current_slide.source))

        if str(self.carousel.current_slide.higher_format) != str(self.carousel.current_slide.source):
            # Not setting for high format image, so return
            return None

        current_slide_index = self.carousel.index
        first_img = self.carousel.slides[0]
        last_img = self.carousel.slides[-1]

        left_side_img = self.carousel.slides[current_slide_index - 1] if current_slide_index - 1 >= 0 else last_img
        right_side_img = self.carousel.slides[current_slide_index + 1] if current_slide_index + 1 < len(
            self.carousel.slides) else first_img

        # print("left_side_img source:",left_side_img.source,"left_side_img hf:",left_side_img.higher_format)
        if left_side_img:
            if left_side_img.source != str(left_side_img.higher_format):
                # print('left...')
                left_side_img.source = str(left_side_img.higher_format)
        if right_side_img:
            if right_side_img.source != str(right_side_img.higher_format):
                # print('right...')
                right_side_img.source = str(right_side_img.higher_format)
        return None
