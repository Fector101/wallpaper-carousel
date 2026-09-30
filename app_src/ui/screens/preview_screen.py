import traceback

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.scatterlayout import ScatterLayout

from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.button import MDIconButton

from ui.widgets.modals import MyTextButton
from ui.widgets.layouts import MyMDScreen
from utils.constants import _rgba, theme_colors


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


from kivy.clock import Clock


class PreviewScreen(MyMDScreen):
    scaled_down_img_texture=ObjectProperty(None, allownone=True)
    # abs_img_path=StringProperty("/data/user/0/org.wally.waller/files/wallpapers/486306-1920x1080-desktop-full-hd-blade-runner-2049-background-image.jpg")
    abs_img_path=StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.proxy = None
        self.image_placement_data = None
        self.scatter = None
        self.image_widget = None
        self.save_btn = None
        self.btn_close = None
        self._preview_entry_texture = None
        self._preview_entry_source = None
        self.name="preview"
        self.built_ui = False

    def build_ui(self,_):
        self.set_image_data()
        print("building ui")
        self.built_ui = True
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
        self.save_btn = MyTextButton(
            text="save",
            pos_hint={'x': .77, 'top': .98},
            on_release=lambda *_: self.handle_confirm_selection(),
            theme_bg_color = "Custom",
            md_bg_color = theme_colors.BUTTON_ACCENT_BG,
            text_color = theme_colors.BUTTON_ACCENT_TEXT,
            adaptive_size = True,
            size_padding = dp(20)
        )
        self.scatter = MyScatter(
            size_hint=(None, None),
            auto_bring_to_front=0

        )  # ,pos_hint={"center_x":0.01, "center_y":0.5})
        # image = MyBoxLayout(size_hint=(1,1),background_color=[1,0,0.5,1])
        self.image_widget = MyImage(
            source="",# <--- never set directly
            fit_mode="cover",
            size_hint=(None, None)
        )
        self.image_widget.opacity=0
        # self.bind(size=lambda _, v: setattr(self.image_widget, 'size', v))
        # self.bind(size=lambda _,v: setattr(scatter,'size',v),pos=lambda _,v: setattr(scatter,'pos',v))

        self.image_widget.bind(texture=self.update_cover_size)
        if self.scaled_down_img_texture is not None: # safe for hot reload
            self.image_widget.texture = self.scaled_down_img_texture
        # Window.bind(size=self.update_cover_size)

        self.scatter.add_widget(self.image_widget)
        root.add_widget(self.scatter)
        root.add_widget(self.btn_close)
        root.add_widget(self.save_btn)
        self.add_widget(root)
        self.format_widget()
        self.image_widget.opacity=1

    def on_enter(self, *args):
        super().on_enter(*args)
        if not self.built_ui:
            Clock.schedule_once(self._timer_set)
        else:
            self.format_widget()

    def _timer_set(self,_):
        Clock.schedule_once(self.build_ui)

    def on_leave(self, *args):
        self.image_widget.opacity = 0
        self.scaled_down_img_texture = None
        self.image_placement_data = None
        self.image_widget.texture = None

    def on_pre_enter(self, *args):
        self.set_scaled_down_texture()

    def set_scaled_down_texture(self):
        if self.image_widget is not None and self.scaled_down_img_texture:
            self.set_image_data()
            self.image_widget.texture = self.scaled_down_img_texture
            self.image_widget.opacity=1


    def format_widget(self, *args):
        if not self.abs_img_path: # safe hot reload
            return None

        from kivy.loader import Loader
        proxy = Loader.image(self.abs_img_path)
        if proxy.loaded:
            self.apply_proxy_image_texture(proxy)
        proxy.bind(
            on_load=self.apply_proxy_image_texture
        )

        self.hide_system_ui()

    def handle_going_back(self, *_):
        self.show_system_ui()
        if self.manager is not None:
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
                _save_crop_and_props(
                    self.abs_img_path, box, viewport["scale"], viewport["cx"], viewport["cy"]
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
        win_w, win_h = Window.size
        if not self.image_widget.texture:
            self.scatter.scale = self.scatter.min_scale
            self.scatter.pos = (
                (win_w - self.scatter.width) / 2,
                (win_h - self.scatter.height) / 2,
            )

            print("ran reset scatter size")
            return
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

        pending = self.image_placement_data
        if pending and pending.get("scale") and pending.get("cx") is not None and pending.get("cy") is not None:
            # self.image_placement_data = None
            self.scatter.scale = pending["scale"]
            self.scatter.pos = (
                win_w / 2 - self.scatter.scale * (pending["cx"] * new_w),
                win_h / 2 - self.scatter.scale * (pending["cy"] * new_h),
            )
        print(f"update_cover_size: {pending}")

    def set_image_data(self):
        try:
            from utils.database import ImageDatabase
            self.image_placement_data = ImageDatabase().get_preview_props(self.abs_img_path)
        except Exception as error_reading_preview_props:
            print(f"Failed to read preview props: {error_reading_preview_props}")
            self.image_placement_data = None
        print(f"got image data: {self.image_placement_data}")

    def apply_proxy_image_texture(self,proxy_image):
        if proxy_image.image.texture:
            self.image_widget.texture = proxy_image.image.texture
            self.image_widget._high_res_loaded = True
            self.image_widget.source = self.abs_img_path


def _save_crop_and_props(abs_img_path, box, scale, cx, cy):
    """Crop the preview image and persist its viewport as one unit.

    The on-disk crop file doubles as the "user selected a crop" marker (see
    ``utils.helper.resolve_user_selected_crop``), so it must only change when
    the DB write also succeeds. The pre-existing crop, if any, is preserved so
    that a failed persistence restores the previous crop (or removes the new
    one when nothing was there before), leaving preview properties unchanged
    and keeping the confirm action in the preview until both succeed.
    """
    import os
    import pathlib
    from utils import helper
    from utils.image_operations import crop_and_save_region
    from utils.database import ImageDatabase

    crop_path = pathlib.Path(helper.crop_path_for(abs_img_path))
    had_previous = crop_path.exists()
    previous_content = crop_path.read_bytes() if had_previous else None

    crop_and_save_region(abs_img_path, box)
    persisted = ImageDatabase().set_preview_props(abs_img_path, scale, cx, cy)
    if not persisted:
        if had_previous and previous_content is not None:
            crop_path.write_bytes(previous_content)
        else:
            try:
                os.remove(str(crop_path))
            except FileNotFoundError:
                pass
        raise Exception("Failed to persist preview viewport")


