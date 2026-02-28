import os, time
from datetime import datetime
from pathlib import Path

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.tabbedpanel import TabbedPanel

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.relativelayout import MDRelativeLayout

from plyer import filechooser

from utils.logger import app_logger
from ui.widgets.layouts import MyMDScreen, Column  # used in .kv file
from ui.widgets.buttons import BottomButtonBar
from utils.config_manager import ConfigManager
from utils.helper import appFolder, load_kv_file  # type
from utils.image_operations import get_or_create_thumbnail
from utils.model import get_app, GalleryTabs

load_kv_file(py_file_absolute_path=__file__)


min_box_size = dp(80)
spacing = dp(2)


def format_file_date(path):
    if not os.path.exists(path):
        app_logger.warning(f"File does not exist to get date format: {path}")
        return None

    timestamp = os.stat(path).st_mtime
    file_date = datetime.fromtimestamp(timestamp).date()
    today = datetime.now().date()

    delta_days = (today - file_date).days

    if delta_days == 0:
        return "Today"
    elif delta_days == 1:
        return "Yesterday"
    elif 2 <= delta_days <= 7:
        return f"{delta_days} days ago"
    else:
        return file_date.strftime("%d %b")


class Thumb(ButtonBehavior, AsyncImage):
    high_resolution_path = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fit_mode = "cover"
        self.mipmap = True
    # def remove_from_thumbnails_display(self):
    #     self.parent.remove_widget(self)


class MyMDGridLayout(MDGridLayout):
    icon_active = StringProperty()
    icon_inactive_color = StringProperty()
    minimum_height = NumericProperty()
    switch_opacity_value_disabled_icon = NumericProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None


class ScrollViewMainColumn(Column):
    pass
    # wallpapers_on_display = ListProperty()


class DateGroupLayout(Column):
    batch = ListProperty()
    title = StringProperty("None")
    # scroll_view_main_column = ObjectProperty()
    is_collapsed = BooleanProperty(False)

    images_container = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rect = None
        self.spacing = dp(10)
        self.padding = [dp(10), 0, dp(20), dp(1)]

        self.toggle_drop_btn = None
        self.adaptive_height = 1
        self.size_hint_x = 1

        Clock.schedule_once(self.build_grid)
        self.image_elements = []

        # self.md_bg_color=[.1,1,.3,1]

    #
    # def fix_images_width(self, width):
    #     width = width - 20
    #     if not self.images_container:
    #         print('none')
    #         return None
    #     print('not none')
    #     available_width = width - spacing
    #
    #     cols = max(1, int(
    #         (available_width + spacing) // (min_box_size + spacing)
    #     ))
    #
    #     total_spacing = spacing * (cols - 1)
    #     box_size = (available_width - total_spacing) / cols
    #
    #     self.images_container.cols = cols
    #     # self.images_container.width=width
    #     for each_image in self.image_elements:
    #         each_image.size = (box_size,box_size)
    #     return None

    # def on_width(self, instance, value):
    #     # self.fix_images_width(value)
    #     print("parent on_width",value)
    def build_grid(self, *args):
        # print("build_grid")
        # return
        header_layout = MDRelativeLayout(
            adaptive_height=1,
            size_hint_x=1,
        )
        header_content_color = (.65, .65, .65, 1)
        # header_content_color = (.8, .8, 1, 1)

        txt = MDLabel(
            text=self.title,
            adaptive_size=True,
            theme_text_color="Custom",
            theme_font_size="Custom",
            font_size=sp(14),
            text_color=header_content_color,
            pos_hint={"center_y": .5}
        )

        self.toggle_drop_btn = MDIconButton(
            icon="triangle",
            theme_icon_color="Custom",
            icon_color=header_content_color,
            theme_font_size="Custom",
            font_size="14sp",
            pos_hint={"center_y": .5, "right": 1}
        )
        # self.toggle_drop_btn.theme_width="Custom"
        # self.toggle_drop_btn.theme_height="Custom"
        # self.toggle_drop_btn.width=20
        # self.toggle_drop_btn.height=20

        self.toggle_drop_btn.bind(on_release=self.toggle_dropdown)

        header_layout.add_widget(txt)
        header_layout.add_widget(self.toggle_drop_btn)
        self.add_widget(header_layout)

        self.images_container = MyMDGridLayout()
        # self.images_container.md_bg_color= [1,0,0,1]

        # self.images_container.size_hint_y = None
        self.images_container.size_hint = [None, None]
        # self.images_container.width = self.width
        # self.images_container.width = Window.width - 30#self.width
        self.images_container.bind(minimum_height=self.images_container.setter("height"))

        window_width_minus_padding = Window.width - 50
        self.images_container.width = dp(window_width_minus_padding)
        # print(f"self.images_container.width: {self.images_container.width} == window_width_minus_padding: {window_width_minus_padding},self.width: {self.width}")
        # if self.images_container.width != window_width_minus_padding:
        #     app_logger.warning(
        #         f"Images sizing Improper: self.width ==  Window.width - 20, {self.images_container.width - 40} == {window_width_minus_padding}, Ignore if images are sized properly, if self.width very smaller than Window.width also ignore"
        #     )

        self.images_container.spacing = spacing
        available_width = window_width_minus_padding - spacing
        # available_width = self.images_container.width - spacing

        cols = max(1, int(
            (available_width + spacing) // (min_box_size + spacing)
        ))

        total_spacing = spacing * (cols - 1)
        box_size = (available_width - total_spacing) / cols

        self.images_container.cols = cols

        for each_data in self.batch:
            if isinstance(each_data, dict):
                thumbnailWidget = Thumb(
                    on_release=each_data["release_function"],
                    high_resolution_path=each_data["high_resolution_path"],
                    source=each_data["thumbnail_path"],
                    # id=each_data["thumbnail_path"],
                )
            elif isinstance(each_data, Thumb):
                thumbnailWidget = each_data
                app_logger.debug(f"Found: {each_data}")
            else:
                app_logger.error(f"Error getting Thumb Class or Init Data, got: {each_data}")
                return None
            thumbnailWidget.size_hint = (None, None)
            thumbnailWidget.size = (box_size, box_size)
            # self.image_elements.append(thumbnailWidget)
            # self.scroll_view_main_column.wallpapers_on_display.append(thumbnailWidget)
            self.images_container.add_widget(thumbnailWidget)

        self.add_widget(self.images_container)
        line = MDBoxLayout(size_hint=[1, None], height=dp(0.5), md_bg_color=[.3, .3, .3, .8])

        self.add_widget(line)
        return None

    def remove_wallpaper_from_badge_display(self, image_absolute_path):
        images_container_widget = self.images_container
        image_widget=None
        for each_image_widget in list(images_container_widget.children):
            if not isinstance(each_image_widget, Thumb):
                app_logger.error(f"Error Getting only Thumb Class, got: {each_image_widget}")
                continue

            if image_absolute_path == each_image_widget.high_resolution_path:
                images_container_widget.remove_widget(each_image_widget)
                image_widget = each_image_widget
                break

        if not images_container_widget.children:
            print("remove from parent called")
            if self.parent:
                self.parent.remove_widget(self)
        else:
            count = len(images_container_widget.children)
            batch_title = self.title.split("|")[0].strip()
            self.title = f"{batch_title}  |  {count} item{'s' if count != 1 else ''}"

        return image_widget

    def add_wallpaper_to_badge_display(self, image_widget):
        images_container_widget = self.images_container
        print('parent',self.parent)
        if not isinstance(image_widget, Thumb):
            app_logger.error(f"Error Getting only Thumb Class, got: {image_widget}")
            return
        images_container_widget.add_widget(image_widget,index=0)

    def toggle_dropdown(self, *args):
        if self.is_collapsed:
            self.images_container.height = self.images_container.minimum_height
            self.images_container.opacity = 1
            self.images_container.disabled = False
            self.toggle_drop_btn.icon = "triangle"
            self.is_collapsed = False
        else:
            self.images_container.height = 0
            self.images_container.opacity = 0
            self.images_container.disabled = True
            self.toggle_drop_btn.icon = "triangle-down"
            self.is_collapsed = True


class GalleryScreen(MyMDScreen):
    current_tab = StringProperty(GalleryTabs.BOTH.value)
    wallpapers = ListProperty([])

    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        self.app = get_app()
        # self.app.device_theme = "light"
        self.app.device_theme = "dark"
        self.name = "thumbs"
        self.app_dir = Path(appFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"

        self.tab_instances = {}
        # print("hot reload stuff in gallery screen")
        # # self.bottom_bar = BottomButtonBar(
        # #     on_camera=None,
        # #     on_settings=None,
        # #     width=dp(120),
        # #     height=dp(500),
        # # )
        # self.bottom_bar = Button(
        #     on_release=self.dev1,
        #     text="triangle",
        #     size_hint=[None, None],
        #     size=[100,100],
        #     # theme_font_size="Custom",
        #     # font_size="14sp",
        #     pos_hint={"center_x": .5,"center_y": .5}
        # )
        #
        # self.add_widget(self.bottom_bar)
        self.initialize_tabs()
        # self.load_saved()

    def initialize_tabs(self):
        self.generate_tab_widgets(tab_name=GalleryTabs.BOTH.value, wallpapers=self._filter_existing_paths(self.myconfig.get_wallpapers()))
        self.generate_tab_widgets(tab_name=GalleryTabs.DAY.value, wallpapers=self._filter_existing_paths(self.myconfig.get_day_wallpapers()))
        self.generate_tab_widgets(tab_name=GalleryTabs.NOON.value, wallpapers=self._filter_existing_paths(self.myconfig.get_noon_wallpapers()))
        self.current_tab = GalleryTabs.BOTH.value
        self.on_current_tab(None, self.current_tab)

    def open_file_chooser(self, *_):
        # file_operation = FileOperation(self.update_thumbnails_method)
        # if platform == 'android':
        #     from android import activity # type: ignore
        #     def test(activity_id,some_int,intent):
        #         try:
        #             print('must be before chooser callback')
        #             print('see intent', intent,bool(intent))
        #             if intent:
        #                 file_operation.intent = intent
        #                 # try:
        #                 #     print("intent data", intent.getData()) # crashes app when no files are picked
        #                 #     print("intent data str", intent.getData().toString())
        #                 # except Exception as weird_thing:
        #                 #     print("weird_thing",weird_thing)
        #         except Exception as error_getting_path:
        #             print("error_getting_path",error_getting_path)
        #
        #     activity.bind(on_activity_result=test) # handling image with no permission
        filechooser.open_file(
            on_selection=self.app.file_operation.copy_add,
            filters=["image"],
            multiple=True
        )

        # ----------------- This Also Works Keeping for Reference ---------------------------
        # from jnius import autoclass, cast
        # from android import activity
        # def test(activity_id,some_int,data):
        #     print("args", data)
        # activity.bind(on_activity_result=test)

        # def open_file_picker():
        #     PythonActivity = autoclass('org.kivy.android.PythonActivity')
        #     Intent = autoclass('android.content.Intent')# autoclass('android.intent.action.OPEN_DOCUMENT')  # Use OPEN_DOCUMENT for permanent files
        #     intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
        #     intent.addCategory(Intent.CATEGORY_OPENABLE)
        #     intent.setType("image/*")  # Only show images
        #
        #     # Start the activity and wait for a result
        #     # Note: You'll need to handle the result in your App class via bind
        #     PythonActivity.mActivity.startActivityForResult(intent, 1001)
        # try:
        #     open_file_picker()
        # except Exception as error_testing_picker:
        #     print("error_testing_picker", error_testing_picker)

    def generate_tab_widgets(self, tab_name, wallpapers, dt=None):
        self.wallpapers = wallpapers
        tab_title = f"{len(self.wallpapers)} images found"

        self.wallpapers = sorted(
            self.wallpapers,
            key=lambda image_path: os.stat(image_path).st_mtime,
            reverse=True  # newest first
        )

        data_of_batch_dict_of_lists = {}

        # group batches and use index's from self.wallpaper to appoint indexes from fullscreen widget
        for index, each_image_path in enumerate(self.wallpapers):
            if not each_image_path or not os.path.exists(each_image_path):
                continue
            date_label = format_file_date(each_image_path)

            if date_label not in data_of_batch_dict_of_lists:
                data_of_batch_dict_of_lists[date_label] = []

            thumb = get_or_create_thumbnail(each_image_path, dest_dir=self.wallpapers_dir)

            data_of_batch_dict_of_lists[date_label].append({
                "thumbnail_path": str(thumb) if thumb else str(each_image_path),
                "high_resolution_path": each_image_path,
                "release_function": lambda instance, p=each_image_path, idx=index: self.open_fullscreen_for_image(p, idx)
            })


        tab_container = Column(size_hint=[1,None])
        tab_container.bind(minimum_height=tab_container.setter("height"))
        self.tab_instances[tab_name] = {}
        for batch_title, list_of_sorted_paths_by_date in data_of_batch_dict_of_lists.items():
            group_title = f"{batch_title}  |  {len(list_of_sorted_paths_by_date)} items"
            date_batch_layout = DateGroupLayout(
                    batch=list_of_sorted_paths_by_date,
                    title=group_title,
            )
            self.tab_instances[tab_name][batch_title] = date_batch_layout
            tab_container.add_widget(date_batch_layout)
        # self.ids.wallpapers_container.add_widget(tab_container)
        self.tab_instances[tab_name]["title"] = tab_title
        self.tab_instances[tab_name]["wallpapers"] = self.wallpapers
        self.tab_instances[tab_name]["widget"] = tab_container

    def open_fullscreen_for_image(self, wallpaper_path = None, wallpaper_index = -1):
        try:

            index = self.wallpapers.index(wallpaper_path)
        except Exception as error_getting_index:
            print("self.wallpapers",self.wallpapers)
            for each in self.wallpapers:
                print(each)
            app_logger.error(f"error_getting_index: {error_getting_index}")

            return
        self.manager.open_image_in_full_screen(index)

    def on_current_tab(self,widget, tab_name):
        scrollView_container = self.ids.wallpapers_container
        tab_data = self.tab_instances[tab_name]

        scrollView_container.clear_widgets()

        self.ids.header_info_label.text = tab_data["title"]
        scrollView_container.add_widget(tab_data["widget"])
        self.wallpapers = tab_data["wallpapers"]

    def load_day_wallpapers(self):
        self.current_tab = GalleryTabs.DAY.value

        # wallpapers = self.myconfig.get_day_wallpapers()
        # self.wallpapers = self._filter_existing_paths(wallpapers)
        # self.update_thumbnails_method()

    def load_noon_wallpapers(self):
        self.current_tab = GalleryTabs.NOON.value


        # wallpapers = self.myconfig.get_noon_wallpapers()
        # self.wallpapers = self._filter_existing_paths(wallpapers)
        # self.update_thumbnails_method()

    def load_saved(self):
        self.current_tab = GalleryTabs.BOTH.value
        # ---------------------------------
        # peek = [str(p) for p in self.wallpapers_dir.glob("*") if True]
        # print("Peek:", peek,self.wallpapers_dir)

        # self.wallpapers = [
        #     str(p) for p in self.wallpapers_dir.glob("*")
        #     if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        # ]
        # print("Loaded wallpapers:", len(self.wallpapers))
        # -------------------------------
        # wallpapers = self.myconfig.get_wallpapers()
        # self.wallpapers = self._filter_existing_paths(wallpapers)
        # Clock.schedule_once(self.update_thumbnails_method)

    @staticmethod
    def _filter_existing_paths(paths):
        """Return only paths that actually exist on disk."""
        if not paths:
            return []
        return [p for p in paths if p and os.path.exists(p)]

    def refresh_gallery_screen(self):
        """
        Used when coming from FullScreen to refresh displayed images.
        :return:
        """
        # return
        # if self.current_tab == "Day":
        #     wallpapers = self._filter_existing_paths(self.myconfig.get_day_wallpapers())
        # elif self.current_tab == "Noon":
        #     wallpapers = self._filter_existing_paths(self.myconfig.get_noon_wallpapers())
        # else:
        #     wallpapers = self._filter_existing_paths(self.myconfig.get_wallpapers())
        #
        # scroll_view_main_column = self.ids.wallpapers_container
        # wallpapers_on_display = scroll_view_main_column.wallpapers_on_display
        #
        # print("wallpapers",wallpapers)
        # for each_img in wallpapers_on_display:
        #     print(each_img.high_resolution_path)
        #     if each_img.high_resolution_path not in wallpapers:
        #         print("removed:",each_img.high_resolution_path)
        #         wallpapers_on_display.remove(each_img)
        #         each_img.parent.remove_widget(each_img)
        #         # scroll_view_main_column.remove_widget(each_img)
        #
        # return
        if self.current_tab == GalleryTabs.DAY.value:
            self.load_day_wallpapers()
        elif self.current_tab == GalleryTabs.NOON.value:
            self.load_noon_wallpapers()
        else:
            self.load_saved()

    def remove_wallpaper_from_thumbnails(self, wallpaper_path, tab=None):
        available_tab_key = tab or self.current_tab
        batch_title = format_file_date(wallpaper_path)
        a_tab_data = self.tab_instances.get(available_tab_key)

        if not a_tab_data or not isinstance(a_tab_data, dict):
            app_logger.error(f"Error getting tab Dict to remove item from thumbnails: {a_tab_data}")
            return None

        # Properly remove from the tab's wallpaper list
        if wallpaper_path in a_tab_data["wallpapers"]:
            a_tab_data["wallpapers"].remove(wallpaper_path)
            if available_tab_key == self.current_tab:
                # Refresh UI element bound to self.wallpapers
                self.on_wallpapers(self, self.wallpapers)

        a_batch_in_a_tab = a_tab_data.get(batch_title)
        widget = None
        if isinstance(a_batch_in_a_tab, DateGroupLayout):
            widget = a_batch_in_a_tab.remove_wallpaper_from_badge_display(wallpaper_path)

            if not a_batch_in_a_tab.images_container.children:
                app_logger.info(f"Deleted empty DateGroupLayout from: {available_tab_key}")
                del a_tab_data[batch_title]

        return widget

    def add_wallpaper_to_thumbnails(self, image_widget, tab=None):
        if not image_widget:
            return None

        wallpaper_path = image_widget.high_resolution_path
        try:
            current_time = time.time()
            os.utime(wallpaper_path, (current_time, current_time))
        except Exception as error_changing_timestamp:
            app_logger.error(f"Error Changing Time Stamp For - {wallpaper_path}, Error: {error_changing_timestamp}")

        available_tab_key = tab or self.current_tab
        a_tab_data = self.tab_instances.get(available_tab_key)

        if not a_tab_data or not isinstance(a_tab_data, dict):
            app_logger.error(f"Error getting tab Dict to add item to thumbnails: {a_tab_data}")
            return None

        batch_title = "Today"
        date_batch_layout = a_tab_data.get(batch_title)

        if isinstance(date_batch_layout, DateGroupLayout):
            date_batch_layout.add_wallpaper_to_badge_display(image_widget)
        else:
            date_batch_layout = DateGroupLayout(
                batch=[image_widget],
                title=f"{batch_title}  |  1 item"
            )
            a_tab_data[batch_title] = date_batch_layout
            a_tab_data["widget"].add_widget(date_batch_layout, index=0)

        if wallpaper_path not in a_tab_data["wallpapers"]:
            a_tab_data["wallpapers"].insert(0, wallpaper_path)
            if available_tab_key == self.current_tab:
                self.on_wallpapers(self, self.wallpapers)

        return None

    def on_wallpapers(self, widget, value):
        size = len(self.wallpapers)
        txt = "image" if size == 1 else "images"
        self.ids.header_info_label.text = f"{size} {txt} found"


if __name__ == "__main__":
    class WallpaperCarouselApp(MDApp):
        interval = 2

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.sm = None

        def build(self):
            self.sm = GalleryScreen()
            # self.sm.load_saved()  # uncomment to load saved images
            return self.sm


    WallpaperCarouselApp().run()
