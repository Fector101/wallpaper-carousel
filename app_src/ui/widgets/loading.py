from kivy.metrics import dp
from kivy.properties import StringProperty

from kivymd.uix.label import MDLabel

from ui.widgets.layouts import Row, SpinningArcWidget
from utils.constants import theme_colors
from utils.model import get_app


class HighResLoadingBadge(Row):
    """A small "Loading HD" pill for when a sharper image is still on its way.

    The preview screen shows the scaled-down texture straight away - the full screen
    hands over the slide texture it already has when navigating (`enter_preview_mode`)
    - and swaps in the full resolution original once `Loader` finishes decoding it.
    Without a sign of that, the user just sees a blurry wallpaper and no reason to
    wait for the sharp one.

    Deliberately **not** a `LoadingLayout`: that one is a full-screen scrim with
    `disabled = True`, meant to block the UI during something slow. Here the user
    should carry on panning and zooming the blurry preview, so this does neither
    disable itself nor consume touches.

    Built on the app's `Row` rather than an `MDRelativeLayout` because KivyMD 2.0's
    `MDRelativeLayout` has no `padding`, and a BoxLayout gives us the adaptive sizing
    for a pill that wraps its own contents.
    """

    text = StringProperty("Loading HD")

    def __init__(self, **kwargs):
        super().__init__(
            adaptive_width=True, adaptive_height=True,
            spacing=dp(9), padding=[dp(10), dp(10), dp(10), dp(10)],
            radius=dp(16), md_bg_color=theme_colors.BG_CARD,
            **kwargs,
        )
        self.app = get_app()
        self.label = MDLabel(
            text=self.text,
            theme_text_color="Custom", text_color=theme_colors.TEXT_PRIMARY,
            font_size=dp(15),
            adaptive_size=1,
            pos_hint={"center_y":0.5}
            # md_bg_color=[1,0,1,1]
        )
        self.bind(text=lambda _, value: setattr(self.label, "text", value))
        self.spinner = SpinningArcWidget(
            size_hint=(None, None), size=(dp(22), dp(22)),
            radius=dp(8), line_width=dp(2.5),
        )
        self.add_widget(self.spinner)
        self.add_widget(self.label)
        # It lives in the tree for the whole visit rather than being added and removed
        # per load, so it has to be invisible itself while there is nothing to report.
        self.opacity = 0

        self.app.bind(device_theme=self._apply_theme)
        # The screens are built before the first theme poll, so binding alone would
        # leave this on its construction colours until the theme changed underneath.
        self._apply_theme()

    def _apply_theme(self, *_):
        self.md_bg_color = theme_colors.BG_CARD
        self.label.text_color = theme_colors.TEXT_PRIMARY
        self.spinner.set_color(theme_colors.PRIMARY)

    def show(self, *_):
        """Idempotent, and safe to call when it was never shown. Stays up until the
        caller hides it - see `PreviewScreen.apply_proxy_image_texture`."""
        self.opacity = 1
        self.spinner.start()

    def hide(self, *_):
        """Idempotent, and safe to call when it was never shown."""
        self.spinner.stop()
        self.opacity = 0