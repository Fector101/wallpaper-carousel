from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.scatterlayout import ScatterLayout

from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.button import MDIconButton

from ui.widgets.layouts import MyMDScreen
from ui.widgets.loading import HighResLoadingBadge
from ui.widgets.modals import HowToPopUpModal, MyTextButton
from utils.config_manager import ConfigManager
from utils.constants import _rgba, theme_colors
from utils.logger import app_logger

my_config = ConfigManager()


class MyScatter(ScatterLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_rotation=False
        self.min_scale = 1
        self.pos=(0,0)

        with self.canvas.before:
            Color(*_rgba(26, 27, 27))
            self.rect = Rectangle(pos=self.pos, size=self.size)
            # This opaque background would otherwise stay the active colour for
            # everything drawn after the scatter in the frame.
            Color(1, 1, 1, 1)

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *_):
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

    def update_rect(self, *_):
        # Manually update the rectangle coordinates when the widget resizes
        self.rect.pos = self.pos
        self.rect.size = self.size

from kivy.clock import Clock

class PreviewScreen(MyMDScreen):
    scaled_down_img_texture=ObjectProperty(None, allownone=True)
    # abs_img_path=StringProperty("/data/user/0/org.wally.waller/files/wallpapers/2112956-3840x2160-desktop-4k-minimalist-background-image.jpg") # hot_reload
    # abs_img_path=StringProperty("/home/fabian/Pictures/1065154.jpg") # hot_reload
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
        self._how_to_shown_this_session = False
        self.how_to_modal = None
        self.high_res_badge = None
        # Deliberately not _maybe_show_how_to() here: it would spend the session flag
        # before build_ui has run, so the card would be shown over an empty screen and
        # the call at the end of build_ui would do nothing.
        # self.build_ui(None) # hot_reload
        # self.update_cover_size(None) # hot_reload
        # self._show_high_res_badge() # hot_reload


    def build_ui(self,_):
        self.set_image_data()
        # print("building ui")
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
        self.image_widget = AsyncImage(
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
        self.high_res_badge = HighResLoadingBadge(pos_hint={'center_x': .5, 'y': .05})
        # Added last: root draws children[0] last, and add_widget inserts at 0, so
        # this ends up on top of the image without disabling anything.
        root.add_widget(self.high_res_badge)
        self.add_widget(root)
        self.format_widget()
        self.image_widget.opacity=1
        # Last, so the card is built and shown over a screen that already has its
        # content, instead of one frame before it.
        self._maybe_show_how_to()

    def on_enter(self, *args):
        super().on_enter(*args)
        if not self.built_ui:
            Clock.schedule_once(self._timer_set)
        else:
            self.format_widget()

    def _maybe_show_how_to(self):
        """Once per app session, and never again once the user ticked the box.

        The screen outlives a single preview visit, so the flag lives here rather than
        in the modal, whose ``hide()`` also removes it from the widget tree. The card
        itself is built here too, so an opted-out user never pays for it.
        """
        if self._how_to_shown_this_session or self._how_to_modal_is_up():
            return
        self._how_to_shown_this_session = True
        if my_config.get_hide_preview_how_to():
            return
        if self.how_to_modal is None:
            self.how_to_modal = HowToPopUpModal()
        Clock.schedule_once(lambda *_: self.how_to_modal.show(self), 0)

    def _how_to_modal_is_up(self):
        """Whether the card is currently in the tree. It may not exist yet: a back
        press can leave the screen before the clock gets round to build_ui()."""
        return self.how_to_modal is not None and self.how_to_modal.parent is not None

    def _timer_set(self,_):
        Clock.schedule_once(self.build_ui)

    def on_leave(self, *args):
        if self._how_to_modal_is_up():
            self.how_to_modal.hide()
        # A preview visit can be left with the sharp texture still on its way.
        self._hide_high_res_badge()
        # hiding img widget and removing texture data to help avoid flickers on_enter
        self.image_widget.opacity = 0
        self.scaled_down_img_texture = None
        self.image_placement_data = None
        # resetting texture to call self.update_cover_size which is bound to texture to get it to reset scatter size & pos.
        self.image_widget.texture = None
        # Unbinding to avoid errors with large images
        if self.proxy: # hot_reload
            self.proxy.unbind(on_load=self.apply_proxy_image_texture)
            self.proxy=None

    def on_pre_enter(self, *args):
        self.set_scaled_down_texture()

    def set_scaled_down_texture(self):
        if self.image_widget is not None and self.scaled_down_img_texture:
            self.set_image_data()
            self.image_widget.texture = self.scaled_down_img_texture
            self.image_widget.opacity=1

    def format_widget(self, *_):
        if not self.abs_img_path: # safe hot reload
            return None

        from kivy.loader import Loader
        self.image_widget._high_res_loaded = False
        self.proxy = Loader.image(self.abs_img_path)
        if self.proxy.loaded:
            self.apply_proxy_image_texture(self.proxy)
        else:
            # Straight away, and taken down by apply_proxy_image_texture (or on_leave),
            # so the badge is up for exactly as long as the sharp texture is missing.
            # A cached load never shows it at all: nothing gets rendered between that
            # call and the hide below, because Kivy only draws on frame ticks.
            self._show_high_res_badge()
        self.proxy.bind(
            on_load=self.apply_proxy_image_texture
        )

        self.hide_system_ui()
        return None

    def _show_high_res_badge(self):
        """Raises the badge. Optional like the badge itself: a hot-reloaded instance
        may predate it, and format_widget() can run against a bare screen."""
        badge = getattr(self, "high_res_badge", None)
        if badge is not None:
            badge.show()

    def _hide_high_res_badge(self):
        """Lowers the badge. Optional: a back press can land before build_ui() has even
        run, and getattr rather than a plain attribute read because an instance from
        before this existed has none (hot reload)."""
        badge = getattr(self, "high_res_badge", None)
        if badge is not None:
            badge.hide()

    def handle_going_back(self, *_):
        # Both this screen and the how-to card listen for the back key while the card is
        # up, and Kivy calls every bound handler, so leave the navigation to the card,
        # which hides itself on the same press.
        if self._how_to_modal_is_up():
            return
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
                app_logger.error(f"Failed to save selected wallpaper: {error_saving_selected_wallpaper}")
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

    def update_cover_size(self, *_):
        win_w, win_h = Window.size
        if not self.image_widget.texture:
            self.scatter.scale = self.scatter.min_scale
            self.scatter.pos = (
                (win_w - self.scatter.width) / 2,
                (win_h - self.scatter.height) / 2,
            )

            app_logger.debug("ran reset scatter size")
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
        app_logger.debug(f"update_cover_size: {pending}")

    def set_image_data(self):
        try:
            from utils.database import ImageDatabase
            self.image_placement_data = ImageDatabase().get_preview_props(self.abs_img_path)
        except Exception as error_reading_preview_props:
            app_logger.error(f"Failed to read preview props: {error_reading_preview_props}")
            self.image_placement_data = None
        app_logger.debug(f"got image data: {self.image_placement_data}")

    def apply_proxy_image_texture(self,proxy_image):
        # Whatever happened, the wait is over - hiding unconditionally keeps a failed
        # decode from stranding the spinner on screen.
        self._hide_high_res_badge()
        if proxy_image.image.texture:
            self.image_widget.texture = proxy_image.image.texture
            self.image_widget._high_res_loaded = True
            self.image_widget.source = self.abs_img_path
        else:
            app_logger.warning(
                f"High resolution image loaded without a texture: {self.abs_img_path}"
            )


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
