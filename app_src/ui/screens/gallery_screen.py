import traceback
from pathlib import Path
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.recycleview import RecycleView
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.button import Button
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from plyer import filechooser

from utils.helper import FileOperation, get_or_create_thumbnail
from utils.config_manager import ConfigManager
from utils.helper import makeDownloadFolder

class GalleryScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name="thumbs"
        self.wallpapers=[]
        self.app_dir = Path(makeDownloadFolder())
        self.myconfig = ConfigManager()
        self.wallpapers_dir = self.app_dir / ".wallpapers"

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        layout.add_widget(Label(text="Wallpapers", size_hint_y=0.1, font_size="22sp"))

        self.rv = RecycleView(size_hint_y=0.8)
        grid = RecycleGridLayout(cols=3,
                                 spacing=5,
                                 default_size=(None, dp(120)),
                                 default_size_hint=(1, None),
                                 size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        self.rv.add_widget(grid)
        self.rv.layout_manager = grid
        self.rv.viewclass = "Thumb"
        layout.add_widget(self.rv)

        btns = BoxLayout(size_hint_y=0.1, spacing=10)
        btns.add_widget(Button(text="Add Images", on_release=self.open_filechooser))
        btns.add_widget(Button(text="Settings", on_release=lambda *_: setattr(self.manager, 'current', 'settings')))
        layout.add_widget(btns)
        self.add_widget(layout)

    def open_filechooser(self, *args):
        file_operation = FileOperation(self.update_thumbnails_method)
        from jnius import autoclass, cast

        def open_file_picker():
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.intent.action.OPEN_DOCUMENT')  # Use OPEN_DOCUMENT for permanent files

            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(autoclass('android.intent.category.OPENABLE'))
            intent.setType("image/*")  # Only show images

            # Start the activity and wait for a result
            # Note: You'll need to handle the result in your App class via bind
            PythonActivity.mActivity.startActivityForResult(intent, 1001)
        filechooser.open_file(on_selection=file_operation.copy_add, filters=["image"], multiple=True)

    def update_thumbnails_method(self,new_images):
        for img in new_images:
            if img not in self.wallpapers:
                self.wallpapers.append(img)
        data = []
        for i, path in enumerate(self.wallpapers):
            # Use a low-res thumbnail for the preview (fallback to original if thumbnail creation/availability fails)
            thumb = get_or_create_thumbnail(path, dest_dir=self.wallpapers_dir )
            print("Thumbnail for", path, "is", thumb)
            data.append({
                "source": thumb if thumb else path,
                "source_path": path,
                "on_release": lambda p=path, idx=i: self.open_fullscreen_for_image(p, idx)
            })
        print("Thumbnail data length:", len(data))
        self.rv.data = data

    def open_fullscreen_for_image(self, path, index):
        print(path, index)
        self.manager.open_image_in_full_screen(index)

    def load_saved(self):
        self.wallpapers = [
            str(p) for p in self.wallpapers_dir.glob("*")
            if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        ]
        print("Loaded wallpapers:", self.wallpapers)
        self.myconfig.set_wallpapers(self.wallpapers)
        self.update_thumbnails_method(self.wallpapers)