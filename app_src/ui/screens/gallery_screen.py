import os, time
from datetime import datetime
from pathlib import Path

from android_notify.config import on_android_platform
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.image import AsyncImage
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.tabbedpanel import TabbedPanel

from kivymd.app import MDApp
from kivymd.uix.boxlayout import BoxLayout, MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonIcon, MDButtonText, MDIconButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.widget import MDWidget

from plyer import filechooser

from utils.logger import app_logger
from ui.widgets.layouts import MyMDScreen, Column, Row, get_nav_bar_height, get_status_bar_height, \
    PlaceOnMainScreen, GenericStatusBarSpacer  # used in .kv file
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


class PreviewImage(ButtonBehavior,MDRelativeLayout):
    high_resolution_path = StringProperty()
    selected = BooleanProperty(False)
    selection_mode = BooleanProperty(False)
    source = StringProperty()

    def __init__(self, **kwargs):
        source = kwargs.get("source")
        super().__init__(**kwargs)
        self.md_bg_color=[1,1,0,1]
        self.checkmark_widget = None
        self.image_widget = AsyncImage(
            source=source,
            fit_mode="cover",
            mipmap=True,
            
            # allow_stretch=True,
        )
        self.image_widget.size_hint=(None,None)
        self.add_widget(self.image_widget)
        self.bind(
            selected=self.on_selected, selection_mode=self.on_selection_mode_changed,
            size=self.fix_image_size)
        # self._show_checkmark()
    def on_selected(self, instance, value):
        """Update visual feedback when selected state changes."""
        self._update_selection_display()

    def on_selection_mode_changed(self, instance, value):
        """Update when selection mode is toggled."""
        self._update_selection_display()

    def _update_selection_display(self):
        """Show/hide checkmark based on selection state."""
        if self.selected:
            self._show_checkmark()
            print("Selected1:", self.high_resolution_path)
        else:
            self._hide_checkmark()

    def _show_checkmark(self):
        """Show selection checkmark."""
        if not self.checkmark_widget:
            from kivymd.uix.label import MDIcon
            self.checkmark_widget = MDIcon(
                icon="check-circle",
                theme_icon_color="Custom",
                icon_color=[0.2, 1, 0.2, 1],
                size_hint=(None, None),
                size=(dp(28), dp(28)),
                pos_hint={"right": 1, "top": 1},
            )
            self.add_widget(self.checkmark_widget)

    def _hide_checkmark(self):
        """Hide selection checkmark."""
        if self.checkmark_widget and self.checkmark_widget in self.children:
            self.remove_widget(self.checkmark_widget)
            self.checkmark_widget = None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        if self.selection_mode:
            self.selected = not self.selected
            return True
        return super().on_touch_down(touch)

    def fix_image_size(self, i,v):
        """Ensure the image widget fills the parent layout."""
        if self.image_widget:
            self.image_widget.size = v#[100.5, 100.5]
            print("fix_image_size:", v)

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
        self.turn_on_selection_mode()
    def build_grid(self, *args):
        app_logger.info(f"DGL_BUILD: starting batch_len={len(self.batch)} parent={self.parent}")
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
        app_logger.info(f"DGL_BUILD: done self.children={len(self.children)} parent={self.parent}")
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
        if images_container_widget is None:
            app_logger.info(f"DGL_REMOVE: images_container is None! parent={self.parent} self={self}")
            return None
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
        app_logger.info(f"DGL_REMOVE: found={image_widget is not None} new_children_count={len(new_children)} self.parent={self.parent}")
        if not new_children:
            if self.parent:
                app_logger.info(f"DGL_REMOVE: removing self from parent ({self.parent})")
                self.parent.remove_widget(self)
            else:
                app_logger.info(f"DGL_REMOVE: no parent to remove from")
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

    def turn_on_selection_mode(self):
        """Enable selection mode for all preview images in this group."""
        for child in self.walk():
            if isinstance(child, PreviewImage):
                child.selection_mode = True
                child.bind(selected=self._on_image_selection_changed)
    
    def _on_image_selection_changed(self, instance, value):
        """Called when any preview image's selection state changes."""
        self.parent.parent.update_selection_count()
    
    def get_selected_images(self):
        """Return list of selected PreviewImage widgets in this group."""
        selected = []
        for child in self.walk():
            if isinstance(child, PreviewImage) and child.selected:
                selected.append(child)
        return selected
    
    def clear_selection(self):
        """Deselect all images in this group."""
        for child in self.walk():
            if isinstance(child, PreviewImage):
                child.selected = False
class MultiSelectManager(MDFloatLayout,PlaceOnMainScreen):
    gallery_screen = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.multi_select_top=MultiselectTop(gallery_screen=self.gallery_screen,hide=self.hide)
        self.multi_select_bottom=MultiselectBottom()
        self.add_widget(self.multi_select_top)
        self.add_widget(self.multi_select_bottom)

    def hide(self, *args):
        self.multi_select_top.select_all_ = False
        if self.parent:
            self.parent.remove_widget(self)
class MultiselectTop(MDFloatLayout):
    status_bar_height = NumericProperty(get_status_bar_height())
    gallery_screen = ObjectProperty()  # will be set by GalleryScreen when creating this manager
    hide = ObjectProperty()
    select_all_=BooleanProperty(False)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color=[.1, .1, .1, 1]
        self.size_hint_y = .25
        self.pos_hint={"top":1}
        self.root_layout = Column(adaptive_height=True,pos_hint={"top":1}, padding=[10,0,10,10],spacing=dp(10))
        self.generic_status_bar_spacer = GenericStatusBarSpacer(
            status_bar_height=self.status_bar_height,
            md_bg_color=[.1, .1, .1, 1])
        self.root_layout.add_widget(self.generic_status_bar_spacer)
        
        # use a horizontal box with a flexible spacer to place icons left and right
        btn_box = Row(orientation="horizontal", pos_hint={"top":1}, adaptive_height=True)
        # btn_box.md_bg_color=[1,0,0,1]
        self.cancel_selection_mode_btn = MDIconButton(icon="close", theme_icon_color="Custom", icon_color=[.8, .8, .8, 1])
        self.toggle_select_all_btn = MDIconButton(icon="playlist-check", theme_icon_color="Custom", icon_color=[.8, .8, .8, 1])
        
        self.cancel_selection_mode_btn.bind(on_release=self.hide)
        self.toggle_select_all_btn.bind(on_release=lambda _: setattr(self, "select_all_", not self.select_all_))
        btn_box.add_widget(self.cancel_selection_mode_btn)
        btn_box.add_widget(Widget())
        btn_box.add_widget(self.toggle_select_all_btn)
        self.root_layout.add_widget(btn_box)
        self.title_widget = MDLabel(
            text="0 items selected",
            theme_text_color="Custom",
            text_color=[.8, .8, .8, 1],adaptive_size=True,
            font_size=sp(24),
            theme_font_size="Custom",bold=1,
            theme_font_name="Custom",font_name="RobotoMono"
            )
        self.title_widget.padding=[10,0,0,0]
        self.root_layout.add_widget(self.title_widget)
        self.add_widget(self.root_layout)
        self.bind(select_all_=self.on_select_all_changed)
        # self.gallery_screen = get_app().sm.get_screen("thumbs")
    # def cancel_selection_mode_btn(self, *args):
    def on_select_all_changed(self, _,v):
        if v:
            self.select_all()
        else:
            self.deselect_all()
    
    
    def update_selection_count(self):
        """Update the displayed selection count."""
        if not self.gallery_screen:
            return
        
        count = 0
        for tab_name, tab_data in self.gallery_screen.tab_instances.items():
            for key, value in tab_data.items():
                if isinstance(value, DateGroupLayout):
                    count += len(value.get_selected_images())
        
        txt = "item" if count == 1 else "items"
        self.title_widget.text = f"{count} {txt} selected"
    
    def select_all(self, *args):
        """Select all images in current tab."""
        if not self.gallery_screen:
            return
        
        current_tab = self.gallery_screen.current_tab
        tab_data = self.gallery_screen.tab_instances.get(current_tab)
        
        if tab_data:
            for key, value in tab_data.items():
                if isinstance(value, DateGroupLayout):
                    for child in value.walk():
                        if isinstance(child, PreviewImage):
                            # print("Selecting:", child.high_resolution_path)
                            child.selected = True
        
        self.update_selection_count()
    
    def deselect_all(self, *args):
        """Deselect all images."""
        if not self.gallery_screen:
            return
        
        for tab_name, tab_data in self.gallery_screen.tab_instances.items():
            for key, value in tab_data.items():
                if isinstance(value, DateGroupLayout):
                    value.clear_selection()
        
        self.update_selection_count()

class IconTextButton(MDButton):
    def __init__(self, icon:str, text:str, **kwargs):
        super().__init__(**kwargs)
        # self.theme_bg_color="Custom"
        # self.md_bg_color=[1,0,0,1]
        self.style="text"
        self.text = text
        self.icon = icon
        self.icon_widget = MDButtonIcon(icon=icon, theme_icon_color="Custom", icon_color=[.8, .8, .8, 1])
        self.text_widget = MDButtonText(text=text, theme_text_color="Custom", text_color=[.8, .8, .8, 1])
        self.add_widget(self.icon_widget)
        self.add_widget(self.text_widget)
    
    def adjust_width(self, *args):
        pass
class MultiselectBottom(MDFloatLayout):
    nav_bar_height = NumericProperty(get_nav_bar_height())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        c=.11
        self.md_bg_color=[c, c, c, 1]
        self.adaptive_height=True
        self.pos_hint={"bottom":1}
        self.btn_box = Row(orientation="horizontal", pos_hint={"top":1}, adaptive_height=True)
        # self.btn_box.md_bg_color=[1,0,0,1]
        self.btn_box.padding = 10
        
        delete_btn = IconTextButton(icon="delete", text="Delete")
        share_btn = IconTextButton(icon="share", text="Share")
        info_btn = IconTextButton(icon="information", text="Info")

        self.btn_box.add_widget(Widget())
        self.btn_box.add_widget(delete_btn)
        self.btn_box.add_widget(Widget())
        self.btn_box.add_widget(share_btn)
        self.btn_box.add_widget(Widget())
        self.btn_box.add_widget(info_btn)
        self.btn_box.add_widget(Widget())

        self.add_widget(self.btn_box)
        self.btn_box.bind(minimum_height=self.setter("height"))

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
        multi_select_manager = MultiSelectManager(gallery_screen=self)
        self.add_widget(multi_select_manager)
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
        sorted_wallpapers = sorted(
            wallpapers,
            key=lambda image_path: os.stat(image_path).st_mtime,
            reverse=True  # newest first
        )
        self.wallpapers = sorted_wallpapers
        tab_title = f"{len(sorted_wallpapers)} images found"

        data_of_batch_dict_of_lists = {}
        # group batches and use index's from self.wallpaper to appoint indexes from fullscreen widget
        for index, each_image_path in enumerate(sorted_wallpapers):
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
        self.tab_instances[tab_name]["title"] = tab_title
        self.tab_instances[tab_name]["wallpapers"] = sorted_wallpapers
        self.tab_instances[tab_name]["widget"] = tab_container
        app_logger.info(f"GENERATE_TAB: tab={tab_name} wallpapers={len(sorted_wallpapers)} list_id={id(sorted_wallpapers)} swp_id={id(self.wallpapers)} batches={list(data_of_batch_dict_of_lists.keys())} widget_children={len(tab_container.children)}")

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
        app_logger.info(f"on_tab {tab_name} wp_len={len(self.wallpapers)} wp_list_id={id(tab_data['wallpapers'])} swp_id={id(self.wallpapers)} wallpapers={tab_data['wallpapers']} widget_children={tab_data['widget'].children}")

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
        app_logger.info(f"REMOVE: tab={available_tab_key} path={wallpaper_path} batch_title={batch_title} a_tab_data_keys={list(a_tab_data.keys()) if a_tab_data else None}")

        if not a_tab_data or not isinstance(a_tab_data, dict):
            app_logger.error(f"Error getting tab Dict to remove item from thumbnails: {a_tab_data}")
            return None

        # Properly remove from the tab's wallpaper list
        was_in_wallpapers = wallpaper_path in a_tab_data["wallpapers"]
        if was_in_wallpapers:
            a_tab_data["wallpapers"].remove(wallpaper_path)
            app_logger.info(f"REMOVE: removed from wallpapers list, remaining={len(a_tab_data['wallpapers'])}")
            if available_tab_key == self.current_tab:
                # Refresh UI element bound to self.wallpapers
                self.wallpapers = a_tab_data["wallpapers"]

        a_batch_in_a_tab = a_tab_data.get(batch_title)
        app_logger.info(f"REMOVE: batch={a_batch_in_a_tab} is_DGL={isinstance(a_batch_in_a_tab, DateGroupLayout)}")
        widget = None
        if isinstance(a_batch_in_a_tab, DateGroupLayout):
            widget = a_batch_in_a_tab.remove_wallpaper_from_badge_display(wallpaper_path)
            app_logger.info(f"REMOVE: after remove_wallpaper_from_badge_display widget={widget} images_container_children={len(a_batch_in_a_tab.images_container.children) if a_batch_in_a_tab.images_container else 'NO_CONTAINER'} parent={a_batch_in_a_tab.parent}")

            if not a_batch_in_a_tab.images_container.children:
                app_logger.info(f"REMOVE: DateGroupLayout empty, removing from widget parent and deleting from tab_data")
                del a_tab_data[batch_title]

        app_logger.info(f"REMOVE: returning widget={widget}")
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
        app_logger.info(f"ADD: tab={available_tab_key} path={wallpaper_path} a_tab_data_keys={list(a_tab_data.keys()) if a_tab_data else None} wallpapers_len={len(a_tab_data['wallpapers']) if a_tab_data else None} wp_list_id={id(a_tab_data['wallpapers']) if a_tab_data else None} widget_children={len(a_tab_data['widget'].children) if a_tab_data and a_tab_data.get('widget') else None}")

        if not a_tab_data or not isinstance(a_tab_data, dict):
            app_logger.error(f"Error getting tab Dict to add item to thumbnails: {a_tab_data}")
            return None

        batch_title = "Today"
        date_batch_layout = a_tab_data.get(batch_title)
        app_logger.info(f"ADD: batch_title={batch_title} found_existing={isinstance(date_batch_layout, DateGroupLayout)}")

        if isinstance(date_batch_layout, DateGroupLayout):
            date_batch_layout.add_wallpaper_to_badge_display(image_widget)
            app_logger.info(f"ADD: added to existing DateGroupLayout, children={len(date_batch_layout.images_container.children) if date_batch_layout.images_container else 'NO_CONTAINER'}")
        else:
            app_logger.info(f"ADD: creating new DateGroupLayout")
            date_batch_layout = DateGroupLayout(
                batch=[image_widget],
                title=f"{batch_title}  |  1 item"
            )
            a_tab_data[batch_title] = date_batch_layout
            a_tab_data["widget"].add_widget(date_batch_layout, index=len(a_tab_data["widget"].children))
            app_logger.info(f"ADD: created and added to widget, widget_children_now={len(a_tab_data['widget'].children)}")


        if wallpaper_path in a_tab_data["wallpapers"]:
            app_logger.error(f"Broken feature wallpaper_path in a_tab_data['wallpapers']")
        a_tab_data["wallpapers"].insert(0, wallpaper_path)
        app_logger.info(f"ADD: wallpapers_now={len(a_tab_data['wallpapers'])} widget_children={len(a_tab_data['widget'].children)}")
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

    def change_amount_of_columns(self,chosen_cols):
        for each_tab,data in self.tab_instances.items():
            tab_container = data["widget"]

            for each in tab_container.walk():
                if isinstance(each, DateGroupLayout):
                    each.change_preview_img_size(None, chosen_cols)


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
