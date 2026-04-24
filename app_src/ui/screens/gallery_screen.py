import os, time
from datetime import datetime
from pathlib import Path

from kivymd.uix.floatlayout import MDFloatLayout

from android_notify.config import on_android_platform
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
from kivymd.uix.button import MDIconButton, MDFabButton
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.relativelayout import MDRelativeLayout

from plyer import filechooser

from utils.logger import app_logger
from ui.widgets.layouts import MyMDScreen, Column, Row, get_nav_bar_height, get_status_bar_height  # used in .kv file
from utils.config_manager import ConfigManager
from utils.helper import appFolder, load_kv_file  # type
from utils.image_operations import get_or_create_thumbnail
from utils.logger import app_logger
from utils.model import get_app, GalleryTabs

my_config = ConfigManager()
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


def get_cols_with_math(available_width):
    return max(1, int(
        (available_width + spacing) // (min_box_size + spacing)
    ))

    # resize_grid


def get_number_of_cols():
    app = MDApp.get_running_app()
    # my_config = ConfigManager()
    cols = my_config.get_cols()

    print("get_number_of_cols", type(cols), cols)
    return cols


class PreviewImage(ButtonBehavior, AsyncImage):
    high_resolution_path = StringProperty()
    # theme_cls = StringProperty()

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
    cols = NumericProperty(0)
    doing_cols_change = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.md_bg_color=[1,0,0,1]
        self.title_text_widget = None
        self.rect = None
        self.spacing = dp(10)
        self.padding = [dp(10), 0, dp(20), dp(1)]

        self.toggle_drop_btn = None
        self.adaptive_height = 1
        self.size_hint_x = 1

        Clock.schedule_once(self.build_grid)
        self.image_elements = []

        self.bind(cols=self.change_preview_img_size)

        # self.md_bg_color=[.1,1,.3,1]

    def build_grid(self, *args):
        header_layout = MDRelativeLayout(
            adaptive_height=1,
            size_hint_x=1,
        )
        header_content_color = (.65, .65, .65, 1)
        # header_content_color = (.8, .8, 1, 1)

        self.title_text_widget = MDLabel(
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

        self.toggle_drop_btn.bind(on_release=self.toggle_dropdown)

        header_layout.add_widget(self.title_text_widget)
        header_layout.add_widget(self.toggle_drop_btn)
        self.add_widget(header_layout)

        self.images_container = MyMDGridLayout(
            # md_bg_color=[0,1,0,1],
            adaptive_width = True
        )

        self.images_container.size_hint_y = None
        self.images_container.bind(minimum_height=self.images_container.setter("height"))

        window_width_minus_padding = self.width - 50

        self.images_container.spacing = spacing
        available_width = window_width_minus_padding - spacing

        self.cols = my_config.get_cols() or get_cols_with_math(available_width)

        total_spacing = spacing * (self.cols - 1)
        box_size = (available_width - total_spacing) / self.cols

        self.images_container.cols = self.cols
        for each_data in self.batch:
            if isinstance(each_data, dict):
                thumbnailWidget = PreviewImage(
                    on_release=each_data["release_function"],
                    high_resolution_path=each_data["high_resolution_path"],
                    source=each_data["thumbnail_path"],
                )
            elif isinstance(each_data, PreviewImage):
                thumbnailWidget = each_data
                app_logger.debug(f"Found: {each_data}")
            else:
                app_logger.error(f"Error getting PreviewImage Class or Init Data, got: {each_data}")
                return None
            thumbnailWidget.size_hint = (None, None)
            thumbnailWidget.size = (box_size, box_size)
            self.images_container.add_widget(thumbnailWidget)

        self.add_widget(self.images_container)
        line = MDBoxLayout(size_hint=[1, None], height=dp(0.5), md_bg_color=[.3, .3, .3, .8])

        self.add_widget(line)
        return None

    def on_size(self,_,size):
        if self.cols == 1:
            if not self.images_container:
                return None
            window_width_minus_padding = self.width - 50
            available_width = window_width_minus_padding - spacing
            self.cols = cols = get_cols_with_math(available_width)
            self.images_container.cols = cols
            total_spacing = spacing * (cols - 1)
            thumb_size = (available_width - total_spacing) / cols
            for each_child in self.walk():
                if isinstance(each_child, PreviewImage):
                    each_child.size=(thumb_size, thumb_size)
        else:
            self.change_preview_img_size(None,self.cols)

        return None

    def remove_wallpaper_from_badge_display(self, image_absolute_path):
        images_container_widget = self.images_container
        image_widget=None
        for each_image_widget in list(images_container_widget.children):
            if not isinstance(each_image_widget, PreviewImage):
                app_logger.error(f"Error Getting only PreviewImage Class, got: {each_image_widget}")
                continue

            if image_absolute_path == each_image_widget.high_resolution_path:
                images_container_widget.remove_widget(each_image_widget)
                image_widget = each_image_widget
                break
        new_children = images_container_widget.children
        if not new_children:
            if self.parent:
                # app_logger.debug("remove from parent called....")
                self.parent.remove_widget(self)
            else:
                # app_logger.debug("No parent....")
                pass
        else:
            self.__update_title(len(new_children))
        return image_widget

    def add_wallpaper_to_badge_display(self, image_widget):
        images_container_widget = self.images_container
        children = images_container_widget.children

        if not isinstance(image_widget, PreviewImage):
            app_logger.error(f"Error Getting only PreviewImage Class, got: {image_widget}")
            return
        images_container_widget.add_widget(image_widget,index=len(children))
        self.__update_title(len(children))

    def __update_title(self,count:int):
        batch_title = self.title.split("|")[0].strip()
        self.title_text_widget.text = f"{batch_title}  |  {count} item{'s' if count != 1 else ''}"

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

    def change_preview_img_size(self,widget,number_of_cols):
        if not self.cols:
            return None

        self.doing_cols_change = True
        self.images_container.cols = number_of_cols
        self.cols = number_of_cols

        window_width_minus_padding = self.width - 50
        available_width = window_width_minus_padding - spacing
        total_spacing = spacing * (self.cols - 1)
        thumb_size = (available_width - total_spacing) / number_of_cols
        # thumb_size = (window_width_minus_padding + spacing + (number_of_cols * spacing))/number_of_cols
        for each_child in self.images_container.children:
            each_child.size = (thumb_size, thumb_size)
        return None
        # self.doing_cols_change=False


class GalleryScreen(MyMDScreen):
    current_tab = StringProperty(GalleryTabs.BOTH.value)
    wallpapers = ListProperty([])
    showing_action_btns=BooleanProperty(False)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        # self.app.device_theme = "light"
        self.app.device_theme = "dark"
        self.name = "thumbs"
        self.app_dir = Path(appFolder())
        self.wallpapers_dir = self.app_dir / "wallpapers"

        self.tab_instances = {}
        # print("hot reload stuff in gallery screen")
        # from ui.widgets.buttons import BottomNavigationBar
        #
        # self.bottom_bar = BottomNavigationBar(
        #     on_camera=None,
        #     on_settings=None,
        #     width=dp(120),
        #     height=dp(500),
        # )
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
        self.initialize_tabs(no_clock=True)
        # self.btm_sheet = MyBtmSheet()
        # self.add_widget(self.btm_sheet)
        # self.load_saved()

    def initialize_tabs(self, no_clock=False, has_files=True):
        if hasattr(self.app, "bottom_bar") and self.app.bottom_bar:
            self.app.bottom_bar.show(animation=False)
        if not has_files:
            return

        def run_widgets_creation( *args):
            self.generate_tab_widgets(tab_name=GalleryTabs.BOTH.value, wallpapers=self._filter_existing_paths(my_config.get_wallpapers()))
            self.generate_tab_widgets(tab_name=GalleryTabs.DAY.value, wallpapers=self._filter_existing_paths(my_config.get_day_wallpapers()))
            self.generate_tab_widgets(tab_name=GalleryTabs.NOON.value, wallpapers=self._filter_existing_paths(my_config.get_noon_wallpapers()))
            self.current_tab = GalleryTabs.BOTH.value
            self.on_current_tab(None, self.current_tab)

        if no_clock:  # using clock in init breaks DateGroupLayout height
            run_widgets_creation()
        else:
            Clock.schedule_once(run_widgets_creation)

    def open_file_chooser(self, *_):
        self.close_choice_popup()
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
        self.app.file_operation.show_spinner()
        self.app.bottom_bar.hide(animation=False)


        def show_chooser(dt=None):
            filechooser.open_file(
                on_selection=self.app.file_operation.copy_add,
                filters=["image"],
                multiple=True
            )
        if on_android_platform():
            Clock.schedule_once(show_chooser)
        else:
            import threading
            threading.Thread(target=show_chooser).start()
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

            thumb = get_or_create_thumbnail(each_image_path, destination_dir=self.wallpapers_dir)

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
            # print("self.wallpapers", self.wallpapers)
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

        # wallpapers = my_config.get_day_wallpapers()
        # self.wallpapers = self._filter_existing_paths(wallpapers)
        # self.update_thumbnails_method()

    def load_noon_wallpapers(self):
        self.current_tab = GalleryTabs.NOON.value

        # wallpapers = my_config.get_noon_wallpapers()
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
        # wallpapers = my_config.get_wallpapers()
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
        #     wallpapers = self._filter_existing_paths(my_config.get_day_wallpapers())
        # elif self.current_tab == "Noon":
        #     wallpapers = self._filter_existing_paths(my_config.get_noon_wallpapers())
        # else:
        #     wallpapers = self._filter_existing_paths(my_config.get_wallpapers())
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
                self.wallpapers = a_tab_data["wallpapers"]

        a_batch_in_a_tab = a_tab_data.get(batch_title)
        widget = None
        if isinstance(a_batch_in_a_tab, DateGroupLayout):
            widget = a_batch_in_a_tab.remove_wallpaper_from_badge_display(wallpaper_path)

            if not a_batch_in_a_tab.images_container.children:
                # app_logger.info(f"Deleted empty DateGroupLayout from: {available_tab_key}")
                del a_tab_data[batch_title]

        return widget

    def add_wallpaper_to_thumbnails(self, image_widget, tab=None):
        if not image_widget or not isinstance(image_widget, PreviewImage):
            app_logger.error(f"Didn't get PreviewImage Widget: {image_widget}")
            return None

        wallpaper_path = image_widget.high_resolution_path
        try:
            current_time = time.time()
            os.utime(wallpaper_path, (current_time, current_time))
        except Exception as error_changing_timestamp:
            app_logger.error(f"Error Changing Time Stamp For - {wallpaper_path}, Error: {error_changing_timestamp}")

        available_tab_key = tab or self.current_tab
        a_tab_data = self.tab_instances.get(available_tab_key)
        # 'Day': {'title': '0 images found', 'wallpapers': [], 'widget': <ui.widgets.layouts.Column object at 0x702cdde25da0>, "Today": <ui.screens.gallery_screen.DateGroupLayout object at 0x702cddff39a0>},"Noon": ...

        if not a_tab_data or not isinstance(a_tab_data, dict):
            app_logger.error(f"Error getting tab Dict to add item to thumbnails: {a_tab_data}")
            return None

        batch_title = "Today"
        date_batch_layout = a_tab_data.get(batch_title)

        if isinstance(date_batch_layout, DateGroupLayout):
            date_batch_layout.add_wallpaper_to_badge_display(image_widget)
        else:
            app_logger.debug(f"Creating DateGroupLayout for batch doesn't exist: {date_batch_layout}")
            date_batch_layout = DateGroupLayout(
                batch=[image_widget],
                title=f"{batch_title}  |  1 item"
            )
            a_tab_data[batch_title] = date_batch_layout
            a_tab_data["widget"].add_widget(date_batch_layout, index=len(a_tab_data["widget"].children))


        if wallpaper_path in a_tab_data["wallpapers"]:
            app_logger.error(f"Broken feature wallpaper_path in a_tab_data['wallpapers']")
        a_tab_data["wallpapers"].insert(0, wallpaper_path)
        if available_tab_key == self.current_tab:
            self.wallpapers = a_tab_data["wallpapers"]

        return None

    def on_wallpapers(self, widget, value):
        size = len(value)
        txt = "image" if size == 1 else "images"
        self.ids.header_info_label.text = f"{size} {txt} found"

    def set_widget_left_and_right_padding(self,left_padding, right_padding,rotation):

        root_container = self.ids.main_container
        if not isinstance(root_container, MDBoxLayout):
            app_logger.error(f"Didn't get Right widget MDBoxLayout got: {root_container}")
            return
        if rotation in ["LEFT", 'RIGHT', "landscape"]:
            root_container.padding=[left_padding+10, left_padding+10, right_padding+10, 10]
            root_container.orientation="horizontal"
            self.ids.tab_buttons_box.orientation="vertical"
            self.ids.head_section.adaptive_width=1
            self.ids.head_section.size_hint_x=None
            self.ids.head_section.width=self.ids.head_section.minimum_width
            self.ids.head_section.padding= [dp(0), 0, dp(10), dp(0)]

        else:
            root_container.padding=[left_padding+10, 10, right_padding+10, 10]
            root_container.orientation="vertical"
            self.ids.tab_buttons_box.orientation="horizontal"
            self.ids.head_section.size_hint_x=1
            self.ids.head_section.padding= [dp(0), dp(self.status_bar_height), dp(10), dp(0)]

    def toggle_choice_popup(self,button_instance,fab_button_layout,add_with_phone_gallery_btn,add_with_phone_camera_btn):
        fab_button_layout.btns = [button_instance,add_with_phone_gallery_btn,add_with_phone_camera_btn]

        if self.showing_action_btns:
            self.close_choice_popup()
        else:
            self.open_choice_popup()

    def open_choice_popup(self):
        fab_button_layout = self.ids.fab_btn_widget
        button_instance = self.ids.fab_button
        self.ids.fab_btn_widget.md_bg_color = [.2, .2, .2, .4]

        y=button_instance.pos[1]
        height=button_instance.height
        self.ids.actions_container_widget.y = height+y + 10
        self.ids.actions_container_widget.opacity = 1
        button_instance.icon = "close"
        fab_button_layout.showing = True
        self.showing_action_btns= True
        if hasattr(self.app, "bottom_bar"):
            self.app.bottom_bar.hide(animation=False)
        else:
            app_logger.warning("No bottom nav bar to hide, You're on Hot Reload ")

    def close_choice_popup(self):
        fab_button_layout=self.ids.fab_btn_widget
        button_instance=self.ids.fab_button
        self.ids.fab_btn_widget.md_bg_color = [0, 0, 0, 0]
        self.ids.actions_container_widget.y=-100
        self.ids.actions_container_widget.opacity = 0
        button_instance.icon = "plus"
        fab_button_layout.showing = False
        self.showing_action_btns= False
        if hasattr(self.app, "bottom_bar"):
            self.app.bottom_bar.show(animation=False)
        else:
            app_logger.warning("No bottom nav bar to show, You're on Hot Reload ")

    def open_camera(self,*_):
        Clock.schedule_once(lambda *_:setattr(self.manager, "current", "camera"))
        self.manager.current="camera"
        self.manager.current_screen.start_camera()
        # self.app.sm.current_screen._start_camera()

    def change_amount_of_columns(self,chosen_cols):
        for each_tab,data in self.tab_instances.items():
            tab_container = data["widget"]

            for each in tab_container.walk():
                if isinstance(each, DateGroupLayout):
                    each.change_preview_img_size(None, chosen_cols)
class FabButtonLayout(MDFloatLayout):
    btns=ListProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.showing=False
        Clock.schedule_once(lambda dt:self.adjust_children(),1)
        Clock.schedule_once(lambda dt:self.adjust_children(),4)

    def on_touch_up(self, touch):
        widget_on_floating_screen = False
        for each_btn in self.btns:
            widget_on_floating_screen = each_btn.collide_point(*touch.pos)
            if widget_on_floating_screen:
                break

        if self.showing and not widget_on_floating_screen:
            return True
        return super(FabButtonLayout, self).on_touch_up(touch)

    def on_touch_down(self, touch):
        widget_on_floating_screen = False
        for each_btn in self.btns:
            widget_on_floating_screen = each_btn.collide_point(*touch.pos)
            if widget_on_floating_screen:
                break
        if self.showing and not widget_on_floating_screen:
            return True

        # if self.collide_point(*touch.pos):
        #     print("Widget clicked!")
        #     # Returning True consumes the touch and stops propagation
        #     return True
        return super(FabButtonLayout, self).on_touch_down(touch)

    def adjust_children(self):
        floating_button = None
        other_btns_case = None
        for each_widget in self.children:
            if isinstance(each_widget, MDFabButton):
                floating_button = each_widget
            if isinstance(each_widget,Column):
                other_btns_case = each_widget
        if not other_btns_case or not floating_button:
            app_logger.error(f"Didn't find any children for other_btns_case:{other_btns_case}, floating_button:{floating_button}")
            return
        y=floating_button.pos[1]
        height=floating_button.height
        other_btns_case.y = height+y + 20


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
