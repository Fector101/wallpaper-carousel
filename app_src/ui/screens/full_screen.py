import os
import threading
import traceback
from pathlib import Path

from kivy.clock import Clock
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, DictProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
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

from ui.widgets.layouts import MyPopUp, MyMDScreen, get_dimensions, LoadingLayout, GenericStatusBarSpacer
from utils.image_operations import thumbnail_path_for, get_image_info, share_image_to_other_app
from utils.helper import appFolder, change_wallpaper
from utils.config_manager import ConfigManager
# from utils.constants import DEV
from utils.model import get_app, GalleryTabs
from kivy.loader import  Loader
from utils.logger import app_logger


my_config=ConfigManager()


class BorderMDBoxLayout(MDBoxLayout):
    line_width = NumericProperty(1)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.after:
            c = .5
            self.bg_color_instr = Color(c, c, c, .8)

            self.border = Line(width=self.line_width, rounded_rectangle=self.round_rect_args)
        self.bind(pos=self.update_border, size=self.update_border)

    @property
    def round_rect_args(self):
        return self.x, self.y, self.width, self.height, self.radius[0]

    def update_border(self, *_):
        self.border.rounded_rectangle = self.round_rect_args  # (self.x,self.y,self.width,self.height,16)


class MyCarousel(Carousel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
    images = [app_src+"assets/icons/both.png",app_src+"assets/icons/moon.png",app_src+"assets/icons/sun.png"]#ListProperty([])
    # images = ["/home/fabian/Documents/Laner/mobile/app_src/assets/icons/both.png","/home/fabian/Documents/Laner/mobile/app_src/assets/icons/moon.png","/home/fabian/Documents/Laner/mobile/app_src/assets/icons/sun.png"]#ListProperty([])
    img_sizes = [100,42,42]
    screen_color = ListProperty()
    fullscreen = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.img = AsyncImage()
        self.img.mipmap=True
        self.i = 0
        self.md_bg_color=self.screen_color

        # self.img
        # self.adaptive_size=True
        self.img.pos_hint = {'center_x': .5, 'center_y': .5}
        self.img.size_hint=[None,None]
        self.padding=[0]
        self._update_image()
        self.add_widget(self.img)

    def get_tab_from_index(self,index):
        tab_name = None
        if self.images[index] == self.images[0]:  # Both Day and Night
            tab_name = GalleryTabs.BOTH.value
        elif self.images[index] == self.images[1]:  # Only Noon
            tab_name = GalleryTabs.NOON.value
        elif self.images[index] == self.images[2]:  # Only Day
            tab_name = GalleryTabs.DAY.value

        return tab_name

    def on_release(self):
        img_path = self.fullscreen.current_image
        gallery_screen = self.app.sm.gallery_screen
        old_tab = self.get_tab_from_index(self.i)

        self.i = self.i + 1 if self.i < len(self.images) - 1 else 0
        new_tab = self.get_tab_from_index(self.i)

        slide = self.fullscreen.remove_image_in_tab_carousel(img_src=img_path)
        self.fullscreen.add_image_to_tab_carousel(slide,new_tab)

        self.__change_tab_from_wallpaper_storage(current_image=img_path,old_tab=old_tab,new_tab=new_tab)
        # try:
        #     gallery_screen.wallpapers.remove(current_image)
        # except ValueError as error_removing_path_from_wallpapers_list:
        #     app_logger.error(f"error_removing_path_from_wallpapers_list: {error_removing_path_from_wallpapers_list}")
        try:
            image_widget = gallery_screen.remove_wallpaper_from_thumbnails(wallpaper_path=img_path,tab=old_tab)
        except Exception as error_finding_widget:
            app_logger.error(f"Error Removing Widget: {error_finding_widget}")
            return None

        if not image_widget:
            app_logger.error(f"Error finding PreviewImage Widget to remove and reuse for another, img_path: {img_path} in tab:{old_tab}")
            return None

        gallery_screen.add_wallpaper_to_thumbnails(image_widget=image_widget,tab=new_tab)
        # self.update_header_texts(img_src)
        return None

    @staticmethod
    def __change_tab_from_wallpaper_storage(current_image,old_tab,new_tab):
        """Moves Wallpaper Path to Right Tab in Storage"""
        if old_tab == GalleryTabs.DAY.value:
            my_config.remove_wallpaper_to_from("day_wallpapers", current_image)
        elif old_tab == GalleryTabs.NOON.value:
            my_config.remove_wallpaper_to_from("noon_wallpapers", current_image)
        elif old_tab == GalleryTabs.BOTH.value:
            my_config.remove_wallpaper(current_image)

        if new_tab == GalleryTabs.BOTH.value:
            my_config.add_wallpaper(current_image)
        elif new_tab == GalleryTabs.NOON.value:
            my_config.add_wallpaper_to_noon_wallpapers(current_image)
        elif new_tab == GalleryTabs.DAY.value:
            my_config.add_wallpaper_to_day_wallpapers(current_image)


    def set_day_image(self):
        self.i = 2
        self._update_image()
    def set_noon_image(self):
        self.i = 1
        self._update_image()
    def set_day_nd_noon_image(self):
        self.i = 0
        self._update_image()
    def _update_image(self):
        self.img.source = self.images[self.i]
        self.img.size = [dp(self.img_sizes[self.i]), dp(self.img_sizes[self.i])]


class FullscreenScreen(MyMDScreen):
    current_image=''# used in toggle btn
    images_data= DictProperty({})
    tabs_carousel_widgets= DictProperty({})
    index=NumericProperty(-1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.carousel_has_images = None
        self.app = get_app()
        self.clock_for_higher_format = None
        self.clock_for_side_by_side = None
        self.app_dir = Path(appFolder())
        self.wallpapers_dir = self.app_dir / "wallpapers"

        self.name = "fullscreen"
        self.md_bg_color =[0, 0, 0, 1]
        self.bottom_height = 0.12
        self.is_fullscreen = False

        self.generic_status_bar_spacer=GenericStatusBarSpacer(
            status_bar_height=self.status_bar_height,
            md_bg_color=[0.8, 0.8, 0.8, 1] if self.app.device_theme == "light" else [.1, .1,.1, 1])
        self.add_widget(self.generic_status_bar_spacer)

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
            text_color=[1, 1, 1, 1],
            on_release=self.toggle_top_button
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

        self.share_btn = MyMDIconButton(icon="share", style="tonal",on_release=lambda x: share_image_to_other_app(self.current_image))
        self.original_carousel_pos_hint = {'x': 0, 'y': 0.125}
        self.original_carousel_size_hint = (1, 1 - .25)
        self.carousel=None
        self.carousel_container=BoxLayout()

        # self.carousel.bind(index=self.on_index)

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

        self.day_noon_both_button=PictureButton(screen_color=self.md_bg_color,fullscreen=self)
        self.day_noon_both_button.size_hint=[None,None]
        s=42
        self.day_noon_both_button.size=[dp(s),dp(s)]
        right_btm_box.add_widget(self.day_noon_both_button)


        self.add_widget(self.layout)
        self.layout.add_widget(self.carousel_container)
        self.header_layout.add_widget(self.btn_toggle)
        self.text_container.add_widget(self.header_title)
        self.text_container.add_widget(self.header_file_size)
        self.header_layout.add_widget(self.text_container)
        self.header_layout.add_widget(self.share_btn)
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

        # self.set_wallpaper_btn.bind(on_release=lambda x: change_wallpaper(self.carousel.current_slide.higher_format))
        self.set_wallpaper_btn.bind(on_release=self.set_as_wallpaper)
        # print("using hot reload stuff")
        # self.update_images(0)  # for hot_reload
        self.load_images()

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
            self.app.sm.gallery_screen.refresh_gallery_screen()
            self.manager.current = "thumbs"
    
    def set_as_wallpaper(self, *args):
        spinner_layout = LoadingLayout()
        def remove_spinner(dt):
            spinner_layout.remove()
        threading.Thread(target=change_wallpaper, args=[self.carousel.current_slide.higher_format, remove_spinner]).start()
        
    def delete_current(self, *_):
        spinner_layout = LoadingLayout()

        gallery_screen = self.manager.gallery_screen
        wallpapers = gallery_screen.wallpapers
        if not wallpapers:
            spinner_layout.remove()
            return
        
        carousel= self.carousel_container.children[0]# carousel is only child

        idx = carousel.index
        # Get path without removing it from the list directly
        path = wallpapers[idx]

        # remove_wallpaper_from_thumbnails edits the underlying list for us
        gallery_screen.remove_wallpaper_from_thumbnails(path)

        if path and os.path.exists(path):
            os.remove(path)
            try:
                thumb = Path(path).parent / "thumbs" / f"{Path(path).stem}_thumb.jpg"
                if thumb.exists():
                    thumb.unlink()
            except Exception as error_deleting_image:
                app_logger.error(f"Error deleting image: {error_deleting_image}")

        current_tab = self.app.sm.gallery_screen.current_tab
        if current_tab == GalleryTabs.BOTH.value:
            my_config.remove_wallpaper(path)
        elif current_tab == GalleryTabs.DAY.value:
            my_config.remove_wallpaper_to_from("day_wallpapers",path)
        elif current_tab == GalleryTabs.NOON.value:
            my_config.remove_wallpaper_to_from("noon_wallpapers", path)

        if not gallery_screen.wallpapers:
            self.manager.current = "thumbs"
            spinner_layout.remove()
            return
            
        # self.update_images()
        self.remove_image_in_tab_carousel(img_src=path)
        new_index=max(0, min(idx, len(gallery_screen.wallpapers) - 1))
        carousel.index = new_index
        # self.__patch_for_first_not_getting_called_by_on_current_slide(index=new_index)
        spinner_layout.remove()
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

    # def update_images(self,index=None):
    def load_images(self,index=None):
        """Rebuild carousel anytime wallpapers change."""
        self.carousel_has_images = False
        # for hot_reload
        # self.data = ["/home/fabian/Pictures/test.jpg"]
        # for p in self.data:
        tabs = [GalleryTabs.BOTH.value, GalleryTabs.DAY.value, GalleryTabs.NOON.value ]
        data = self.images_data
        self.tabs_carousel_widgets={}
        for each_tab in tabs:
            wallpapers=data[each_tab]
            carousel = MyCarousel(direction="right", loop=True,
                                   size_hint=self.original_carousel_size_hint,
                                   pos_hint=self.original_carousel_pos_hint)
            for p in wallpapers:
                img = AsyncImage(
                    source=p,
                    fit_mode="contain",
                )
                img.higher_format = p
                carousel.add_widget(img)
                # carousel.bind(current_slide=self.on_current_slide)
                self.carousel_has_images = True
            self.tabs_carousel_widgets[each_tab] = carousel

    def update_header_texts(self,image_path):
        self.header_title.text = os.path.basename(image_path)
        if os.path.exists(image_path):
            self.header_file_size.text = format_size(os.path.getsize(image_path))

        day_images = my_config.get_day_wallpapers()
        noon_images = my_config.get_noon_wallpapers()

        if image_path in day_images:
            self.day_noon_both_button.set_day_image()
        elif image_path in noon_images:
            self.day_noon_both_button.set_noon_image()
        else:
            self.day_noon_both_button.set_day_nd_noon_image()

    def on_current_slide(self, carousel, index): # type: ignore
        current_slide = carousel.current_slide
        if not current_slide: # this method gets called when using remove_widget to remove slide
            print("no slide")
            self.manager.go_to_thumbs()
            return None
        img_src=current_slide.higher_format
        self.current_image = img_src
        # print("self.current_image",self.current_image)
        self.update_header_texts(img_src)
        print()
        return None


    def on_leave(self, *args):
        self.index=-1
        carousel = self.carousel_container.children[0]
        carousel.unbind(current_slide=self.on_current_slide)

    def on_index(self,widget,value):
        current_tab=self.manager.gallery_screen.current_tab
        self.carousel_container.clear_widgets()
        self.carousel_container.add_widget(self.tabs_carousel_widgets[current_tab])
        carousel = self.tabs_carousel_widgets[current_tab]
        carousel.bind(current_slide=self.on_current_slide)
        if carousel.slides:
            carousel.index = value
            if value == 0:
                self.on_current_slide(carousel,0)
    def remove_image_in_tab_carousel(self,img_src,tab_name=None): # tab_name args for when i add multiselect feature to gallery screen
        tab_name=tab_name or self.manager.gallery_screen.current_tab
        carousel = self.tabs_carousel_widgets[tab_name] # same location in memory with current carousel if displaying so no need for calling self.carousel_container.children[0]
        index=0
        slides=carousel.slides
        for slide in slides:
            if slide.source==img_src:
                # print("found:", os.path.basename(img_src))
                carousel.remove_widget(slide)
                return slide
            index+=1

        app_logger.error(f"slide not found for path: {img_src}, tab_name: {tab_name}")
        # if slides and index+1 < len(slides): # if not empty
        #     self.update_header_texts(img_src)
        return None

    def add_image_to_tab_carousel(self,image_widget,tab_name):
        carousel = self.tabs_carousel_widgets[tab_name]
        print('adding...',image_widget,tab_name,carousel.children,carousel.slides)
        if carousel._index is None:
            carousel._index = 0
        carousel.add_widget(image_widget,len(carousel.slides))


def patch_resolution(proxy_image, image_object):
    image_object.texture = proxy_image.image.texture
