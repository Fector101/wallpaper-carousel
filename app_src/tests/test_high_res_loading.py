"""Guards for the preview screen's "Loading HD" indicator.

The preview shows the scaled-down texture immediately and swaps in the full
resolution original whenever `Loader` finishes decoding it. That gap is invisible
to the user - a blurry wallpaper with no sign that a sharp one is seconds away - so
`HighResLoadingBadge` fills it.

What is easy to get wrong here, and what these tests pin down:

* The indicator must not block. `LoadingLayout` is a full-screen scrim with
  `disabled = True`; panning and zooming the blurry preview has to keep working.
* A cached or quick decode must not flash a spinner, so the show is delayed
  (hence asserting on the delay, not just that something was scheduled).
* Every path has to take the spinner down again: the texture arriving, a decode that
  produced nothing, and leaving the screen mid-load. A badge stuck on screen is worse
  than no badge.
* `SpinningArcWidget` used to schedule a 60fps interval in `__init__` and never cancel
  it, so every loading overlay ever created left a clock callback running for the life
  of the process. The tests below are as much about that leak as about the badge.
"""

import sys
import tempfile
from pathlib import Path
from unittest import mock

import image_samples
import pytest

APP_SRC = Path(__file__).resolve().parent.parent
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

from kivy.metrics import dp  # noqa: E402
from kivy.properties import StringProperty  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402

from ui.screens import preview_screen as preview_module  # noqa: E402
from ui.widgets import layouts as layouts_module  # noqa: E402
from ui.widgets.layouts import LoadingLayout, SpinningArcWidget  # noqa: E402
from ui.widgets.loading import HighResLoadingBadge  # noqa: E402
from utils.constants import theme_colors  # noqa: E402

FONT_DIR = APP_SRC / "assets" / "fonts" / "Roboto_Mono" / "static"

#: A real, decodable wallpaper. ``format_widget`` reads the header before it asks the
#: loader for anything, so the path this module used to hardcode (never on disk) would
#: make every badge test pass for the wrong reason: the load gets skipped and there is
#: nothing left to assert about the badge.
WALLPAPER = image_samples.write_png(Path(tempfile.mkdtemp()) / "example.png")


@pytest.fixture(scope="module", autouse=True)
def _kivymd_app():
    """KivyMD refuses to instantiate any widget without a running MDApp, and the app's
    labels use the custom font, which main.py registers at import time.

    `device_theme` mirrors the real app: it is the property the badge binds, and
    `_sync_theme_colors` pushes it into the `theme_colors` singleton before any widget
    handler runs (see the theme priming note in `.opencode/facts`).
    """
    from kivy.app import App
    from kivy.core.text import LabelBase
    from kivymd.app import MDApp

    if "RobotoMono" not in LabelBase._fonts:
        LabelBase.register(
            name="RobotoMono",
            fn_regular=str(FONT_DIR / "RobotoMono-Regular.ttf"),
            fn_italic=str(FONT_DIR / "RobotoMono-Italic.ttf"),
            fn_bold=str(FONT_DIR / "RobotoMono-Bold.ttf"),
        )

    class _App(MDApp):
        device_theme = StringProperty("dark")

        def _sync_theme_colors(self, *_args):
            theme_colors.theme = self.device_theme

        def build(self):
            return None

    app = _App()
    previous = App._running_app
    App._running_app = app
    app.bind(device_theme=app._sync_theme_colors)
    app._sync_theme_colors()
    yield app
    App._running_app = previous


@pytest.fixture(autouse=True)
def _reset_theme(_kivymd_app):
    """Other test files flip the shared `theme_colors` singleton, so start from dark every
    time and leave it there, otherwise these tests depend on the file order."""
    _kivymd_app.device_theme = "dark"
    theme_colors.theme = "dark"
    yield
    _kivymd_app.device_theme = "dark"


def _host():
    return Widget()


def _badge():
    return HighResLoadingBadge()


def _screen(**attrs):
    """A PreviewScreen without running __init__ (see test_preview_how_to._preview)."""
    screen = preview_module.PreviewScreen.__new__(preview_module.PreviewScreen)
    screen.built_ui = True
    screen.abs_img_path = attrs.pop("abs_img_path", WALLPAPER)
    screen.image_widget = mock.MagicMock()
    screen.proxy = None
    screen.how_to_modal = None
    screen.high_res_badge = mock.MagicMock()
    screen.hide_system_ui = mock.MagicMock()
    screen.set_image_data = mock.MagicMock()
    for key, value in attrs.items():
        setattr(screen, key, value)
    return screen


def _proxy(loaded, texture=mock.sentinel.sharp):
    proxy = mock.MagicMock()
    proxy.loaded = loaded
    proxy.image.texture = texture
    return proxy


def _fake_loader(monkeypatch, proxy):
    """`format_widget` imports Loader inside the function, so the module attribute is
    what has to be swapped."""
    loader = mock.MagicMock()
    loader.image.return_value = proxy
    monkeypatch.setattr("kivy.loader.Loader", loader)
    return loader


def _fake_clock(monkeypatch, module):
    clock = mock.MagicMock()
    monkeypatch.setattr(module, "Clock", clock)
    return clock


# --- the spinner underneath it ---------------------------------------------------

def test_a_new_arc_is_not_already_spinning():
    """The old widget scheduled its 60fps interval in __init__ and nothing ever cancelled
    it, so every overlay the app ever showed left a callback running until the process
    died. Rotation is now the caller's job."""
    arc = SpinningArcWidget()

    assert arc.spinning is False


def test_the_rotation_starts_on_request_and_stops_again(monkeypatch):
    clock = _fake_clock(monkeypatch, layouts_module)
    arc = SpinningArcWidget()

    arc.start()
    arc.start()  # a second show must not stack a second rotation

    assert arc.spinning is True
    assert clock.schedule_interval.call_count == 1

    arc.stop()
    arc.stop()  # and hiding something already hidden must not blow up

    assert arc.spinning is False
    clock.schedule_interval.return_value.cancel.assert_called_once()


def test_an_arc_that_lost_its_parent_stops_itself():
    """Belt and braces for any future caller who removes the arc without stopping it:
    the rotation checks on every tick instead of trusting the caller."""
    host = _host()
    arc = SpinningArcWidget()
    host.add_widget(arc)
    arc.start()

    host.remove_widget(arc)
    arc.update_arc(0.016)

    assert arc.spinning is False


def test_the_arc_keeps_the_look_the_loading_overlays_already_had():
    """The five `LoadingLayout` call sites pass nothing, so the defaults have to stay
    exactly as they were."""
    arc = SpinningArcWidget()
    arc._update_origin()

    assert list(arc.size) == [100, 100]
    assert arc.radius == 40
    assert arc.line_width == 4
    assert arc.arc.width == 4
    assert arc._arc_tuple == (arc.center_x, arc.center_y, 40, 0, 270)


def test_a_smaller_arc_is_a_mini_spinner():
    """`Line.circle` reads back as None until the instruction has been built by the GL
    backend, so the geometry is checked where it is computed."""
    arc = SpinningArcWidget(radius=dp(6), line_width=dp(2), size=(dp(18), dp(18)))

    assert list(arc.size) == [dp(18), dp(18)]
    assert arc._arc_tuple == (arc.center_x, arc.center_y, dp(6), 0, 270)
    assert arc.arc.width == dp(2)


def test_the_arc_can_be_repainted():
    """The colour used to be baked in at construction, so a theme change left the spinner
    spinning in the old theme's colour."""
    arc = SpinningArcWidget()

    arc.set_color([0, 1, 0, 1])

    assert list(arc.color_instr.rgba) == [0, 1, 0, 1]


def test_removing_a_loading_overlay_stops_its_spinner():
    """`LoadingLayout.remove()` is how every loading overlay in the app is dismissed, so
    this is where the leak had to be closed."""
    layout = LoadingLayout()

    layout.remove()

    assert layout.spinner.spinning is False


# --- the badge itself ------------------------------------------------------------

def test_the_badge_says_loading_hd():
    assert _badge().label.text == "Loading HD"


def test_the_badge_is_invisible_while_there_is_nothing_to_report():
    """It stays in the tree for the whole visit instead of being added and removed per
    load, so its pill background would otherwise sit over the preview permanently."""
    badge = _badge()

    assert badge.opacity == 0


def test_showing_the_badge_spins_and_hiding_it_stops():
    badge = _badge()

    badge.show()

    assert badge.spinner.spinning is True
    assert badge.opacity == 1

    badge.hide()

    assert badge.spinner.spinning is False
    assert badge.opacity == 0


def test_showing_and_hiding_repeatedly_is_safe():
    """`format_widget` runs again on every re-entry to the preview, and the badge is
    shown and hidden from independent paths, so both have to tolerate repeats."""
    badge = _badge()

    badge.show()
    badge.hide()
    badge.hide()
    badge.show()

    assert badge.spinner.spinning is True

    badge.hide()

    assert badge.spinner.spinning is False


def test_the_badge_does_not_swallow_touches():
    """It sits on top of the image, so if it consumed touches the user could not pan or
    zoom the preview while a sharp texture was on its way."""
    badge = _badge()
    badge.size = (dp(140), dp(32))
    badge.pos = (0, 0)
    touch = mock.MagicMock()
    touch.is_mouse_scrolling = False
    touch.ud = {}
    touch.grab_current = None
    touch.x, touch.y = badge.center
    touch.pos = badge.center
    assert badge.collide_point(*touch.pos) is True

    # Kivy reports "not consumed" as a falsy return, not necessarily False.
    assert not badge.on_touch_down(touch)
    assert not badge.on_touch_up(touch)


def test_the_badge_wraps_its_contents():
    """A pill that clipped its label, or a spinner that spilled out of it, would look
    broken on a device and not in any unit test.

    `Clock.tick()` is what gives the label a measured texture to size the pill around;
    it is safe in this file because nothing here starts a real loader (the proxies are
    fakes), which is the reason the how-to tests avoid ticking.
    """
    from kivy.clock import Clock

    badge = _badge()
    host = _host()
    host.size = (dp(360), dp(800))
    host.add_widget(badge)
    Clock.tick()
    badge.do_layout()

    assert badge.label.texture_size[0] > 0
    assert badge.width > badge.label.width
    assert badge.height >= dp(32)
    assert badge.spinner.x >= 0
    assert badge.label.right <= badge.width
    assert badge.spinner.top <= badge.height


def test_the_badge_is_a_finger_print_not_a_full_screen_block():
    badge = _badge()

    assert badge.disabled is False
    assert list(badge.size_hint) == [None, None]  # adaptive, never over the whole image


# --- theming ---------------------------------------------------------------------

def test_badge_colours_come_from_the_theme():
    badge = _badge()

    assert list(badge.md_bg_color) == list(theme_colors.BG_CARD)
    assert list(badge.label.text_color) == list(theme_colors.TEXT_PRIMARY)
    assert list(badge.spinner.color_instr.rgba) == list(theme_colors.PRIMARY)


def test_light_mode_recolours_the_badge_in_place(_kivymd_app):
    """The badge is built once and reused for every preview, so a theme change has to
    repaint it rather than rebuild it."""
    badge = _badge()

    _kivymd_app.device_theme = "light"
    try:
        assert badge.md_bg_color == [1.0, 1.0, 1.0, 1.0]
        assert badge.label.text_color == [0.0, 0.0, 0.0, 1.0]
        assert list(badge.spinner.color_instr.rgba) == list(theme_colors.PRIMARY)
    finally:
        _kivymd_app.device_theme = "dark"


def test_the_badge_is_themed_at_construction():
    """`device_theme` is still "dark" when the screens are built and only changes at the
    first 1s theme poll, so a widget that only binds would stay on its construction
    colours until the user changed the theme."""
    badge = _badge()

    assert list(badge.md_bg_color) == list(theme_colors.BG_CARD)
    assert list(badge.label.text_color) == list(theme_colors.TEXT_PRIMARY)


# --- a slow decode shows it ------------------------------------------------------

def test_a_cached_decode_never_shows_the_badge(monkeypatch):
    """The common case on a revisit: the loader already has it, and a spinner for a
    frame would be a flicker, not information."""
    proxy = _proxy(loaded=True)
    _fake_loader(monkeypatch, proxy)
    screen = _screen()

    screen.format_widget()

    assert screen.image_widget.texture is proxy.image.texture
    # Loaded means the wait is already over: never up, and taken straight back down.
    assert screen.high_res_badge.show.call_count == 0
    assert screen.high_res_badge.hide.call_count == 1


def test_a_pending_decode_shows_the_badge_immediately(monkeypatch):
    """No grace period: the badge goes up as soon as the sharp texture is known to be
    missing, so nothing waits on a Clock to put it on screen."""
    clock = _fake_clock(monkeypatch, preview_module)
    proxy = _proxy(loaded=False)
    _fake_loader(monkeypatch, proxy)
    screen = _screen()

    screen.format_widget()

    screen.high_res_badge.show.assert_called_once()
    clock.schedule_once.assert_not_called()


def test_the_screen_records_whether_the_sharp_texture_arrived(monkeypatch):
    """`_high_res_loaded` was set on arrival but never read by anything, so nothing
    could tell a loaded preview from a pending one."""
    monkeypatch.setattr(preview_module, "Clock", mock.MagicMock())
    proxy = _proxy(loaded=False)
    _fake_loader(monkeypatch, proxy)
    screen = _screen()

    screen.format_widget()
    assert screen.image_widget._high_res_loaded is False

    screen.apply_proxy_image_texture(_proxy(loaded=True))

    assert screen.image_widget._high_res_loaded is True


def test_re_entering_the_preview_restarts_the_badge(monkeypatch):
    """`on_enter` calls format_widget() again on every visit. There is no pending event
    left over from the last one to fire against the new load."""
    clock = _fake_clock(monkeypatch, preview_module)
    proxy = _proxy(loaded=False)
    _fake_loader(monkeypatch, proxy)
    screen = _screen()

    screen.format_widget()
    screen.format_widget()

    assert screen.high_res_badge.show.call_count == 2
    clock.schedule_once.assert_not_called()


# --- every path takes it down again ------------------------------------------------

def test_the_badge_goes_away_when_the_sharp_texture_arrives(monkeypatch):
    monkeypatch.setattr(preview_module, "Clock", mock.MagicMock())
    screen = _screen()

    screen.apply_proxy_image_texture(_proxy(loaded=True))

    screen.high_res_badge.hide.assert_called_once()


def test_a_decode_that_produced_no_texture_still_takes_the_badge_down(monkeypatch):
    """A failed load must not leave a spinner running over a permanently blurry
    wallpaper, and it should say something in the log."""
    warning = mock.MagicMock()
    monkeypatch.setattr(preview_module, "app_logger", mock.MagicMock(warning=warning))
    screen = _screen()
    screen.image_widget._high_res_loaded = False

    screen.apply_proxy_image_texture(_proxy(loaded=True, texture=None))

    screen.high_res_badge.hide.assert_called_once()
    assert screen.image_widget._high_res_loaded is False
    warning.assert_called_once()
    assert screen.abs_img_path in warning.call_args[0][0]


def test_leaving_the_screen_mid_load_takes_the_badge_down(monkeypatch):
    monkeypatch.setattr(preview_module, "Clock", mock.MagicMock())
    screen = _screen()

    screen.on_leave()

    screen.high_res_badge.hide.assert_called_once()


def test_leaving_before_the_badge_exists_does_not_crash():
    """A back press can land before build_ui() has run, when there is no badge and no
    pending show to clean up."""
    screen = _screen(high_res_badge=None)

    screen.on_leave()


def test_a_loaded_preview_leaves_nothing_running(monkeypatch):
    """The end-to-end version of the two tests above: a load that completes while the
    screen is left behind nothing pending and nothing spinning."""
    clock = _fake_clock(monkeypatch, preview_module)
    proxy = _proxy(loaded=False)
    _fake_loader(monkeypatch, proxy)
    badge = _badge()
    screen = _screen(high_res_badge=badge)

    screen.format_widget()
    # Up for exactly as long as the sharp texture is missing.
    assert badge.opacity == 1
    assert badge.spinner.spinning is True

    screen.apply_proxy_image_texture(proxy)
    screen.on_leave()

    assert badge.opacity == 0
    assert badge.spinner.spinning is False


# --- it is part of the screen -------------------------------------------------------

def test_the_screen_owns_the_badge_and_does_not_build_it_eagerly():
    from ui.screens.preview_screen import PreviewScreen

    screen = PreviewScreen()

    assert screen.high_res_badge is None


def test_building_the_ui_puts_the_badge_over_the_image(monkeypatch):
    """Kivy inserts children at index 0 and draws them last, so the badge has to be added
    last to end up on top of the preview."""
    clock = _fake_clock(monkeypatch, preview_module)
    from ui.screens.preview_screen import PreviewScreen

    screen = PreviewScreen()
    screen._how_to_shown_this_session = True  # not what this test is about
    screen.set_image_data = mock.MagicMock()
    screen.build_ui(None)

    assert isinstance(screen.high_res_badge, HighResLoadingBadge)
    root = screen.screen_content.children[0]
    assert root.children[0] is screen.high_res_badge
    # Built hidden and idle. (A cached load has nothing to report, and with no
    # abs_img_path format_widget returns before it even asks the loader.)
    assert screen.high_res_badge.opacity == 0
    assert screen.high_res_badge.spinner.spinning is False


def test_the_badge_sits_where_it_does_not_cover_the_controls(monkeypatch):
    """Bottom centre: `btn_close` and `save_btn` own the top corners, and the badge is a
    pill that must stay clear of both."""
    _fake_clock(monkeypatch, preview_module)
    from ui.screens.preview_screen import PreviewScreen

    screen = PreviewScreen()
    screen._how_to_shown_this_session = True
    screen.set_image_data = mock.MagicMock()
    screen.build_ui(None)
    root = screen.screen_content.children[0]
    root.size = (dp(360), dp(800))
    root.do_layout()

    badge = screen.high_res_badge
    assert badge.x > 0
    assert badge.right < root.width
    assert badge.y > 0
    # The pill is nowhere near either control vertically.
    assert badge.top < screen.btn_close.y
    assert badge.top < screen.save_btn.y

def test_the_label_text_can_be_overridden():
    """`text` is a property, so a caller (or a future translation) changes the words and
    the pill resizes around them, rather than the property being a dead knob."""
    badge = _badge()

    badge.text = "Loading Full Size"

    assert badge.label.text == "Loading Full Size"
