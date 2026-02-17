import os
from pathlib import Path

from kivy.clock import Clock
from kivy.properties import ListProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.metrics import dp, sp
from kivy.uix.popup import Popup
from kivy.uix.carousel import Carousel
from kivymd.uix.label import MDLabel
from kivymd.uix.relativelayout import MDRelativeLayout

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.button import MDIconButton
from kivy.graphics import Color, Line

from ui.widgets.layouts import MyPopUp, MyMDScreen, get_dimensions
from utils.image_operations import thumbnail_path_for, get_image_info
from utils.helper import appFolder, change_wallpaper
from utils.config_manager import ConfigManager
from utils.constants import DEV
from utils.model import get_app


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

    def update_border(self, *_):
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

def format_size(bytes_size):
    """
    Convert bytes to human-readable size.
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024

class MyMDIconButton(MDIconButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_bg_color = "Custom"
        self.bg_color = 'black'
        self.theme_text_color = 'Custom'
        self.text_color = 'white'

class PictureButton(ButtonBehavior,MDRelativeLayout):
    app_src = ''#'/home/fabian/Documents/Laner/mobile/app_src/'
    images = [app_src+"assets/icons/t.png",app_src+"assets/icons/moon.png",app_src+"assets/icons/sun.png"]#ListProperty([])
    # images = ["/home/fabian/Documents/Laner/mobile/app_src/assets/icons/t.png","/home/fabian/Documents/Laner/mobile/app_src/assets/icons/moon.png","/home/fabian/Documents/Laner/mobile/app_src/assets/icons/sun.png"]#ListProperty([])
    img_sizes = [100,42,42]
    screen_color = ListProperty()
    fullscreen = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.myconfig = ConfigManager()
        self.img = AsyncImage()
        self.img.mipmap=True
        self.i = 0
        self.md_bg_color=self.screen_color

        # self.img
        # self.adaptive_size=True
        self.img.pos_hint = {'center_x': .5, 'center_y': .5}
        self.img.size_hint=[None,None]
        self.padding=[0]
        self.img.source = self.images[self.i]
        self.img.size=[dp(self.img_sizes[self.i]),dp(self.img_sizes[self.i])]

        self.add_widget(self.img)
    def on_release(self):
        self.i = self.i + 1 if self.i < len(self.images) - 1 else 0
        self.img.source = self.images[self.i]
        self.img.size=[dp(self.img_sizes[self.i]),dp(self.img_sizes[self.i])]

        current_image = self.fullscreen.current_image
        # Both Day and Night
        if self.images[self.i] == self.images[0]:
            self.myconfig.add_wallpaper(current_image)
            self.myconfig.remove_wallpaper_to_from("noon_wallpapers", current_image)
            self.myconfig.remove_wallpaper_to_from("day_wallpapers", current_image)

        # Only Night
        if self.images[self.i] == self.images[1]:
            self.myconfig.add_wallpaper_to_noon_wallpapers(current_image)
            self.myconfig.remove_wallpaper_to_from("day_wallpapers", current_image)
            self.myconfig.remove_wallpaper(current_image)

        # Only Day
        if self.images[self.i] == self.images[2]:
            self.myconfig.add_wallpaper_to_day_wallpapers(current_image)
            self.myconfig.remove_wallpaper_to_from("noon_wallpapers", current_image)
            self.myconfig.remove_wallpaper(current_image)

    def set_day_image(self):
        self.i = 2
        self.img.source = self.images[self.i]
        self.img.size = [dp(self.img_sizes[self.i]), dp(self.img_sizes[self.i])]
    def set_noon_image(self):
        self.i = 1
        self.img.source = self.images[self.i]
        self.img.size = [dp(self.img_sizes[self.i]), dp(self.img_sizes[self.i])]
    def set_day_nd_noon_image(self):
        self.i = 0
        self.img.source = self.images[self.i]
        self.img.size = [dp(self.img_sizes[self.i]), dp(self.img_sizes[self.i])]


class FullscreenScreen(MyMDScreen):
    current_image: str # used in toggle btn

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.clock_for_higher_format = None
        self.clock_for_side_by_side = None
        self.app_dir = Path(appFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"

        self.name = "fullscreen"
        self.md_bg_color =[0, 0, 0, 1]
        self.bottom_height = 0.12
        self.is_fullscreen = False

        # Main layout container
        self.layout = MDFloatLayout(md_bg_color=[0, 0, 0, 1])
        self.layout.pos_hint ={"top":1}
        # self.layout.orientation="vertical"

        self.header_layout = BorderMDBoxLayout(
            orientation="horizontal", radius=[25],
            size_hint=[.95, None], height=dp(60),
            pos_hint={'center_x': .5, 'top': .98},
            padding=[dp(10), dp(10)], spacing=dp(8))
        self.header_layout.y = get_dimensions()[0]
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
        self.text_container = MDBoxLayout(orientation="vertical")
        # self.text_container.md_bg_color=[.1, 1, 0, 1]
        self.header_title = MDLabel(text="", pos_hint={'center_y': .48})
        self.header_file_size = MDLabel(text=" ", pos_hint={'center_y': .46},adaptive_size=True,padding=[dp(4),dp(1)])

        self.header_file_size.font_size = sp(12)
        self.header_file_size.radius = dp(5)
        self.header_file_size.md_bg_color = [1,1,1,.2]
        self.header_title.shorten = True
        self.header_title.shorten_from = "right"
        self.header_title.text_color = 'white'
        self.header_file_size.text_color = [.6,.6,.6,1]

        self.original_carousel_pos_hint = {'x': 0, 'y': 0.125}
        self.original_carousel_size_hint = (1, 1 - .25)
        self.carousel = MyCarousel(direction="right", loop=True,
                                   size_hint=self.original_carousel_size_hint,
                                   pos_hint=self.original_carousel_pos_hint)
        self.carousel.bind(index=self.on_current_slide)

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
        left_btm_box = BorderMDBoxLayout(
            pos_hint={'center_x': .1, 'center_y': .549},
            spacing=dp(20),
            adaptive_size=True,
            radius=[25],
            md_bg_color=[.1, .1, .1, 1],
        )
        self.set_wallpaper_btn = MyMDIconButton(icon="wall", style="tonal")
        left_btm_box.add_widget(self.set_wallpaper_btn)
        self.btn_delete = MyMDIconButton(icon="trash-can", style="tonal", )  # ext="Delete")
        self.btn_info = MyMDIconButton(icon="information-outline", style="tonal", )  # Button(text="Info")
        self.btn_fullscreen = MyMDIconButton(icon="fullscreen", style="tonal")
        right_btm_box= MDBoxLayout(
            # orientation='horizontal',
            # size_hint=(1, self.bottom_height),
            pos_hint={'center_x': .9, 'center_y': .549},
            # spacing=dp(20),
            adaptive_size=True,
            radius=[25],
            md_bg_color=[.1, .1, .1, 1],
            # size_hint=[1,1]
            # md_bg_color=[bg, bg, bg, 1]
        )
        if DEV:
            self.day_noon_both_button=PictureButton(screen_color=self.md_bg_color,fullscreen=self)
            self.day_noon_both_button.size_hint=[None,None]
            s=42
            self.day_noon_both_button.size=[dp(s),dp(s)]
            # self.time_btn.theme_font_size='Custom'
            # self.time_btn.font_size=sp(120)

            right_btm_box.add_widget(self.day_noon_both_button)


        self.add_widget(self.layout)
        self.layout.add_widget(self.carousel)
        self.header_layout.add_widget(self.btn_toggle)
        self.text_container.add_widget(self.header_title)
        self.text_container.add_widget(self.header_file_size)
        self.header_layout.add_widget(self.text_container)
        self.layout.add_widget(self.header_layout)


        self.btm_btn_layout_root.add_widget(left_btm_box)
        self.btn_layout.add_widget(self.btn_delete)
        self.btn_layout.add_widget(self.btn_info)
        self.btn_layout.add_widget(self.btn_fullscreen)
        self.btm_btn_layout_root.add_widget(self.btn_layout)
        self.btm_btn_layout_root.add_widget(right_btm_box)
        self.layout.add_widget(self.btm_btn_layout_root)

        # Bind events
        self.btn_delete.bind(on_release=self.delete_current)
        self.btn_info.bind(on_release=self.show_info)
        self.btn_fullscreen.bind(on_release=self.toggle_fullscreen)
        self.btn_toggle.bind(on_release=self.toggle_top_button)
        self.set_wallpaper_btn.bind(on_release=lambda x: change_wallpaper(self.carousel.current_slide.higher_format))
        # self.update_images()  # for hot_reload

    def toggle_fullscreen(self, *_):
        # print(self.carousel.children[0].children)
        self.is_fullscreen = True

        self.carousel.size_hint = (1, 1)
        self.carousel.pos_hint = {'center_x': .5, 'center_y': .5}
        self.header_layout.md_bg_color = [0, 0, 0, 0]
        self.header_title.text_color = [0, 0, 0, 0]
        self.header_layout.bg_color_instr.a = 0
        self.header_file_size.text_color = [0, 0, 0, 0]
        self.header_file_size.md_bg_color = [0, 0, 0, 0]

        self.btn_toggle.text_color = [1, 1, 1, .9]
        self.btn_toggle.style = "outlined"

        self.btm_btn_layout_root.pos_hint = {"y": -2}
        # self.btn_layout.disabled = True

        self.btn_toggle.icon = "close"
        for img in self.carousel.slides:
            img.fit_mode = "cover"

        self.layout.do_layout()

    def toggle_top_button(self, *_):
        # If in fullscreen mode → restore controls
        if self.btn_toggle.icon == "close":
            self.carousel.size_hint = self.original_carousel_size_hint
            self.carousel.pos_hint = self.original_carousel_pos_hint
            self.header_layout.pos_hint = {'center_x': .5, 'top': .97}
            self.header_title.text_color = [1, 1, 1, 1]
            self.header_layout.bg_color_instr.a = .8
            self.header_file_size.md_bg_color = [1, 1, 1, .2]
            self.header_file_size.text_color = [.6, .6, .6, 1]

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
            self.app.sm.gallery_screen.load_current_tab_wallpapers()
            self.manager.current = "thumbs"

    def delete_current(self, *_):
        gallery_screen = self.manager.gallery_screen
        wallpapers = gallery_screen.wallpapers
        if not wallpapers:
            return

        idx = self.carousel.index
        path = wallpapers.pop(idx)

        if path and os.path.exists(path):
            # if self.app.sm.gallery_screen.current_tab not in ["Day", "Noon"]:
            os.remove(path)
            # remove its low-res thumbnail (if exists)
            try:
                thumb = Path(path).parent / "thumbs" / f"{Path(path).stem}_thumb.jpg"
                if thumb.exists():
                    thumb.unlink()
            except Exception as error_deleting_image:
                print(f"Error deleting image: {error_deleting_image}")
                pass

        if self.app.sm.gallery_screen.current_tab == "Both":
            ConfigManager().remove_wallpaper(path)
            # ConfigManager().remove_wallpaper_to_from("day_wallpapers", path)
            # ConfigManager().remove_wallpaper_to_from("noon_wallpapers", path)


        if self.app.sm.gallery_screen.current_tab == "Day":
            ConfigManager().remove_wallpaper_to_from("day_wallpapers",path)


        if self.app.sm.gallery_screen.current_tab == "Noon":
            ConfigManager().remove_wallpaper_to_from("noon_wallpapers", path)

        if not wallpapers:
            gallery_screen.update_thumbnails_method()
            self.manager.current = "thumbs"
            return
        gallery_screen.wallpapers=wallpapers
        gallery_screen.update_thumbnails_method()
        self.update_images()
        self.carousel.index = max(0, min(idx, len(wallpapers) - 1))

    # ====================================================================
    #               IMAGE INFO POPUP
    # ====================================================================
    def show_info(self, *_):
        gallery_screen = self.manager.gallery_screen

        if not gallery_screen.wallpapers:
            return

        idx = self.carousel.index
        path = gallery_screen.wallpapers[idx]

        popup = MyPopUp(
            info = get_image_info(path)
            # title="Image Info",
            # content=Label(text=f"Path:\n{path}"),
            # size_hint=(0.8, 0.4)
        )
        popup.open()

    def update_images(self):
        """Rebuild carousel anytime wallpapers change."""
        gallery_screen = self.manager.gallery_screen
        self.carousel.clear_widgets()

        # for hot_reload
        # self.data = ["/home/fabian/Downloads/home screen.png",
        #              "/home/fabian/Downloads/storage screen modal - Delete.png",
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

    def update_header_texts(self,image_path):
        self.header_title.text = os.path.basename(image_path)
        if os.path.exists(image_path):
            self.header_file_size.text = format_size(os.path.getsize(image_path))

        day_images = self.myconfig.get_day_wallpapers()
        noon_images = self.myconfig.get_noon_wallpapers()

        if image_path in day_images:
            self.day_noon_both_button.set_day_image()
        elif image_path in noon_images:
            self.day_noon_both_button.set_noon_image()
        else:
            self.day_noon_both_button.set_day_nd_noon_image()

    def on_current_slide(self, carousel, index): # type: ignore
        if hasattr(self.carousel.current_slide,"higher_format"):
            self.current_image = self.carousel.current_slide.higher_format
        current_slide = self.carousel.current_slide
        if self.clock_for_side_by_side:
            self.clock_for_side_by_side.cancel()
        if self.clock_for_higher_format:
            self.clock_for_higher_format.cancel()
        if not current_slide:
            return None
        def change_img(_):
            current_slide.source = str(current_slide.higher_format)

        self.update_header_texts(current_slide.higher_format)
        self.clock_for_higher_format = Clock.schedule_once(change_img, 1)
        self.clock_for_side_by_side = Clock.schedule_once(self.set_side_by_side, 1.5)
        return None
    #
    # def set_side_by_side1(self, widget):
    #     if os.path.basename(widget.source) != os.path.basename(self.carousel.current_slide.source):
    #         return None
    #     print(os.path.basename(widget.source), "on load:", os.path.basename(self.carousel.current_slide.source))
    #     current_slide_index = self.carousel.index
    #     first_img = self.carousel.slides[0]
    #     last_img = self.carousel.slides[-1]
    #
    #     left_side_img = self.carousel.slides[current_slide_index - 1] if current_slide_index - 1 >= 0 else last_img
    #     right_side_img = self.carousel.slides[current_slide_index + 1] if current_slide_index + 1 < len(
    #         self.carousel.slides) else first_img
    #
    #     print("left_side_img source:", os.path.basename(left_side_img.source), "left_side_img hf:",
    #           os.path.basename(left_side_img.higher_format))
    #     if left_side_img:
    #         if left_side_img.source != str(left_side_img.higher_format):
    #             print('left...')
    #             left_side_img.source = str(left_side_img.higher_format)
    #     if right_side_img:
    #         if right_side_img.source != str(right_side_img.higher_format):
    #             print('right...')
    #             right_side_img.source = str(right_side_img.higher_format)
    #     return None

    def set_side_by_side(self, *_):
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

        # print("left_side_img source:", os.path.basename(left_side_img.source), "left_side_img hf:",
        #       os.path.basename(left_side_img.higher_format))
        if left_side_img:
            if left_side_img.source != str(left_side_img.higher_format):
                # print('left...')
                left_side_img.source = str(left_side_img.higher_format)
        if right_side_img:
            if right_side_img.source != str(right_side_img.higher_format):
                # print('right...')
                right_side_img.source = str(right_side_img.higher_format)
        return None
