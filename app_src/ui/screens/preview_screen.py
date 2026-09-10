from kivymd.uix.floatlayout import MDFloatLayout

from kivy.metrics import dp
from kivymd.uix.button import MDIconButton

from kivy.core.window import Window
from kivymd.uix.screen import MDScreen

from kivy.uix.floatlayout import FloatLayout
from ui.widgets.layouts import MyMDScreen
from kivy.properties import ListProperty, StringProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.scatterlayout import ScatterLayout
from utils.constants import _rgba


class MyImage(AsyncImage):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.test)
    def test(self, instance, value):
        print("on_pos: ", value)

class MyScatter(ScatterLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_rotation=False
        self.min_scale = 1
        self.pos=(0,0)

        with self.canvas.before:
            Color(*_rgba(26, 27, 27))
            self.rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        # Manually update the rectangle coordinates when the widget resizes
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_transform(self, instance, value):
        super().on_transform(instance, value)

        # Prevent scaling smaller than the screen
        if self.scale < self.min_scale:
            self.scale = self.min_scale

        # Constrain translation so the image doesn't drag completely off-screen
        parent = self.parent
        if not parent:
            return
        min_x = parent.width - (self.width * self.scale)

        min_y = parent.height - (self.height * self.scale)

        # Clamp position within bounds
        x = max(min_x, min(self.x, 0))
        y = max(min_y, min(self.y, 0))

        # Center if smaller than the screen on an axis
        # if self.width * self.scale < parent.width:
        #     x = (parent.width - (self.width * self.scale)) / 2
        # if self.height * self.scale < parent.height:
        #     y = (parent.height - (self.height * self.scale)) / 2

        self.pos = (x, y)


class MyBoxLayout(BoxLayout):
    background_color = ListProperty([1,0,0,1])
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(*self.background_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        # Manually update the rectangle coordinates when the widget resizes
        self.rect.pos = self.pos
        self.rect.size = self.size


class PreviewScreen(MyMDScreen):
    abs_img_path=StringProperty("/data/user/0/org.wally.waller/files/wallpapers/486306-1920x1080-desktop-full-hd-blade-runner-2049-background-image.jpg")
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name="preview"
        root = MDFloatLayout()
        self.btn_close = MDIconButton(
            icon="close",
            style="outlined",
            size=(dp(200), dp(200)),
            pos_hint={'x': .025, 'top': .98},
            # pos_hint={'center_x': .5, 'center_y': .5},
            theme_text_color='Custom',
            text_color=[1, 1, 1, .9],
            on_release=lambda *_: self.handle_going_back(),
            md_bg_color=[.1, .1, .1, 1],
            theme_bg_color='Custom'
        )
        self.save_btn = MDIconButton(
            icon="check",
            style="outlined",
            size=(dp(200), dp(200)),
            pos_hint={'x': .85, 'top': .98},
            # pos_hint={'center_x': .5, 'center_y': .5},
            theme_text_color='Custom',
            text_color=[1, 1, 1, .9],
            on_release=lambda *_: self.handle_confirm_selection(),
            md_bg_color=[.1, .1, .1, 1],
            theme_bg_color='Custom'
        )
        self.scatter = MyScatter(
            size_hint=(None, None),
            auto_bring_to_front=0

        )  # ,pos_hint={"center_x":0.01, "center_y":0.5})
        # image = MyBoxLayout(size_hint=(1,1),background_color=[1,0,0.5,1])
        self.image_widget = MyImage(
            source=self.abs_img_path,
            fit_mode="cover",
            keep_ratio=True,
            size_hint=(None, None)
        )
        # self.bind(size=lambda _, v: setattr(self.image_widget, 'size', v))
        # self.bind(size=lambda _,v: setattr(scatter,'size',v),pos=lambda _,v: setattr(scatter,'pos',v))

        self._pending_restore = None
        self.image_widget.bind(texture=self.update_cover_size)
        Window.bind(size=self.update_cover_size)

        self.scatter.add_widget(self.image_widget)
        root.add_widget(self.scatter)
        root.add_widget(self.btn_close)
        root.add_widget(self.save_btn)
        self.update_cover_size()
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.scatter.scale = self.scatter.min_scale
        self.image_widget.source=self.abs_img_path
        try:
            from utils.database import ImageDatabase
            self._pending_restore = ImageDatabase().get_preview_props(self.abs_img_path)
        except Exception as error_reading_preview_props:
            print(f"Failed to read preview props: {error_reading_preview_props}")
            self._pending_restore = None
        print(f"self.abs_img_path:{self.abs_img_path}")
        self.hide_system_ui()
        self.update_cover_size()

    def handle_going_back(self, *_):
        self.show_system_ui()
        self.manager.go_to_fullscreen()

    def handle_confirm_selection(self, *_):
        info = self._preview_crop_info()
        if not info:
            return
        box, viewport = info
        import threading
        from ui.widgets.layouts import LoadingLayout
        spinner_layout = LoadingLayout()
        state = {"ok": False}

        def finish(_):
            spinner_layout.remove()
            if state["ok"]:
                self.handle_going_back()

        def do_save():
            try:
                from utils.image_operations import crop_and_save_region
                crop_and_save_region(self.abs_img_path, box)
                from utils.database import ImageDatabase
                ImageDatabase().set_preview_props(
                    self.abs_img_path, viewport["scale"], viewport["cx"], viewport["cy"]
                )
                state["ok"] = True
            except Exception as error_saving_selected_wallpaper:
                print(f"Failed to save selected wallpaper: {error_saving_selected_wallpaper}")
            from kivy.clock import Clock
            Clock.schedule_once(finish)

        threading.Thread(target=do_save, daemon=True).start()



    def _preview_crop_info(self):
        if not self.image_widget.texture:
            return None
        from utils.image_operations import compute_preview_crop
        win_w, win_h = Window.size
        return compute_preview_crop(
            (win_w, win_h),
            self.image_widget.size,
            (self.image_widget.texture.width, self.image_widget.texture.height),
            self.scatter.scale,
            self.scatter.pos,
        )

    def update_cover_size(self, *args):
        if not self.image_widget.texture:
            return

        win_w, win_h = Window.size
        tex_w = self.image_widget.texture.width
        tex_h = self.image_widget.texture.height

        if win_h == 0 or tex_h == 0:
            return

        win_aspect = win_w / win_h
        tex_aspect = tex_w / tex_h

        # COVER LOGIC: Force the image to cover the screen entirely
        if tex_aspect > win_aspect:
            new_h = win_h
            new_w = win_h * tex_aspect
        else:
            new_w = win_w
            new_h = win_w / tex_aspect

        self.image_widget.size = (new_w, new_h)
        self.scatter.size = (new_w, new_h)

        # Center the scatter initially inside the window
        self.scatter.pos = (
            (win_w - new_w) / 2,
            (win_h - new_h) / 2
        )

        pending = self._pending_restore
        self._pending_restore = None
        if pending and pending.get("scale") and pending.get("cx") is not None and pending.get("cy") is not None:
            self.scatter.scale = pending["scale"]
            self.scatter.pos = (
                win_w / 2 - self.scatter.scale * (pending["cx"] * new_w),
                win_h / 2 - self.scatter.scale * (pending["cy"] * new_h),
            )
