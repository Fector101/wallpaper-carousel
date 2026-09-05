import os
from pathlib import Path

from kivy.clock import Clock
from kivy.properties import ListProperty, ObjectProperty, NumericProperty
from kivy.metrics import dp, sp

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.carousel import Carousel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.menu.menu import MDDropdownLeadingIconItem
from kivymd.uix.relativelayout import MDRelativeLayout

from ui.widgets.layouts import MyMDScreen, LoadingLayout

from utils.config_manager import ConfigManager
from utils.helper import format_size
from utils.model import get_app, GalleryTabs
from utils.logger import app_logger


my_config=ConfigManager()



class BorderMDBoxLayout(MDBoxLayout):
    line_width = NumericProperty(1)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.graphics import Color, Line

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


class MyMDIconButton(MDIconButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_bg_color = "Custom"
        self.bg_color = 'black'
        self.theme_text_color = 'Custom'
        self.text_color = 'white'


class FullscreenDropdownItem(MDDropdownLeadingIconItem):
    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.ids.label.pos_hint = {"center_y": .44}
        Clock.schedule_once(self._hide_divider, 0)

    def _hide_divider(self, *args):
        for child in self.children:
            if child.__class__.__name__ == "MDDivider":
                child.opacity = 0
                child.size_hint_y = None
                child.height = 0
                break


class PictureButton(ButtonBehavior,MDRelativeLayout):
    app_src = ''#'/home/fabian/Documents/Laner/mobile/app_src/'
    images = [app_src+"assets/icons/t.png",app_src+"assets/icons/moon.png",app_src+"assets/icons/sun.png"]#ListProperty([])
    # images = ["/home/fabian/Documents/Laner/mobile/app_src/assets/icons/t.png","/home/fabian/Documents/Laner/mobile/app_src/assets/icons/moon.png","/home/fabian/Documents/Laner/mobile/app_src/assets/icons/sun.png"]#ListProperty([])
    img_sizes = [100,42,42]
    screen_color = ListProperty()
    fullscreen = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.uix.image import AsyncImage
        self.app = get_app()
        self.elevation = 0
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
        current_image = self.fullscreen.current_image
        gallery_screen = self.app.sm.gallery_screen
        old_tab = self.get_tab_from_index(self.i)
        self.i = self.i + 1 if self.i < len(self.images) - 1 else 0
        new_tab = self.get_tab_from_index(self.i)

        app_logger.info(f"FS_CYCLE: i={self.i} old_tab={old_tab} new_tab={new_tab} current_image={current_image}")
        self._update_image()
        self.__change_tab_from_wallpaper_storage(current_image=current_image,old_tab=old_tab,new_tab=new_tab)

        # try:
        #     gallery_screen.wallpapers.remove(current_image)
        # except ValueError as error_removing_path_from_wallpapers_list:
        #     app_logger.error(f"error_removing_path_from_wallpapers_list: {error_removing_path_from_wallpapers_list}")
        try:
            image_widget = gallery_screen.remove_wallpaper_from_thumbnails(wallpaper_path=current_image,tab=old_tab)
        except Exception as error_finding_widget:
            app_logger.error(f"Error Removing Widget: {error_finding_widget}")
            return None

        if not image_widget:
            app_logger.error(f"Error finding PreviewImage Widget to remove and reuse for another, image_widget: {image_widget}")
            return None

        gallery_screen.add_wallpaper_to_thumbnails(image_widget=image_widget,tab=new_tab)
        app_logger.info(f"FS_CYCLE: done cycle {old_tab} -> {new_tab}")
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

        try:
            from utils.database import ImageDatabase
            ImageDatabase().update_tab(current_image, new_tab)
        except Exception:
            pass


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

# delete_dialog_popup = DialogScreen(ok_callback = self.delete_current)


class FullscreenScreen(MyMDScreen):
    current_image: str # used in toggle btn

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "fullscreen"
        self.btm_btn_layout_root = None
        self.share_btn = None
        self.carousel = None
        self.text_container = None
        self.header_title = None
        self.day_noon_both_button = None
        self.dropdown_btn = None
        self.header_dropdown_menu = None
        self.btn_fullscreen=None
        self.original_carousel_pos_hint = None
        self.original_carousel_size_hint = None
        self.set_wallpaper_btn = None
        self.btn_home_widget = None
        self.btn_layout = None
        self.header_file_size = None
        self.btn_close = None
        self.btn_toggle = None
        self.header_layout = None
        self.layout = None
        self.generic_status_bar_spacer = None
        self.info_popup = None
        self.carousel_has_images = None
        self.clock_for_higher_format = None
        self.md_bg_color =[0, 0, 0, 1]
        self.bottom_height = 0.12
        self.is_fullscreen = False
        
        from utils.helper import appFolder
        self.app = get_app()
        self.app_dir = Path(appFolder())
        self.wallpapers_dir = self.app_dir / "wallpapers"
        self.built_ui = False
        # self.build_ui()# hot_reload

    def on_enter(self, *args):
        super().on_enter(*args)
        if not self.built_ui:
            Clock.schedule_once(self._timer_set)
        else:
            self._reload_high_res_on_reenter()

    def _timer_set(self, _):
        Clock.schedule_once(self.build_ui)

    def _reload_high_res_on_reenter(self):
        current_slide = self.carousel.current_slide
        if not current_slide:
            return
        current_slide._high_res_loaded = False
        self._load_high_res(current_slide)

    def build_ui(self, _=None):
        if self.built_ui:
            return
        self.built_ui = True

        from kivymd.uix.label import MDLabel
        from kivymd.uix.floatlayout import MDFloatLayout
        from ui.widgets.layouts import get_dimensions, GenericStatusBarSpacer
        from ui.widgets.modals import DialogScreen, InfoPopUpModal
        from utils.image_operations import share_image_to_other_app

        self.generic_status_bar_spacer=GenericStatusBarSpacer(
            status_bar_height=self.status_bar_height,
            md_bg_color=[.1, .1, .1, 1])
        self.add_widget(self.generic_status_bar_spacer)
        sub_text = "This wallpaper will be permanently removed from App Storage"
        header_text = "Remove Image?"
        delete_dialog_popup = DialogScreen(header_text=header_text, subtitle_text=sub_text, ok_callback = self.delete_current)
        self.info_popup = InfoPopUpModal()
        # self.add_widget(self.info_popup) # hot_reload
        # Main layout container
        self.layout = MDFloatLayout(md_bg_color=[0, 0, 0, 1])
        self.layout.pos_hint ={"top":1}


        self.header_layout = BorderMDBoxLayout(
            orientation="horizontal", radius=[25],
            size_hint=[.95, None], height=dp(60),
            pos_hint={'center_x': .5, 'top': .98},
            padding=[dp(10), dp(10)], spacing=dp(8))
        self.header_layout.y = get_dimensions()[0]
        self.header_layout.md_bg_color = [.1, .1, .1, 1]
        self.app.bind(device_theme=self._set_theme_color)
        self.btn_toggle = MDIconButton(
            icon="chevron-left",
            style="standard",
            size=(dp(70), dp(70)),
            pos_hint={'center_y': 0.5},
            theme_text_color='Custom',
            text_color=[1, 1, 1, 1],
            on_release=self.handle_going_back,
            md_bg_color = [.1, .1, .1, 1],
            theme_bg_color = 'Custom'
        )


        self.btn_close = MDIconButton(
            icon="close",
            style="outlined",
            size=(dp(70), dp(70)),
            pos_hint={'x': .025, 'top': .98},
            theme_text_color='Custom',
            text_color=[1, 1, 1, .9],
            opacity=0,
            disabled=True,
            on_release=lambda *_: self.leave_preview_mode(),
            md_bg_color = [.1, .1, .1, 1],
            theme_bg_color = 'Custom'
        )

        self.text_container = MDBoxLayout(orientation="vertical")
        self.header_title = MDLabel(text="", pos_hint={'center_y': .48})
        self.header_file_size = MDLabel(text=" ", pos_hint={'center_y': .46},adaptive_size=True,padding=[dp(4),dp(1)])

        self.header_file_size.font_size = sp(12)
        self.header_file_size.radius = dp(5)
        self.header_file_size.md_bg_color = [1,1,1,.2]
        self.header_title.shorten = True
        self.header_title.shorten_from = "right"
        self.header_title.text_color = 'white'
        self.header_file_size.text_color = [.6,.6,.6,1]

        self.share_btn = MyMDIconButton(icon="share", style="tonal", theme_icon_color="Custom", icon_color=[1,1,1,1], on_release=lambda *_args: share_image_to_other_app(self.current_image))
        self.dropdown_btn = MyMDIconButton(icon="dots-vertical", style="tonal", theme_icon_color="Custom", icon_color=[1,1,1,1])
        self.original_carousel_pos_hint = {'x': 0, 'y': 0.125}
        self.original_carousel_size_hint = (1, 1 - .25)
        self.carousel = MyCarousel(direction="right", loop=True,
                                   size_hint=self.original_carousel_size_hint,
                                   pos_hint=self.original_carousel_pos_hint)

        self._build_dropdown_menu(
            delete_callback=lambda *_args: self._run_dropdown_action(
                lambda: delete_dialog_popup.show(img_texture=self.carousel.current_slide.texture)
            ),
            info_callback=lambda *_args: self._run_dropdown_action(
                lambda: self.info_popup.show(image_abs_path=self.current_image, img_texture=self.carousel.current_slide.texture)
            ),
        )

        self.btm_btn_layout_root = MDRelativeLayout(
            size_hint=(1, self.bottom_height),
            pos_hint={"y": 0}
        )
        self.btn_layout = BorderMDBoxLayout(
            pos_hint={'center_x': .5, 'center_y': .55},
            spacing=dp(20),
            padding=[dp(20), dp(5)],
            adaptive_size=True,
            radius=[25],
            md_bg_color=[.1, .1, .1, 1],
        )
        left_btm_box = BorderMDBoxLayout(
            pos_hint={'center_x': .1, 'center_y': .549},
            spacing=dp(20),
            adaptive_size=True,
            radius=[25],
            md_bg_color=[.1, .1, .1, 1],
        )
        self.set_wallpaper_btn = MyMDIconButton(icon="wall", style="tonal", theme_icon_color="Custom", icon_color=[1,1,1,1])
        left_btm_box.add_widget(self.set_wallpaper_btn)
        # home-plus-outline, shape-plus, or widgets-outline.
        self.btn_home_widget = MyMDIconButton(icon="home-plus", style="tonal", theme_icon_color="Custom", icon_color=[1,1,1,1])
        self.btn_fullscreen = MyMDIconButton(icon="fullscreen", style="tonal", theme_icon_color="Custom", icon_color=[1,1,1,1])
        right_btm_box= MDBoxLayout(
            pos_hint={'center_x': .9, 'center_y': .549},
            adaptive_size=True,
            radius=[25],
            md_bg_color=[.1, .1, .1, 1],
        )

        self.day_noon_both_button=PictureButton(screen_color=self.md_bg_color,fullscreen=self)
        self.day_noon_both_button.size_hint=[None,None]
        s=42
        self.day_noon_both_button.size=[dp(s),dp(s)]
        right_btm_box.add_widget(self.day_noon_both_button)


        self.add_widget(self.layout)
        self.layout.add_widget(self.carousel)
        self.text_container.add_widget(self.header_title)
        self.text_container.add_widget(self.header_file_size)
        self.header_layout.add_widget(self.btn_toggle)
        self.header_layout.add_widget(self.text_container)
        self.header_layout.add_widget(self.dropdown_btn)
        self.layout.add_widget(self.header_layout)
        self.layout.add_widget(self.btn_close)


        self.btm_btn_layout_root.add_widget(left_btm_box)
        self.btn_layout.add_widget(self.share_btn)
        self.btn_layout.add_widget(self.btn_home_widget)
        self.btn_layout.add_widget(self.btn_fullscreen)
        self.btm_btn_layout_root.add_widget(self.btn_layout)
        self.btm_btn_layout_root.add_widget(right_btm_box)
        self.layout.add_widget(self.btm_btn_layout_root)

        # Bind events
        self.dropdown_btn.bind(on_release=lambda *_args: self.header_dropdown_menu.open())
        self.btn_fullscreen.bind(on_release=self.enter_preview_mode)

        # self.set_wallpaper_btn.bind(on_release=lambda x: change_wallpaper(self.carousel.current_slide.higher_format))
        self.set_wallpaper_btn.bind(on_release=self.set_as_wallpaper)
        self.btn_home_widget.bind(on_release=self.add_widget_to_home_screen)
        # p("using hot reload stuff")
        # self.update_images(0)  # for hot_reload

    def _build_dropdown_menu(self, delete_callback, info_callback):
        is_dark = self.app.device_theme == "dark"
        text_color = [1, 1, 1, 1] if is_dark else [0, 0, 0, 1]
        bg_color = [.15, .15, .15, 1] if is_dark else [1, 1, 1, 1]
        self._menu_items_data = [
            {"text": "Delete", "leading_icon": "trash-can-outline", "on_release": delete_callback,
             "theme_text_color": "Custom", "theme_bg_color": "Custom",
             "text_color": text_color, "leading_icon_color": text_color, "md_bg_color": bg_color,
             "viewclass": "FullscreenDropdownItem"},
            {"text": "Info", "leading_icon": "information-outline", "on_release": info_callback,
             "theme_text_color": "Custom", "theme_bg_color": "Custom",
             "text_color": text_color, "leading_icon_color": text_color, "md_bg_color": bg_color,
             "viewclass": "FullscreenDropdownItem"},
        ]
        self.header_dropdown_menu = MDDropdownMenu(
            caller=self.dropdown_btn,
            items=self._menu_items_data,
            width_mult=2.5,
            theme_bg_color="Custom",
            ver_growth="down",
            hor_growth="left",
        )

    def _run_dropdown_action(self, action, *_args):
        if self.header_dropdown_menu is not None:
            self.header_dropdown_menu.dismiss()
        action()

    def _update_menu_theme(self, bg_color, text_color):
        if self.header_dropdown_menu is None:
            return
        self.header_dropdown_menu.md_bg_color = bg_color
        for item in self._menu_items_data:
            item["md_bg_color"] = bg_color
            item["text_color"] = text_color
            item["leading_icon_color"] = text_color
        self.header_dropdown_menu.items = self._menu_items_data

    def _set_theme_color(self, _, theme):
        is_dark = theme == "dark"
        sb_bg = [.1, .1, .1, 1] if is_dark else [0.8, 0.8, 0.8, 1]
        header_bg = [.1, .1, .1, 1] if is_dark else [.9, .9, .9, 1]
        tc = [1, 1, 1, 1] if is_dark else [0, 0, 0, 1]
        menu_bg = [.15, .15, .15, 1] if is_dark else [1, 1, 1, 1]
        self.generic_status_bar_spacer.md_bg_color = sb_bg
        self.header_layout.md_bg_color = header_bg
        self.btn_toggle.md_bg_color = header_bg
        self.btn_layout.md_bg_color = header_bg
        self.btn_close.md_bg_color = header_bg
        self.btn_toggle.text_color = tc
        self.header_title.text_color = tc
        self.set_wallpaper_btn.icon_color = tc
        self.btn_home_widget.icon_color = tc
        self.btn_fullscreen.icon_color = tc
        self.share_btn.icon_color = tc
        self.dropdown_btn.icon_color = tc
        self._update_menu_theme(menu_bg, tc)

    def enter_preview_mode(self, *_):
        self.is_fullscreen = True

        self.carousel.size_hint = (1, 1)
        self.carousel.pos_hint = {'center_x': .5, 'center_y': .5}

        self.header_layout.pos_hint = {'center_x': .5, 'top': 1.2}

        self.btn_close.opacity = 1
        self.btn_close.disabled = False

        self.btm_btn_layout_root.pos_hint = {"y": -2}
        for img in self.carousel.slides:
            img.fit_mode = "cover"

        self.layout.do_layout()
        self.hide_system_ui()
        self.generic_status_bar_spacer.status_bar_height=0

    def handle_going_back(self, *_):
        if self.is_fullscreen:
            self.leave_preview_mode()
        else:
            self.back_to_gallery_screen()
    
    def set_as_wallpaper(self, *_):
        import threading
        from utils.helper import change_wallpaper
        spinner_layout = LoadingLayout()
        def remove_spinner(_):
            spinner_layout.remove()
        threading.Thread(target=change_wallpaper, args=[self.carousel.current_slide.higher_format, remove_spinner], daemon=True).start()

    def add_widget_to_home_screen(self, *_):
        from utils.android import add_home_screen_widget
        current_slide = self.carousel.current_slide
        image_path = current_slide.higher_format if current_slide else None
        add_home_screen_widget(image_path=image_path)

    def delete_current(self, *_):
        spinner_layout = LoadingLayout()

        gallery_screen = self.manager.gallery_screen
        wallpapers = gallery_screen.wallpapers
        if not wallpapers:
            spinner_layout.remove()
            return

        idx = self.carousel.index
        # Get path without removing it from the list directly
        path = wallpapers[idx]

        # remove_wallpaper_from_thumbnails edits the underlying list for us
        gallery_screen.remove_wallpaper_from_thumbnails(path)

        if path and os.path.exists(path):
            os.remove(path)
            try:
                from utils.database import ImageDatabase
                ImageDatabase().remove_image(path)
            except Exception:
                pass
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
            
        self.update_images()
        new_index=max(0, min(idx, len(gallery_screen.wallpapers) - 1))
        self.carousel.index = new_index
        self.__patch_for_first_not_getting_called_by_on_current_slide(index=new_index)
        spinner_layout.remove()

    def update_images(self,index=None):
        """Rebuild carousel anytime wallpapers change."""
        from kivy.uix.image import Image
        from utils.image_operations import thumbnail_path_for
        self.build_ui()
        self.carousel.unbind(current_slide=self.on_current_slide)
        self.carousel.clear_widgets()
        self.carousel_has_images = False
        gallery_screen = self.manager.gallery_screen

        for p in gallery_screen.wallpapers:
            img = Image(
                source=str(thumbnail_path_for(p)),
                fit_mode="cover" if self.is_fullscreen else "contain",
            )
            img.higher_format = p
            self.carousel_has_images = True
            self.carousel.add_widget(img)
        self.carousel.bind(current_slide=self.on_current_slide)

        self.__patch_for_first_not_getting_called_by_on_current_slide(index)

    def __patch_for_first_not_getting_called_by_on_current_slide(self,index):
        if index == 0:
            self.on_current_slide(self.carousel,0)

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
        """Using on_current_slide instead of on_index to prevent multiple Calls"""
        if not self.carousel_has_images or not carousel.current_slide:
            return None

        current_slide = carousel.current_slide

        if hasattr(current_slide, "higher_format"):
            self.current_image = current_slide.higher_format

        if self.clock_for_higher_format:
            self.clock_for_higher_format.cancel()
            self.clock_for_higher_format = None

        self.update_header_texts(current_slide.higher_format)
        self.clock_for_higher_format = Clock.schedule_once(
            lambda dt: self._load_high_res(current_slide), 0.8)
        return None

    def _load_high_res(self, slide):
        from kivy.loader import Loader
        if getattr(slide, '_high_res_loaded', False):
            return
        hf = str(slide.higher_format)
        if slide.source == hf:
            slide._high_res_loaded = True
            return
        slide._high_res_loaded = True
        proxy = Loader.image(hf)
        proxy.bind(on_load=lambda p, obj=slide: self._apply_high_res(p, obj))
        if proxy.image is not None and proxy.image.texture:
            self._apply_high_res(proxy, slide)

    def _apply_high_res(self, proxy_image, slide):
        if proxy_image.image.texture:
            slide.texture = proxy_image.image.texture
            slide.source = str(slide.higher_format)
            slide._high_res_loaded = True

    def leave_preview_mode(self,*_):
        self.carousel.size_hint = self.original_carousel_size_hint
        self.carousel.pos_hint = self.original_carousel_pos_hint
        self.header_layout.pos_hint = {'center_x': .5, 'top': .98}

        self.btn_close.opacity = 0
        self.btn_close.disabled = True

        self.btm_btn_layout_root.pos_hint = {"y": 0}

        self.set_wallpaper_btn.icon_color = [1,1,1,1] if self.app.device_theme == "dark" else [0,0,0,1]
        self.btn_home_widget.icon_color = self.set_wallpaper_btn.icon_color
        self.btn_fullscreen.icon_color = self.set_wallpaper_btn.icon_color
        self.share_btn.icon_color = self.set_wallpaper_btn.icon_color
        self.dropdown_btn.icon_color = self.set_wallpaper_btn.icon_color
        self.is_fullscreen = False

        for img in self.carousel.slides:
            img.fit_mode = "contain"

        self.show_system_ui()
        self.generic_status_bar_spacer.status_bar_height=self.status_bar_height

    def back_to_gallery_screen(self,*_):
        self.app.sm.gallery_screen.refresh_gallery_screen()
        self.manager.current = "thumbs"


def patch_resolution(proxy_image, image_object, higher_format):
    if proxy_image.image.texture:
        image_object.texture = proxy_image.image.texture
        image_object.source = higher_format
        image_object._high_res_loaded = True

def hide_nav_btn_and_status_bar():
    from android_notify.internal.java_classes import autoclass
    from android_notify.config import get_python_activity_context, on_android_platform
    if not on_android_platform():
        return
    try:
        View = autoclass('android.view.View')
        decor_view = get_python_activity_context().getWindow().getDecorView()
        decor_view.setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
        )
    except Exception as error_hiding_nav_btn_and_status_bar:
        app_logger.exception(error_hiding_nav_btn_and_status_bar)


def thing(*_):
    print(f"bad img: {_}")