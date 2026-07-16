import os, time
import urllib.request
import threading
import traceback
from pathlib import Path

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.button import MDButton, MDButtonIcon, MDButtonText, MDIconButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.widget import MDWidget

from ui.widgets.layouts import MyMDScreen, Column, Row, PlaceOnMainScreen
from utils.config_manager import ConfigManager
from utils.helper import appFolder, load_kv_file
from utils.logger import app_logger
from utils.model import get_app
from utils.marketplace_data import get_marketplace_provider
from ui.widgets.android import toast

load_kv_file(py_file_absolute_path=__file__)
my_config = ConfigManager()
provider = get_marketplace_provider()

min_box_size = dp(80)
spacing = dp(2)


class MarketplaceCard(ButtonBehavior, MDRelativeLayout):
    source = StringProperty()
    wp_name = StringProperty()
    author = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._normal_image_pos = None
        self._normal_image_size = None

        self.image_widget = AsyncImage(
            source=self.source,
            fit_mode="cover",
            mipmap=True,
            size_hint=(None, None),
        )
        self.add_widget(self.image_widget)
        self.bind(size=self._fix_image_size)

    def _fix_image_size(self, _, size):
        if self.image_widget:
            self.image_widget.pos = (0, 0)
            self.image_widget.size = size

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._play_press_down_effect()
        touch.grab(self)
        return True

    def on_touch_up(self, touch):
        self._play_press_up_effect()
        if touch.grab_current is self:
            touch.ungrab(self)
            self.dispatch("on_release")
            return True
        return super().on_touch_up(touch)

    def _play_press_down_effect(self):
        from kivy.animation import Animation
        Animation.cancel_all(self.image_widget, "pos", "size", "opacity")
        self._normal_image_pos = self.image_widget.pos[:]
        self._normal_image_size = self.image_widget.size[:]
        inset = dp(3)
        pressed_pos = [self._normal_image_pos[0] + inset, self._normal_image_pos[1] + inset]
        pressed_size = [
            max(0, self._normal_image_size[0] - (inset * 2)),
            max(0, self._normal_image_size[1] - (inset * 2)),
        ]
        Animation(pos=pressed_pos, size=pressed_size, opacity=.75, duration=.06).start(self.image_widget)

    def _play_press_up_effect(self):
        from kivy.animation import Animation
        Animation.cancel_all(self.image_widget, "pos", "size", "opacity")
        normal_pos = self._normal_image_pos or [0, 0]
        normal_size = self._normal_image_size or self.size[:]
        Animation(pos=normal_pos, size=normal_size, opacity=1, duration=.08).start(self.image_widget)


class MarketplaceDetail(MDFloatLayout, PlaceOnMainScreen):
    gallery_screen = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.wallpaper_data = None
        self.downloaded_ids = set()

        self.size_hint = [1, 1]
        self.pos_hint = {"top": 1}
        self._build_ui()

    def _build_ui(self):
        self.bg = MDBoxLayout(
            orientation="vertical",
            md_bg_color=[.1, .1, .1, 1],
            size_hint=[1, 1],
            pos_hint={"top": 1},
        )

        header_row = Row(
            adaptive_height=True,
            padding=[dp(15), dp(10)],
            spacing=dp(10),
        )
        self.back_btn = MDIconButton(
            icon="arrow-left",
            theme_icon_color="Custom",
            icon_color=[.8, .8, .8, 1],
            on_release=self._go_back,
        )
        self.title_label = MDLabel(
            text="",
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1],
            font_name="RobotoMono",
            bold=True,
            font_size=sp(18),
            adaptive_size=True,
            pos_hint={"center_y": .5},
        )
        header_row.add_widget(self.back_btn)
        header_row.add_widget(self.title_label)
        header_row.add_widget(MDWidget())
        self.bg.add_widget(header_row)

        scroll = ScrollView(size_hint=[1, 1])
        content = Column(
            adaptive_height=True,
            padding=[dp(15), dp(5), dp(15), dp(100)],
            spacing=dp(15),
        )

        self.preview_image = AsyncImage(
            size_hint=[1, None],
            height=dp(250),
            fit_mode="contain",
            mipmap=True,
        )
        content.add_widget(self.preview_image)

        self.author_label = MDLabel(
            text="",
            theme_text_color="Custom",
            text_color=[.7, .7, .7, 1],
            font_name="RobotoMono",
            font_size=sp(13),
            adaptive_size=True,
        )
        content.add_widget(self.author_label)

        info_row = Row(adaptive_height=True, spacing=dp(15))
        self.resolution_label = MDLabel(
            text="",
            theme_text_color="Custom",
            text_color=[.6, .6, .6, 1],
            font_name="RobotoMono",
            font_size=sp(12),
            adaptive_size=True,
        )
        self.size_label = MDLabel(
            text="",
            theme_text_color="Custom",
            text_color=[.6, .6, .6, 1],
            font_name="RobotoMono",
            font_size=sp(12),
            adaptive_size=True,
        )
        info_row.add_widget(self.resolution_label)
        info_row.add_widget(self.size_label)
        content.add_widget(info_row)

        self.download_btn = MDButton(
            style="filled",
            theme_bg_color="Custom",
            md_bg_color=get_color_from_hex("#98F1DD"),
            theme_height="Custom",
            height=dp(48),
            size_hint=[1, None],
            radius=[dp(10)],
            on_release=self._download_wallpaper,
        )
        self.download_btn_text = MDButtonText(
            text="Download",
            theme_text_color="Custom",
            text_color=get_color_from_hex("#262C3A"),
            font_name="RobotoMono",
            font_size=sp(14),
            pos_hint={"center_x": .5, "center_y": .5},
        )
        self.download_btn.add_widget(self.download_btn_text)
        content.add_widget(self.download_btn)

        scroll.add_widget(content)
        self.bg.add_widget(scroll)
        self.add_widget(self.bg)

    def show(self, wallpaper_data):
        self.wallpaper_data = wallpaper_data
        self.title_label.text = wallpaper_data["name"]
        self.preview_image.source = wallpaper_data["image_url"]
        self.author_label.text = "by " + wallpaper_data["author"]
        self.resolution_label.text = wallpaper_data["resolution"]
        self.size_label.text = str(round(wallpaper_data["size_kb"] / 1024, 1)) + " MB"

        wp_id = wallpaper_data["id"]
        if wp_id in self.downloaded_ids:
            self.download_btn_text.text = "Downloaded"
            self.download_btn.disabled = True
            self.download_btn.md_bg_color = [.3, .3, .3, 1]
        else:
            self.download_btn_text.text = "Download"
            self.download_btn.disabled = False
            self.download_btn.md_bg_color = get_color_from_hex("#98F1DD")

        if not self.parent:
            self.gallery_screen.add_widget(self)

    def _go_back(self, *args):
        if self.parent:
            self.parent.remove_widget(self)
        if hasattr(self.app, "bottom_bar") and self.app.bottom_bar:
            self.app.bottom_bar.show(animation=False)

    def _download_wallpaper(self, *args):
        if not self.wallpaper_data:
            return

        self.download_btn_text.text = "Downloading..."
        self.download_btn.disabled = True

        def do_download():
            try:
                image_url = self.wallpaper_data["image_url"]
                wallpapers_dir = Path(appFolder()) / "wallpapers"
                wallpapers_dir.mkdir(parents=True, exist_ok=True)

                safe_name = self.wallpaper_data["name"].replace(" ", "_").lower()
                filename = self.wallpaper_data["id"] + "_" + safe_name + ".jpg"
                dest_path = wallpapers_dir / filename

                if dest_path.exists():
                    Clock.schedule_once(lambda dt: self._on_download_done(str(dest_path)), 0)
                    return

                urllib.request.urlretrieve(image_url, str(dest_path))

                current_time = time.time()
                os.utime(str(dest_path), (current_time, current_time))

                my_config.add_wallpaper(str(dest_path))

                Clock.schedule_once(lambda dt: self._on_download_done(str(dest_path)), 0)

            except Exception as e:
                app_logger.exception("Error downloading wallpaper: %s", e)
                Clock.schedule_once(lambda dt: self._on_download_error(str(e)), 0)

        threading.Thread(target=do_download, daemon=True).start()

    def _on_download_done(self, path):
        self.downloaded_ids.add(self.wallpaper_data["id"])
        self.download_btn_text.text = "Downloaded"
        self.download_btn.md_bg_color = [.3, .3, .3, 1]
        toast("Wallpaper downloaded!")

        if self.app.sm and hasattr(self.app.sm, "gallery_screen"):
            self.app.sm.gallery_screen.initialize_tabs(no_clock=True)

    def _on_download_error(self, error_msg):
        self.download_btn_text.text = "Download Failed"
        self.download_btn.disabled = False
        self.download_btn.md_bg_color = get_color_from_hex("#98F1DD")
        toast("Download failed: " + error_msg)


class CategoryButton(MDButton):
    category_name = StringProperty()
    is_selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_bg_color = "Custom"
        self.theme_height = "Custom"
        self.theme_width = "Custom"
        self.height = dp(36)
        self.width = dp(70)

        self.text_widget = MDButtonText(
            text=self.category_name,
            pos_hint={"center_x": .5, "center_y": .5},
            theme_text_color="Custom",
            font_name="RobotoMono",
        )
        self.add_widget(self.text_widget)
        self.bind(is_selected=self._update_appearance, category_name=self.text_widget.setter("text"))
        self._update_appearance()

    def _update_appearance(self, *args):
        if self.is_selected:
            self.md_bg_color = get_color_from_hex("#98F1DD")
            self.text_widget.text_color = get_color_from_hex("#262C3A")
        else:
            self.md_bg_color = [.25, .25, .25, 1]
            self.text_widget.text_color = [.85, .85, .85, 1]


class MarketplaceScreen(MyMDScreen):
    current_category = StringProperty("All")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "marketplace"
        self.app = get_app()
        self.categories = []
        self.all_wallpapers = []
        self.filtered_wallpapers = []
        self.category_buttons = []
        self.detail_view = None
        self._grid_container = None
        self._cards = []
        self._build_ui()

    def _build_ui(self):
        self.main_container = Column(
            pos_hint={"top": 1},
            size_hint=[1, 1],
            padding=[10, 10],
            spacing=dp(10),
        )

        header_column = Column(
            adaptive_height=True,
            padding=[dp(20), 0, dp(20), dp(10)],
            spacing=dp(5),
        )

        title = MDLabel(
            text="Marketplace",
            theme_font_name="Custom",
            font_name="RobotoMono",
            theme_text_color="Custom",
            text_color="black" if self.app.device_theme == "light" else "white",
            bold=True,
            theme_font_size="Custom",
            font_size="24sp",
            adaptive_size=True,
        )
        header_column.add_widget(title)

        self.info_label = MDLabel(
            text="0 wallpapers found",
            theme_font_name="Custom",
            font_name="RobotoMono",
            theme_text_color="Custom",
            text_color="black" if self.app.device_theme == "light" else "white",
            italic=True,
            theme_font_size="Custom",
            font_size="14sp",
            adaptive_size=True,
        )
        header_column.add_widget(self.info_label)
        self.main_container.add_widget(header_column)

        self.categories_row = Row(
            adaptive_height=True,
            spacing=dp(10),
            padding=[dp(10), 0, 0, dp(5)],
        )
        self.main_container.add_widget(self.categories_row)

        self.scroll_view = ScrollView(size_hint=(1, 1))
        self._grid_container = Column(
            size_hint_y=None,
            padding=[0, 0, 0, dp(120)],
            spacing=dp(10),
        )
        self._grid_container.bind(minimum_height=self._grid_container.setter("height"))
        self.scroll_view.add_widget(self._grid_container)
        self.main_container.add_widget(self.scroll_view)

        self.add_widget(self.main_container)

        self.detail_view = MarketplaceDetail(gallery_screen=self)
        self._load_data()

    def _load_data(self):
        self.categories = provider.get_categories()
        self.all_wallpapers = provider.get_wallpapers("All")
        self.filtered_wallpapers = self.all_wallpapers

        self._build_category_buttons()
        self._build_wallpaper_grid()

    def _build_category_buttons(self):
        self.categories_row.clear_widgets()
        self.category_buttons = []

        for cat in self.categories:
            btn = CategoryButton(category_name=cat, is_selected=(cat == self.current_category))
            btn.bind(on_release=lambda instance, c=cat: self._on_category_selected(c))
            self.category_buttons.append(btn)
            self.categories_row.add_widget(btn)

    def _on_category_selected(self, category):
        self.current_category = category
        self.filtered_wallpapers = provider.get_wallpapers(category)

        for btn in self.category_buttons:
            btn.is_selected = (btn.category_name == category)

        self._build_wallpaper_grid()

    def _build_wallpaper_grid(self):
        self._grid_container.clear_widgets()
        self._cards = []

        wallpapers = self.filtered_wallpapers
        count = len(wallpapers)
        txt = "wallpaper" if count == 1 else "wallpapers"
        self.info_label.text = str(count) + " " + txt + " found"

        available_width = self.scroll_view.width - dp(20) if self.scroll_view.width > 0 else Window.width - dp(20)
        cols = max(2, int((available_width + spacing) // (min_box_size + spacing)))
        card_width = (available_width - spacing * (cols - 1)) / cols

        for wp in wallpapers:
            card = MarketplaceCard(
                source=wp["thumbnail_url"],
                wp_name=wp["name"],
                author=wp["author"],
                size_hint=(None, None),
                size=(card_width, card_width + dp(40)),
            )
            card.bind(on_release=lambda instance, data=wp: self._open_detail(data))
            self._cards.append(card)

        row_layout = None
        for i, card in enumerate(self._cards):
            if i % cols == 0:
                row_layout = Column(
                    adaptive_height=True,
                    spacing=spacing,
                )
                self._grid_container.add_widget(row_layout)

            if row_layout:
                row_layout.add_widget(card)

    def _open_detail(self, wallpaper_data):
        self.detail_view.show(wallpaper_data)
        if hasattr(self.app, "bottom_bar") and self.app.bottom_bar:
            self.app.bottom_bar.hide(animation=False)

    def on_size(self, _, size):
        if self._cards:
            Clock.schedule_once(lambda dt: self._build_wallpaper_grid(), 0.1)

    def set_widget_left_and_right_padding(self, left_padding, right_padding, rotation):
        self.main_container.padding = [dp(10), dp(10), dp(10), dp(10)]
