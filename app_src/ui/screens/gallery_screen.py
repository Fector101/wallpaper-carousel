from kivymd.app import MDApp
import traceback
from pathlib import Path
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage
from kivymd.uix.label import MDLabel
from plyer import filechooser

from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFabButton

from ui.widgets.buttons import BottomButtonBar
from ui.widgets.layouts import Row,Column # used in .kv file

from utils.image_operations import get_or_create_thumbnail
from utils.config_manager import ConfigManager
from utils.helper import appFolder, load_kv_file  # type

load_kv_file(py_file_absolute_path=__file__)

class MyMDRecycleGridLayout(RecycleGridLayout):
    icon_active = StringProperty()
    icon_inactive_color = StringProperty()
    minimum_height = NumericProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Thumb(ButtonBehavior, AsyncImage):
    source_path = StringProperty()


class GalleryScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "thumbs"
        self.wallpapers = []
        self.app_dir = Path(appFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / "wallpapers"
        # self.md_bg_color = [0.1, 0.1, 0.1, 1]
        # layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        # self.header_layout = BoxLayout(orientation="vertical", spacing=10, size_hint_y=0.13)
        # self.header_layout.padding = [dp(20), 0, dp(20), dp(10)]
        # app_name_label=MDLabel(
        #     text="Waller",theme_font_name="Custom",font_name="RobotoMono",
        #     theme_text_color="Custom",text_color="white",
        #     bold=True,theme_font_size="Custom",font_size="24sp"
        # )
        # app_name_label.adaptive_size=True
        # # app_name_label.md_bg_color=[1,1,11,1]
        # self.header_info_label=MDLabel(
        #     text="0 images found",theme_font_name="Custom",
        #     font_name="RobotoMono",
        #     theme_text_color="Custom",text_color="white",
        #     italic=True,theme_font_size="Custom",
        #     font_size="14sp",adaptive_size=True
        # )
        # # self.header_info_label.md_bg_color=[1,1,0,1]
        # self.header_layout.add_widget(app_name_label)
        # self.header_layout.add_widget(self.header_info_label)
        # layout.add_widget(self.header_layout)

        # self.rv = RecycleView(size_hint_y=0.8)
        # grid = MyMDRecycleGridLayout(cols=3,
        #                          spacing=5,
        #                          default_size=(None, dp(120)),
        #                          default_size_hint=(1, None),
        #                          size_hint_y=None,
        #                          padding=[0, 0, 0, dp(120)]
        #                              )
        # grid.bind(minimum_height=grid.setter("height"))
        # self.rv.add_widget(grid)
        # self.rv.layout_manager = grid
        # self.rv.viewclass = "Thumb"
        # layout.add_widget(self.rv)
        #
        # add_btn = MDFabButton(
        #     icon="plus",
        #     on_release=self.open_filechooser,
        #     theme_bg_color=  "Custom",
        #     md_bg_color=  [0.9, 0.9, 0, 1] if self.app.device_theme == "light" else [1,1,0,1]
        # )
        #
        # add_btn.pos_hint={"right": .9, "center_y": 0.25}
        # add_btn.theme_font_size = "Custom"
        # add_btn.font_size = sp(30)
        # self.add_widget(layout)
        # self.add_widget(add_btn)



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
        # self.load_saved()# for hot_reload


    @staticmethod
    def open_filechooser(*_):
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
        app=MDApp.get_running_app()
        filechooser.open_file(on_selection=app.file_operation.copy_add, filters=["image"], multiple=True)


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

    def update_thumbnails_method(self,new_images):
        # self.wallpapers = self.wallpapers + new_images
        for img in new_images:
           if img not in self.wallpapers:
               self.wallpapers.append(img)

        self.ids.header_info_label.text = f"{len(self.wallpapers)} images found"
        # self.header_info_label.text = f"{len(self.wallpapers)} images found"
        data = []
        self.ids.rv.data = []
        # self.rv.data = []
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


    # def fetch_recovered_images(self, dt=0):
    #     MediaStoreImages = autoclass('android.provider.MediaStore$Images$Media')
    #     ContentUris = autoclass('android.content.ContentUris')
    #     BuildVersion = autoclass("android.os.Build$VERSION")
    #
    #     context = get_python_activity_context()
    #     resolver = context.getContentResolver()
    #
    #     folder_name = "Waller/wallpapers"
    #     image_uris = []
    #
    #     projection = [MediaStoreImages._ID]
    #     query_uri = MediaStoreImages.EXTERNAL_CONTENT_URI
    #     sort_order = MediaStoreImages.DATE_ADDED + " DESC"
    #
    #     sdk = BuildVersion.SDK_INT
    #     log.warning(f"SDK VERSION = {sdk}")
    #
    #     # ----------------------------
    #     # ANDROID 10+ (API 29+)
    #     # ----------------------------
    #     if sdk >= 29:
    #         selection = MediaStoreImages.RELATIVE_PATH + " LIKE ?"
    #         selection_args = [f"%Pictures/{folder_name}/%"]
    #
    #         cursor = resolver.query(
    #             query_uri,
    #             projection,
    #             selection,
    #             selection_args,
    #             sort_order
    #         )
    #
    #         if cursor:
    #             try:
    #                 id_col = cursor.getColumnIndexOrThrow(MediaStoreImages._ID)
    #                 while cursor.moveToNext():
    #                     image_id = cursor.getLong(id_col)
    #                     uri = ContentUris.withAppendedId(query_uri, image_id)
    #                     image_uris.append(str(uri))
    #             finally:
    #                 cursor.close()
    #
    #     # ----------------------------
    #     # FALLBACK (Android 9 and below OR empty)
    #     # ----------------------------
    #     if not image_uris:
    #         log.warning("Falling back to DATA path query")
    #
    #         selection = MediaStoreImages.DATA + " LIKE ?"
    #         selection_args = [f"%/Pictures/{folder_name}/%"]
    #
    #         cursor = resolver.query(
    #             query_uri,
    #             projection,
    #             selection,
    #             selection_args,
    #             sort_order
    #         )
    #
    #         if cursor:
    #             try:
    #                 id_col = cursor.getColumnIndexOrThrow(MediaStoreImages._ID)
    #                 while cursor.moveToNext():
    #                     image_id = cursor.getLong(id_col)
    #                     uri = ContentUris.withAppendedId(query_uri, image_id)
    #                     image_uris.append(str(uri))
    #             finally:
    #                 cursor.close()
    #
    #     log.warning(f"FOUND {len(image_uris)} IMAGES")
    #     return image_uris

    def load_saved(self):
        # peek = [str(p) for p in self.wallpapers_dir.glob("*") if True]
        # print("Peek:", peek,self.wallpapers_dir)
        self.wallpapers = [
            str(p) for p in self.wallpapers_dir.glob("*")
            if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        ]

        # print("Loaded wallpapers:", len(self.wallpapers))
        self.myconfig.set_wallpapers(self.wallpapers)
        self.update_thumbnails_method(self.wallpapers)

        # Clock.schedule_once(self.fetch_recovered_images,2)


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
