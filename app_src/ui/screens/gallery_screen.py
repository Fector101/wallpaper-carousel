import traceback, os
from kivymd.app import MDApp
from pathlib import Path
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from plyer import filechooser

from kivymd.uix.button import MDFabButton

from ui.widgets.buttons import BottomButtonBar
from ui.widgets.layouts import Row, Column, MyMDScreen # used in .kv file

from utils.image_operations import get_or_create_thumbnail
from utils.config_manager import ConfigManager
from utils.helper import appFolder, load_kv_file  # type
from utils.model import get_app

load_kv_file(py_file_absolute_path=__file__)
from kivy.uix.tabbedpanel import TabbedPanel





class MyMDRecycleGridLayout(RecycleGridLayout):
    icon_active = StringProperty()
    icon_inactive_color = StringProperty()
    minimum_height = NumericProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)



class MyTabbedPanel(TabbedPanel):
    tab_height = dp(35)
    tab_width = dp(80)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tab_strip.spacing=20

class Thumb(ButtonBehavior, AsyncImage):
    source_path = StringProperty()


class GalleryScreen(MyMDScreen):
    current_tab = StringProperty("Both")
    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        self.app=get_app()
        # self.app.device_theme = "light"
        self.app.device_theme = "dark"
        self.name = "thumbs"
        self.wallpapers = []
        self.app_dir = Path(appFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"

        # print("hot reload stuff in gallery screen")
        # self.bottom_bar = BottomButtonBar(
        #     on_camera=None,
        #     on_settings=None,
        #     width=dp(120),
        #     height=dp(500)
        #
        # )
        # # w=.3
        # # self.bottom_bar.btn_settings.text_color=[w,w,.4,1]
        # self.add_widget(self.bottom_bar)
        self.load_saved()# for hot_reload

    def open_filechooser(self,*_):
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
        filechooser.open_file(on_selection=self.app.file_operation.copy_add, filters=["image"], multiple=True)


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

    def update_thumbnails_method(self):
        # self.wallpapers = self.wallpapers + new_images
        # for img in new_images:
        #    if img not in self.wallpapers:
        #        self.wallpapers.append(img)

        self.ids.header_info_label.text = f"{len(self.wallpapers)} images found"
        data = []
        self.ids.rv.data = []
        try:
            for  i, path in enumerate(self.wallpapers):
                # Use a low-res thumbnail for the preview (fallback to original if thumbnail creation/availability fails)
                thumb = get_or_create_thumbnail(path, dest_dir=self.wallpapers_dir )
                # print("Thumbnail for", path, "is", thumb)
                data.append({
                    "source": str(thumb) if thumb else str(path),
                    "source_path": path,
                    "on_release": lambda p=path, idx=i: self.open_fullscreen_for_image(p, idx)
                })
            # print("Thumbnail data length:", len(data))

            self.ids.rv.data = data

        except Exception as error_updating_recycle_view:
            print(error_updating_recycle_view)
            traceback.print_exc()

    def open_fullscreen_for_image(self, path, index): # type: ignore
        # print(path, index)
        self.manager.open_image_in_full_screen(index)

    def load_day_wallpapers(self):
        self.current_tab = "Day"
        wallpapers = self.myconfig.get_day_wallpapers()
        self.wallpapers = self._filter_existing_paths(wallpapers)
        self.update_thumbnails_method()

    def load_noon_wallpapers(self):
        self.current_tab = "Noon"
        wallpapers = self.myconfig.get_noon_wallpapers()
        self.wallpapers = self._filter_existing_paths(wallpapers)
        self.update_thumbnails_method()

    def load_saved(self):
        self.current_tab = "Both"
        # peek = [str(p) for p in self.wallpapers_dir.glob("*") if True]
        # print("Peek:", peek,self.wallpapers_dir)

        # self.wallpapers = [
        #     str(p) for p in self.wallpapers_dir.glob("*")
        #     if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        # ]
        # print("Loaded wallpapers:", len(self.wallpapers))
        wallpapers = self.myconfig.get_wallpapers()
        self.wallpapers = self._filter_existing_paths(wallpapers)
        self.update_thumbnails_method()

    @staticmethod
    def _filter_existing_paths(paths):
        """Return only paths that actually exist on disk."""
        if not paths:
            return []

        return [p for p in paths if p and os.path.exists(p)]

    def load_current_tab_wallpapers(self):
        if self.current_tab == "Day":
            self.load_day_wallpapers()
        elif self.current_tab == "Noon":
            self.load_noon_wallpapers()
        else:
            self.load_saved()

if __name__ == "__main__":
    class WallpaperCarouselApp(MDApp):
        interval = 2  # default rotation interval

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.sm = None

        def build(self):
            self.sm = GalleryScreen()
            # self.sm.load_saved()  # uncomment to load saved images
            return self.sm



    WallpaperCarouselApp().run()
